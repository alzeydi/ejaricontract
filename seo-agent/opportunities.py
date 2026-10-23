#!/usr/bin/env python3
"""SEO agent helper: rank pages by click opportunity and judge experiments.

No third-party dependencies. Two sub-commands:

  rank      Read Search Console rows (query, page, clicks, impressions, position)
            and estimate how many extra clicks/28d each page could win.

            python3 seo-agent/opportunities.py rank rows.tsv [--exclude /guide/x,/guide/y]

            rows.tsv: tab-separated, header line required, columns in any order:
            query  page  clicks  impressions  position

  evaluate  Before/after test for one experiment page, normalised by the rest
            of the site (control) so a sitewide swing is not credited to the change.

            python3 seo-agent/opportunities.py evaluate \
                --before 8,1078 --after 21,1120 \
                --control-before 448,23506 --control-after 470,24100

            Each pair is clicks,impressions over windows of EQUAL length.
"""
import argparse
import csv
import math
import sys
from collections import defaultdict

# Organic CTR by position, conservative for 2026 SERPs (AI Overviews, ads,
# People-also-ask). Used only to rank opportunities, never as a promise.
CTR_CURVE = {1: .22, 2: .13, 3: .09, 4: .065, 5: .05, 6: .04, 7: .032,
             8: .027, 9: .023, 10: .02}


def expected_ctr(pos):
    if pos <= 0:
        return 0.0
    if pos < 1:
        pos = 1
    lo = int(math.floor(pos))
    if lo >= 10:
        # page 2 decays from 1.2% to ~0.4%; beyond 20 almost nothing
        return max(.012 - (pos - 11) * .0009, .004) if pos <= 20 else .002
    hi = lo + 1
    a, b = CTR_CURVE[lo], CTR_CURVE.get(hi, .012)
    return a + (b - a) * (pos - lo)


def norm_page(url):
    return url.split('#', 1)[0].replace('https://ejarihelper.ae', '') or '/'


def rank(path, exclude):
    pages = defaultdict(lambda: {'clicks': 0, 'impr': 0, 'pos_w': 0.0,
                                 'snippet_gap': 0.0, 'rank_gain': 0.0, 'top': []})
    with open(path, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            page = norm_page(r['page'])
            if page in exclude:
                continue
            clicks, impr, pos = int(float(r['clicks'])), int(float(r['impressions'])), float(r['position'])
            if impr == 0:
                continue
            p = pages[page]
            p['clicks'] += clicks
            p['impr'] += impr
            p['pos_w'] += pos * impr
            ctr = clicks / impr
            # 1) snippet gap: already ranking, under-clicked → title/description work
            gap = impr * max(0.0, expected_ctr(pos) - ctr) if pos <= 10 else 0.0
            # 2) striking distance: pos 4–20 → content/internal links could lift it to ~3
            gain = impr * max(0.0, expected_ctr(3) - expected_ctr(pos)) * 0.3 if 4 <= pos <= 20 else 0.0
            p['snippet_gap'] += gap
            p['rank_gain'] += gain
            p['top'].append((gap + gain, r['query'], impr, pos, clicks))
    rows = []
    for page, p in pages.items():
        total = p['snippet_gap'] + p['rank_gain']
        p['top'].sort(reverse=True)
        rows.append((total, page, p))
    rows.sort(reverse=True)
    print('page\tclicks\timpr\tctr%\tavg_pos\tsnippet_gap\trank_gain\topportunity\ttop_queries')
    for total, page, p in rows:
        if total < 1:
            continue
        avg = p['pos_w'] / p['impr']
        tq = '; '.join(f'{q} ({i} impr, pos {pos:.1f}, {c} cl)' for _, q, i, pos, c in p['top'][:4])
        print(f"{page}\t{p['clicks']}\t{p['impr']}\t{100*p['clicks']/p['impr']:.2f}\t{avg:.1f}\t"
              f"{p['snippet_gap']:.1f}\t{p['rank_gain']:.1f}\t{total:.1f}\t{tq}")


def pair(s):
    c, i = s.split(',')
    return int(c), int(i)


def evaluate(a):
    (cb, ib), (ca, ia) = a.before, a.after
    (kb, jb), (ka, ja) = a.control_before, a.control_after
    ctr_b, ctr_a = cb / max(ib, 1), ca / max(ia, 1)
    lift = (ca + .5) / (cb + .5) - 1
    ctrl = (ka + .5) / (kb + .5) - 1
    net = (1 + lift) / (1 + ctrl) - 1
    # two-proportion z-test on CTR
    pool = (cb + ca) / max(ib + ia, 1)
    se = math.sqrt(pool * (1 - pool) * (1 / max(ib, 1) + 1 / max(ia, 1))) or 1e-9
    z = (ctr_a - ctr_b) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    if ca + cb < 10 and ia + ib < 400:
        verdict = 'INCONCLUSIVE (too little data — extend the window)'
    elif net >= .15 and (p < .1 or ca - cb >= 10):
        verdict = 'WIN'
    elif net <= -.15 and (p < .1 or cb - ca >= 10):
        verdict = 'LOSS'
    else:
        verdict = 'NEUTRAL'
    print(f'page clicks {cb}→{ca} ({lift:+.0%}), control {kb}→{ka} ({ctrl:+.0%}), net {net:+.0%}')
    print(f'page CTR {ctr_b:.2%}→{ctr_a:.2%}, z={z:.2f}, p={p:.3f}')
    print(f'verdict: {verdict}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('rank')
    r.add_argument('rows')
    r.add_argument('--exclude', default='')
    e = sub.add_parser('evaluate')
    for k in ('before', 'after', 'control-before', 'control-after'):
        e.add_argument('--' + k, type=pair, required=True)
    a = ap.parse_args()
    if a.cmd == 'rank':
        rank(a.rows, {x.strip() for x in a.exclude.split(',') if x.strip()})
    else:
        evaluate(a)


if __name__ == '__main__':
    sys.exit(main())
