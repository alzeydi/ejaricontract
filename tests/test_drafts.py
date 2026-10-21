"""Landlord-link drafts: encrypted, field values only, gone after 72 hours.

Storage runs on the in-memory fallback, or on a real Postgres when
TEST_DATABASE_URL is set.
Run with:  python3 -m pytest tests/ -q
"""
import os
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault('ANTHROPIC_API_KEY', 'test')

import app as appmod  # noqa: E402

TENANT = {'tenant_name': 'TEST TENANT', 'tenant_emirates_id': '784-1990-1234567-1',
          'premises_no_dewa': '012345678', 'data': 'BASE64-FILE-BYTES'}


@pytest.fixture
def drafts(monkeypatch):
    monkeypatch.setenv('DRAFT_ENC_KEY', Fernet.generate_key().decode())
    test_db = os.environ.get('TEST_DATABASE_URL')
    monkeypatch.setattr(appmod, '_DB_URL', test_db or '')
    if test_db:
        appmod._init_db()
        conn = appmod._get_conn()
        with conn, conn.cursor() as cur:
            cur.execute('TRUNCATE drafts')
        conn.close()
    appmod._mem_drafts.clear()


@pytest.fixture
def client():
    return appmod.app.test_client()


def _create(client):
    r = client.post('/contract/draft', json={'ext': TENANT, 'form': {'tenant_phone': '+971501234567', 'x': 'y'}})
    assert r.status_code == 200
    return r.get_json()


def test_off_without_a_key(client, monkeypatch):
    for var in ('DRAFT_ENC_KEY', 'SECRET_KEY', 'ADMIN_PASSWORD'):
        monkeypatch.delenv(var, raising=False)
    assert client.post('/contract/draft', json={}).status_code == 404
    assert client.get('/config').get_json()['drafts_enabled'] is False


def test_create_share_and_merge(client, drafts):
    d = _create(client)
    token = d['token']
    assert len(token) == 32 and token == token.lower()  # survives canonical_path()
    assert d['url'].endswith(f'/contract/d/{token}')
    assert d['ext']['premises_no_dewa'] == '012345678'
    assert 'data' not in d['ext'] and 'x' not in d['form']  # only whitelisted text fields

    page = client.get(f'/contract/d/{token}')
    assert page.status_code == 200
    assert page.headers['X-Robots-Tag'] == 'noindex, nofollow'
    assert b'noindex' in page.data

    m = client.post(f'/contract/draft/{token}/merge',
                    json={'ext': {'lessor_name': 'TEST LESSOR', 'tenant_name': ''}}).get_json()
    assert m['ext']['lessor_name'] == 'TEST LESSOR'
    assert m['ext']['tenant_name'] == 'TEST TENANT'  # empty values never erase
    assert m['expires_at'] == d['expires_at']        # merging never extends the 72 h
    assert client.get(f'/contract/draft/{token}').get_json()['ext']['lessor_name'] == 'TEST LESSOR'


def test_stored_encrypted_under_a_token_hash(client, drafts):
    token = _create(client)['token']
    if os.environ.get('TEST_DATABASE_URL'):
        conn = appmod._get_conn()
        with conn, conn.cursor() as cur:
            cur.execute('SELECT token_hash, ciphertext FROM drafts')
            rows = cur.fetchall()
        conn.close()
    else:
        rows = [(k, v[0]) for k, v in appmod._mem_drafts.items()]
    assert len(rows) == 1
    key, blob = rows[0]
    assert token not in key and 'TEST TENANT' not in blob and '784-1990' not in blob


def test_expires_after_72_hours(client, drafts, monkeypatch):
    token = _create(client)['token']
    later = appmod._utcnow() + timedelta(hours=appmod.DRAFT_TTL_HOURS, minutes=1)
    monkeypatch.setattr(appmod, '_utcnow', lambda: later)
    assert client.get(f'/contract/draft/{token}').status_code == 404
    assert client.get(f'/contract/d/{token}').status_code == 404


def test_unknown_or_malformed_tokens(client, drafts):
    assert client.get('/contract/draft/' + '0' * 32).status_code == 404
    assert client.get('/contract/draft/not-a-token').status_code == 404
    assert client.post('/contract/draft/' + '0' * 32 + '/merge', json={}).status_code == 404


def test_robots_keeps_drafts_out_of_search(client):
    assert 'Disallow: /contract/' in client.get('/robots.txt').get_data(as_text=True)


def test_key_derived_from_secret_key(client, monkeypatch):
    monkeypatch.delenv('DRAFT_ENC_KEY', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'prod-secret')
    monkeypatch.setattr(appmod, '_DB_URL', '')
    appmod._mem_drafts.clear()
    token = client.post('/contract/draft', json={'ext': TENANT}).get_json()['token']
    assert client.get(f'/contract/draft/{token}').get_json()['ext']['tenant_name'] == 'TEST TENANT'
