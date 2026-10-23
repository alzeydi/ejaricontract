# SEO agent — ejarihelper.ae

**Goal:** grow organic clicks from Google (Search Console *clicks*, 28-day window) week after week,
without risking the site's two real assets: factual accuracy and the payment funnel.

Baseline when the agent started (GSC, 25 Sep – 22 Oct 2026): **456 clicks · 24,584 impressions ·
CTR 1.85% · avg position 9.1.** 56% of clicks come from one page, `/guide/dewa-premises-number`.

The agent runs **weekly** as a scheduled task. Every run follows this file top to bottom.
`ledger.md` is its memory: open experiments, results, run log. Read it first, update it last.

---

## 0. Setup

1. Attach the repo with push access (`add_repo alzeydi/ejaricontract`, access `push`), clone it,
   `pip install -r requirements.txt pytest --break-system-packages`, run `python3 -m pytest tests/ -q`.
   If the baseline suite fails, **stop**: report the failure, change nothing.
2. Read `seo-agent/ledger.md`, `SEO-STRATEGY.md` §6 ("Чего делать нельзя") and the README sections
   *URL canonicalisation* and *Ejari fees*.

## 1. Pull data

Search Console lives on Ivan's Mac (the `gscServer` MCP tools, property `sc-domain:ejarihelper.ae`).
If those tools are missing or fail twice, the Mac is offline: **do not edit anything**, send a
one-line report ("GSC недоступен — компьютер офлайн, прогон пропущен") and end.

Pull, with `end` = 3 days ago (GSC data is final after ~3 days):

| What | Tool / params |
|---|---|
| Site totals, daily trend, 28d | `get_performance_overview` days=28 |
| Pages, this 28d vs previous 28d | `compare_search_periods` dimensions=page, limit=50 |
| Query × page rows | `get_advanced_search_analytics` dimensions=`query,page`, sort_by=impressions, row_limit=500 |
| Per-experiment windows | `get_advanced_search_analytics` dimensions=page, filter page equals `<url>`, explicit dates |
| Indexing of pages changed in the last 2 runs | `check_indexing_issues` |
| Sitemap health | `get_sitemaps` |

**GA4** — if any Google Analytics tool is available (e.g. `run_report` from Google's
analytics-mcp): landing page × sessions, engagement rate, key events (`template_downloaded`,
`cta_click`, `purchase`) for the same 28 days. Use it to break ties toward pages that convert,
and never ship a change that lowers a page's key-event rate (check in evaluation). If no GA tool
exists, say so in the report and continue on GSC alone.

Write the query × page rows to a TSV (`query	page	clicks	impressions	position`) and run:

```
python3 seo-agent/opportunities.py rank /tmp/rows.tsv --exclude <pages with an OPEN experiment>
```

## 2. Evaluate open experiments

An experiment is due when it has been live **≥ 21 days**. For each due one:

1. Before window = the N days ending the day before `live`; after window = N days starting 3 days
   after `live` (skip the re-crawl period). Use N = min(28, days available). Same N both sides.
2. Control = site totals minus all pages with open experiments, same windows.
3. `python3 seo-agent/opportunities.py evaluate --before c,i --after c,i --control-before c,i --control-after c,i`
4. Verdict → action:
   * **WIN** — keep. Note the lesson in ledger *Learnings* (what kind of change worked, where).
   * **NEUTRAL** — keep (the facts are still better); the page is free for a new experiment.
   * **LOSS** — revert the *title/description/H1* part with a new commit (`git revert` only if the
     commit contains nothing else). **Never revert a factual correction.**
   * **INCONCLUSIVE** — leave open, re-check next run; close as NEUTRAL after 56 days.
5. Update the row in `ledger.md` (status, result numbers, verdict).

## 3. Choose this week's changes

Budget per run: **at most 2 experiments** (two different pages) **plus** any factual fixes.
One open experiment per page at a time, otherwise nothing can be attributed.

Pick from the top of the `rank` output, then decide the lever by where the page ranks:

| Situation | Lever |
|---|---|
| Position ≤ 10, CTR well below the curve (`snippet_gap` dominates) | Title + meta description + H1/intro rewrite. Match the exact words of the top 3 queries; promise what the SERP answer can't give (step-by-step, current fee table, official link, “what if” cases). Keep a number or a year where it is a true differentiator. |
| Position 4–20 (`rank_gain` dominates) | Content depth for the queries the page half-answers: a section or FAQ per uncovered sub-intent, a comparison table, internal links **into** the page from the 2 strongest pages with descriptive anchors. |
| Query cluster ≥ 100 impressions/28d landing on a page that doesn't target it | Either add a dedicated section with an `id` anchor on the closest page, or (max **1 new page per run**) a new guide — only if the intent is genuinely different. Follow README *“When adding a page”* exactly (slug list, sitemap, `PAGES` in tests, `dateModified`). |
| Page has facts older than ~3 months on fees, timings, laws | Verify and refresh first — accuracy is the site's edge and outdated numbers lose AI-overview citations. |

**Facts rule.** Every fee, deadline, phone number or legal reference you write must be checked in
this same run against an official source (dewa.gov.ae, dubailand.gov.ae, rdc.gov.ae, u.ae,
dubai.gov.ae, the law text). Record the URL and check date in the ledger. If sources disagree or
can't be fetched, don't write the number. When you add a new figure, add or extend a test in
`tests/test_seo.py` that pins it (see `test_dewa_fees_are_consistent_sitewide`).

**Top-page caution.** `/guide/dewa-premises-number` carries most of the traffic. Touch it only with
a single title/description experiment at a time, never together with other changes to it.

## 4. Implement

Allowed:
* `static/**/*.html` — titles, meta, OG/Twitter tags, H1, intro, sections, FAQ (visible **and**
  FAQPage JSON-LD in sync), HowTo/Article JSON-LD, internal links, related-guides blocks.
* New guide pages + the registration points README lists for them.
* `tests/test_seo.py` — only to add checks or to make an existing check precise (never to silence
  a real failure).
* `seo-agent/ledger.md`.

Forbidden:
* `app.py` logic beyond slug lists/sitemap entries for a new page: payments, prices, Ziina,
  admin, canonical/redirect logic, robots AI policy.
* Prices or fees as literals where README says to use a token (`__CONTRACT_PRICE__` etc.).
* Changing existing URLs/slugs, deleting pages, removing the non-affiliation disclaimer.
* Bumping `dateModified` without a real content change. Fake freshness is a spam signal.
* Doorway/near-duplicate pages, keyword stuffing, hidden text, invented reviews or statistics.
* More than 3 page files touched per run (factual-fix sweeps across pages are the exception).

Title ≤ 60 chars, description ≤ 155 (tests enforce). Update `dateModified` (JSON-LD Article) and the
visible “Updated …” line together when content materially changes — the sitemap reads `lastmod`
from it.

## 5. Ship and verify

1. `python3 -m pytest tests/ -q` must be green.
2. Look at each changed page rendered at 390 px wide (Playwright with
   `executablePath: '/opt/pw-browsers/chromium'`) — tables and FAQ must read cleanly.
3. Update `ledger.md` (new experiment rows with the baseline numbers, run log entry).
4. Commit to `master` with message `seo-agent: EXP-NNN <page> — <change>` (+ session attribution),
   `git fetch origin master && git rebase origin/master`, push. Railway auto-deploys `master`
   (project `Ejarihelper.ae`, id `5dffb740-1aef-4d33-b7fd-8c7fae4e0726`, ~7 min).
5. Wait for the deployment to reach SUCCESS (`list-deployments`), then fetch each changed URL and
   confirm the new `<title>` is live. If the deploy fails: roll back with Railway, revert the
   commit, report.
6. Resubmit the sitemap: `submit_sitemap` `https://ejarihelper.ae/sitemap.xml`.

## 6. Report (in Russian, short)

Send with SendUserMessage. Format:

```
SEO-агент · <дата>
Клики 28д: X (±Y% к пред. 28д) · показы · CTR · позиция
Оценка экспериментов: EXP-… WIN/LOSS/NEUTRAL (+N кликов), что откатил
Что изменил сегодня: EXP-… страница — что и почему (ожидание: +N кликов/28д)
Нужно от тебя: <только если есть: ссылки, Cloudflare, доступы>
```

No ё. Numbers over adjectives. If nothing was worth changing, say so — a run without changes is fine.

---

## Why changes are slow to show

Google re-crawls a changed guide in days, but positions and CTR settle over 2–4 weeks, so a weekly
cadence with a 21-day evaluation keeps 2–6 experiments in flight at any time. Backlinks remain the
ceiling for positions on head terms (`tenancy contract dubai`, `ejari`); on-site work wins CTR,
long-tail and AI-overview citations. Off-site work is in `SEO-OFFSITE-PLAYBOOK.md` — the agent
reminds Ivan about it, it doesn't do it.
