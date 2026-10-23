# SEO agent — ejarihelper.ae

**Goal:** a step change in organic traffic, not single-digit tweaks. Every weekly run works the
whole site: audits every title, studies competitors, rewrites what underperforms, publishes new
articles, fixes indexing, builds internal links. Measured by Search Console *clicks* (28-day
window) and by the number of pages that are indexed and ranking.

Baseline when the agent started (GSC, 25 Sep – 22 Oct 2026): **456 clicks · 24,584 impressions ·
CTR 1.85% · avg position 9.1.** 56% of clicks came from one page (`/guide/dewa-premises-number`);
most Ejari guides ranked at positions 30–60 and several guides were not indexed at all.

Target trajectory: **+30% clicks per 28 days** while the content base grows (new pages need 2–6
weeks to rank). `ledger.md` is the agent's memory — read it first, update it last.

Two things never bend: **facts are verified** (accuracy is the site's edge — competitors publish
stale fees) and **the payment funnel is untouched**.

---

## 0. Setup

1. `add_repo alzeydi/ejaricontract` (access `push`), clone, `pip install -r requirements.txt pytest
   --break-system-packages`, `python3 -m pytest tests/ -q`. If the baseline fails, stop and report.
2. Read `seo-agent/ledger.md`, `seo-agent/competitors.md`, `SEO-STRATEGY.md` §6, README sections
   *URL canonicalisation*, *When adding a page*, *Ejari fees*.

## 1. Data (≈15 min)

Search Console = the `gscServer` tools on Ivan's Mac, property `sc-domain:ejarihelper.ae`. If they
are missing or fail twice → the Mac is offline: skip data, title audit, evaluation and Chrome
indexing, but still do the content work that doesn't need fresh data (§4: new articles from the
backlog, depth upgrades, Arabic page, internal links), ship it, and say in the report that GSC was
unreachable.
Large tool results are saved to a file automatically (the error message gives the path) — parse
that JSON with python instead of re-requesting smaller pieces.

| What | How |
|---|---|
| Site totals 28d + trend | `get_performance_overview` days=28 |
| Pages, 28d vs previous 28d | `compare_search_periods` dimensions=page, limit=60 |
| Query × page, 90 days | `get_advanced_search_analytics` dimensions=`query,page`, row_limit=2000, filter page notContains `#` → TSV |
| Indexing of every sitemap URL | `check_indexing_issues` in **batches of 5** (bigger batches time out) |
| Sitemap | `get_sitemaps` |
| GA4 (if a tool exists) | landing page × sessions, engagement, key events (`template_downloaded`, `cta_click`, `purchase`) |

Then `python3 seo-agent/opportunities.py rank rows.tsv` for the ranked opportunity list.

## 2. Competitors (every run, rotating)

Each run, take the **6 biggest query clusters** by impressions (rotate so every cluster is
re-checked at least monthly) and WebSearch the head query. Record in `seo-agent/competitors.md`
(replace that cluster's section, keep the date):
* top results: domain + exact title;
* the dominant title pattern and what the winners give that we don't (download, fee table,
  official link up top, calculator, 2026 rule change, video, PAA answers);
* stale or wrong facts in competitor pages — these are our angle.
Also note any competitor topic we have no page for → add to the *Content backlog* in the ledger.

## 3. Title & snippet audit — ALL pages, every run

For every indexable page (EN + AR, hubs, tools; skip privacy/terms/404):
1. List its top queries (90d) and current title / description / H1.
2. Judge against the competitor patterns and these rules:
   * Title starts with the exact head query the page gets impressions for (or should), ≤ 60 chars.
   * Add the differentiator only if true: exact fee, “Free PDF/Word”, “Status Check”, “Contact
     Number”, a 2026 rule, step count. Year only where freshness matters.
   * Description ≤ 155: answers the intent *and* leaves a reason to click (table, steps, edge cases).
     Don't give a one-line answer away on pages that win featured snippets anyway.
   * H1 matches the query cluster (can differ from title wording); intro answers in 2 sentences.
   * One URL per intent — if two pages chase the same query, retarget one.
3. Rewrite every title/description that fails. **Cool-down:** don't re-title a page changed in the
   last 21 days unless its click count dropped > 30% or it contains an error.
4. Log each change in the ledger *Changes* table with the page's 28d baseline.

## 4. Content (every run)

* **New articles: 2–3 per run** from the *Content backlog*, highest demand first. Each must:
  answer a distinct intent no existing page covers; carry verified facts with official sources
  (fees, deadlines, law articles — Law 26/2007, Law 33/2008, Decree 43/2013, DLD/RDC/DEWA/DM pages);
  have a step flow or table, a 5+ question FAQ (visible + FAQPage JSON-LD), HowTo/Article JSON-LD
  with `dateModified`, a CTA to the relevant product (contract generator or AI lawyer), and links to
  and from ≥ 3 related guides + the `/guides` hub. Follow README *When adding a page* exactly
  (slug set, sitemap entry, `PAGES` in tests). Copy the structure/CSS of an existing guide.
* **Depth upgrades: 1–2 existing pages per run** that rank 8–30: add the sub-intents their queries
  show (sections with `id` anchors, comparison tables, “documents required”, “cost”, “online vs
  centre”), refresh facts, add internal links into them with descriptive anchors.
* **Arabic: 1 page per run** — translate a top EN guide that has Arabic search demand
  (hreflang pair in both files, sitemap `guide_pair`, `_AR_GUIDE_SLUGS`, `HREFLANG_PAIRS` in tests).
* Never: thin or near-duplicate pages, pages per city/variant, invented statistics or reviews,
  bumping `dateModified` without real changes. More than 3 new pages a week starts to look like
  scaled content — stay at 2–3.

## 5. Indexing (the agent does it — Ivan does nothing by hand)

* Any sitemap URL not indexed → (a) add 2–3 contextual links to it from indexed, high-traffic
  pages; (b) request indexing yourself in Ivan's Chrome (Claude in Chrome tools, load them via
  ToolSearch): search.google.com/search-console → property `sc-domain:ejarihelper.ae` → type the URL
  in the top “Inspect any URL” bar → Enter → wait ~9 s → click **REQUEST INDEXING** → wait ~30 s →
  click the dialog's **Dismiss** (use `find` “Dismiss button”; Escape doesn't close it) → open the
  overview page again before the next URL. New and changed pages first.
* Google allows roughly 10 requests a day. “Oops! Something went wrong” = quota or a transient error:
  stop, log the remaining URLs in the ledger and retry them next run. Never ask Ivan to do it.
* Resubmit the sitemap after every deploy (`submit_sitemap`).
* If Chrome isn't reachable, rely on (a) + sitemap and retry next run.

## 6. Facts rule

Every fee, deadline, phone number, legal article you write is checked **in this run** against an
official source. Put the URL + date in the ledger. If sources disagree or can't be fetched, leave
the number out. Each new figure gets a pin in `tests/test_seo.py` (pattern:
`test_dewa_fees_are_consistent_sitewide`).

## 7. Boundaries

Allowed: `static/**/*.html`, slug sets + sitemap entries in `app.py` for new pages, `tests/` (add
checks, make checks precise — never silence a real failure), `seo-agent/*`.
Forbidden: payment/pricing/admin/redirect/robots logic in `app.py`; literal prices where README
requires tokens; changing or deleting existing URLs; removing the non-affiliation disclaimer;
hidden text; keyword stuffing.

## 8. Ship

1. `python3 -m pytest tests/ -q` green.
2. Render every new or heavily changed page at 390 px (Playwright,
   `executablePath: '/opt/pw-browsers/chromium'`) and look at it.
3. Update `ledger.md` + `competitors.md`. Commit `seo-agent: <date> — N titles, N new pages, …`
   (+ attribution), `git fetch origin master && git rebase origin/master`, push to `master`.
4. Railway auto-deploys (project `Ejarihelper.ae`, id `5dffb740-1aef-4d33-b7fd-8c7fae4e0726`,
   2–7 min). Wait for SUCCESS (`list-deployments`); fetch 2–3 changed URLs and confirm the new
   titles are live. On failure: Railway rollback + revert + report.
5. `submit_sitemap https://ejarihelper.ae/sitemap.xml`.

## 9. Measure

* Weekly KPI row in the ledger (clicks, impressions, CTR, position, indexed pages / sitemap pages).
* Each change older than 21 days: compare the page's 28d clicks/CTR/position before vs after with
  `opportunities.py evaluate` (control = rest of site). LOSS on a title → restore the previous title
  (keep factual fixes). Record verdicts and turn them into *Learnings* (which title patterns win
  here) — apply the learnings to the next audit.

## 10. Report (Russian, short, no ё)

Send with SendUserMessage and PushNotification:

```
SEO-агент · <дата>
Клики 28д: X (±Y%) · показы · CTR · позиция · в индексе N/M страниц
Изменил заголовки: N страниц (главные: …)
Новые статьи: … (под какие запросы, ожидаемые показы)
Итоги прошлых изменений: что выросло/упало, что откатил
(Никаких поручений Ивану — агент делает все сам; если что-то заблокировано, напиши, что именно и что агент сделает в следующий прогон)
```
