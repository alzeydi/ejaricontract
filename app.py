#!/usr/bin/env python3
"""Ejari Tenancy Contract Generator - Flask Backend"""

import io, os, re, base64, json, threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from flask import Flask, request, send_file, jsonify, send_from_directory, session, redirect, abort, Response
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import anthropic

app = Flask(__name__, static_folder='static')
# Trust X-Forwarded-Proto/Host from the platform's reverse proxy so request.host_url
# returns https://… — otherwise canonical, og:url, JSON-LD, sitemap, robots all use http://
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(app)
# Secret key for session cookies — set SECRET_KEY in Railway env vars
app.secret_key = os.environ.get('SECRET_KEY') or os.environ.get('ADMIN_PASSWORD', 'dev-key')

TEMPLATE_PDF = os.path.join(os.path.dirname(__file__), 'template.pdf')
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# FREE_MODE=true  → no payment required; AI extraction is free
# FREE_MODE=false (default) → users must pay CONTRACT_PRICE_AED via Ziina
FREE_MODE = os.environ.get('FREE_MODE', 'false').lower() in ('1', 'true', 'yes')

# ── Prices and public fees ─────────────────────────────────────────────
# Every price and fee shown on the site comes from here: pages use the
# __PLACEHOLDER__ tokens that render_page() substitutes (see PAGE_TOKENS).
CONTRACT_PRICE_AED = int(os.environ.get('CONTRACT_PRICE_AED', '39'))
LEGAL_PRICE_AED = int(os.environ.get('LEGAL_PRICE_AED', '50'))        # 30-minute chat session
LEGAL_FILE_TOPUP_AED = int(os.environ.get('LEGAL_FILE_TOPUP_AED', '25'))
CONTRACT_PRICE_FILS = CONTRACT_PRICE_AED * 100

# Dubai Land Department Ejari fees (2026), shown sitewide. The components
# must add up to the totals — tests/test_seo.py checks that.
EJARI_FEE_PARTS_ONLINE = {'registration': 100, 'knowledge': 10, 'innovation': 10, 'service_partner': 55, 'vat': 2.75}
EJARI_FEE_PARTS_TYPING = {'registration': 100, 'knowledge': 10, 'innovation': 10, 'service_partner': 95, 'vat': 4.75}
EJARI_FEE_ONLINE = '177.75'   # AED, Dubai REST / DLD portal
EJARI_FEE_TYPING = '219.75'   # AED, trustee / typing centre
EJARI_CERT_TIMING = 'the same day, usually within minutes'

# LEGAL_FREE_MODE=true  → /legal-chat is unlimited and free (paywall hidden)
# LEGAL_FREE_MODE=false (default) → users pay LEGAL_PRICE_AED for a 30-minute session
LEGAL_FREE_MODE = os.environ.get('LEGAL_FREE_MODE', 'false').lower() in ('1', 'true', 'yes')

# ZIINA_EMBEDDED=true  → pay inline via the embedded checkout widget (needs a
#                        verified business profile + whitelisted domain at Ziina).
# ZIINA_EMBEDDED=false (default) → use Ziina's hosted page via redirect, which
#                        works on an unverified/individual account. Flip to true
#                        once the trade license + embedded checkout are approved.
ZIINA_EMBEDDED = os.environ.get('ZIINA_EMBEDDED', 'false').lower() in ('1', 'true', 'yes')

def get_template_size():
    r = PdfReader(TEMPLATE_PDF)
    p = r.pages[0]
    return float(p.mediabox.width), float(p.mediabox.height)

FS = 7.5

def fill_ejari_pdf(data):
    PDF_W, PDF_H = get_template_size()

    def y(t): return PDF_H - t - 5.2
    def fx(x): return x + 3

    def fmt_money(val):
        try:
            n = float(str(val).replace(',','').replace(' ',''))
            return f"{int(round(n)):,}"
        except:
            return str(val)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(PDF_W, PDF_H))
    c.setFillColorRGB(0, 0, 0)

    def draw(x, ty, text, fs=None):
        if not text: return
        c.setFont("Helvetica", fs or FS)
        c.drawString(x, y(ty), str(text))

    # PAGE 1
    draw(fx(44.3),  111.3, data.get('date',''))

    # Lessor
    draw(fx(85.6),  173.2, data.get('owner_name',''))
    draw(fx(86.8),  195.2, data.get('lessor_name',''))
    draw(fx(106.3), 218.2, data.get('lessor_emirates_id',''))
    draw(fx(75.8),  240.2, data.get('lessor_license_no','').strip() or 'N/A')
    draw(fx(372.3), 240.2, data.get('lessor_licensing_authority','').strip() or 'N/A')
    draw(fx(85.2),  265.2, data.get('lessor_email',''))
    draw(fx(88.1),  287.2, data.get('lessor_phone',''))

    # Tenant
    draw(fx(87.5),  343.2, data.get('tenant_name',''))
    draw(fx(106.9), 365.2, data.get('tenant_emirates_id',''))
    draw(fx(75.8),  388.2, data.get('tenant_license_no','').strip() or 'N/A')
    draw(fx(372.3), 388.2, data.get('tenant_licensing_authority','').strip() or 'N/A')
    draw(fx(85.9),  413.2, data.get('tenant_email',''))
    draw(fx(88.8),  435.2, data.get('tenant_phone',''))

    # Property usage X
    usage = data.get('property_usage', 'Residential')
    CY = 493.0
    if usage == 'Residential':   draw(370.5, CY, 'X', fs=6.5)
    elif usage == 'Commercial':  draw(257.6, CY, 'X', fs=6.5)
    elif usage == 'Industrial':  draw(150.5, CY, 'X', fs=6.5)

    # Property info
    draw(fx(62.5),  515.2, data.get('plot_no',''))
    draw(fx(344.4), 515.2, data.get('makani_no',''))
    draw(fx(85.9),  538.2, data.get('building_name',''))
    draw(fx(348.6), 538.2, data.get('property_no',''))
    draw(fx(83.4),  561.2, data.get('property_type',''))
    draw(fx(373.5), 561.2, data.get('property_area',''))
    draw(fx(64.9),  584.2, data.get('location',''))
    draw(fx(381.2), 584.2, data.get('premises_no_dewa',''))

    # Contract dates
    draw(107.9, 641.3, data.get('contract_from',''))
    draw(187.5, 641.3, data.get('contract_to',''))

    # Financials
    cv = fmt_money(data.get('contract_value',''))
    draw(fx(356.3), 641.2, f"{cv} AED")
    ar = fmt_money(data.get('annual_rent',''))
    draw(fx(77.0),  666.2, f"{ar} AED")
    sd = data.get('security_deposit','').strip()
    draw(fx(392.0), 666.2, f"{fmt_money(sd)} AED" if sd else '')
    draw(fx(97.0),  688.2, data.get('mode_of_payment',''))

    # Signatures p1
    draw(fx(196.1), 798.2, data.get('tenant_sign_date',''))
    draw(fx(469.1), 798.2, data.get('lessor_sign_date',''))

    c.showPage()

    # PAGE 2
    draw(fx(196.1), 797.7, data.get('tenant_sign_date',''))
    draw(fx(469.1), 797.7, data.get('lessor_sign_date',''))
    c.showPage()

    # PAGE 3
    terms = data.get('additional_terms', [])
    for i, ty_pos in enumerate([318.7, 343.7, 368.7, 393.7, 418.7]):
        text = terms[i].strip() if i < len(terms) else ''
        if text:
            draw(50.0, ty_pos, text, fs=7)
    draw(fx(196.1), 767.7, data.get('tenant_sign_date',''))
    draw(fx(469.1), 767.7, data.get('lessor_sign_date',''))

    c.save()
    packet.seek(0)

    overlay  = PdfReader(packet)
    original = PdfReader(TEMPLATE_PDF)
    writer   = PdfWriter()
    for i in range(len(original.pages)):
        orig_page = original.pages[i]
        if i < len(overlay.pages):
            orig_page.merge_page(overlay.pages[i])
        writer.add_page(orig_page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


# ── Ratings storage (PostgreSQL with file fallback) ─────────────────────
_RATINGS_FILE = Path(os.path.dirname(__file__)) / 'ratings.json'
_DB_URL = os.environ.get('DATABASE_URL', '')

def _get_conn():
    if not _DB_URL:
        return None
    import psycopg2
    url = _DB_URL
    # Railway sometimes uses postgres:// — psycopg2 needs postgresql://
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return psycopg2.connect(url)

def _init_db():
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS ratings (
                        id SERIAL PRIMARY KEY,
                        stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS leads (
                        id SERIAL PRIMARY KEY,
                        phone TEXT NOT NULL,
                        source TEXT DEFAULT 'post_download',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                # Payment ledger — Ziina intent ids only, no personal data.
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        intent_id TEXT PRIMARY KEY,
                        product TEXT NOT NULL,
                        amount_fils INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'created',
                        created_at TIMESTAMP DEFAULT NOW(),
                        confirmed_at TIMESTAMP,
                        ga_reported_at TIMESTAMP,
                        generations INTEGER NOT NULL DEFAULT 0
                    )
                ''')
                # Free-extraction rate limit: a keyed hash of the IP that
                # changes every day (no raw IPs), rows dropped after 2 days.
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS extract_usage (
                        ip_hash TEXT NOT NULL,
                        day DATE NOT NULL,
                        count INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (ip_hash, day)
                    )
                ''')
                # Landlord-link drafts: contract field values only (never
                # files), encrypted, keyed by a hash of the link token,
                # deleted 72 h after creation.
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS drafts (
                        token_hash TEXT PRIMARY KEY,
                        ciphertext TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL
                    )
                ''')
                # OCR spend per extraction — token counts only.
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS ocr_costs (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT NOW(),
                        docs INTEGER NOT NULL,
                        input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL,
                        est_usd NUMERIC(10, 5) NOT NULL
                    )
                ''')
    finally:
        conn.close()

try:
    _init_db()
except Exception as e:
    print(f'[ratings] DB init skipped: {e}')

def load_ratings():
    conn = _get_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*), COALESCE(SUM(stars),0) FROM ratings')
                    count, total = cur.fetchone()
                    return {'count': int(count), 'total': int(total)}
        finally:
            conn.close()
    # file fallback (local dev)
    try:
        if _RATINGS_FILE.exists():
            return json.loads(_RATINGS_FILE.read_text())
    except Exception:
        pass
    return {'count': 0, 'total': 0}

def save_rating(stars):
    conn = _get_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO ratings (stars) VALUES (%s)', (stars,))
        finally:
            conn.close()
        return
    # file fallback (local dev)
    try:
        data = load_ratings()
        data['total'] += stars
        data['count'] += 1
        _RATINGS_FILE.write_text(json.dumps(data))
    except Exception:
        pass

# ── Routes ─────────────────────────────────────────────────────────────

def page_tokens():
    """Price and fee tokens substituted into every page (see the constants at the top)."""
    return {
        '__CONTRACT_PRICE__': str(CONTRACT_PRICE_AED),
        '__LAWYER_PRICE__': str(LEGAL_PRICE_AED),
        '__FILES_TOPUP_PRICE__': str(LEGAL_FILE_TOPUP_AED),
        '__EJARI_FEE_ONLINE__': EJARI_FEE_ONLINE,
        '__EJARI_FEE_TYPING__': EJARI_FEE_TYPING,
        '__EJARI_CERT_TIMING__': EJARI_CERT_TIMING,
    }


def render_page(*rel_path):
    """Serve a static HTML page with __BASE_URL__, __GA4_ID__ and the price tokens injected.

    GA4_MEASUREMENT_ID (a G-XXXXXXXXXX id) comes from the environment; when
    unset the placeholder stays as-is and the front-end guard skips the
    gtag('config') call, so pages work without GA4 configured.
    """
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    ga4_id = os.environ.get('GA4_MEASUREMENT_ID', '')
    with open(os.path.join(app.static_folder, *rel_path), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    for token, value in page_tokens().items():
        html = html.replace(token, value)
    if ga4_id:
        html = html.replace('__GA4_ID__', ga4_id)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


# ── Canonical URL shape ────────────────────────────────────────────────
# Nothing on the site links to them, but crawlers keep discovering URL
# variants of real pages — trailing slashes, .html suffixes, mixed case,
# doubled slashes — and every one of those used to be a hard 404 (Search
# Console: "Not found (404)"). They now collapse into the canonical URL with
# a single 301, in the same hop as the scheme/host fix.

# Bare directory paths have no index page of their own — point them at the
# closest real entry point instead of 404ing.
_SECTION_REDIRECTS = {
    # /guides is a real hub page now; /guide is its singular typo-twin.
    '/guide': '/guides',
    '/tools': '/guides',
    '/index': '/',
    '/home': '/',
    '/404': '/',
    # The one URL Search Console actually flagged (crawled 14 Aug 2026):
    # Googlebot walked up from /download/dld-tenancy-contract.pdf. The page
    # that hosts and explains that template is the right landing spot.
    '/download': '/guide/tenancy-contract-dubai',
    '/downloads': '/guide/tenancy-contract-dubai',
    '/ar': '/ar/legal-chat',
    '/ar/guide': '/ar/legal-chat',
    '/ar/guides': '/ar/legal-chat',
}


def canonical_path(path):
    """Return the canonical spelling of a request path (unchanged if already canonical)."""
    # .well-known paths must keep their exact spelling.
    if path.startswith('/.well-known/'):
        return path
    if path.startswith('/static/'):
        # Static assets keep their case-sensitive on-disk name. The one
        # exception is page HTML: /static/guide/x.html is the un-templated
        # source of /guide/x — __BASE_URL__ is never substituted there, so it
        # ships a broken canonical tag and Google indexes it as a duplicate.
        if not path.lower().endswith(('.html', '.htm')):
            return path
        path = path[len('/static'):]
    p = re.sub(r'/{2,}', '/', path).lower()
    for suffix in ('.html', '.htm'):
        if p.endswith(suffix):
            p = p[:-len(suffix)]
            break
    if len(p) > 1:
        p = p.rstrip('/') or '/'
    return _SECTION_REDIRECTS.get(p, p)


@app.before_request
def redirect_canonical():
    """Force the canonical host (no www), scheme (https) and path shape in a single 301.
    Avoids the http→https→non-www redirect chain that confuses Googlebot and
    causes 'Page with redirect' indexing errors."""
    from flask import redirect, request as req
    host = req.host.lower()
    proto = req.headers.get('X-Forwarded-Proto', 'http' if not req.is_secure else 'https').lower()
    needs_https = proto == 'http' and not host.startswith('localhost') and not host.startswith('127.')
    needs_apex = host.startswith('www.')
    # Only GET/HEAD are normalised: POST endpoints are called by our own JS and
    # by Ziina webhooks with exact paths, and a 301 would drop the body.
    new_path = canonical_path(req.path) if req.method in ('GET', 'HEAD') else req.path
    if needs_https or needs_apex or new_path != req.path:
        new_host = host[4:] if needs_apex else host
        new_scheme = 'https' if needs_https else proto
        query = req.query_string.decode()
        target = f'{new_scheme}://{new_host}{new_path}' + (f'?{query}' if query else '')
        return redirect(target, code=301)

@app.route('/')
def index():
    return render_page('index.html')

@app.route('/rate', methods=['POST'])
def rate():
    body = request.json or {}
    stars = body.get('stars')
    if not isinstance(stars, int) or stars < 1 or stars > 5:
        return jsonify({'ok': False, 'error': 'Invalid rating'}), 400
    save_rating(stars)
    return jsonify({'ok': True})


# ── Trustpilot Invitation API ──────────────────────────────────────────
# Sends a service review invitation a few days after a paid Legal Chat session.
# Requires three env vars (no-ops silently if any are missing):
#   TRUSTPILOT_API_KEY, TRUSTPILOT_API_SECRET, TRUSTPILOT_BUSINESS_UNIT_ID
TP_API_BASE = 'https://api.trustpilot.com'
_tp_token = {'value': '', 'exp': 0}


def _trustpilot_token():
    api_key = os.environ.get('TRUSTPILOT_API_KEY', '')
    api_secret = os.environ.get('TRUSTPILOT_API_SECRET', '')
    if not (api_key and api_secret):
        return ''
    import time as _time
    if _tp_token['value'] and _tp_token['exp'] > _time.time() + 60:
        return _tp_token['value']
    creds = base64.b64encode(f'{api_key}:{api_secret}'.encode()).decode()
    try:
        r = req_lib.post(
            f'{TP_API_BASE}/v1/oauth/oauth-business-users-for-applications/accesstoken',
            headers={'Authorization': f'Basic {creds}',
                     'Content-Type': 'application/x-www-form-urlencoded'},
            data='grant_type=client_credentials',
            timeout=10,
        )
        data = r.json()
        _tp_token['value'] = data.get('access_token', '')
        _tp_token['exp'] = _time.time() + int(data.get('expires_in', 3600))
        return _tp_token['value']
    except Exception as e:
        print(f'[trustpilot] token error: {e}')
        return ''


def trustpilot_invite(email, name, reference_id, delay_days=3):
    """Schedule a Trustpilot service review invitation. Best-effort; never raises."""
    bu_id = os.environ.get('TRUSTPILOT_BUSINESS_UNIT_ID', '')
    if not (email and bu_id):
        return False
    try:
        token = _trustpilot_token()
        if not token:
            return False
        send_at = datetime.now(timezone.utc) + timedelta(days=delay_days)
        r = req_lib.post(
            f'{TP_API_BASE}/v1/private/business-units/{bu_id}/email-invitations',
            headers={'Authorization': f'Bearer {token}',
                     'Content-Type': 'application/json'},
            json={
                'consumerEmail': email,
                'consumerName': (name or 'Customer')[:60],
                'referenceId': reference_id,
                'senderName': 'Ejari Helper',
                'replyTo': os.environ.get('TRUSTPILOT_REPLY_TO', 'hello@ejarihelper.ae'),
                'locale': 'en-US',
                'preferredSendTime': send_at.strftime('%Y-%m-%dT%H:%M:%S'),
                'redirectUri': 'https://ejarihelper.ae/?tp=1',
            },
            timeout=10,
        )
        ok = r.status_code in (200, 201)
        if not ok:
            print(f'[trustpilot] invite failed {r.status_code}: {r.text[:200]}')
        return ok
    except Exception as e:
        print(f'[trustpilot] invite error: {e}')
        return False


def _ziina_customer_info(intent_data):
    """Best-effort extraction of email + name from a Ziina payment_intent response."""
    email = (intent_data.get('customer_email')
             or intent_data.get('email')
             or (intent_data.get('customer') or {}).get('email')
             or '')
    name = (intent_data.get('customer_name')
            or (intent_data.get('customer') or {}).get('name')
            or '')
    return (email or '').strip(), (name or '').strip()


def _send_telegram(text: str):
    """Send notification to Telegram. Requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        req_lib.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=5
        )
    except Exception as e:
        print(f'[telegram] {e}')


@app.route('/lead', methods=['POST'])
def lead():
    body = request.json or {}
    phone = (body.get('phone') or '').strip()
    if not phone or len(phone.replace(' ', '').replace('-', '').replace('+', '')) < 7:
        return jsonify({'ok': False, 'error': 'Invalid phone'}), 400
    conn = _get_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO leads (phone, source) VALUES (%s, %s)',
                                (phone, 'post_download'))
        finally:
            conn.close()
    else:
        print(f'[lead] {phone}')  # fallback: visible in Railway logs
    _send_telegram(
        f'🔔 <b>New Ejari Helper lead</b>\n'
        f'📱 {phone}\n'
        f'⏰ {datetime.now().strftime("%d %b %Y, %H:%M")}'
    )
    return jsonify({'ok': True})


@app.route('/admin/telegram-setup')
def telegram_setup():
    """Helper: fetch recent bot updates to find your Telegram chat_id."""
    if not _is_admin():
        return redirect('/admin')
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        return jsonify({'error': 'TELEGRAM_BOT_TOKEN not set in Railway'}), 400
    try:
        resp = req_lib.get(f'https://api.telegram.org/bot{token}/getUpdates', timeout=5)
        data = resp.json()
        chats = {}
        for update in data.get('result', []):
            msg = update.get('message') or update.get('channel_post') or {}
            chat = msg.get('chat', {})
            if chat and chat.get('id') not in chats:
                chats[chat['id']] = {
                    'chat_id': chat.get('id'),
                    'type': chat.get('type'),
                    'name': (f"{chat.get('first_name','')} {chat.get('last_name','')}").strip()
                          or chat.get('title') or chat.get('username', ''),
                }
        return jsonify({
            'instruction': 'Send any message to your bot first, then refresh this page',
            'set_this_env': 'TELEGRAM_CHAT_ID',
            'found_chats': list(chats.values()),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _is_admin():
    """True if request carries a valid admin session cookie."""
    admin_pw = os.environ.get('ADMIN_PASSWORD', '')
    return bool(admin_pw and session.get('admin') == admin_pw)


_ADMIN_CSS = """
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#f4f3f0;color:#111;font-size:14px;min-height:100vh}
.top{background:#fff;border-bottom:1px solid #ddd;padding:0 24px;height:52px;display:flex;align-items:center;justify-content:space-between}
.top-brand{font-weight:700;font-size:15px;color:#16423c}
.top-out{font-size:12px;color:#999;text-decoration:none}
.top-out:hover{color:#16423c}
.wrap{max-width:700px;margin:32px auto;padding:0 20px}
h1{font-size:18px;font-weight:600;margin-bottom:20px}
.card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:28px}
.meta{font-size:12px;color:#999;margin-bottom:20px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-weight:600;color:#555;padding:7px 10px;border-bottom:1.5px solid #ddd}
td{padding:8px 10px;border-bottom:1px solid #f4f3f0;vertical-align:top}
tr:last-child td{border-bottom:none}
td.phone{font-weight:500;color:#16423c}
td.date{color:#999;font-size:12px}
.empty{color:#999;text-align:center;padding:32px 0}
label{display:block;font-size:12px;font-weight:600;color:#555;margin-bottom:6px}
input[type=password]{width:100%;padding:10px 12px;border:1.5px solid #ddd;border-radius:7px;font-size:14px;outline:none}
input[type=password]:focus{border-color:#16423c}
.btn{display:block;width:100%;background:#16423c;color:#fff;border:none;border-radius:7px;padding:11px;font-size:14px;font-weight:600;cursor:pointer;margin-top:14px}
.btn:hover{background:#2a7a6f}
.err{background:#fdf2f2;border:1px solid #e8bebe;border-radius:7px;padding:10px 14px;font-size:13px;color:#c0392b;margin-bottom:16px}
</style>"""


def _login_page(error=False):
    err = '<div class="err">Wrong password — try again.</div>' if error else ''
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin — Ejari Helper</title>{_ADMIN_CSS}</head><body>
<div style="display:flex;align-items:center;justify-content:center;min-height:100vh">
<div style="width:320px">
  <div style="font-weight:700;font-size:16px;color:#16423c;text-align:center;margin-bottom:24px">Ejari Helper</div>
  <div class="card">
    <h1 style="margin-bottom:20px;font-size:16px">Admin sign in</h1>
    {err}
    <form method="POST" action="/admin/login">
      <label>Password</label>
      <input type="password" name="password" autofocus>
      <button class="btn">Sign in →</button>
    </form>
  </div>
</div></div></body></html>""", 200


def _leads_page(leads_list):
    total = len(leads_list)
    rows = ''.join(
        f'<tr><td class="phone">{r["phone"]}</td>'
        f'<td class="date">{r["created_at"][:16].replace("T"," ")}</td></tr>'
        for r in leads_list
    ) or f'<tr><td colspan="2" class="empty">No leads yet</td></tr>'
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Leads — Ejari Helper</title>{_ADMIN_CSS}</head><body>
<div class="top">
  <span class="top-brand">Ejari Helper · Admin</span>
  <a href="/admin/logout" class="top-out">Sign out</a>
</div>
<div class="wrap">
  <h1>Leads</h1>
  <div class="card">
    <div class="meta">{total} lead{'s' if total != 1 else ''} total · newest first</div>
    <table>
      <tr><th>Phone / WhatsApp</th><th>Date</th></tr>
      {rows}
    </table>
  </div>
</div></body></html>"""


@app.route('/admin')
def admin_index():
    if not os.environ.get('ADMIN_PASSWORD'):
        return 'ADMIN_PASSWORD env var not set', 403
    if not _is_admin():
        return _login_page()
    # Load leads and render HTML table
    conn = _get_conn()
    if not conn:
        return _leads_page([])
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, phone, source, created_at FROM leads ORDER BY created_at DESC LIMIT 200'
                )
                rows = cur.fetchall()
        leads_list = [{'id': r[0], 'phone': r[1], 'source': r[2], 'created_at': str(r[3])} for r in rows]
        return _leads_page(leads_list)
    finally:
        conn.close()


@app.route('/admin/login', methods=['POST'])
def admin_login():
    admin_pw = os.environ.get('ADMIN_PASSWORD', '')
    if request.form.get('password') == admin_pw:
        session['admin'] = admin_pw
        return redirect('/admin')
    return _login_page(error=True)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')


@app.route('/admin/leads')
def admin_leads():
    if not _is_admin():
        return redirect('/admin')
    conn = _get_conn()
    if not conn:
        return jsonify({'error': 'No DB connection'}), 500
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, phone, source, created_at FROM leads ORDER BY created_at DESC LIMIT 200'
                )
                rows = cur.fetchall()
        leads_list = [{'id': r[0], 'phone': r[1], 'source': r[2], 'created_at': str(r[3])} for r in rows]
        return jsonify({'total': len(leads_list), 'leads': leads_list})
    finally:
        conn.close()


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico',
                               mimetype='image/x-icon', max_age=2592000)


@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    return send_from_directory('static', 'apple-touch-icon.png',
                               mimetype='image/png', max_age=2592000)


# Paths no crawler should touch: admin, payment flows, chat API.
_ROBOTS_DISALLOW = [
    '/admin', '/admin/', '/payment-success', '/verify-payment', '/create-payment',
    '/legal-chat/payment-success', '/legal-chat/create-payment',
    '/legal-chat/verify-payment', '/legal-chat/message', '/legal-chat/state',
    '/legal-chat/files-payment', '/legal-chat/files-payment-success',
    '/legal-chat/files-verify-payment',
    '/contract/',
]

# Citation/search AI crawlers — explicitly allowed. AI assistants already drive
# ~10% of sessions and refer users to the legal-chat product; blocking these
# bots cuts that acquisition channel.
#
# The *-User agents matter most: they are not indexers but live fetches made
# when a real person asks an assistant about this site. Cloudflare's AI Crawl
# Control reports ChatGPT-User as the single busiest crawler here, so a block
# on it is a block on real users mid-question.
_ROBOTS_AI_ALLOWED = [
    'OAI-SearchBot', 'ChatGPT-User',        # OpenAI: search index + live fetch
    'PerplexityBot', 'Perplexity-User',     # Perplexity: index + live fetch
    'ClaudeBot', 'Claude-User',             # Anthropic: index + live fetch
    'Applebot',                             # Apple search (see Applebot-Extended below)
]

# Training crawlers — opted out (content may be cited/referenced, not trained on).
#
# Google-Extended and Applebot-Extended are not crawlers at all: they are
# control tokens. Disallowing them is how you decline Gemini and Apple
# Intelligence training while keeping normal search crawling. Applebot-Extended
# used to sit in the allowed list above, which said the opposite of this file's
# own stated policy — it grants training permission, it does not fetch anything.
#
# Bytespider, meta-externalagent and Amazonbot are here because Cloudflare's
# managed robots.txt used to block them and no longer does. Stating the policy
# ourselves is weaker than a network block — a crawler that ignores robots.txt
# still gets through — so the durable fix is to re-block these six in
# Cloudflare's AI Crawl Control.
_ROBOTS_AI_BLOCKED = [
    'GPTBot', 'CCBot',                      # OpenAI / Common Crawl training
    'Google-Extended', 'Applebot-Extended', # training control tokens
    'Bytespider', 'meta-externalagent', 'Amazonbot',
]


@app.route('/robots.txt')
def robots_txt():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    disallow = ''.join(f'Disallow: {p}\n' for p in _ROBOTS_DISALLOW)
    parts = ['# AI policy: citation/search assistants welcome, model training opted out.\n'
             '# Content-Usage: ai-train=no, use=reference\n\n']
    # Machine-readable form of the same policy. Cloudflare's managed robots.txt
    # used to emit this; it is disabled now, so the app states it directly.
    signal = 'Content-Signal: search=yes,ai-train=no,use=reference\n'
    for bot in _ROBOTS_AI_ALLOWED:
        parts.append(f'User-agent: {bot}\nAllow: /\n{disallow}\n')
    for bot in _ROBOTS_AI_BLOCKED:
        parts.append(f'User-agent: {bot}\nDisallow: /\n\n')
    parts.append(f'User-agent: *\n{signal}Allow: /\n{disallow}\n')
    parts.append(f'Sitemap: {base_url}/sitemap.xml\n')
    return ''.join(parts), 200, {'Content-Type': 'text/plain'}


@app.route('/llms.txt')
def llms_txt():
    """llms.txt — a plain-language site summary for AI assistants."""
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    content = f"""# Ejari Helper (ejarihelper.ae)

> Dubai tenancy paperwork, done in minutes. Two paid products for Dubai tenants
> and landlords: an AI-filled DLD tenancy contract generator (AED {CONTRACT_PRICE_AED}) and an AI
> rental lawyer chat for Dubai tenancy-law questions (AED {LEGAL_PRICE_AED} per 30-minute
> session, first question free). All guidance is grounded in Dubai Law No. 26 of
> 2007, Law No. 33 of 2008 and Decree No. 43 of 2013.

## Products

- [Ejari tenancy contract generator]({base_url}/): upload Emirates IDs and the
  Title Deed; AI extracts the details and fills the official Dubai Land
  Department (DLD) Unified Tenancy Contract PDF, ready to sign and register
  with Ejari. Price: AED {CONTRACT_PRICE_AED}, no account required.
- [AI rental lawyer chat]({base_url}/legal-chat): instant, citation-backed
  answers on Dubai rental disputes — security deposits, rent increases (RERA
  index), eviction notices, RDC filings. Price: AED {LEGAL_PRICE_AED} for 30 minutes vs
  ~AED 1,500/hour at a law firm. Arabic landing: {base_url}/ar/legal-chat

## Start here

- [What is Ejari]({base_url}/what-is-ejari): the definition page — what the
  Dubai Land Department registry is, why Law No. 26 of 2007 makes it
  mandatory, what it costs, and how to get one.
- [Ejari help]({base_url}/ejari-help): the nine problems that actually block a
  registration (document mismatches, expired certificates, landlords
  withholding a Title Deed, DEWA refusals) and the fix for each.
- [All guides]({base_url}/guides): the complete index.
- [About]({base_url}/about): who runs this site, how the guidance is sourced,
  and an explicit statement that we are not affiliated with DLD or RERA.

## Free tools

- [RERA rent increase calculator]({base_url}/tools/rent-increase-calculator):
  checks the maximum legal rent increase under Decree 43/2013.
- [Blank DLD tenancy contract template]({base_url}/guide/tenancy-contract-dubai):
  free download, Word and PDF.

## Guides (canonical URLs)

- [Ejari registration]({base_url}/guide/ejari-registration): how to make an
  Ejari online via Dubai REST, AED {EJARI_FEE_ONLINE}, documents checklist.
- [Ejari cost]({base_url}/guide/ejari-cost): the full 2026 fee breakdown —
  AED {EJARI_FEE_ONLINE} filed yourself (AED 100 registration + AED 10 knowledge +
  AED 10 innovation + AED 55 service partner + AED 2.75 VAT) versus
  AED {EJARI_FEE_TYPING} at a trustee centre. Cancellation is free.
- [Ejari check]({base_url}/guide/ejari-check): check status in Dubai REST, by
  SMS to 4488 or on the DLD portal; re-download the certificate free; verify
  authenticity via the QR code.
- [Ejari number]({base_url}/guide/ejari-number): format 22-99999/2026, where
  to find it, and how it differs from the 9-digit DEWA premises number.
- [Ejari renewal]({base_url}/guide/ejari-renewal): renew every contract year,
  fees, grace period, late-renewal consequences.
- [Ejari cancellation]({base_url}/guide/ejari-cancellation): free, required at
  move-out.
- [Ejari fines]({base_url}/guide/ejari-fine): what late registration/renewal
  actually costs.
- [Dubai tenancy contract]({base_url}/guide/tenancy-contract-dubai): DLD format,
  required fields, free template.
- [Rental disputes / RDC]({base_url}/guide/rental-dispute): file at rdc.gov.ae,
  3.5% fee (min AED 500), hearing in 7–15 days.
- [Security deposit refund]({base_url}/guide/security-deposit-refund-dubai):
  wear-and-tear rules, demand letter, RDC claim.
- [Rent increase rules]({base_url}/guide/rent-increase-dubai): Decree 43/2013
  caps, 90-day notice, how to dispute.
- [Eviction notice rules]({base_url}/guide/eviction-notice-dubai): 12-month
  notarised notice, valid grounds, compensation.
- [DEWA premise number]({base_url}/guide/dewa-premises-number): find the 9-digit
  code on bills, Ejari, Title Deed.
- [DEWA activation]({base_url}/guide/dewa-activation): Move In, deposits,
  24-hour setup.
- [DEWA transfer]({base_url}/guide/dewa-transfer): moving between homes.

## Policy

- Citation and referral by AI assistants: welcome.
- Use of this site's content for model training: not permitted
  (ai-train=no, use=reference). See robots.txt.
- Contact: hello@ejarihelper.ae
- Affiliation: independent. NOT affiliated with, endorsed by, or connected to
  the Dubai Land Department, RERA, or any UAE government body. "Ejari" is a
  Dubai Land Department mark. Official portal: dubailand.gov.ae
"""
    return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

# Google ignores <changefreq> and <priority> entirely and reads only
# <lastmod>, so the sitemap carries lastmod and nothing else. The date is
# lifted from each page's own JSON-LD dateModified, which keeps the sitemap
# and the structured data from ever drifting apart.
_SITE_DEFAULT_LASTMOD = '2026-08-20'
_LASTMOD_RE = re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"')
_lastmod_cache = {}


def page_lastmod(path):
    """Read dateModified out of the page's structured data. Falls back to the
    site default for pages that carry no Article schema (privacy, terms)."""
    if path in _lastmod_cache:
        return _lastmod_cache[path]
    rel = (path.strip('/') or 'index') + '.html'
    try:
        with open(os.path.join(app.static_folder, *rel.split('/')), encoding='utf-8') as f:
            m = _LASTMOD_RE.search(f.read())
        date = m.group(1) if m else _SITE_DEFAULT_LASTMOD
    except OSError:
        date = _SITE_DEFAULT_LASTMOD
    _lastmod_cache[path] = date
    return date


# Lower-cased because canonical_path() lower-cases every request path: a
# mixed-case key would be served from a URL that 301s, and IndexNow does not
# follow redirects when verifying keyLocation.
INDEXNOW_KEY = os.environ.get('INDEXNOW_KEY', '').lower()


@app.route('/<key>.txt')
def indexnow_key_file(key):
    """IndexNow verifies ownership by fetching /<key>.txt containing the key."""
    if not INDEXNOW_KEY or key.lower() != INDEXNOW_KEY.lower():
        abort(404)
    return INDEXNOW_KEY, 200, {'Content-Type': 'text/plain'}


@app.route('/admin/indexnow', methods=['POST'])
def indexnow_submit():
    """Push every sitemap URL to IndexNow (Bing, Yandex, DuckDuckGo).
    Google ignores IndexNow, so the sitemap remains the route that matters
    there — this just shortens the lag on the other engines after a deploy."""
    if not session.get('admin'):
        return jsonify({'error': 'unauthorized'}), 401
    if not INDEXNOW_KEY:
        return jsonify({'error': 'INDEXNOW_KEY not set'}), 400
    import requests
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    host = base_url.split('://', 1)[-1]
    urls = re.findall(r'<loc>([^<]+)</loc>', sitemap_xml()[0])
    try:
        r = requests.post('https://api.indexnow.org/IndexNow', timeout=15, json={
            'host': host, 'key': INDEXNOW_KEY,
            'keyLocation': f'{base_url}/{INDEXNOW_KEY}.txt',
            'urlList': urls})
        return jsonify({'submitted': len(urls), 'status': r.status_code})
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/sitemap.xml')
def sitemap_xml():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))

    def hreflang_links(en_path, ar_path):
        """xhtml:link alternates for pages that exist in EN + AR."""
        en = f'{base_url}{en_path}'
        ar = f'{base_url}{ar_path}'
        return (f'\n    <xhtml:link rel="alternate" hreflang="en" href="{en}"/>'
                f'\n    <xhtml:link rel="alternate" hreflang="ar" href="{ar}"/>'
                f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{en}"/>')

    def guide_pair(slug):
        return (f'/guide/{slug}', f'/ar/guide/{slug}')

    # (path, (en_path, ar_path) or None)
    entries = [
        ('/', None),
        ('/what-is-ejari', None),
        ('/ejari-help', None),
        ('/guides', None),
        ('/guide/ejari-registration', None),
        ('/guide/ejari-cost', None),
        ('/guide/ejari-check', None),
        ('/guide/ejari-number', None),
        ('/guide/ejari-renewal', guide_pair('ejari-renewal')),
        ('/guide/ejari-cancellation', None),
        ('/guide/ejari-fine', None),
        ('/guide/tenancy-contract-dubai', None),
        ('/guide/rental-dispute', guide_pair('rental-dispute')),
        ('/guide/security-deposit-refund-dubai', None),
        ('/guide/rent-increase-dubai', None),
        ('/guide/eviction-notice-dubai', None),
        ('/guide/early-termination-tenancy-contract-dubai', None),
        ('/guide/tenancy-contract-addendum-dubai', None),
        ('/guide/dubai-housing-fee', None),
        ('/guide/dewa-activation', None),
        ('/guide/dewa-premises-number', guide_pair('dewa-premises-number')),
        ('/guide/dewa-transfer', None),
        ('/tools/rent-increase-calculator', None),
        ('/ar/guide/rental-dispute', guide_pair('rental-dispute')),
        ('/ar/guide/ejari-renewal', guide_pair('ejari-renewal')),
        ('/ar/guide/dewa-premises-number', guide_pair('dewa-premises-number')),
        ('/legal-chat', ('/legal-chat', '/ar/legal-chat')),
        ('/ar/legal-chat', ('/legal-chat', '/ar/legal-chat')),
        ('/how-it-works', None),
        ('/about', None),
        ('/privacy', None),
        ('/terms', None),
    ]
    urls = ''
    for path, pair in entries:
        urls += (f'\n  <url>\n    <loc>{base_url}{path}</loc>'
                 f'{hreflang_links(*pair) if pair else ""}'
                 f'\n    <lastmod>{page_lastmod(path)}</lastmod>\n  </url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
           f'{urls}\n</urlset>')
    return xml, 200, {'Content-Type': 'application/xml'}


_GUIDE_SLUGS = {'ejari-registration', 'dewa-activation', 'rental-dispute',
                'ejari-renewal', 'dewa-premises-number', 'tenancy-contract-dubai',
                'dewa-transfer', 'ejari-cancellation',
                'security-deposit-refund-dubai', 'rent-increase-dubai',
                'eviction-notice-dubai', 'ejari-fine',
                'ejari-check', 'ejari-cost', 'ejari-number',
                'early-termination-tenancy-contract-dubai',
                'tenancy-contract-addendum-dubai', 'dubai-housing-fee'}

_TOOL_SLUGS = {'rent-increase-calculator'}


@app.route('/tools/<slug>')
def tool(slug):
    if slug not in _TOOL_SLUGS:
        abort(404)
    return render_page('tools', f'{slug}.html')

# Guides that also exist in Arabic under /ar/guide/<slug>
_AR_GUIDE_SLUGS = {'rental-dispute', 'ejari-renewal', 'dewa-premises-number'}

@app.route('/guide/<slug>')
def guide(slug):
    if slug not in _GUIDE_SLUGS:
        abort(404)
    return render_page('guide', f'{slug}.html')


@app.route('/ar/guide/<slug>')
def guide_ar(slug):
    # An English-only guide requested under /ar/ is a real page in the wrong
    # language folder — send it to its English twin instead of 404ing.
    if slug not in _AR_GUIDE_SLUGS:
        if slug in _GUIDE_SLUGS:
            return redirect(f'/guide/{slug}', 301)
        abort(404)
    return render_page('ar', 'guide', f'{slug}.html')


@app.route('/what-is-ejari')
def what_is_ejari():
    """Definition page for the head term. Deliberately a top-level URL rather
    than /guide/… — it is the entry point of the whole Ejari cluster, not one
    guide among twelve."""
    return render_page('what-is-ejari.html')


@app.route('/ejari-help')
def ejari_help():
    return render_page('ejari-help.html')


@app.route('/guides')
def guides_index():
    return render_page('guides.html')


@app.route('/about')
def about():
    return render_page('about.html')


@app.route('/privacy')
def privacy():
    return render_page('privacy.html')


@app.route('/terms')
def terms():
    return render_page('terms.html')


@app.errorhandler(404)
def page_not_found(_e):
    """Branded 404 that keeps the 404 status — never a soft 404.

    A missing page used to bounce to the homepage with a 302, which Google
    classifies as a soft 404 and which drops the visitor with no explanation.
    Now the status is honest and the page routes people to the real content.
    JSON for API paths so front-end fetch() callers still get JSON.
    """
    if request.path.startswith(('/legal-chat/', '/admin/', '/webhook/', '/contract/draft/')):
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    body, _status, headers = render_page('404.html')
    return body, 404, headers


# ── Legal Chat (paid AI consultation on Dubai rental disputes) ─────────
LEGAL_FREE_MESSAGES = 1
LEGAL_SESSION_MINUTES = 30
LEGAL_PRICE_FILS = LEGAL_PRICE_AED * 100

# File-upload quota: first 3 files in a session are free, then each
# LEGAL_FILE_TOPUP_AED top-up grants 3 more uploads.
LEGAL_FILE_FREE_LIMIT = 3
LEGAL_FILE_TOPUP_FILS = LEGAL_FILE_TOPUP_AED * 100
LEGAL_FILE_TOPUP_FILES = 3
LEGAL_FILE_MAX_BYTES = 8 * 1024 * 1024  # 8 MB per file (base64-decoded)
LEGAL_FILE_ALLOWED_MIME = {'application/pdf', 'image/jpeg', 'image/png'}

LEGAL_SYSTEM_PROMPT = (
    "You are an AI legal assistant specialised in Dubai (UAE) residential and "
    "commercial rental law. Your scope covers: tenancy contracts, Ejari "
    "registration, security deposits, rent increases (RERA calculator and Decree "
    "43 of 2013), eviction notices (12-month notarised notice under Law 26/2007 "
    "as amended by Law 33/2008), maintenance obligations, early termination, and "
    "filing cases at the Rental Dispute Settlement Centre (RDC, rdc.gov.ae).\n\n"
    "Style: concise, structured, plain English. Cite the specific article/law "
    "when relevant (e.g. \"Article 25(2) of Law 33/2008\"). Quote the RDC filing "
    "fee as 3.5% of annual rent (min AED 500, max AED 20,000). Always end with a "
    "clear next step the user can take today.\n\n"
    "Boundaries: you provide legal information, not legal representation. For "
    "complex cases or when monetary stakes are high, recommend the user files at "
    "the RDC or consults a licensed advocate. Do NOT invent article numbers or "
    "case law — if unsure, say so."
)


def _legal_access_state():
    """Return (mode, remaining_free, paid_until_iso). mode ∈ paid|free|locked."""
    if LEGAL_FREE_MODE:
        # Pretend the user has an always-fresh paid session — front-end will hide the paywall.
        far_future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        return 'paid', 0, far_future
    now = datetime.now(timezone.utc)
    paid_until_str = session.get('legal_paid_until')
    if paid_until_str:
        try:
            paid_until = datetime.fromisoformat(paid_until_str)
            if paid_until > now:
                return 'paid', 0, paid_until_str
        except Exception:
            pass
    used = int(session.get('legal_free_used', 0))
    remaining = max(0, LEGAL_FREE_MESSAGES - used)
    return ('free' if remaining > 0 else 'locked'), remaining, None


def _legal_files_state():
    """Return (used, allowance, remaining) for file uploads in this session.
    allowance grows by LEGAL_FILE_TOPUP_FILES each successful paid top-up.
    """
    used = int(session.get('legal_files_used', 0))
    extra = int(session.get('legal_files_extra', 0))
    allowance = LEGAL_FILE_FREE_LIMIT + extra
    remaining = max(0, allowance - used)
    return used, allowance, remaining


@app.route('/legal-chat')
def legal_chat_page():
    return render_page('legal-chat.html')


@app.route('/ar/legal-chat')
def legal_chat_ar_page():
    """Arabic landing for the AI rental lawyer (rental-disputes focus)."""
    return render_page('ar', 'legal-chat.html')


@app.route('/legal-chat/state')
def legal_chat_state():
    mode, remaining, paid_until = _legal_access_state()
    files_used, files_allowance, files_remaining = _legal_files_state()
    return jsonify({
        'mode': mode,
        'remaining_free': remaining,
        'paid_until': paid_until,
        'free_mode': LEGAL_FREE_MODE,
        'ziina_embedded': ZIINA_EMBEDDED,
        'free_limit': LEGAL_FREE_MESSAGES,
        'price_aed': LEGAL_PRICE_FILS // 100,
        'session_minutes': LEGAL_SESSION_MINUTES,
        'files': {
            'used': files_used,
            'allowance': files_allowance,
            'remaining': files_remaining,
            'free_limit': LEGAL_FILE_FREE_LIMIT,
            'topup_aed': LEGAL_FILE_TOPUP_FILS // 100,
            'topup_files': LEGAL_FILE_TOPUP_FILES,
            'max_mb': LEGAL_FILE_MAX_BYTES // (1024 * 1024),
            'allowed_ext': ['pdf', 'jpg', 'jpeg', 'png'],
        },
    })


@app.route('/legal-chat/message', methods=['POST'])
def legal_chat_message():
    body = request.json or {}
    messages = body.get('messages') or []
    files = body.get('files') or []
    if not isinstance(messages, list) or not messages:
        return jsonify({'error': 'No messages'}), 400
    if not isinstance(files, list):
        files = []

    # Normalise + cap conversation length (last 20 turns)
    safe = []
    for m in messages[-20:]:
        role = m.get('role')
        content = (m.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            safe.append({'role': role, 'content': content[:4000]})
    if not safe or safe[-1]['role'] != 'user':
        return jsonify({'error': 'Last message must be from user'}), 400

    mode, remaining, paid_until = _legal_access_state()
    if mode == 'locked':
        return jsonify({
            'error': 'paywall',
            'message': f'Free preview is over. Unlock {LEGAL_SESSION_MINUTES} minutes of expert chat for AED {LEGAL_PRICE_FILS // 100}.',
        }), 402

    # Validate attached files
    validated_files = []
    if files:
        files_used, files_allowance, files_remaining = _legal_files_state()
        if len(files) > files_remaining:
            return jsonify({
                'error': 'file_paywall',
                'message': (
                    f'You have used {files_used} of {files_allowance} file uploads in this session. '
                    f'Top up AED {LEGAL_FILE_TOPUP_FILS // 100} for {LEGAL_FILE_TOPUP_FILES} more uploads.'
                ),
                'files': {
                    'used': files_used,
                    'allowance': files_allowance,
                    'remaining': files_remaining,
                    'topup_aed': LEGAL_FILE_TOPUP_FILS // 100,
                    'topup_files': LEGAL_FILE_TOPUP_FILES,
                },
            }), 402

        for f in files:
            if not isinstance(f, dict):
                return jsonify({'error': 'Invalid file payload'}), 400
            mime = (f.get('mime_type') or '').lower()
            data = f.get('data') or ''
            name = (f.get('name') or 'file')[:120]
            if mime not in LEGAL_FILE_ALLOWED_MIME:
                return jsonify({'error': f'Unsupported file type: {mime or "unknown"}. Allowed: PDF, JPG, PNG.'}), 400
            try:
                raw_len = len(base64.b64decode(data, validate=False))
            except Exception:
                return jsonify({'error': f'Could not decode file: {name}'}), 400
            if raw_len > LEGAL_FILE_MAX_BYTES:
                return jsonify({
                    'error': f'File "{name}" is {raw_len // (1024*1024)} MB — limit is {LEGAL_FILE_MAX_BYTES // (1024*1024)} MB.'
                }), 400
            validated_files.append({'mime_type': mime, 'data': data, 'name': name})

    # If files attached, replace the last user message content with a multimodal block list.
    if validated_files:
        last_text = safe[-1]['content']
        blocks = [build_content_block(f) for f in validated_files]
        blocks.append({'type': 'text', 'text': last_text or 'Please review the attached file(s).'})
        safe[-1] = {'role': 'user', 'content': blocks}

    try:
        msg = claude.messages.create(
            model='claude-opus-4-7',
            max_tokens=2500,
            system=LEGAL_SYSTEM_PROMPT,
            messages=safe,
        )
        reply = ''.join(b.text for b in msg.content if hasattr(b, 'text')).strip()
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

    if mode == 'free':
        session['legal_free_used'] = int(session.get('legal_free_used', 0)) + 1
    if validated_files:
        session['legal_files_used'] = int(session.get('legal_files_used', 0)) + len(validated_files)

    new_mode, new_remaining, new_paid_until = _legal_access_state()
    files_used, files_allowance, files_remaining = _legal_files_state()
    return jsonify({
        'ok': True,
        'reply': reply,
        'mode': new_mode,
        'remaining_free': new_remaining,
        'paid_until': new_paid_until,
        'files': {
            'used': files_used,
            'allowance': files_allowance,
            'remaining': files_remaining,
        },
    })


@app.route('/legal-chat/create-payment', methods=['POST'])
def legal_create_payment():
    """Create Ziina payment intent for the legal chat unlock."""
    base_url = request.host_url.rstrip('/')
    data, error = _ziina_create(
        'lawyer',
        success_url=f'{base_url}/legal-chat/payment-success?intent_id={{PAYMENT_INTENT_ID}}',
        cancel_url=f'{base_url}/legal-chat?cancelled=1',
        failure_url=f'{base_url}/legal-chat?failed=1',
    )
    if error:
        return jsonify({'error': error}), 502
    return jsonify({
        'ok': True,
        'embedded_url': data['embedded_url'],
        'redirect_url': data.get('redirect_url', ''),
        'intent_id': data.get('id', ''),
    })


def _grant_legal_session(intent_id, confirmed_at):
    """Open the paid chat window for a confirmed intent.

    The window is anchored to the payment time, so re-opening the success
    URL (refresh, back button, another tab) never extends or restarts it.
    Returns paid_until, or None when that window has already passed.
    """
    paid_at = (confirmed_at.replace(tzinfo=timezone.utc) if confirmed_at
               else datetime.now(timezone.utc))
    paid_until = paid_at + timedelta(minutes=LEGAL_SESSION_MINUTES)
    if paid_until <= datetime.now(timezone.utc):
        return None
    granted = set(session.get('legal_intents', []))
    if intent_id not in granted:
        granted.add(intent_id)
        session['legal_intents'] = list(granted)
        session['legal_free_used'] = 0
    session['legal_paid_until'] = paid_until.isoformat()
    return paid_until


@app.route('/legal-chat/verify-payment', methods=['POST'])
def legal_verify_payment():
    """Embedded-checkout callback — verify the intent and grant a 30-min window."""
    intent_id = (request.json or {}).get('intent_id', '')
    if not intent_id:
        return jsonify({'paid': False, 'error': 'No intent_id'}), 400
    r = _ziina_confirm(intent_id, 'lawyer')
    if r['paid']:
        paid_until = _grant_legal_session(intent_id, r['confirmed_at'])
        if paid_until:
            return jsonify({'paid': True, 'paid_until': paid_until.isoformat()})
        return jsonify({'paid': False, 'status': 'expired'})
    return jsonify({'paid': False, 'status': r['status']})


@app.route('/legal-chat/payment-success')
def legal_payment_success():
    """Ziina redirect target — verify payment and grant a 30-min chat window."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return redirect('/legal-chat')
    r = _ziina_confirm(intent_id, 'lawyer')
    if r['paid'] and _grant_legal_session(intent_id, r['confirmed_at']):
        return redirect(f'/legal-chat?unlocked=1&tid={intent_id}')
    return redirect('/legal-chat?pending=1')


@app.route('/legal-chat/files-payment', methods=['POST'])
def legal_files_payment():
    """Create Ziina payment intent for a file-upload top-up (+3 files)."""
    base_url = request.host_url.rstrip('/')
    data, error = _ziina_create(
        'lawyer_files',
        success_url=f'{base_url}/legal-chat/files-payment-success?intent_id={{PAYMENT_INTENT_ID}}',
        cancel_url=f'{base_url}/legal-chat?files_cancelled=1',
        failure_url=f'{base_url}/legal-chat?files_failed=1',
    )
    if error:
        return jsonify({'error': error}), 502
    return jsonify({
        'ok': True,
        'embedded_url': data['embedded_url'],
        'redirect_url': data.get('redirect_url', ''),
        'intent_id': data.get('id', ''),
    })


def _grant_legal_files(intent_id):
    """Grant +N uploads for a verified, completed top-up intent (idempotent)."""
    granted = set(session.get('legal_files_intents', []))
    if intent_id not in granted:
        session['legal_files_extra'] = int(session.get('legal_files_extra', 0)) + LEGAL_FILE_TOPUP_FILES
        granted.add(intent_id)
        session['legal_files_intents'] = list(granted)


@app.route('/legal-chat/files-verify-payment', methods=['POST'])
def legal_files_verify_payment():
    """Embedded-checkout callback — verify the top-up intent and grant +3 uploads."""
    intent_id = (request.json or {}).get('intent_id', '')
    if not intent_id:
        return jsonify({'paid': False, 'error': 'No intent_id'}), 400
    r = _ziina_confirm(intent_id, 'lawyer_files')
    if r['paid']:
        _grant_legal_files(intent_id)
        return jsonify({'paid': True, 'added': LEGAL_FILE_TOPUP_FILES})
    return jsonify({'paid': False, 'status': r['status']})


@app.route('/legal-chat/files-payment-success')
def legal_files_payment_success():
    """Ziina redirect target — verify payment and grant +3 file uploads."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return redirect('/legal-chat')
    r = _ziina_confirm(intent_id, 'lawyer_files')
    if r['paid']:
        _grant_legal_files(intent_id)
        return redirect(f'/legal-chat?files_unlocked=1&tid={intent_id}')
    return redirect('/legal-chat?files_pending=1')


@app.route('/how-it-works')
def how_it_works():
    return render_page('how-it-works.html')

@app.route('/download/dld-tenancy-contract.pdf')
def download_template():
    """Serve the blank DLD tenancy contract form for manual filling."""
    return send_file(TEMPLATE_PDF, mimetype='application/pdf',
                     as_attachment=True, download_name='dld-tenancy-contract.pdf')


TEMPLATE_DOCX = os.path.join(os.path.dirname(__file__), 'dld-tenancy-contract.docx')

@app.route('/download/dld-tenancy-contract.docx')
def download_template_docx():
    """Serve the editable Word version of the DLD tenancy contract."""
    return send_file(
        TEMPLATE_DOCX,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True, download_name='dld-tenancy-contract.docx')


@app.route('/health')
def health():
    db_status = 'no_url'
    ratings = None
    if _DB_URL:
        try:
            r = load_ratings()
            ratings = r
            db_status = 'ok'
        except Exception as e:
            db_status = str(e)
    return jsonify({
        'status': 'ok',
        'template': os.path.exists(TEMPLATE_PDF),
        'db': db_status,
        'ratings': ratings,
    })

@app.route('/config')
def config():
    return jsonify({'free_mode': FREE_MODE, 'legal_free_mode': LEGAL_FREE_MODE, 'ziina_embedded': ZIINA_EMBEDDED,
                    'contract_price_aed': CONTRACT_PRICE_AED, 'turnstile_site_key': TURNSTILE_SITE_KEY,
                    'drafts_enabled': drafts_enabled()})


def build_content_block(f):
    """Build image or document block from file dict."""
    mime = f['mime_type']
    if mime == 'application/pdf':
        return {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': f['data']}}
    if mime not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
        mime = 'image/jpeg'
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': f['data']}}


# Per-document extraction prompts — focused, short → faster response
DOC_PROMPTS = {
    'TENANT_EMIRATES_ID': (
        'Extract from this UAE Emirates ID. Return ONLY JSON, no markdown:\n'
        '{"tenant_name":"Full English name","tenant_emirates_id":"784-XXXX-XXXXXXX-X"}'
    ),
    'LESSOR_EMIRATES_ID': (
        'Extract from this UAE Emirates ID. Return ONLY JSON, no markdown:\n'
        '{"lessor_name":"Full English name","lessor_emirates_id":"784-XXXX-XXXXXXX-X"}'
    ),
    'TITLE_DEED': (
        'Extract from this Dubai Title Deed. Return ONLY JSON, no markdown:\n'
        '{"owner_name":"","plot_no":"","building_name":"CAPS","property_no":"","property_type":"Apartment|Villa|Studio|Townhouse|Office|Retail|Warehouse","property_area":"m² number only","location":"community name","premises_no_dewa":"9 digits","makani_no":"10 digits no spaces"}'
    ),
    'PREVIOUS_EJARI': (
        'Extract from this Dubai Ejari registration certificate. Return ONLY JSON, no markdown:\n'
        '{"tenant_phone":"mobile number","annual_rent":"digits only","security_deposit":"digits only","contract_from":"DD/MM/YYYY","contract_to":"DD/MM/YYYY","building_name":"","property_no":"","location":"","premises_no_dewa":"9 digits","makani_no":"10 digits no spaces","plot_no":""}'
    ),
}


OCR_MODEL = 'claude-haiku-4-5'
OCR_USD_PER_MTOK = (1.00, 5.00)  # input, output — claude-haiku-4-5 list price

# Free extraction is abuse-prone (each call costs OCR tokens): a daily cap
# per visitor plus, when TURNSTILE_SECRET is set, a Cloudflare Turnstile check.
EXTRACT_DAILY_LIMIT = int(os.environ.get('EXTRACT_DAILY_LIMIT', '5'))
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET', '')

# Paid generations: re-downloads after fixing a typo are part of the price.
GENERATIONS_PER_PAYMENT = 5
GENERATION_WINDOW_HOURS = 24


def extract_one(f):
    """Extract data from a single document using haiku (fast). Returns (fields, usage)."""
    prompt = DOC_PROMPTS.get(f['label'], 'Extract all key text fields. Return ONLY JSON.')
    content = [build_content_block(f), {'type': 'text', 'text': prompt}]
    msg = claude.messages.create(
        model=OCR_MODEL,
        max_tokens=300,
        messages=[{'role': 'user', 'content': content}]
    )
    usage = (msg.usage.input_tokens, msg.usage.output_tokens)
    text = ''.join(b.text for b in msg.content if hasattr(b, 'text'))
    text = text.replace('```json', '').replace('```', '').strip()
    return json.loads(text), usage


def _client_ip():
    # Behind Cloudflare the edge's address is what reaches the app; the
    # visitor's is in CF-Connecting-IP.
    return request.headers.get('CF-Connecting-IP') or request.remote_addr or ''


def _extract_quota_hit():
    """Count one free extraction for this visitor. Returns (allowed, used_today)."""
    day = datetime.now(timezone.utc).date()
    key = (app.secret_key + day.isoformat()).encode()
    ip_hash = hmac.new(key, _client_ip().encode(), hashlib.sha256).hexdigest()[:32]
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            k = (ip_hash, day)
            _mem_extract_usage[k] = _mem_extract_usage.get(k, 0) + 1
            used = _mem_extract_usage[k]
        return used <= EXTRACT_DAILY_LIMIT, used
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM extract_usage WHERE day < %s', (day - timedelta(days=1),))
                cur.execute('INSERT INTO extract_usage (ip_hash, day, count) VALUES (%s, %s, 1) '
                            'ON CONFLICT (ip_hash, day) DO UPDATE SET count = extract_usage.count + 1 '
                            'RETURNING count', (ip_hash, day))
                used = cur.fetchone()[0]
    finally:
        conn.close()
    return used <= EXTRACT_DAILY_LIMIT, used


_mem_extract_usage = {}


def _turnstile_ok(token):
    if not TURNSTILE_SECRET:
        return True
    if not token:
        return False
    try:
        r = req_lib.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
                         data={'secret': TURNSTILE_SECRET, 'response': token, 'remoteip': _client_ip()},
                         timeout=8)
        return bool(r.json().get('success'))
    except Exception as e:
        print(f'[turnstile] verify error: {e}', flush=True)
        return True  # fail open: an outage at Cloudflare must not block customers; the daily cap still applies


def _log_ocr_cost(docs, input_tokens, output_tokens):
    usd = (input_tokens * OCR_USD_PER_MTOK[0] + output_tokens * OCR_USD_PER_MTOK[1]) / 1_000_000
    print(f'[ocr] docs={docs} in={input_tokens} out={output_tokens} usd={usd:.5f}', flush=True)
    try:
        conn = _get_conn()
        if conn:
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute('INSERT INTO ocr_costs (docs, input_tokens, output_tokens, est_usd) '
                                    'VALUES (%s, %s, %s, %s)', (docs, input_tokens, output_tokens, round(usd, 5)))
            finally:
                conn.close()
    except Exception as e:
        print(f'[ocr] cost log failed: {e}', flush=True)
    return usd


@app.route('/extract', methods=['POST'])
def extract():
    """OCR endpoint — free, rate-limited; parallel per-document extraction with haiku."""
    try:
        payload = request.json or {}
        files = payload.get('files', [])
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        if not _turnstile_ok(payload.get('turnstile_token', '')):
            return jsonify({'error': 'Please complete the security check and try again.',
                            'code': 'verification_failed'}), 403
        allowed, _used = _extract_quota_hit()
        if not allowed:
            return jsonify({'error': f'Free extraction limit reached ({EXTRACT_DAILY_LIMIT} per day). '
                                     'You can still type the details in by hand.',
                            'code': 'rate_limited'}), 429

        # Run all documents in parallel threads
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        failed_docs = []
        tokens_in = tokens_out = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(extract_one, f): f['label'] for f in files}
            for future in as_completed(futures):
                label = futures[future]
                try:
                    results[label], (ti, to) = future.result()
                    tokens_in += ti
                    tokens_out += to
                except Exception as e:
                    results[label] = {}  # skip failed doc, don't break whole request
                    failed_docs.append(label)
                    print(f'[extract] {label} failed: {type(e).__name__}: {str(e)[:200]}', flush=True)
        _log_ocr_cost(len(files), tokens_in, tokens_out)

        # Merge all results — later docs override earlier for same key
        merged = {}
        for label in ['TENANT_EMIRATES_ID', 'LESSOR_EMIRATES_ID', 'TITLE_DEED', 'PREVIOUS_EJARI']:
            if label in results:
                for k, v in results[label].items():
                    if v and str(v).strip():  # only overwrite with non-empty values
                        merged[k] = v

        # Ensure all expected keys exist
        defaults = ['tenant_name','tenant_emirates_id','tenant_phone','lessor_name',
                    'owner_name','lessor_emirates_id','plot_no','building_name',
                    'property_no','property_type','property_area','location',
                    'premises_no_dewa','makani_no','annual_rent','security_deposit',
                    'contract_from','contract_to']
        for k in defaults:
            merged.setdefault(k, '')

        return jsonify({'ok': True, 'data': merged, 'failed_docs': failed_docs})

    except Exception as e:
        print(f'[extract] error: {type(e).__name__}: {e}', flush=True)
        return jsonify({'error': 'Extraction failed. Please try again.'}), 500


# ── Preview (free) and paid PDF ─────────────────────────────────────────
_PDFIUM_LOCK = threading.Lock()  # pdfium is not thread-safe
PREVIEW_SCALE = 1.3              # ≈94 dpi — readable, not print quality
WATERMARK = 'PREVIEW — ejarihelper.ae'


def _watermark(pdf_bytes):
    """Stamp a diagonal PREVIEW watermark three times on every page."""
    writer = PdfWriter(clone_from=io.BytesIO(pdf_bytes))
    for page in writer.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(w, h))
        c.setFillColorRGB(0.75, 0.12, 0.12)
        c.setFillAlpha(0.22)
        c.setFont('Helvetica-Bold', 40)
        for y in (h * 0.22, h * 0.52, h * 0.82):
            c.saveState()
            c.translate(w / 2, y)
            c.rotate(32)
            c.drawCentredString(0, 0, WATERMARK)
            c.restoreState()
        c.save()
        packet.seek(0)
        page.merge_page(PdfReader(packet).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def render_preview_pages(data):
    """Filled contract → watermarked JPEG data URLs, one per page. No PDF leaves the server."""
    import pypdfium2 as pdfium
    pdf = _watermark(fill_ejari_pdf(data))
    pages = []
    with _PDFIUM_LOCK:
        doc = pdfium.PdfDocument(pdf)
        try:
            for i in range(len(doc)):
                img = doc[i].render(scale=PREVIEW_SCALE).to_pil().convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=62, optimize=True)
                pages.append('data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode())
        finally:
            doc.close()
    return pages


# ── Contract field rules (mirrored in static/index.html → FIELD_RULES) ──
REQUIRED_FIELDS = [
    'tenant_name', 'tenant_emirates_id', 'tenant_phone', 'lessor_name', 'lessor_emirates_id',
    'building_name', 'property_no', 'property_type', 'location', 'plot_no', 'premises_no_dewa',
    'contract_from', 'contract_to', 'annual_rent', 'contract_value', 'mode_of_payment',
]
_EID_RE = re.compile(r'^784-\d{4}-\d{7}-\d$')
_DATE_RE = re.compile(r'^(\d{2})/(\d{2})/(\d{4})$')
_AMOUNT_RE = re.compile(r'^\d+(\.\d{1,2})?$')


def _parse_date(value):
    m = _DATE_RE.match(value or '')
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def normalize_contract(data):
    """Canonical forms: dashed Emirates IDs, digit-only numbers (leading zeros kept)."""
    for k in ('tenant_emirates_id', 'lessor_emirates_id'):
        digits = re.sub(r'\D', '', data.get(k, ''))
        if len(digits) == 15:
            data[k] = f'{digits[:3]}-{digits[3:7]}-{digits[7:14]}-{digits[14]}'
    for k in ('premises_no_dewa', 'makani_no'):
        data[k] = re.sub(r'\s', '', data.get(k, ''))
    for k in ('annual_rent', 'contract_value', 'security_deposit'):
        data[k] = re.sub(r'[,\s]', '', data.get(k, ''))
    return data


def validate_contract(data):
    """Field → message for every missing or malformed field ({} when the contract is complete)."""
    errors = {k: 'Required' for k in REQUIRED_FIELDS if not str(data.get(k, '')).strip()}
    for k in ('tenant_emirates_id', 'lessor_emirates_id'):
        if data.get(k) and not _EID_RE.match(data[k]):
            errors[k] = 'Emirates ID format: 784-XXXX-XXXXXXX-X'
    if data.get('premises_no_dewa') and not re.fullmatch(r'\d{9}', data['premises_no_dewa']):
        errors['premises_no_dewa'] = 'DEWA premise number: 9 digits'
    if data.get('makani_no') and not re.fullmatch(r'\d{10}', data['makani_no']):
        errors['makani_no'] = 'Makani number: 10 digits'
    for k in ('annual_rent', 'contract_value', 'security_deposit'):
        if data.get(k) and not _AMOUNT_RE.match(data[k]):
            errors[k] = 'Numbers only, no separators'
    for k in ('contract_from', 'contract_to', 'date'):
        if data.get(k) and not _parse_date(data[k]):
            errors[k] = 'Date format: DD/MM/YYYY'
    start, end = _parse_date(data.get('contract_from')), _parse_date(data.get('contract_to'))
    if start and end and end <= start:
        errors['contract_to'] = 'End date must be after the start date'
    return errors


def _contract_data(body):
    data = body.get('data') if isinstance(body.get('data'), dict) else None
    if data is None:
        return None
    data = {k: (v if isinstance(v, list) else str(v).strip()[:300]) for k, v in data.items()}
    if not data.get('date'):
        data['date'] = datetime.now().strftime('%d/%m/%Y')
    return normalize_contract(data)


def _invalid(errors):
    return jsonify({'error': 'Please fix the highlighted fields.', 'code': 'invalid', 'fields': errors}), 422


@app.route('/preview', methods=['POST'])
def preview():
    data = _contract_data(request.json or {})
    if data is None:
        return jsonify({'error': 'No data'}), 400
    errors = validate_contract(data)
    if errors:
        return _invalid(errors)
    try:
        return jsonify({'ok': True, 'pages': render_preview_pages(data)})
    except Exception as e:
        print(f'[preview] error: {type(e).__name__}: {e}', flush=True)
        return jsonify({'error': 'Could not build the preview. Please try again.'}), 500


def _ledger_use_generation(intent_id):
    """Spend one of a payment's generations. True when allowed."""
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            row = _mem_payments.get(intent_id)
            if (not row or row['status'] != 'completed' or row['generations'] >= GENERATIONS_PER_PAYMENT
                    or row['confirmed_at'] < _utcnow() - timedelta(hours=GENERATION_WINDOW_HOURS)):
                return False
            row['generations'] += 1
            return True
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE payments SET generations = generations + 1 "
                            "WHERE intent_id = %s AND status = 'completed' AND generations < %s "
                            "AND confirmed_at > (NOW() AT TIME ZONE 'utc') - make_interval(hours => %s) "
                            "RETURNING generations", (intent_id, GENERATIONS_PER_PAYMENT, GENERATION_WINDOW_HOURS))
                return cur.fetchone() is not None
    finally:
        conn.close()


@app.route('/generate', methods=['POST'])
def generate():
    """The clean PDF — only for a server-confirmed contract payment."""
    body = request.json or {}
    data = _contract_data(body)
    if data is None:
        return jsonify({'error': 'No data'}), 400
    errors = validate_contract(data)
    if errors:
        return _invalid(errors)  # before spending one of the paid downloads
    if not FREE_MODE:
        intent_id = (body.get('intent_id') or '').strip()
        r = _ziina_confirm(intent_id, 'contract')
        if not r['paid']:
            return jsonify({'error': 'Payment required', 'code': 'payment_required'}), 402
        if not _ledger_safe(_ledger_use_generation, intent_id):
            return jsonify({'error': 'This payment has been used for its downloads. '
                                     'Contact us if you need another copy.', 'code': 'generation_limit'}), 403
    try:
        pdf_bytes = fill_ejari_pdf(data)
    except Exception as e:
        print(f'[generate] error: {type(e).__name__}: {e}', flush=True)
        return jsonify({'error': 'Could not build the PDF. Please try again.'}), 500
    name = f"ejari_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     as_attachment=True, download_name=name)


# ── Landlord link: a shared, short-lived contract draft ─────────────────
# The tenant creates /contract/d/<token> and sends it to the landlord, who
# adds their Emirates ID and Title Deed on that page. Only the extracted text
# values are kept — never files — encrypted with DRAFT_ENC_KEY (Fernet) and
# deleted DRAFT_TTL_HOURS after creation. The key is DRAFT_ENC_KEY or, if unset,
# derived from SECRET_KEY; with neither the feature is off. The DB row is keyed by a hash of the token, so the table alone does not
# reveal working links.
DRAFT_TTL_HOURS = 72
DRAFT_EXT_KEYS = [
    'tenant_name', 'tenant_emirates_id', 'tenant_phone', 'lessor_name', 'lessor_emirates_id', 'owner_name',
    'property_usage', 'building_name', 'property_no', 'property_type', 'property_area', 'location', 'plot_no',
    'premises_no_dewa', 'makani_no', 'tenant_license_no', 'tenant_licensing_authority', 'lessor_license_no',
    'lessor_licensing_authority', 'annual_rent', 'security_deposit', 'contract_from', 'contract_to',
]
DRAFT_FORM_KEYS = [
    'tenant_phone', 'tenant_email', 'lessor_phone', 'lessor_email', 'contract_date', 'contract_from',
    'contract_to', 'annual_rent', 'contract_value', 'security_deposit', 'mode_of_payment', 't1', 't2', 't3', 't4', 't5',
]
_DRAFT_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')  # lowercase hex survives canonical_path()
_mem_drafts = {}


def _draft_cipher():
    """Fernet cipher from DRAFT_ENC_KEY, or derived from SECRET_KEY when that is set.
    None (feature off) only with neither — never with the 'dev-key' fallback."""
    from cryptography.fernet import Fernet
    key = os.environ.get('DRAFT_ENC_KEY', '')
    if key:
        try:
            return Fernet(key.encode())
        except Exception as e:
            print(f'[drafts] DRAFT_ENC_KEY is not a valid Fernet key: {e}', flush=True)
            return None
    secret = os.environ.get('SECRET_KEY') or os.environ.get('ADMIN_PASSWORD', '')
    if not secret:
        return None
    derived = hashlib.sha256(b'ejarihelper-drafts-v1:' + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def drafts_enabled():
    return _draft_cipher() is not None


def _draft_clean(payload):
    def pick(src, keys):
        src = src if isinstance(src, dict) else {}
        return {k: str(src.get(k) or '').strip()[:300] for k in keys}
    return {'ext': pick(payload.get('ext'), DRAFT_EXT_KEYS), 'form': pick(payload.get('form'), DRAFT_FORM_KEYS)}


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _draft_save(token, draft, expires_at=None):
    cipher = _draft_cipher()
    now = _utcnow()
    expires_at = expires_at or now + timedelta(hours=DRAFT_TTL_HOURS)
    blob = cipher.encrypt(json.dumps(draft).encode()).decode()
    conn = _get_conn()
    if not conn:
        _mem_drafts[_token_hash(token)] = (blob, expires_at)
        return expires_at
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM drafts WHERE expires_at < %s', (now,))
                cur.execute('INSERT INTO drafts (token_hash, ciphertext, created_at, expires_at) VALUES (%s, %s, %s, %s) '
                            'ON CONFLICT (token_hash) DO UPDATE SET ciphertext = EXCLUDED.ciphertext',
                            (_token_hash(token), blob, now, expires_at))
    finally:
        conn.close()
    return expires_at


def _draft_load(token):
    """(draft, expires_at) or (None, None) when unknown, expired or undecryptable."""
    cipher = _draft_cipher()
    if not cipher or not _DRAFT_TOKEN_RE.match(token or ''):
        return None, None
    now = _utcnow()
    conn = _get_conn()
    if not conn:
        for k in [k for k, (_, exp) in _mem_drafts.items() if exp < now]:
            del _mem_drafts[k]
        row = _mem_drafts.get(_token_hash(token))
    else:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM drafts WHERE expires_at < %s', (now,))
                    cur.execute('SELECT ciphertext, expires_at FROM drafts WHERE token_hash = %s', (_token_hash(token),))
                    row = cur.fetchone()
        finally:
            conn.close()
    if not row:
        return None, None
    try:
        return json.loads(cipher.decrypt(row[0].encode(), ttl=DRAFT_TTL_HOURS * 3600)), row[1]
    except Exception:
        return None, None


def _draft_response(token, draft, expires_at):
    return jsonify({'ok': True, 'token': token, 'url': f'{request.host_url.rstrip("/")}/contract/d/{token}',
                    'expires_at': expires_at.replace(tzinfo=timezone.utc).isoformat(), **draft})


@app.route('/contract/draft', methods=['POST'])
def draft_create():
    if not drafts_enabled():
        return jsonify({'error': 'Not available'}), 404
    import secrets
    token = secrets.token_hex(16)
    draft = _draft_clean(request.json or {})
    expires_at = _draft_save(token, draft)
    return _draft_response(token, draft, expires_at)


@app.route('/contract/draft/<token>')
def draft_get(token):
    draft, expires_at = _draft_load(token)
    if draft is None:
        return jsonify({'error': 'This link has expired or does not exist.', 'code': 'not_found'}), 404
    return _draft_response(token, draft, expires_at)


@app.route('/contract/draft/<token>/merge', methods=['POST'])
def draft_merge(token):
    """Add the landlord's extracted values. Non-empty values win: the Title Deed is authoritative."""
    draft, expires_at = _draft_load(token)
    if draft is None:
        return jsonify({'error': 'This link has expired or does not exist.', 'code': 'not_found'}), 404
    incoming = _draft_clean(request.json or {})
    for part in ('ext', 'form'):
        for k, v in incoming[part].items():
            if v:
                draft[part][k] = v
    _draft_save(token, draft, expires_at)  # same expiry: merging never extends the 72 h
    return _draft_response(token, draft, expires_at)


@app.route('/contract/d/<token>')
def draft_page(token):
    draft, _ = _draft_load(token)
    body, _status, headers = render_page('contract-draft.html')
    headers = dict(headers, **{'X-Robots-Tag': 'noindex, nofollow', 'Referrer-Policy': 'no-referrer',
                               'Cache-Control': 'no-store'})
    return body, (200 if draft is not None else 404), headers


import requests as req_lib
import uuid, hmac, hashlib

ZIINA_API_KEY = os.environ.get('ZIINA_API_KEY', '')
ZIINA_API     = 'https://api-v2.ziina.com/api'
ZIINA_HEADERS = {'Authorization': f'Bearer {ZIINA_API_KEY}', 'Content-Type': 'application/json'}

PRODUCTS = {
    'contract':     {'name': 'Ejari tenancy contract', 'amount_fils': CONTRACT_PRICE_FILS},
    'lawyer':       {'name': f'AI rental lawyer — {LEGAL_SESSION_MINUTES} min', 'amount_fils': LEGAL_PRICE_FILS},
    'lawyer_files': {'name': f'AI rental lawyer — +{LEGAL_FILE_TOPUP_FILES} file uploads', 'amount_fils': LEGAL_FILE_TOPUP_FILS},
}

_INTENT_ID_RE = re.compile(r'^[A-Za-z0-9_-]{8,64}$')


# ── Payment errors → server log + Telegram ─────────────────────────────
_ALERT_EVERY_SECONDS = 600
_last_alert = {}  # stage -> epoch seconds, per worker


def _payment_error(stage, product='', intent_id='', detail=''):
    """Log a payment failure with context and alert Telegram (max once per stage per 10 min)."""
    import time as _time
    detail = str(detail)[:500]
    print('[payment-error] ' + json.dumps({
        'stage': stage, 'product': product, 'intent_id': intent_id,
        'path': request.path if request else '', 'detail': detail,
    }), flush=True)
    now = _time.time()
    if now - _last_alert.get(stage, 0) < _ALERT_EVERY_SECONDS:
        return
    _last_alert[stage] = now
    _send_telegram(
        f'⚠️ <b>Payment error: {stage}</b>\n'
        f'🧾 {product or "?"} · {intent_id or "no intent"}\n'
        f'{detail[:300]}\n'
        f'⏰ {datetime.now().strftime("%d %b %Y, %H:%M")}'
    )


# ── Payment ledger ─────────────────────────────────────────────────────
# One row per Ziina intent: id, product, amount, status, timestamps — no
# email, name or documents. It makes confirmation idempotent across the two
# gunicorn workers and restarts, and lets the front-end report each purchase
# to GA4 exactly once. Without DATABASE_URL (local dev) a dict stands in.
_mem_payments = {}


def _utcnow():
    """Naive UTC, matching the ledger's NOW() AT TIME ZONE 'utc'."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


_mem_lock = threading.Lock()


def _ledger_record(intent_id, product, amount_fils):
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            _mem_payments.setdefault(intent_id, {
                'intent_id': intent_id, 'product': product, 'amount_fils': amount_fils,
                'status': 'created', 'confirmed_at': None, 'ga_reported_at': None, 'generations': 0})
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO payments (intent_id, product, amount_fils) VALUES (%s, %s, %s) '
                            'ON CONFLICT (intent_id) DO NOTHING', (intent_id, product, amount_fils))
    finally:
        conn.close()


def _ledger_get(intent_id):
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            row = _mem_payments.get(intent_id)
            return dict(row) if row else None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('SELECT intent_id, product, amount_fils, status, confirmed_at, ga_reported_at, generations '
                            'FROM payments WHERE intent_id = %s', (intent_id,))
                r = cur.fetchone()
    finally:
        conn.close()
    if not r:
        return None
    keys = ('intent_id', 'product', 'amount_fils', 'status', 'confirmed_at', 'ga_reported_at', 'generations')
    return dict(zip(keys, r))


def _ledger_mark_paid(intent_id, product, amount_fils):
    """Mark an intent completed. Returns True only for the call that flipped it."""
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            row = _mem_payments.setdefault(intent_id, {
                'intent_id': intent_id, 'product': product, 'amount_fils': amount_fils,
                'status': 'created', 'confirmed_at': None, 'ga_reported_at': None, 'generations': 0})
            if row['confirmed_at']:
                return False
            row.update(status='completed', confirmed_at=_utcnow())
            return True
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO payments (intent_id, product, amount_fils) VALUES (%s, %s, %s) '
                            'ON CONFLICT (intent_id) DO NOTHING', (intent_id, product, amount_fils))
                cur.execute("UPDATE payments SET status = 'completed', confirmed_at = NOW() AT TIME ZONE 'utc' "
                            'WHERE intent_id = %s AND confirmed_at IS NULL RETURNING 1', (intent_id,))
                return cur.fetchone() is not None
    finally:
        conn.close()


def _ledger_claim_report(intent_id):
    """Atomically claim the right to report this purchase to analytics (once ever)."""
    conn = _get_conn()
    if not conn:
        with _mem_lock:
            row = _mem_payments.get(intent_id)
            if not row or row['status'] != 'completed' or row['ga_reported_at']:
                return False
            row['ga_reported_at'] = _utcnow()
            return True
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE payments SET ga_reported_at = NOW() AT TIME ZONE 'utc' WHERE intent_id = %s "
                            "AND status = 'completed' AND ga_reported_at IS NULL RETURNING 1", (intent_id,))
                return cur.fetchone() is not None
    finally:
        conn.close()


def _ledger_safe(fn, *args):
    """Run a ledger call; a DB hiccup must never block a paying customer."""
    try:
        return fn(*args)
    except Exception as e:
        _payment_error('ledger_db', args[1] if len(args) > 1 else '', args[0] if args else '', e)
        return None


def _product_for_amount(amount_fils):
    for key, p in PRODUCTS.items():
        if p['amount_fils'] == amount_fils:
            return key
    return 'unknown'


def _notify_sale(product, intent_id, amount_fils, data):
    """One-time side effects of a new sale: Telegram, plus a Trustpilot invite for chat."""
    email, name = _ziina_customer_info(data or {})
    label = {'contract': '💰 <b>Contract sold</b>', 'lawyer': '💼 <b>Legal Chat unlocked</b>',
             'lawyer_files': '📎 <b>Legal Chat file top-up</b>'}.get(product, f'💳 <b>Payment ({product})</b>')
    _send_telegram(
        f'{label}\n'
        f'💵 AED {amount_fils / 100:g}\n'
        f'📧 {email or "(no email)"}\n'
        f'🧾 {intent_id}\n'
        f'⏰ {datetime.now().strftime("%d %b %Y, %H:%M")}'
    )
    if product == 'lawyer' and email:
        trustpilot_invite(email, name, reference_id=f'legal-{intent_id}', delay_days=3)


def _ziina_create(product, success_url, cancel_url, failure_url):
    """Create a Ziina payment intent for a product. Returns (data, error_message)."""
    p = PRODUCTS[product]
    payload = {
        'amount': p['amount_fils'],
        'currency_code': 'AED',
        'message': f'Ejari Helper — {p["name"]}',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'failure_url': failure_url,
        'allow_tips': False,
        'operation_id': str(uuid.uuid4()),
    }
    try:
        resp = req_lib.post(f'{ZIINA_API}/payment_intent', json=payload, headers=ZIINA_HEADERS, timeout=10)
    except Exception as e:
        _payment_error('create_exception', product, '', e)
        return None, 'Payment provider is unreachable. Please try again in a minute.'
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code not in (200, 201) or 'embedded_url' not in data:
        _payment_error('create_http', product, '', f'HTTP {resp.status_code}: {str(data)[:300] or resp.text[:300]}')
        return None, 'Could not start the payment. Please try again.'
    intent_id = data.get('id', '')
    print(f'[payment] created {product} intent {intent_id}', flush=True)
    _ledger_safe(_ledger_record, intent_id, product, p['amount_fils'])
    return data, None


def _ziina_confirm(intent_id, expected_product=None):
    """Confirm an intent with the ledger and, if needed, Ziina's API.

    Returns {'paid', 'status', 'product', 'amount_fils', 'newly_paid', 'confirmed_at'}.
    A sale notification goes out once, for whichever call first sees the
    intent completed (redirect, polling or webhook).
    """
    result = {'paid': False, 'status': '', 'product': expected_product or '',
              'amount_fils': 0, 'newly_paid': False, 'confirmed_at': None}
    if not intent_id or not _INTENT_ID_RE.match(intent_id):
        result['status'] = 'invalid'
        return result
    row = _ledger_safe(_ledger_get, intent_id)
    if row and row['status'] == 'completed':
        result.update(paid=True, status='completed', product=row['product'],
                      amount_fils=row['amount_fils'], confirmed_at=row['confirmed_at'])
    else:
        try:
            resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
            data = resp.json()
        except Exception as e:
            _payment_error('confirm_exception', expected_product or '', intent_id, e)
            result['status'] = 'error'
            return result
        if resp.status_code != 200:
            _payment_error('confirm_http', expected_product or '', intent_id,
                           f'HTTP {resp.status_code}: {str(data)[:300]}')
            result['status'] = 'error'
            return result
        result['status'] = data.get('status', '')
        if result['status'] != 'completed':
            return result
        amount = int(data.get('amount') or 0)
        product = row['product'] if row else (expected_product or _product_for_amount(amount))
        expected_amount = row['amount_fils'] if row else PRODUCTS.get(product, {}).get('amount_fils', amount)
        if amount and amount != expected_amount:
            _payment_error('amount_mismatch', product, intent_id, f'paid {amount} fils, expected {expected_amount}')
            return result
        newly = _ledger_safe(_ledger_mark_paid, intent_id, product, amount or expected_amount)
        row = _ledger_safe(_ledger_get, intent_id) or {}
        result.update(paid=True, product=product, amount_fils=amount or expected_amount,
                      newly_paid=bool(newly), confirmed_at=row.get('confirmed_at'))
        if newly:
            _notify_sale(product, intent_id, result['amount_fils'], data)
    if expected_product and result['product'] != expected_product:
        # A completed intent for another product must not unlock this one.
        _payment_error('product_mismatch', expected_product, intent_id, f'intent is for {result["product"]}')
        result['paid'] = False
    return result


@app.route('/payment/confirm', methods=['POST'])
def payment_confirm():
    """Server-confirmed payment status for analytics.

    `report` is true for exactly one call per transaction, ever — the
    front-end fires `purchase` / `payment_success` / `chat_paid` only then.
    """
    body = request.json or {}
    intent_id = (body.get('intent_id') or '').strip()
    product = body.get('product') or None
    if product not in PRODUCTS:
        product = None
    r = _ziina_confirm(intent_id, product)
    if not r['paid']:
        return jsonify({'paid': False, 'status': r['status']})
    report = bool(_ledger_safe(_ledger_claim_report, intent_id))
    return jsonify({
        'paid': True,
        'report': report,
        'transaction_id': intent_id,
        'product': r['product'],
        'item_name': PRODUCTS.get(r['product'], {}).get('name', r['product']),
        'value': r['amount_fils'] / 100,
        'currency': 'AED',
    })


# Apple Pay domain verification — required by Ziina embedded checkout.
# Ziina/Apple gives you a verification string; provide it either via the
# APPLE_PAY_DOMAIN_FILE env var or a file in the repo root named
# apple-developer-merchantid-domain-association (no extension).
_APPLE_PAY_FILE = Path(__file__).resolve().parent / 'apple-developer-merchantid-domain-association'


@app.route('/.well-known/apple-developer-merchantid-domain-association')
@app.route('/.well-known/apple-developer-merchantid-domain-association.txt')
def apple_pay_domain_association():
    """Serve the Apple Pay domain-association file for Ziina embedded checkout."""
    content = os.environ.get('APPLE_PAY_DOMAIN_FILE', '')
    if not content and _APPLE_PAY_FILE.exists():
        content = _APPLE_PAY_FILE.read_text().strip()
    if not content:
        return 'Apple Pay domain association not configured', 404
    return Response(content, mimetype='text/plain')


@app.route('/create-payment', methods=['POST'])
def create_payment():
    """Create a Ziina Payment Intent and return redirect_url to frontend."""
    base_url = request.host_url.rstrip('/')
    data, error = _ziina_create(
        'contract',
        # Ziina substitutes the intent id, so the return is verifiable even
        # when it lands in a new tab or another browser (no sessionStorage).
        success_url=f'{base_url}/?paid=1&intent_id={{PAYMENT_INTENT_ID}}',
        cancel_url=f'{base_url}/?cancelled=1',
        failure_url=f'{base_url}/?failed=1',
    )
    if error:
        return jsonify({'error': error}), 502
    return jsonify({
        'ok': True,
        'embedded_url': data['embedded_url'],
        'redirect_url': data.get('redirect_url', ''),
        'intent_id': data.get('id', ''),
    })


@app.route('/payment-success')
def payment_success():
    """Legacy Ziina return URL — verify, then hand over to the homepage."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return redirect('/')
    r = _ziina_confirm(intent_id, 'contract')
    if r['paid']:
        return redirect(f'/?paid=1&intent_id={intent_id}')
    return redirect(f'/?payment_pending=1&intent_id={intent_id}')


@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Frontend polls this to confirm payment is completed."""
    intent_id = (request.json or {}).get('intent_id', '')
    if not intent_id:
        return jsonify({'paid': False, 'error': 'No intent_id'}), 400
    r = _ziina_confirm(intent_id, 'contract')
    return jsonify({'paid': r['paid'], 'status': r['status']})


@app.route('/webhook/ziina', methods=['POST'])
def ziina_webhook():
    """Receive Ziina webhook events."""
    # Verify HMAC signature if secret is configured
    webhook_secret = os.environ.get('ZIINA_WEBHOOK_SECRET', '')
    if webhook_secret:
        sig = request.headers.get('X-Hmac-Signature', '')
        expected = hmac.new(webhook_secret.encode(), request.data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            _payment_error('webhook_sig', '', '', 'invalid X-Hmac-Signature')
            return jsonify({'error': 'Invalid signature'}), 401
    else:
        print('[payment] WARNING: ZIINA_WEBHOOK_SECRET not set — webhook is unauthenticated', flush=True)

    try:
        event = request.json or {}
        data = event.get('data', {})
        if event.get('event') == 'payment_intent.status.updated':
            intent_id = data.get('id')
            print(f'[payment] webhook {intent_id} → {data.get("status")}', flush=True)
            if data.get('status') == 'completed' and intent_id:
                # Re-read the intent from Ziina rather than trusting the body.
                _ziina_confirm(intent_id)
        return jsonify({'ok': True})
    except Exception as e:
        _payment_error('webhook_exception', '', '', e)
        return jsonify({'error': 'Webhook processing failed'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5055, debug=False)
