#!/usr/bin/env python3
"""Ejari Tenancy Contract Generator - Flask Backend"""

import io, os, base64, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from flask import Flask, request, send_file, jsonify, send_from_directory, session, redirect
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
# FREE_MODE=false (default) → users must pay 30 AED via Ziina before extraction
FREE_MODE = os.environ.get('FREE_MODE', 'false').lower() in ('1', 'true', 'yes')

# LEGAL_FREE_MODE=true  → /legal-chat is unlimited and free (paywall hidden)
# LEGAL_FREE_MODE=false (default) → users pay 100 AED for a 30-minute session
LEGAL_FREE_MODE = os.environ.get('LEGAL_FREE_MODE', 'false').lower() in ('1', 'true', 'yes')

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

@app.before_request
def redirect_canonical():
    """Force canonical host (no www) AND canonical scheme (https) in a single 301.
    Avoids the http→https→non-www redirect chain that confuses Googlebot and
    causes 'Page with redirect' indexing errors."""
    from flask import redirect, request as req
    host = req.host.lower()
    proto = req.headers.get('X-Forwarded-Proto', 'http' if not req.is_secure else 'https').lower()
    needs_https = proto == 'http' and not host.startswith('localhost') and not host.startswith('127.')
    needs_apex = host.startswith('www.')
    if needs_https or needs_apex:
        new_host = host[4:] if needs_apex else host
        new_scheme = 'https' if needs_https else proto
        return redirect(f'{new_scheme}://{new_host}{req.full_path.rstrip("?")}', code=301)

@app.route('/')
def index():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

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


@app.route('/robots.txt')
def robots_txt():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    content = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /admin\n'
        'Disallow: /admin/\n'
        'Disallow: /payment-success\n'
        'Disallow: /verify-payment\n'
        'Disallow: /create-payment\n'
        'Disallow: /legal-chat/payment-success\n'
        'Disallow: /legal-chat/create-payment\n'
        'Disallow: /legal-chat/message\n'
        'Disallow: /legal-chat/state\n'
        'Disallow: /legal-chat/files-payment\n'
        'Disallow: /legal-chat/files-payment-success\n'
        f'Sitemap: {base_url}/sitemap.xml\n'
    )
    return content, 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap_xml():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/guide/ejari-registration</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base_url}/guide/dewa-activation</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base_url}/guide/rental-dispute</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base_url}/guide/ejari-renewal</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base_url}/guide/tenancy-contract-dubai</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base_url}/guide/dewa-premises-number</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>{base_url}/guide/dewa-transfer</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base_url}/guide/ejari-cancellation</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base_url}/legal-chat</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{base_url}/how-it-works</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{base_url}/privacy</loc>
    <changefreq>yearly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>{base_url}/terms</loc>
    <changefreq>yearly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}


_GUIDE_SLUGS = {'ejari-registration', 'dewa-activation', 'rental-dispute',
                'ejari-renewal', 'dewa-premises-number', 'tenancy-contract-dubai',
                'dewa-transfer', 'ejari-cancellation'}

@app.route('/guide/<slug>')
def guide(slug):
    if slug not in _GUIDE_SLUGS:
        from flask import redirect
        return redirect('/', 302)
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    guide_path = os.path.join(app.static_folder, 'guide', f'{slug}.html')
    with open(guide_path, encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/privacy')
def privacy():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'privacy.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/terms')
def terms():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'terms.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


# ── Legal Chat (paid AI consultation on Dubai rental disputes) ─────────
LEGAL_FREE_MESSAGES = 1
LEGAL_SESSION_MINUTES = 30
LEGAL_PRICE_FILS = 10000  # 100 AED

# File-upload quota: first 3 files in a session are free, then each
# 50 AED top-up grants 3 more uploads.
LEGAL_FILE_FREE_LIMIT = 3
LEGAL_FILE_TOPUP_FILS = 5000   # 50 AED
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
    allowance grows by LEGAL_FILE_TOPUP_FILES each successful 50 AED top-up.
    """
    used = int(session.get('legal_files_used', 0))
    extra = int(session.get('legal_files_extra', 0))
    allowance = LEGAL_FILE_FREE_LIMIT + extra
    remaining = max(0, allowance - used)
    return used, allowance, remaining


@app.route('/legal-chat')
def legal_chat_page():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'legal-chat.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/legal-chat/state')
def legal_chat_state():
    mode, remaining, paid_until = _legal_access_state()
    files_used, files_allowance, files_remaining = _legal_files_state()
    return jsonify({
        'mode': mode,
        'remaining_free': remaining,
        'paid_until': paid_until,
        'free_mode': LEGAL_FREE_MODE,
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
    """Create Ziina payment intent for 100 AED legal chat unlock."""
    try:
        base_url = request.host_url.rstrip('/')
        payload = {
            'amount': LEGAL_PRICE_FILS,
            'currency_code': 'AED',
            'message': f'Ejari Helper — AI Legal Chat ({LEGAL_SESSION_MINUTES} min)',
            'success_url': f'{base_url}/legal-chat/payment-success?intent_id={{PAYMENT_INTENT_ID}}',
            'cancel_url':  f'{base_url}/legal-chat?cancelled=1',
            'failure_url': f'{base_url}/legal-chat?failed=1',
            'allow_tips': False,
            'operation_id': str(uuid.uuid4()),
        }
        resp = req_lib.post(f'{ZIINA_API}/payment_intent', json=payload, headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if resp.status_code not in (200, 201) or 'embedded_url' not in data:
            return jsonify({'error': data.get('message', 'Ziina error'), 'raw': data}), 502
        return jsonify({
            'ok': True,
            'embedded_url': data['embedded_url'],
            'redirect_url': data.get('redirect_url', ''),
            'intent_id': data.get('id', ''),
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


def _grant_legal_session(intent_id, data):
    """Mark a verified, completed intent as a fresh 30-minute legal-chat session."""
    paid_until = datetime.now(timezone.utc) + timedelta(minutes=LEGAL_SESSION_MINUTES)
    session['legal_paid_until'] = paid_until.isoformat()
    session['legal_free_used'] = 0
    email, name = _ziina_customer_info(data)
    _send_telegram(
        f'💼 <b>Legal Chat unlocked</b>\n'
        f'💵 AED {LEGAL_PRICE_FILS // 100}\n'
        f'📧 {email or "(no email)"}\n'
        f'⏰ {datetime.now().strftime("%d %b %Y, %H:%M")}'
    )
    if email:
        trustpilot_invite(email, name, reference_id=f'legal-{intent_id}', delay_days=3)
    return paid_until


@app.route('/legal-chat/verify-payment', methods=['POST'])
def legal_verify_payment():
    """Embedded-checkout callback — verify the intent and grant a 30-min window."""
    try:
        intent_id = (request.json or {}).get('intent_id', '')
        if not intent_id:
            return jsonify({'paid': False, 'error': 'No intent_id'}), 400
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if data.get('status') == 'completed':
            paid_until = _grant_legal_session(intent_id, data)
            return jsonify({'paid': True, 'paid_until': paid_until.isoformat()})
        return jsonify({'paid': False, 'status': data.get('status', '')})
    except Exception as e:
        return jsonify({'paid': False, 'error': str(e)}), 500


@app.route('/legal-chat/payment-success')
def legal_payment_success():
    """Ziina redirect target — verify payment and grant a 30-min chat window."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return redirect('/legal-chat')
    try:
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if data.get('status') == 'completed':
            _grant_legal_session(intent_id, data)
            return redirect(f'/legal-chat?unlocked=1&tid={intent_id}')
        return redirect(f'/legal-chat?pending=1')
    except Exception as e:
        return f'Error verifying payment: {e}', 500


@app.route('/legal-chat/files-payment', methods=['POST'])
def legal_files_payment():
    """Create Ziina payment intent for a 50 AED file-upload top-up (+3 files)."""
    try:
        base_url = request.host_url.rstrip('/')
        payload = {
            'amount': LEGAL_FILE_TOPUP_FILS,
            'currency_code': 'AED',
            'message': f'Ejari Helper — Legal Chat file uploads (+{LEGAL_FILE_TOPUP_FILES})',
            'success_url': f'{base_url}/legal-chat/files-payment-success?intent_id={{PAYMENT_INTENT_ID}}',
            'cancel_url':  f'{base_url}/legal-chat?files_cancelled=1',
            'failure_url': f'{base_url}/legal-chat?files_failed=1',
            'allow_tips': False,
            'operation_id': str(uuid.uuid4()),
        }
        resp = req_lib.post(f'{ZIINA_API}/payment_intent', json=payload, headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if resp.status_code not in (200, 201) or 'embedded_url' not in data:
            return jsonify({'error': data.get('message', 'Ziina error'), 'raw': data}), 502
        return jsonify({
            'ok': True,
            'embedded_url': data['embedded_url'],
            'redirect_url': data.get('redirect_url', ''),
            'intent_id': data.get('id', ''),
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


def _grant_legal_files(intent_id, data):
    """Grant +N uploads for a verified, completed top-up intent (idempotent)."""
    granted = set(session.get('legal_files_intents', []))
    if intent_id not in granted:
        session['legal_files_extra'] = int(session.get('legal_files_extra', 0)) + LEGAL_FILE_TOPUP_FILES
        granted.add(intent_id)
        session['legal_files_intents'] = list(granted)
        email, _name = _ziina_customer_info(data)
        _send_telegram(
            f'📎 <b>Legal Chat file top-up</b>\n'
            f'💵 AED {LEGAL_FILE_TOPUP_FILS // 100} · +{LEGAL_FILE_TOPUP_FILES} uploads\n'
            f'📧 {email or "(no email)"}\n'
            f'⏰ {datetime.now().strftime("%d %b %Y, %H:%M")}'
        )


@app.route('/legal-chat/files-verify-payment', methods=['POST'])
def legal_files_verify_payment():
    """Embedded-checkout callback — verify the top-up intent and grant +3 uploads."""
    try:
        intent_id = (request.json or {}).get('intent_id', '')
        if not intent_id:
            return jsonify({'paid': False, 'error': 'No intent_id'}), 400
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if data.get('status') == 'completed':
            _grant_legal_files(intent_id, data)
            return jsonify({'paid': True, 'added': LEGAL_FILE_TOPUP_FILES})
        return jsonify({'paid': False, 'status': data.get('status', '')})
    except Exception as e:
        return jsonify({'paid': False, 'error': str(e)}), 500


@app.route('/legal-chat/files-payment-success')
def legal_files_payment_success():
    """Ziina redirect target — verify payment and grant +3 file uploads."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return redirect('/legal-chat')
    try:
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        if data.get('status') == 'completed':
            _grant_legal_files(intent_id, data)
            return redirect('/legal-chat?files_unlocked=1')
        return redirect('/legal-chat?files_pending=1')
    except Exception as e:
        return f'Error verifying payment: {e}', 500


@app.route('/how-it-works')
def how_it_works():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'how-it-works.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/download/dld-tenancy-contract.pdf')
def download_template():
    """Serve the blank DLD tenancy contract form for manual filling."""
    return send_file(TEMPLATE_PDF, mimetype='application/pdf',
                     as_attachment=True, download_name='dld-tenancy-contract.pdf')


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
    return jsonify({'free_mode': FREE_MODE, 'legal_free_mode': LEGAL_FREE_MODE})


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


def extract_one(f):
    """Extract data from a single document using haiku (fast)."""
    prompt = DOC_PROMPTS.get(f['label'], 'Extract all key text fields. Return ONLY JSON.')
    content = [build_content_block(f), {'type': 'text', 'text': prompt}]
    msg = claude.messages.create(
        model='claude-haiku-4-5',
        max_tokens=300,
        messages=[{'role': 'user', 'content': content}]
    )
    text = ''.join(b.text for b in msg.content if hasattr(b, 'text'))
    text = text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)


@app.route('/extract', methods=['POST'])
def extract():
    """OCR endpoint — parallel per-document extraction with haiku."""
    try:
        payload = request.json
        files = payload.get('files', [])
        intent_id = payload.get('intent_id', '')

        if not files:
            return jsonify({'error': 'No files provided'}), 400

        # Validate payment session — one payment = one extraction (skipped in FREE_MODE)
        if not FREE_MODE and intent_id:
            if intent_id in used_intents:
                return jsonify({'error': 'This payment has already been used. Please make a new payment to extract again.', 'code': 'already_used'}), 403

        # Run all documents in parallel threads
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(extract_one, f): f['label'] for f in files}
            for future in as_completed(futures):
                label = futures[future]
                try:
                    results[label] = future.result()
                except Exception as e:
                    results[label] = {}  # skip failed doc, don't break whole request

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

        # Mark intent as used — prevents re-use of the same payment (skipped in FREE_MODE)
        if not FREE_MODE and intent_id:
            used_intents.add(intent_id)

        return jsonify({'ok': True, 'data': merged})

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        if not data: return jsonify({'error': 'No data'}), 400
        if not data.get('date'):
            data['date'] = datetime.now().strftime('%d/%m/%Y')
        pdf_bytes = fill_ejari_pdf(data)
        name = f"ejari_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                         as_attachment=True, download_name=name)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


import requests as req_lib
import uuid, hmac, hashlib

ZIINA_API_KEY = os.environ.get('ZIINA_API_KEY', '')
ZIINA_API     = 'https://api-v2.ziina.com/api'
ZIINA_HEADERS = {'Authorization': f'Bearer {ZIINA_API_KEY}', 'Content-Type': 'application/json'}

# In-memory store of paid and used payment_intent ids (replace with DB in production)
paid_intents = set()
used_intents = set()  # intent_ids that have already been used for extraction


@app.route('/create-payment', methods=['POST'])
def create_payment():
    """Create a Ziina Payment Intent and return redirect_url to frontend."""
    try:
        base_url = request.host_url.rstrip('/')
        payload = {
            'amount': 3000,          # 30 AED in fils
            'currency_code': 'AED',
            'message': 'Ejari Helper — AI document extraction',
            'success_url': f'{base_url}/?paid=1',
            'cancel_url':  f'{base_url}/?cancelled=1',
            'failure_url': f'{base_url}/?failed=1',
            'allow_tips': False,
            'operation_id': str(uuid.uuid4()),
        }
        resp = req_lib.post(f'{ZIINA_API}/payment_intent', json=payload, headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()

        if resp.status_code not in (200, 201) or 'embedded_url' not in data:
            return jsonify({'error': data.get('message', 'Ziina error'), 'raw': data}), 502

        intent_id = data.get('id', '')

        return jsonify({
            'ok': True,
            'embedded_url': data['embedded_url'],
            'redirect_url': data.get('redirect_url', ''),
            'intent_id': intent_id,
        })

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/payment-success')
def payment_success():
    """Ziina redirects here after successful payment. Verify and mark as paid."""
    intent_id = request.args.get('intent_id', '')
    if not intent_id:
        return send_from_directory('static', 'index.html')

    try:
        # Verify with Ziina API that payment is actually completed
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        status = data.get('status', '')

        if status == 'completed':
            paid_intents.add(intent_id)
            # Redirect to frontend with paid flag
            return f'''<html><head><meta http-equiv="refresh" content="0;url=/?paid=1&intent_id={intent_id}"></head>
            <body>Payment confirmed, redirecting...</body></html>'''
        else:
            return f'''<html><head><meta http-equiv="refresh" content="0;url=/?payment_pending=1&intent_id={intent_id}"></head>
            <body>Payment status: {status}</body></html>'''

    except Exception as e:
        return f'Error verifying payment: {e}', 500


@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Frontend polls this to confirm payment is completed."""
    try:
        intent_id = (request.json or {}).get('intent_id', '')
        if not intent_id:
            return jsonify({'paid': False, 'error': 'No intent_id'}), 400

        # Check in-memory cache first
        if intent_id in paid_intents:
            return jsonify({'paid': True})

        # Double-check with Ziina API
        resp = req_lib.get(f'{ZIINA_API}/payment_intent/{intent_id}', headers=ZIINA_HEADERS, timeout=10)
        data = resp.json()
        status = data.get('status', '')
        paid = status == 'completed'

        if paid:
            paid_intents.add(intent_id)

        return jsonify({'paid': paid, 'status': status})

    except Exception as e:
        return jsonify({'paid': False, 'error': str(e)}), 500


@app.route('/webhook/ziina', methods=['POST'])
def ziina_webhook():
    """Receive Ziina webhook events."""
    # Verify HMAC signature if secret is configured
    webhook_secret = os.environ.get('ZIINA_WEBHOOK_SECRET', '')
    if webhook_secret:
        sig = request.headers.get('X-Hmac-Signature', '')
        expected = hmac.new(webhook_secret.encode(), request.data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return jsonify({'error': 'Invalid signature'}), 401

    try:
        event = request.json
        event_type = event.get('event')
        data = event.get('data', {})

        if event_type == 'payment_intent.status.updated':
            intent_id = data.get('id')
            status    = data.get('status')
            if status == 'completed' and intent_id:
                paid_intents.add(intent_id)
                print(f'[Ziina] Payment completed: {intent_id}')

        return jsonify({'ok': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5055, debug=False)
