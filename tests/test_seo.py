"""SEO / indexing-hygiene tests: canonical redirects, robots, sitemap, page heads.

Run with:  python3 -m pytest tests/ -q
"""
import html
import os
import re

import pytest

os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
os.environ['BASE_URL'] = 'https://ejarihelper.ae'

from app import app  # noqa: E402

CANONICAL = 'https://ejarihelper.ae'

# Every indexable page the sitemap advertises.
PAGES = [
    '/', '/legal-chat', '/ar/legal-chat', '/how-it-works', '/privacy', '/terms',
    '/guide/ejari-registration', '/guide/ejari-renewal', '/guide/ejari-cancellation',
    '/guide/ejari-fine', '/guide/tenancy-contract-dubai', '/guide/rental-dispute',
    '/guide/security-deposit-refund-dubai', '/guide/rent-increase-dubai',
    '/guide/eviction-notice-dubai', '/guide/dewa-premises-number',
    '/guide/dewa-activation', '/guide/dewa-transfer',
    '/tools/rent-increase-calculator',
    '/ar/guide/rental-dispute', '/ar/guide/ejari-renewal', '/ar/guide/dewa-premises-number',
]

# Pages that exist in both languages: en-path -> ar-path.
HREFLANG_PAIRS = {
    '/guide/rental-dispute': '/ar/guide/rental-dispute',
    '/guide/ejari-renewal': '/ar/guide/ejari-renewal',
    '/guide/dewa-premises-number': '/ar/guide/dewa-premises-number',
    '/legal-chat': '/ar/legal-chat',
}


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def get(client, path, **kw):
    return client.get(path, base_url=CANONICAL, **kw)


# ── http→https: single-hop 301 ────────────────────────────────────────

@pytest.mark.parametrize('path', ['/', '/guide/ejari-renewal', '/legal-chat', '/terms'])
def test_http_redirects_to_https_in_one_hop(client, path):
    r = client.get(path, base_url='http://ejarihelper.ae',
                   headers={'X-Forwarded-Proto': 'http'})
    assert r.status_code == 301
    assert r.headers['Location'] == f'{CANONICAL}{path}'
    # The target must answer 200 directly — exactly one hop.
    r2 = client.get(path, base_url=CANONICAL, headers={'X-Forwarded-Proto': 'https'})
    assert r2.status_code == 200


def test_http_www_collapses_in_single_hop(client):
    """http + www must be fixed by ONE 301, not a redirect chain."""
    r = client.get('/guide/ejari-renewal', base_url='http://www.ejarihelper.ae',
                   headers={'X-Forwarded-Proto': 'http'})
    assert r.status_code == 301
    assert r.headers['Location'] == f'{CANONICAL}/guide/ejari-renewal'


def test_https_www_collapses_in_single_hop(client):
    r = client.get('/', base_url='https://www.ejarihelper.ae',
                   headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 301
    assert r.headers['Location'] == f'{CANONICAL}/'


def test_redirect_preserves_query_string(client):
    r = client.get('/legal-chat?unlocked=1&tid=abc', base_url='http://ejarihelper.ae',
                   headers={'X-Forwarded-Proto': 'http'})
    assert r.status_code == 301
    assert r.headers['Location'] == f'{CANONICAL}/legal-chat?unlocked=1&tid=abc'


def test_https_apex_not_redirected(client):
    r = get(client, '/', headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 200


# ── page heads: canonical + hreflang + lengths ────────────────────────

@pytest.mark.parametrize('path', PAGES)
def test_page_serves_200_with_canonical(client, path):
    r = get(client, path, headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '__BASE_URL__' not in body, 'unreplaced placeholder'
    assert f'<link rel="canonical" href="{CANONICAL}{path}">' in body


@pytest.mark.parametrize('path', PAGES)
def test_title_and_description_lengths(client, path):
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    title = html.unescape(re.search(r'<title>(.*?)</title>', body).group(1))
    desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', body).group(1))
    assert len(title) <= 60, f'{path}: title {len(title)} chars'
    assert len(desc) <= 155, f'{path}: description {len(desc)} chars'


@pytest.mark.parametrize('en,ar', sorted(HREFLANG_PAIRS.items()))
def test_hreflang_full_set_on_both_versions(client, en, ar):
    for path in (en, ar):
        body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
        assert f'<link rel="alternate" hreflang="en" href="{CANONICAL}{en}">' in body, path
        assert f'<link rel="alternate" hreflang="ar" href="{CANONICAL}{ar}">' in body, path
        assert f'<link rel="alternate" hreflang="x-default" href="{CANONICAL}{en}">' in body, path


def test_ar_pages_linked_from_en_footers(client):
    """AR pages must be reachable from EN pages (crawl path, ≤3 clicks from home)."""
    body = get(client, '/', headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    for ar in ['/ar/guide/rental-dispute', '/ar/guide/ejari-renewal',
               '/ar/guide/dewa-premises-number', '/ar/legal-chat']:
        assert f'href="{ar}"' in body, f'homepage missing link to {ar}'


# ── structured data ───────────────────────────────────────────────────

@pytest.mark.parametrize('path', PAGES)
def test_json_ld_parses(client, path):
    import json
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S)
    for b in blocks:
        json.loads(b)


@pytest.mark.parametrize('path', [
    '/guide/ejari-renewal', '/guide/ejari-registration', '/guide/rental-dispute',
    '/guide/security-deposit-refund-dubai', '/guide/rent-increase-dubai',
    '/guide/eviction-notice-dubai', '/guide/ejari-fine',
    '/tools/rent-increase-calculator', '/ar/legal-chat', '/how-it-works',
])
def test_faq_schema_present(client, path):
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    assert 'FAQPage' in body


# ── robots / llms / sitemap ───────────────────────────────────────────

def test_robots_ai_policy(client):
    body = get(client, '/robots.txt').get_data(as_text=True)
    for bot in ['OAI-SearchBot', 'PerplexityBot', 'ClaudeBot', 'Applebot-Extended']:
        assert f'User-agent: {bot}\nAllow: /' in body, bot
    for bot in ['GPTBot', 'Google-Extended', 'CCBot']:
        assert f'User-agent: {bot}\nDisallow: /\n' in body, bot
    assert 'Disallow: /legal-chat/message' in body
    assert 'Disallow: /legal-chat/create-payment' in body
    assert f'Sitemap: {CANONICAL}/sitemap.xml' in body


def test_llms_txt(client):
    r = get(client, '/llms.txt')
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'AED 15' in body and 'AED 50' in body
    assert f'{CANONICAL}/legal-chat' in body
    assert f'{CANONICAL}/guide/rental-dispute' in body


def test_sitemap_covers_all_pages(client):
    body = get(client, '/sitemap.xml').get_data(as_text=True)
    for path in PAGES:
        if path in ('/privacy',):
            continue
        assert f'<loc>{CANONICAL}{path}</loc>' in body, path
    # hreflang clusters for AR twins
    assert body.count('hreflang="ar"') == len(HREFLANG_PAIRS) * 2


def test_unknown_guide_redirects_home(client):
    r = get(client, '/guide/does-not-exist', headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 302
    r = get(client, '/tools/does-not-exist', headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 302
