# SEO agent ledger

Read first, update last (see `AGENT.md`). Metrics are Google Search Console, `sc-domain:ejarihelper.ae`.

## Site KPI history (28-day windows)

| Window end | Clicks | Impressions | CTR | Avg pos | Note |
|---|---|---|---|---|---|
| 2026-09-24 | — | — | — | — | previous window (page-level only, see EXP baselines) |
| 2026-10-22 | 456 | 24,584 | 1.85% | 9.1 | agent baseline |

## Experiments

Status: OPEN · WIN · NEUTRAL · LOSS (reverted) · INCONCLUSIVE.
Baseline = 28 days before going live. Evaluate on or after the *Eval from* date.

| ID | Live | Page | Change | Hypothesis | Baseline (cl / impr / CTR / pos) | Eval from | Status | Result |
|---|---|---|---|---|---|---|---|---|
| EXP-001 | 2026-10-23 | /guide/dewa-transfer | **Factual fix + snippet.** Page claimed there is no DEWA transfer and the deposit doesn't move; DEWA's Move-to service transfers the deposit. Rewrote around Move-to: fees AED 275 (112.50+20 / 112.50+30), 15 working hours, inputs, when to use Move Out + Move In. Title → “DEWA Transfer to New Apartment 2026: Deposit Moves With You”; new description, H1, FAQ + HowTo JSON-LD. | Matching “transfer / move to new apartment” wording + a hook competitors lack lifts CTR 0.74% → ≥ 2% (+14 cl/28d); fresher, correct facts help position on “dewa transfer” queries. | 8 / 1,078 / 0.74% / 6.6 | 2026-11-13 | OPEN | |
| EXP-002 | 2026-10-23 | /guide/dewa-activation | **Factual fix + snippet.** Fees AED 100 → AED 155 (125 + 10 + 10 + 10), “24 hours” → 15 working hours, 991 → 04 601 9999, added the auto welcome-email path. Title → “DEWA Activation for New Tenants 2026: Fees, Deposit, Steps” (targets “dewa registration for new tenant” pos 1.9 / 0 clicks and “dewa activation” pos 3.9 / 0 clicks). | CTR 0.72% → ≥ 2% (+7 cl/28d). | 4 / 556 / 0.72% / 8.9 | 2026-11-13 | OPEN | |

Sources checked 2026-10-23: [DEWA Move-to](https://www.dewa.gov.ae/en/consumer/supply-management/transfer-of-electricity-water-move-to),
[DEWA Move-in](https://www.dewa.gov.ae/en/consumer/supply-management/activation-of-electricity-water-move-in),
[DEWA Move-out](https://www.dewa.gov.ae/en/consumer/supply-management/deactivation-of-electricity-water-move-out).

## Backlog (seen in data, not started)

* `/guide/tenancy-contract-dubai` — clicks −31% vs previous 28d (159 → 110) while position improved 12.7 → 9.8.
  “tenancy contract” 415 impr at pos 2.6 with 1 click and “tenancy contract download” 373 impr at pos 9.1 with 1 click:
  investigate SERP layout before touching (likely AI overview / downloads pack).
* `/guide/rental-dispute` — 3,969 impr, CTR 0.5%, pos 12.1; most impressions are anonymised long tail.
  “www.rdc.gov.ae english” 134 impr at pos 4.2 (navigational). Needs ranking (content/links), not just a snippet.
* `/guide/dewa-premises-number` — “dewa premise number” 775 impr at pos 2.5, CTR 2.8% (curve ≈ 13%).
  Description gives the full answer away (zero-click). Candidate for a careful single title/description test.
  “dewa account number” 125 impr at pos 8.1, 0 clicks — section exists; consider a clearer anchor/FAQ.
* `/guide/ejari-renewal` pos 39, `/guide/ejari-registration` pos 31, `/what-is-ejari` pos 32 — link-limited head terms.
* `/guide/dewa-premises-number`, `/index.html` still say DEWA connects “within 24 hours” (official: 15 working hours) — align when the page is next touched.

## Learnings

* (none yet)

## Run log

* 2026-10-23 — agent set up. Baseline pulled. EXP-001, EXP-002 shipped. Tests: DEWA fee consistency check added.
