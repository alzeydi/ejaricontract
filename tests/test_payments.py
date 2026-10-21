"""Payment ledger tests: Ziina create/confirm, idempotency, one-time analytics report.

Ziina and Telegram are faked. The ledger runs on its in-memory fallback, or on
a real Postgres when TEST_DATABASE_URL is set.
Run with:  python3 -m pytest tests/ -q
"""
import os

import pytest

os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
os.environ.pop('DATABASE_URL', None)

import app as appmod  # noqa: E402


class FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class FakeZiina:
    """Stands in for requests.post/get against the Ziina API."""

    def __init__(self):
        self.intents = {}
        self.fail_create = None
        self.n = 0

    def post(self, url, json=None, headers=None, timeout=None):
        if self.fail_create:
            return self.fail_create
        self.n += 1
        iid = f'intent-{self.n:04d}'
        self.intents[iid] = {'id': iid, 'status': 'requires_payment_instrument', 'amount': json['amount']}
        return FakeResp(201, {'id': iid, 'embedded_url': 'https://pay.ziina.com/e/' + iid,
                              'redirect_url': 'https://pay.ziina.com/r/' + iid})

    def get(self, url, headers=None, timeout=None):
        iid = url.rsplit('/', 1)[-1]
        if iid not in self.intents:
            return FakeResp(404, {'message': 'not found'})
        return FakeResp(200, dict(self.intents[iid], customer_email='buyer@example.com'))

    def pay(self, iid):
        self.intents[iid]['status'] = 'completed'


@pytest.fixture
def ziina(monkeypatch):
    fake = FakeZiina()
    monkeypatch.setattr(appmod.req_lib, 'post', fake.post)
    monkeypatch.setattr(appmod.req_lib, 'get', fake.get)
    test_db = os.environ.get('TEST_DATABASE_URL')  # e.g. postgresql://pg@localhost:55432/postgres
    monkeypatch.setattr(appmod, '_DB_URL', test_db or '')
    if test_db:
        appmod._init_db()
        conn = appmod._get_conn()
        with conn, conn.cursor() as cur:
            cur.execute('TRUNCATE payments')
        conn.close()
    appmod._mem_payments.clear()
    appmod._last_alert.clear()
    return fake


@pytest.fixture
def telegram(monkeypatch):
    sent = []
    monkeypatch.setattr(appmod, '_send_telegram', sent.append)
    monkeypatch.setattr(appmod, 'trustpilot_invite', lambda *a, **k: True)
    return sent


@pytest.fixture
def client():
    return appmod.app.test_client()


def _create(client, path='/create-payment'):
    r = client.post(path, json={})
    assert r.status_code == 200, r.get_json()
    return r.get_json()['intent_id']


def test_contract_success_url_carries_intent_id(client, ziina, monkeypatch, telegram):
    seen = {}
    real_post = ziina.post

    def spy(url, json=None, **kw):
        seen.update(json)
        return real_post(url, json=json, **kw)
    monkeypatch.setattr(appmod.req_lib, 'post', spy)
    _create(client)
    assert seen['success_url'].endswith('/?paid=1&intent_id={PAYMENT_INTENT_ID}')
    assert seen['amount'] == appmod.CONTRACT_PRICE_FILS


def test_unpaid_intent_is_not_reported(client, ziina, telegram):
    iid = _create(client)
    r = client.post('/payment/confirm', json={'intent_id': iid, 'product': 'contract'}).get_json()
    assert r['paid'] is False
    assert telegram == []


def test_purchase_reported_exactly_once(client, ziina, telegram):
    iid = _create(client)
    ziina.pay(iid)
    first = client.post('/payment/confirm', json={'intent_id': iid, 'product': 'contract'}).get_json()
    assert first == {'paid': True, 'report': True, 'transaction_id': iid, 'product': 'contract',
                     'item_name': 'Ejari tenancy contract',
                     'value': appmod.CONTRACT_PRICE_FILS / 100, 'currency': 'AED'}
    for _ in range(3):  # reloads, second tab, verify-payment polling
        client.post('/verify-payment', json={'intent_id': iid})
        again = client.post('/payment/confirm', json={'intent_id': iid, 'product': 'contract'}).get_json()
        assert again['paid'] is True and again['report'] is False
    sales = [m for m in telegram if 'Contract sold' in m]
    assert len(sales) == 1


def test_webhook_and_redirect_notify_once(client, ziina, telegram):
    iid = _create(client)
    ziina.pay(iid)
    client.post('/webhook/ziina', json={'event': 'payment_intent.status.updated',
                                        'data': {'id': iid, 'status': 'completed'}})
    assert client.post('/verify-payment', json={'intent_id': iid}).get_json()['paid'] is True
    assert len([m for m in telegram if 'Contract sold' in m]) == 1


def test_webhook_body_is_not_trusted(client, ziina, telegram):
    iid = _create(client)  # never paid at Ziina
    client.post('/webhook/ziina', json={'event': 'payment_intent.status.updated',
                                        'data': {'id': iid, 'status': 'completed'}})
    assert client.post('/verify-payment', json={'intent_id': iid}).get_json()['paid'] is False


def test_contract_intent_cannot_unlock_lawyer(client, ziina, telegram):
    iid = _create(client)
    ziina.pay(iid)
    r = client.post('/legal-chat/verify-payment', json={'intent_id': iid}).get_json()
    assert r['paid'] is False
    assert any('product_mismatch' in m for m in telegram)


def test_legal_window_is_anchored_to_payment(client, ziina, telegram):
    iid = _create(client, '/legal-chat/create-payment')
    ziina.pay(iid)
    r1 = client.get(f'/legal-chat/payment-success?intent_id={iid}')
    assert f'unlocked=1&tid={iid}' in r1.headers['Location']
    until1 = client.get('/legal-chat/state').get_json()['paid_until']
    client.get(f'/legal-chat/payment-success?intent_id={iid}')  # refresh
    assert client.get('/legal-chat/state').get_json()['paid_until'] == until1
    assert len([m for m in telegram if 'Legal Chat unlocked' in m]) == 1


def test_amount_mismatch_is_rejected(client, ziina, telegram):
    iid = _create(client)
    ziina.intents[iid]['amount'] = 100
    ziina.pay(iid)
    assert client.post('/verify-payment', json={'intent_id': iid}).get_json()['paid'] is False
    assert any('amount_mismatch' in m for m in telegram)


def test_create_failure_alerts_without_leaking(client, ziina, telegram):
    ziina.fail_create = FakeResp(401, {'message': 'Unauthorized', 'secret': 'x'})
    r = client.post('/create-payment', json={})
    assert r.status_code == 502
    body = r.get_json()
    assert set(body) == {'error'} and 'Unauthorized' not in body['error']
    assert any('create_http' in m for m in telegram)
    client.post('/create-payment', json={})
    assert len([m for m in telegram if 'create_http' in m]) == 1  # throttled


def test_invalid_intent_id_never_hits_ziina(client, ziina, telegram):
    r = client.post('/payment/confirm', json={'intent_id': '../../x', 'product': 'contract'}).get_json()
    assert r == {'paid': False, 'status': 'invalid'}
