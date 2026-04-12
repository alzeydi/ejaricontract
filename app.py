#!/usr/bin/env python3
"""Ejari Tenancy Contract Generator - Flask Backend"""

import io, os, base64, json
from pathlib import Path
from datetime import datetime
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import anthropic

app = Flask(__name__, static_folder='static')
CORS(app)

TEMPLATE_PDF = os.path.join(os.path.dirname(__file__), 'template.pdf')
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

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


# ── Ratings storage ────────────────────────────────────────────────────
RATINGS_FILE = Path(os.path.dirname(__file__)) / 'ratings.json'

def load_ratings():
    try:
        if RATINGS_FILE.exists():
            return json.loads(RATINGS_FILE.read_text())
    except Exception:
        pass
    return {'total': 0, 'count': 0}

def save_ratings(data):
    try:
        RATINGS_FILE.write_text(json.dumps(data))
    except Exception:
        pass

def rating_json_fragment():
    """Return aggregateRating JSON fragment for schema injection (empty until 3+ reviews)."""
    r = load_ratings()
    if r['count'] < 3:
        return ''
    avg = round(r['total'] / r['count'], 1)
    return f', "aggregateRating": {{"@type": "AggregateRating", "ratingValue": "{avg}", "ratingCount": "{r[\'count\']}"}}'

# ── Routes ─────────────────────────────────────────────────────────────

@app.before_request
def redirect_www():
    """Redirect www.ejarihelper.ae → ejarihelper.ae"""
    from flask import redirect, request as req
    host = req.host.lower()
    if host.startswith('www.'):
        url = req.url.replace('://www.', '://', 1)
        return redirect(url, code=301)

@app.route('/')
def index():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    with open(os.path.join(app.static_folder, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    html = html.replace('__BASE_URL__', base_url)
    html = html.replace('__RATING_JSON__', rating_json_fragment())
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/rate', methods=['POST'])
def rate():
    body = request.json or {}
    stars = body.get('stars')
    if not isinstance(stars, int) or stars < 1 or stars > 5:
        return jsonify({'ok': False, 'error': 'Invalid rating'}), 400
    data = load_ratings()
    data['total'] += stars
    data['count'] += 1
    save_ratings(data)
    return jsonify({'ok': True})

@app.route('/robots.txt')
def robots_txt():
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    content = f'User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n'
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
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'template': os.path.exists(TEMPLATE_PDF)})

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

        # Validate payment session — one payment = one extraction
        if intent_id:
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

        # Mark intent as used — prevents re-use of the same payment
        if intent_id:
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

        if resp.status_code not in (200, 201) or 'redirect_url' not in data:
            return jsonify({'error': data.get('message', 'Ziina error'), 'raw': data}), 502

        # Fix the success_url placeholder — Ziina doesn't template {id}, so we pass it manually
        intent_id = data.get('id', '')
        redirect = data['redirect_url']

        return jsonify({'ok': True, 'redirect_url': redirect, 'intent_id': intent_id})

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
