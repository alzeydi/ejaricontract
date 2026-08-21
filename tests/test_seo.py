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
    '/what-is-ejari', '/ejari-help', '/guides', '/about',
    '/guide/ejari-check', '/guide/ejari-cost', '/guide/ejari-number',
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
    '/guide/ejari-check', '/guide/ejari-cost', '/guide/ejari-number',
    '/what-is-ejari', '/ejari-help', '/about',
    '/tools/rent-increase-calculator', '/ar/legal-chat', '/how-it-works',
])
def test_faq_schema_present(client, path):
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    assert 'FAQPage' in body


# ── robots / llms / sitemap ───────────────────────────────────────────

def test_robots_ai_policy(client):
    body = get(client, '/robots.txt').get_data(as_text=True)
    # Citation and live-fetch agents: the acquisition channel, kept open.
    for bot in ['OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot', 'Perplexity-User',
                'ClaudeBot', 'Claude-User', 'Applebot']:
        assert f'User-agent: {bot}\nAllow: /' in body, bot
    # Training crawlers and training control tokens: opted out.
    for bot in ['GPTBot', 'CCBot', 'Google-Extended', 'Applebot-Extended',
                'Bytespider', 'meta-externalagent', 'Amazonbot']:
        assert f'User-agent: {bot}\nDisallow: /\n' in body, bot
    assert 'Content-Signal: search=yes,ai-train=no,use=reference' in body


def test_applebot_extended_is_not_treated_as_a_crawler(client):
    """Applebot-Extended grants permission to train Apple Intelligence; it
    fetches nothing. Allowing it while declaring ai-train=no contradicts the
    file's own policy, so it belongs in the disallow list, not the allow list."""
    body = get(client, '/robots.txt').get_data(as_text=True)
    assert 'User-agent: Applebot-Extended\nAllow: /' not in body
    assert 'User-agent: Applebot-Extended\nDisallow: /' in body
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


def test_unknown_guide_returns_404_not_a_soft_404(client):
    """A page that does not exist must say 404 — bouncing to the homepage is a
    soft 404 in Google's eyes and hides the broken link from the visitor."""
    for path in ('/guide/does-not-exist', '/tools/does-not-exist',
                 '/ar/guide/does-not-exist', '/no-such-page'):
        r = get(client, path, headers={'X-Forwarded-Proto': 'https'})
        assert r.status_code == 404, path
        body = r.get_data(as_text=True)
        assert 'noindex' in body, path
        # The 404 page routes people back into the site.
        assert '/legal-chat' in body and '/guide/ejari-registration' in body, path


# ── URL-shape normalisation: no 404s for variants of real pages ───────

@pytest.mark.parametrize('variant,canonical', [
    ('/guide/ejari-renewal/', '/guide/ejari-renewal'),
    ('/guide/ejari-renewal.html', '/guide/ejari-renewal'),
    ('/guide/Ejari-Renewal', '/guide/ejari-renewal'),
    ('/GUIDE/EJARI-RENEWAL/', '/guide/ejari-renewal'),
    ('/legal-chat/', '/legal-chat'),
    ('/how-it-works/', '/how-it-works'),
    ('/how-it-works.html', '/how-it-works'),
    ('/tools/rent-increase-calculator/', '/tools/rent-increase-calculator'),
    ('/ar/guide/ejari-renewal/', '/ar/guide/ejari-renewal'),
    ('/ar/legal-chat/', '/ar/legal-chat'),
    ('/guide//ejari-renewal', '/guide/ejari-renewal'),
    ('/index.html', '/'),
    ('/privacy/', '/privacy'),
    ('/terms/', '/terms'),
])
def test_url_variants_301_to_canonical_then_200(client, variant, canonical):
    r = get(client, variant, headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 301, variant
    assert r.headers['Location'] == f'{CANONICAL}{canonical}', variant
    # One hop only: the target answers 200 directly.
    assert get(client, canonical, headers={'X-Forwarded-Proto': 'https'}).status_code == 200


@pytest.mark.parametrize('section,target', [
    ('/guide', '/guides'),
    ('/guide/', '/guides'),
    ('/tools', '/guides'),
    ('/ar', '/ar/legal-chat'),
    ('/ar/', '/ar/legal-chat'),
    ('/ar/guide', '/ar/legal-chat'),
    # The URL Search Console reported, reached by walking up from
    # /download/dld-tenancy-contract.pdf.
    ('/download/', '/guide/tenancy-contract-dubai'),
    ('/download', '/guide/tenancy-contract-dubai'),
])
def test_bare_directory_paths_301_somewhere_real(client, section, target):
    """Crawlers walk up the path tree; these have no index page of their own.
    Each must land on a 200 in ONE hop — a 301 into a 404 is still a 404."""
    r = get(client, section, headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 301, section
    assert r.headers['Location'] == f'{CANONICAL}{target}', section
    assert get(client, target, headers={'X-Forwarded-Proto': 'https'}).status_code == 200, section


def test_download_files_themselves_still_serve(client):
    """Only the bare directory redirects — the actual files must not move."""
    for path in ('/download/dld-tenancy-contract.pdf', '/download/dld-tenancy-contract.docx'):
        assert get(client, path, headers={'X-Forwarded-Proto': 'https'}).status_code == 200, path


def test_english_only_guide_under_ar_redirects_to_english_twin(client):
    r = get(client, '/ar/guide/ejari-fine', headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 301
    assert r.headers['Location'].endswith('/guide/ejari-fine')
    assert get(client, '/guide/ejari-fine',
               headers={'X-Forwarded-Proto': 'https'}).status_code == 200


def test_variant_and_scheme_collapse_in_one_hop(client):
    """http + www + trailing slash must all be fixed by ONE 301."""
    r = client.get('/guide/ejari-renewal/', base_url='http://www.ejarihelper.ae',
                   headers={'X-Forwarded-Proto': 'http'})
    assert r.status_code == 301
    assert r.headers['Location'] == f'{CANONICAL}/guide/ejari-renewal'


def test_static_assets_are_not_rewritten(client):
    """Static filenames are case-sensitive on disk — normalisation must skip them."""
    for path in ('/static/css/base.css', '/static/og-image.png', '/static/favicon.svg'):
        r = get(client, path, headers={'X-Forwarded-Proto': 'https'})
        assert r.status_code == 200, path


@pytest.mark.parametrize('raw,canonical', [
    ('/static/index.html', '/'),
    ('/static/how-it-works.html', '/how-it-works'),
    ('/static/legal-chat.html', '/legal-chat'),
    ('/static/terms.html', '/terms'),
    ('/static/guide/ejari-fine.html', '/guide/ejari-fine'),
    ('/static/tools/rent-increase-calculator.html', '/tools/rent-increase-calculator'),
    ('/static/ar/legal-chat.html', '/ar/legal-chat'),
    ('/static/ar/guide/ejari-renewal.html', '/ar/guide/ejari-renewal'),
    ('/static/404.html', '/'),
])
def test_raw_static_html_301s_to_the_served_url(client, raw, canonical):
    """The on-disk copies still carry unsubstituted __BASE_URL__ placeholders,
    so a crawler that reaches them sees a duplicate with a broken canonical."""
    r = get(client, raw, headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 301, raw
    assert r.headers['Location'] == f'{CANONICAL}{canonical}', raw


def test_post_endpoints_are_not_normalised(client):
    """A 301 on POST would drop the request body — the handler must be reached.
    Sends an invalid rating so nothing is written: 400 proves it got there."""
    r = client.post('/rate', base_url=CANONICAL, json={'stars': 99},
                    headers={'X-Forwarded-Proto': 'https'})
    assert r.status_code == 400


# ── sitemap freshness ─────────────────────────────────────────────────

def test_sitemap_carries_lastmod_and_not_the_ignored_hints(client):
    """Google reads <lastmod> and ignores <changefreq>/<priority> outright.
    A sitemap without lastmod carries no freshness signal at all."""
    body = get(client, '/sitemap.xml').get_data(as_text=True)
    assert body.count('<lastmod>') == body.count('<loc>')
    assert '<changefreq>' not in body
    assert '<priority>' not in body


@pytest.mark.parametrize('path', [
    '/what-is-ejari', '/guide/ejari-cost', '/guide/ejari-registration',
    '/guide/ejari-fine', '/how-it-works',
])
def test_sitemap_lastmod_matches_the_pages_own_datemodified(client, path):
    """The sitemap date is lifted from the page's structured data, so the two
    can never drift apart and contradict each other."""
    sitemap = get(client, '/sitemap.xml').get_data(as_text=True)
    entry = re.search(rf'<loc>{re.escape(CANONICAL + path)}</loc>.*?<lastmod>([\d-]+)</lastmod>',
                      sitemap, re.S)
    assert entry, f'{path} missing from sitemap'
    page = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    declared = re.search(r'"dateModified":\s*"([\d-]+)"', page)
    assert declared, f'{path} has no dateModified in its JSON-LD'
    assert entry.group(1) == declared.group(1), path


@pytest.mark.parametrize('path', PAGES)
def test_every_page_declares_a_modification_date(client, path):
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    assert re.search(r'"dateModified":\s*"\d{4}-\d{2}-\d{2}"', body), path


# ── snippet + image preview permissions ───────────────────────────────

@pytest.mark.parametrize('path', PAGES)
def test_robots_meta_allows_large_previews(client, path):
    """Without max-image-preview:large the guides cannot win an image-rich
    result, and max-snippet:-1 is what allows a full featured snippet."""
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    assert 'max-image-preview:large' in body, path
    assert 'max-snippet:-1' in body, path


# ── E-E-A-T: the non-affiliation disclaimer ───────────────────────────

@pytest.mark.parametrize('path', PAGES)
def test_non_affiliation_disclaimer_on_every_page(client, path):
    """'Ejari' is a Dubai Land Department mark and this domain contains it.
    Saying plainly that the site is independent is both the legal safeguard
    and a trust signal on YMYL content."""
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    assert 'eh-f-disc' in body, path
    assert 'dubailand.gov.ae' in body, path


def test_about_page_is_linked_from_every_page(client):
    for path in PAGES:
        body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
        assert 'href="/about"' in body, path


# ── intent coverage: one URL per head query ───────────────────────────

@pytest.mark.parametrize('path,phrase', [
    ('/what-is-ejari', 'what is ejari'),
    ('/ejari-help', 'ejari help'),
    ('/guide/ejari-registration', 'how to make an ejari'),
    ('/guide/ejari-cost', 'ejari cost'),
    ('/guide/ejari-check', 'ejari check'),
    ('/guide/ejari-number', 'ejari number'),
])
def test_head_queries_have_a_page_that_targets_them(client, path, phrase):
    """Each head query needs a URL whose title and H1 actually answer it —
    a phrase buried inside another page cannot rank for it."""
    body = get(client, path, headers={'X-Forwarded-Proto': 'https'}).get_data(as_text=True)
    title = html.unescape(re.search(r'<title>(.*?)</title>', body).group(1)).lower()
    h1 = html.unescape(re.sub(r'<[^>]*>', ' ', re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S).group(1))).lower()
    words = phrase.split()
    assert all(w in title for w in words if w not in ('an', 'to', 'how')), f'{path}: title misses "{phrase}"'
    assert all(w in h1 for w in words), f'{path}: h1 misses "{phrase}"'


def test_fee_figure_is_consistent_sitewide(client):
    """The Ejari fee is this site's headline fact and its main competitive
    edge. One stale copy of it anywhere undermines the whole claim."""
    import pathlib
    stale = []
    for f in pathlib.Path('static').rglob('*.html'):
        text = f.read_text(encoding='utf-8')
        for bad in ('122.50', 'AED 215', 'AED 220'):
            if bad in text:
                stale.append(f'{f}: {bad}')
    assert not stale, 'superseded Ejari fee still on: ' + ', '.join(stale)


# ── live-site checks (opt in with LIVE_SEO_TESTS=1) ───────────────────

@pytest.mark.skipif(not os.environ.get('LIVE_SEO_TESTS'),
                    reason='hits the live site; set LIVE_SEO_TESTS=1 to run')
def test_live_robots_is_not_overridden_by_cloudflare():
    """Cloudflare's managed robots.txt is prepended to ours and contradicts
    it — it disallows ClaudeBot and Applebot-Extended, which _ROBOTS_AI_ALLOWED
    deliberately allows. Two groups for one user-agent is resolved differently
    by different parsers, so the app must be the only source of truth.
    Fix: Cloudflare dashboard -> disable the managed robots.txt."""
    import urllib.request
    with urllib.request.urlopen('https://ejarihelper.ae/robots.txt', timeout=20) as r:
        body = r.read().decode()
    assert 'Cloudflare Managed content' not in body, (
        'Cloudflare is injecting its own robots.txt ahead of the app\'s')
    for bot in ['ClaudeBot', 'Applebot-Extended']:
        assert f'User-agent: {bot}\nDisallow: /' not in body, f'{bot} blocked by an override'
