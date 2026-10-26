#!/usr/bin/env python3
"""Search Console data for the SEO agent (service account, cloud-only).

Key JSON in env GSC_SERVICE_ACCOUNT_JSON (or path in GSC_SERVICE_ACCOUNT_FILE);
the account must be a Full user on property sc-domain:ejarihelper.ae.

  overview [--days 28]              totals + previous period + daily trend
  pages [--days 28] [--limit 60]    per-page metrics, this vs previous window
  queries [--days 90] --out f.tsv   query x page rows (for opportunities.py)
  inspect URL [URL ...]             URL Inspection (index status)
  sitemaps                          list sitemaps
  submit-sitemap [URL]              (re)submit sitemap

Data lags 2-3 days; inspection quota 2,000/day. Requesting indexing is not in the API.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys

import requests

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
except ImportError:  # pragma: no cover
    sys.exit('pip install google-auth requests --break-system-packages')

SITE = os.environ.get('GSC_SITE', 'sc-domain:ejarihelper.ae')
API = 'https://searchconsole.googleapis.com'
SCOPES = ['https://www.googleapis.com/auth/webmasters']


def _creds():
    raw = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
    path = os.environ.get('GSC_SERVICE_ACCOUNT_FILE')
    if raw:
        c = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif path:
        c = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    else:
        sys.exit('GSC_SERVICE_ACCOUNT_JSON or GSC_SERVICE_ACCOUNT_FILE is not set')
    c.refresh(Request())
    return c


def _session():
    s = requests.Session()
    s.headers['Authorization'] = f'Bearer {_creds().token}'
    return s


def _q(site):
    return requests.utils.quote(site, safe='')


def query(s, body):
    r = s.post(f'{API}/webmasters/v3/sites/{_q(SITE)}/searchAnalytics/query', json=body, timeout=60)
    r.raise_for_status()
    return r.json().get('rows', [])


def window(days, end_lag=3):
    end = dt.date.today() - dt.timedelta(days=end_lag)
    return (end - dt.timedelta(days=days - 1)).isoformat(), end.isoformat()


def prev_window(cur, days):
    pe = dt.date.fromisoformat(cur[0]) - dt.timedelta(days=1)
    return (pe - dt.timedelta(days=days - 1)).isoformat(), pe.isoformat()


def totals(rows):
    c = sum(r['clicks'] for r in rows)
    i = sum(r['impressions'] for r in rows)
    pos = sum(r['position'] * r['impressions'] for r in rows) / i if i else 0
    return {'clicks': c, 'impressions': i, 'ctr': round(c / i, 4) if i else 0, 'position': round(pos, 1)}


def cmd_overview(a):
    s = _session()
    cur = window(a.days)
    out = {'site': SITE}
    for name, (st, en) in (('current', cur), ('previous', prev_window(cur, a.days))):
        rows = query(s, {'startDate': st, 'endDate': en, 'dimensions': ['date'], 'rowLimit': 1000})
        out[name] = {'start': st, 'end': en, **totals(rows)}
        if name == 'current':
            out['daily'] = [{'date': r['keys'][0], 'clicks': r['clicks'], 'impressions': r['impressions'],
                             'position': round(r['position'], 1)} for r in rows]
    c, p = out['current'], out['previous']
    out['delta'] = {k: (round((c[k] - p[k]) / p[k] * 100, 1) if p[k] else None) for k in ('clicks', 'impressions')}
    print(json.dumps(out, indent=1))


def cmd_pages(a):
    s = _session()
    cur = window(a.days)
    prev = prev_window(cur, a.days)

    def fetch(st, en):
        agg = {}
        for r in query(s, {'startDate': st, 'endDate': en, 'dimensions': ['page'], 'rowLimit': 1000}):
            d = agg.setdefault(r['keys'][0].split('#', 1)[0], {'clicks': 0, 'impressions': 0, 'posw': 0.0})
            d['clicks'] += r['clicks']
            d['impressions'] += r['impressions']
            d['posw'] += r['position'] * r['impressions']
        return agg

    c, p = fetch(*cur), fetch(*prev)
    zero = {'clicks': 0, 'impressions': 0, 'posw': 0}
    res = []
    for page in sorted(set(c) | set(p), key=lambda k: -c.get(k, zero)['impressions']):
        cc, pp = c.get(page, zero), p.get(page, zero)
        res.append({'page': page.replace('https://ejarihelper.ae', '') or '/',
                    'clicks': cc['clicks'], 'impressions': cc['impressions'],
                    'ctr': round(cc['clicks'] / cc['impressions'], 4) if cc['impressions'] else 0,
                    'position': round(cc['posw'] / cc['impressions'], 1) if cc['impressions'] else None,
                    'prev_clicks': pp['clicks'], 'prev_impressions': pp['impressions'],
                    'prev_position': round(pp['posw'] / pp['impressions'], 1) if pp['impressions'] else None})
    print(json.dumps({'current': cur, 'previous': prev, 'pages': res[:a.limit]}, indent=1))


def cmd_queries(a):
    s = _session()
    st, en = window(a.days)
    rows, start = [], 0
    while True:
        chunk = query(s, {'startDate': st, 'endDate': en, 'dimensions': ['query', 'page'],
                          'rowLimit': 5000, 'startRow': start})
        rows += chunk
        if len(chunk) < 5000:
            break
        start += 5000
    with open(a.out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['query', 'page', 'clicks', 'impressions', 'position'])
        for r in rows:
            if '#' in r['keys'][1]:
                continue
            w.writerow([r['keys'][0], r['keys'][1], r['clicks'], r['impressions'], round(r['position'], 1)])
    print(json.dumps({'window': [st, en], 'rows': len(rows), 'out': a.out}))


def cmd_inspect(a):
    s = _session()
    out = []
    for url in a.urls:
        r = s.post(f'{API}/v1/urlInspection/index:inspect',
                   json={'inspectionUrl': url, 'siteUrl': SITE, 'languageCode': 'en-US'}, timeout=60)
        if r.status_code != 200:
            out.append({'url': url, 'error': r.status_code, 'body': r.text[:300]})
            continue
        idx = r.json().get('inspectionResult', {}).get('indexStatusResult', {})
        out.append({'url': url, 'verdict': idx.get('verdict'), 'coverage': idx.get('coverageState'),
                    'indexed': idx.get('verdict') == 'PASS', 'last_crawl': idx.get('lastCrawlTime'),
                    'canonical_google': idx.get('googleCanonical'), 'robots': idx.get('robotsTxtState'),
                    'fetch': idx.get('pageFetchState')})
    print(json.dumps(out, indent=1))


def cmd_sitemaps(a):
    r = _session().get(f'{API}/webmasters/v3/sites/{_q(SITE)}/sitemaps', timeout=60)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=1))


def cmd_submit(a):
    r = _session().put(f'{API}/webmasters/v3/sites/{_q(SITE)}/sitemaps/{_q(a.url)}', timeout=60)
    ok = r.status_code in (200, 204)
    print(json.dumps({'sitemap': a.url, 'status': r.status_code, 'ok': ok}))
    if not ok:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    x = sub.add_parser('overview'); x.add_argument('--days', type=int, default=28); x.set_defaults(f=cmd_overview)
    x = sub.add_parser('pages'); x.add_argument('--days', type=int, default=28); x.add_argument('--limit', type=int, default=60); x.set_defaults(f=cmd_pages)
    x = sub.add_parser('queries'); x.add_argument('--days', type=int, default=90); x.add_argument('--out', default='rows.tsv'); x.set_defaults(f=cmd_queries)
    x = sub.add_parser('inspect'); x.add_argument('urls', nargs='+'); x.set_defaults(f=cmd_inspect)
    x = sub.add_parser('sitemaps'); x.set_defaults(f=cmd_sitemaps)
    x = sub.add_parser('submit-sitemap'); x.add_argument('url', nargs='?', default='https://ejarihelper.ae/sitemap.xml'); x.set_defaults(f=cmd_submit)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
