"""Generator tests: free extraction limits, watermarked preview, paid-only PDF.

Ziina and the OCR model are faked. Storage runs on the in-memory fallback, or
on a real Postgres when TEST_DATABASE_URL is set.
Run with:  python3 -m pytest tests/ -q
"""
import os

import pytest

os.environ.setdefault('ANTHROPIC_API_KEY', 'test')

import app as appmod  # noqa: E402
from test_payments import FakeZiina  # noqa: E402

CONTRACT = {'tenant_name': 'TEST TENANT', 'tenant_emirates_id': '784-1990-1234567-1',
            'annual_rent': '85000', 'contract_from': '01/11/2026', 'contract_to': '31/10/2027'}
DOC = {'label': 'TENANT_EMIRATES_ID', 'data': 'eA==', 'mime_type': 'image/png'}


@pytest.fixture
def env(monkeypatch):
    fake = FakeZiina()
    monkeypatch.setattr(appmod.req_lib, 'post', fake.post)
    monkeypatch.setattr(appmod.req_lib, 'get', fake.get)
    test_db = os.environ.get('TEST_DATABASE_URL')
    monkeypatch.setattr(appmod, '_DB_URL', test_db or '')
    if test_db:
        appmod._init_db()
        conn = appmod._get_conn()
        with conn, conn.cursor() as cur:
            cur.execute('TRUNCATE payments, extract_usage')
        conn.close()
    monkeypatch.setattr(appmod, '_send_telegram', lambda *_: None)
    monkeypatch.setattr(appmod, 'extract_one', lambda f: ({'tenant_name': 'TEST TENANT'}, (1000, 50)))
    monkeypatch.setattr(appmod, 'FREE_MODE', False)
    monkeypatch.setattr(appmod, 'TURNSTILE_SECRET', '')
    appmod._mem_payments.clear()
    appmod._mem_extract_usage.clear()
    return fake


@pytest.fixture
def client():
    return appmod.app.test_client()


def _paid_intent(client, fake):
    iid = client.post('/create-payment', json={}).get_json()['intent_id']
    fake.pay(iid)
    return iid


def test_extraction_is_free_and_capped_per_visitor(client, env):
    codes = [client.post('/extract', json={'files': [DOC]}).status_code
             for _ in range(appmod.EXTRACT_DAILY_LIMIT + 1)]
    assert codes == [200] * appmod.EXTRACT_DAILY_LIMIT + [429]
    other = client.post('/extract', json={'files': [DOC]}, headers={'CF-Connecting-IP': '203.0.113.9'})
    assert other.status_code == 200  # the cap is per visitor


def test_rate_limit_stores_no_raw_ip(client, env):
    if os.environ.get('TEST_DATABASE_URL'):
        pytest.skip('inspects the in-memory store')
    client.post('/extract', json={'files': [DOC]}, headers={'CF-Connecting-IP': '198.51.100.7'})
    keys = [k[0] for k in appmod._mem_extract_usage]
    assert keys and all('198.51.100.7' not in k for k in keys)


def test_turnstile_required_when_configured(client, env, monkeypatch):
    monkeypatch.setattr(appmod, 'TURNSTILE_SECRET', 'secret')
    r = client.post('/extract', json={'files': [DOC]})
    assert r.status_code == 403 and r.get_json()['code'] == 'verification_failed'


def test_preview_returns_watermarked_images_not_a_pdf(client, env):
    r = client.post('/preview', json={'data': CONTRACT})
    body = r.get_json()
    assert r.status_code == 200 and len(body['pages']) == 3
    assert all(p.startswith('data:image/jpeg;base64,') for p in body['pages'])
    assert b'%PDF' not in r.data


def test_pdf_requires_confirmed_payment(client, env):
    assert client.post('/generate', json={'data': CONTRACT}).status_code == 402
    iid = client.post('/create-payment', json={}).get_json()['intent_id']  # created, not paid
    assert client.post('/generate', json={'data': CONTRACT, 'intent_id': iid}).status_code == 402


def test_paid_pdf_and_redownload_limit(client, env):
    iid = _paid_intent(client, env)
    for _ in range(appmod.GENERATIONS_PER_PAYMENT):
        r = client.post('/generate', json={'data': CONTRACT, 'intent_id': iid})
        assert r.status_code == 200 and r.data.startswith(b'%PDF')
    r = client.post('/generate', json={'data': CONTRACT, 'intent_id': iid})
    assert r.status_code == 403 and r.get_json()['code'] == 'generation_limit'


def test_lawyer_payment_does_not_buy_a_contract(client, env):
    iid = client.post('/legal-chat/create-payment', json={}).get_json()['intent_id']
    env.pay(iid)
    assert client.post('/generate', json={'data': CONTRACT, 'intent_id': iid}).status_code == 402


def test_free_mode_skips_payment(client, env, monkeypatch):
    monkeypatch.setattr(appmod, 'FREE_MODE', True)
    assert client.post('/generate', json={'data': CONTRACT}).status_code == 200
