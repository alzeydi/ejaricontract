# Ejari Helper — ejarihelper.ae

Flask app with two products:

1. **Ejari tenancy contract generator** — upload Emirates IDs + Title Deed, AI extracts the fields and fills the official DLD Unified Tenancy Contract PDF. **AED 15** per contract (Ziina checkout).
2. **AI rental lawyer chat** (`/legal-chat`) — Dubai tenancy-law Q&A grounded in Law 26/2007, Law 33/2008 and Decree 43/2013. **AED 50** per 30-minute session.

Static marketing/guide pages live in `static/` and are served through Flask routes that inject `__BASE_URL__` and `__GA4_ID__` placeholders.

## Analytics (GA4)

### Setup

Set the env var **`GA4_MEASUREMENT_ID`** (e.g. `G-XXXXXXXXXX`) in Railway. Every page's gtag block loads both the existing Google Ads tag (`AW-18223357108`) and, when the env var is set, the GA4 property. Without the env var, GA4 calls are skipped silently.

### Events fired by the front-end

| Event | Where it fires | Params |
|---|---|---|
| `contract_started` | Contract form opened or first document chosen (homepage) | `source`: `form_opened` \| `first_document` |
| `contract_docs_uploaded` | All 3 required documents selected (homepage) | `docs_count` |
| `payment_success` | Ziina success (embedded callback **and** `?paid=1` redirect return), deduped per intent | `value: 15`, `currency: 'AED'`, `transaction_id`, `product: 'contract'` |
| `template_downloaded` | Any click on a `/download/...` link (Word/PDF template), site-wide | `file_name`, `source_page` |
| `chat_started` | First message sent in `/legal-chat` (per browser session) | `source_page` |
| `chat_paid` | Legal-chat unlock — `?unlocked=1&tid=` redirect return **and** embedded verify success, deduped per intent | `value: 50`, `currency: 'AED'`, `transaction_id` |
| `cta_click` | Any guide/tool → product link (`/`, `/legal-chat`, `/ar/legal-chat`, `/#…`), or any `a[data-cta]` element site-wide | `source_page`, `cta_target` |

### ⚠️ Manual step: mark each as a Key Event

GA4 does **not** treat custom events as conversions automatically. In **GA4 Admin → Events** (wait up to 24 h for each event name to appear after first firing, or create them manually via "Create event"), toggle **"Mark as key event"** for **all seven**:

`contract_started`, `contract_docs_uploaded`, `payment_success`, `template_downloaded`, `chat_started`, `chat_paid`, `cta_click`

`payment_success` and `chat_paid` carry `value` + `currency` (AED 15 / AED 50), so revenue reporting works once they're key events.

### Verifying on mobile (majority of converting traffic)

1. Open **GA4 Admin → DebugView** on desktop. On the phone, load any page with **`?_ga_debug=1`** in the URL (e.g. `https://ejarihelper.ae/legal-chat?_ga_debug=1`) — the gtag config then sets `debug_mode: true` and every event from that page-load shows up in DebugView.
2. On mobile Safari and mobile Chrome, walk the funnel: open the contract form (`contract_started`), pick 3 documents (`contract_docs_uploaded`), tap a guide CTA (`cta_click`), download the template (`template_downloaded`), send a chat message (`chat_started`).
3. Payment events are best verified with a real AED 1 test intent or by loading `/legal-chat?unlocked=1&tid=test123` (fires `chat_paid` once per `tid`) and `/?paid=1` after a stored intent.
4. All navigation-time events (`cta_click`, `template_downloaded`) rely on gtag's default `sendBeacon` transport, which survives page unload on iOS Safari.

## Other env vars

`BASE_URL`, `ANTHROPIC_API_KEY`, `ZIINA_API_KEY`, `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `FREE_MODE`, `LEGAL_FREE_MODE`, `ZIINA_EMBEDDED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, Trustpilot keys — see comments in `app.py`.

## Post-deploy checklist (after each SEO-relevant deploy)

1. **GSC**: resubmit `sitemap.xml` (Search Console → Sitemaps), then use *URL Inspection → Request indexing* for changed/new URLs. Priority order for the current cluster: `/what-is-ejari`, `/ejari-help`, `/guide/ejari-cost`, `/guide/ejari-check`, `/guide/ejari-number`, `/guides`, `/about`, `/guide/ejari-registration`, then the rest.
2. **GA4**: confirm the 7 key events are marked (see Analytics above); walk the funnel once on a phone with `?_ga_debug=1` and watch DebugView.
3. **Rich Results Test**: run the edited guide URLs (FAQ + HowTo should be detected).
4. **Redirects**: `curl -sI http://ejarihelper.ae/guide/ejari-renewal` → exactly one `301` to the https URL, which returns `200`.
5. **404s**: in GSC → *Pages → Not found (404)*, open the URL list and check each entry now 301s to a live page **in one hop** (`curl -sIL` and count the hops — a 301 into a 404 still counts as a 404). Anything left should be a URL that genuinely never existed — those are fine to leave as 404s and can be marked *Validate fix*.
   The one URL reported so far was `https://ejarihelper.ae/download/` (crawled 14 Aug 2026): Googlebot walking up from `/download/dld-tenancy-contract.pdf`. Any new file served under a bare directory needs that directory added to `_SECTION_REDIRECTS`.

## URL canonicalisation

`canonical_path()` in `app.py` folds every URL variant into one canonical spelling,
and `redirect_canonical()` emits it together with the scheme/host fix as a **single**
301 — no chains. Handled variants:

| Variant | Result |
| --- | --- |
| `http://`, `www.` | `https://ejarihelper.ae/…` |
| trailing slash — `/guide/x/` | `/guide/x` |
| `.html` / `.htm` suffix — `/guide/x.html` | `/guide/x` |
| upper/mixed case — `/Guide/X` | `/guide/x` |
| doubled slashes — `/guide//x` | `/guide/x` |
| bare directory — `/guide`, `/tools`, `/ar` | `/`, `/`, `/ar/legal-chat` |
| bare directory — `/download` | `/guide/tenancy-contract-dubai` |
| raw source file — `/static/guide/x.html` | `/guide/x` |
| English-only guide under `/ar/` | `/guide/x` |

Exceptions: `POST` is never redirected (a 301 drops the body), `/.well-known/*` keeps
its exact spelling, and non-HTML files under `/static/` keep their case-sensitive
on-disk name.

Anything that really does not exist returns a **404 with the branded
`static/404.html`** — never a bounce to the homepage, which Google counts as a soft 404.
API paths (`/legal-chat/*`, `/admin/*`, `/webhook/*`) get a JSON 404 instead.

When adding a page: add the slug to `_GUIDE_SLUGS` / `_AR_GUIDE_SLUGS` / `_TOOL_SLUGS`
(or a top-level route for a cluster entry point like `/what-is-ejari`), the URL to
`sitemap_xml()`, and the path to `PAGES` in `tests/test_seo.py`. The page must carry
`dateModified` in its JSON-LD — `sitemap_xml()` reads `<lastmod>` straight out of it,
and `test_every_page_declares_a_modification_date` fails without it.

## Ejari fees — single source of truth

The 2026 government fee is **AED 177.75** filed yourself (Dubai REST / DLD portal) and
**AED 219.75** at a trustee centre:

| | Online | Trustee centre |
| --- | --- | --- |
| Registration | 100.00 | 100.00 |
| Knowledge fee | 10.00 | 10.00 |
| Innovation fee | 10.00 | 10.00 |
| Service-partner fee | 55.00 | 95.00 |
| VAT (5% of the partner fee only) | 2.75 | 4.75 |
| **Total** | **177.75** | **219.75** |

Cancellation is free and renewal costs the same as first registration. This figure is
the site's main competitive edge — every competitor audited publishes a stale or vague
number — so `test_fee_figure_is_consistent_sitewide` fails the build if a superseded
figure (`122.50`, `AED 215`, `AED 220`) reappears anywhere in `static/`.

## SEO strategy docs

- `SEO-STRATEGY.md` — competitor teardown, on-site audit, phase plan, what still needs
  the owner (Cloudflare dashboard, trade-licence details, Dubai REST screenshots).
- `SEO-OFFSITE-PLAYBOOK.md` — link-building targets and digital-PR pitches, plus the
  Google Ads campaign structure, keyword lists, negatives and ad copy.

### Live-site checks

`tests/test_seo.py` includes network tests that are skipped by default:

```
LIVE_SEO_TESTS=1 python3 -m pytest tests/ -q
```

`test_live_robots_is_not_overridden_by_cloudflare` fails while Cloudflare's managed
`robots.txt` is enabled — it is prepended to the app's own and contradicts it,
disallowing `ClaudeBot` and `Applebot-Extended` that `_ROBOTS_AI_ALLOWED` allows.
Turn the managed file off in the Cloudflare dashboard so `app.py` is the only source
of truth.

## IndexNow (optional)

Set `INDEXNOW_KEY` (lowercase hex) to enable instant URL submission to Bing, Yandex
and DuckDuckGo — Google does not participate, so this supplements the sitemap rather
than replacing it. The key file is served at `/<key>.txt`; `POST /admin/indexnow`
(admin session required) submits every sitemap URL.

## Tests

```
python3 -m pytest tests/ -q
```

Covers canonical-redirect behaviour (single-hop http→https 301, URL-shape normalisation,
404-not-soft-404), robots/llms/sitemap output, and page-head SEO invariants
(canonical + hreflang).
