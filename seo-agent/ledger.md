# SEO agent ledger

Read first, update last (see `AGENT.md`). Metrics: Google Search Console, `sc-domain:ejarihelper.ae`.

## Site KPI history (28-day windows)

| Window end | Clicks | Impressions | CTR | Avg pos | Indexed / sitemap | Note |
|---|---|---|---|---|---|---|
| 2026-10-22 | 456 | 24,584 | 1.85% | 9.1 | ≥ 20 / 29 (eviction-notice, security-deposit, ejari-number, rent calculator, about not indexed) | agent baseline |
| 2026-10-23 (GSC lag) | 459 (+4.6%) | 24,866 (−3.2%) | 1.85% | 9.1 (was 11.5) | 28 / 32 indexed (not indexed: ejari-number, eviction-notice, about, terms — 'Discovered, currently not indexed') | run 2026-10-26; data ends 23 Oct, i.e. before the 10-23 title rewrites show effect |
| 2026-10-30 (GSC lag) | 432 (−1.8% vs prev 28d 440; −5% vs baseline 456) | 26,415 (+6.2%) | 1.64% | 9.2 (prev 10.8) | 30 / 35 indexed (not indexed: ejari-number, eviction-notice, shared-housing, about, terms — all 'Discovered, currently not indexed') | run 2026-11-02 |
| 2026-11-06 (GSC lag) | 650 (+44.4% vs prev 28d 450) | 26,784 (+8.6%) | 2.43% | 9.5 (prev 9.9) | 31 / 37 indexed (not indexed: ejari-number, eviction-notice, maintenance, tenant-not-paying-rent, about, terms — all 'Discovered, currently not indexed') | run 2026-11-09; window 10 Oct–6 Nov already includes the 10-23 title rewrites |
| 2026-11-13 (GSC lag) | 714 (+54.2% vs prev 28d 463; +57% vs baseline 456) | 27,115 (+11.6%) | 2.63% | 10.0 (prev 9.3) | 32 / 40 indexed (not indexed: ejari-number, eviction-notice, maintenance, landlord-selling, ejari-co-occupants, about, terms 'Discovered, not indexed'; tenant-not-paying + AR selling 'unknown to Google') | run 2026-11-16; NB 4 Nov = one-day spike 131 clicks across 8 pages (housing-fee 22, rental-dispute 22, tenancy-contract 20) — excluding it ≈ 583 (+26%) |

## Changes

Baseline = page's last 28 days before the change (clicks / impressions / CTR / position). Evaluate from the date shown.

| ID | Live | Page | Change | Baseline | Eval from | Verdict |
|---|---|---|---|---|---|---|
| C-001 | 2026-10-23 | /guide/dewa-transfer | Factual rewrite around DEWA Move-to (deposit transfers; AED 275; 15 working hours) + title “DEWA Transfer to New Apartment 2026: Deposit Moves With You” | 8 / 1,078 / 0.74% / 6.6 | 2026-11-13 || WIN (6→17 clicks over 22d windows, CTR 0.70→2.05%, p=0.017) — keep |
| C-002 | 2026-10-23 | /guide/dewa-activation | Fees AED 100 → 155, 24 h → 15 working hours, 991 → 04 601 9999 + title “DEWA Activation for New Tenants 2026: Fees, Deposit, Steps” | 4 / 556 / 0.72% / 8.9 | 2026-11-13 || NEUTRAL (3→3, CTR 0.69→0.38%) — retitled again as C-018 |
| C-003 | 2026-10-23 | /guide/tenancy-contract-dubai | Title → “Tenancy Contract Dubai 2026: Free DLD PDF & Word Download” (head query first + “download” intent); new description; addendum link | 110 / 5,995 / 1.84% / 9.8 | 2026-11-13 || NEUTRAL (94→87, CTR 1.08→1.34%, net −53% vs control) — retitled again as C-019 |
| C-004 | 2026-10-23 | /guide/dewa-premises-number | Title → “DEWA Premise Number: Where to Find It, Even With No Bill”; description no longer gives the answer away (zero-click fix). Top page — watch closely | 255 / 8,869 / 2.88% / 4.3 | 2026-11-13 || LOSS by formula (net −41% vs control) but page CTR 1.80→2.21% (p=0.027), pos 5.0→4.1, clicks +31%; control is inflated by new pages + 4 Nov spike → judged KEEP, re-evaluate 2026-12-14 with clean control |
| C-005 | 2026-10-23 | /guide/rental-dispute | Title → “RDC Dubai: Case Status, Contact Number & Filing Fee 2026” (matches “rdc case status” 406 impr, “rdc contact number” 386 impr) | 20 / 3,969 / 0.50% / 12.1 | 2026-11-13 || WIN (18→55, CTR 0.53→1.36%, p<0.001) — keep |
| C-006 | 2026-10-23 | /guide/ejari-check | Title → “Ejari Check Online & Certificate Download: 3 Ways (2026)” | 17 / 925 / 1.84% / 16.0 | 2026-11-13 || NEUTRAL+ (14→27, CTR 2.01→4.11%, p=0.024; net +11%) — keep |
| C-007 | 2026-10-23 | /guide/ejari-renewal | Title → “Ejari Renewal Online 2026: Documents Required, Fee, Steps” (matches “documents required for ejari renewal”) | 0 / 423 / 0% / 39.2 | 2026-11-13 || WIN (0→16, CTR 0→6.8%) — keep |
| C-008 | 2026-10-23 | /guide/ejari-registration | Title → “Ejari Registration Online: How to Make Ejari, Docs, Fees” | 1 / 296 / 0.34% / 31.5 | 2026-11-13 || INCONCLUSIVE (1→7) — keep, re-evaluate 12-14 |
| C-009 | 2026-10-23 | /guide/ejari-cancellation | Title → “Ejari Cancellation 2026: Documents, Fee & Who Can Cancel” (dropped unsafe “in 5 Minutes”) | 8 / 522 / 1.53% / 16.7 | 2026-11-13 || NEUTRAL (4→7; position 16→26) — retitled as C-022 |
| C-010 | 2026-10-23 | /guide/ejari-cost | Title → “Ejari Cost 2026: AED 177.75 Online vs AED 219.75 at Centre” | 3 / 369 / 0.81% / 10.6 | 2026-11-13 || NEUTRAL (3→10, net +76%, p=0.15) — keep |
| C-011 | 2026-10-23 | /what-is-ejari | Title → “What Is Ejari? Meaning, Cost & Why Dubai Tenants Need It” | 1 / 250 / 0.4% / 32.4 | 2026-11-13 || WIN (0→21, CTR 0→5.3%) — keep |
| C-012 | 2026-10-23 | /guide/ejari-number | Title → “Ejari Number: Format, Example & 4 Places to Find It” (targets “ejari number sample/example” now landing on registration) | not indexed | 2026-11-13 || not indexed — no data |
| C-013 | 2026-10-23 | /guide/ejari-fine | Title → “Ejari Fine Dubai: Is There a Penalty for Late Ejari? (2026)” | 1 / 70 / 1.4% / 6.4 | 2026-11-13 || INCONCLUSIVE (1→1) — keep |
| C-014 | 2026-10-23 | /guide/rent-increase-dubai | Title → “Dubai Rent Increase 2026: Max %, 90-Day Notice, Calculator” + description | 0 / 3 / — / 8 | 2026-11-13 || INCONCLUSIVE (no impressions) — keep |
| C-015 | 2026-10-23 | /guide/eviction-notice-dubai | Title → “Eviction Notice Dubai 2026: 12-Month Rule & 4 Legal Grounds” | not indexed | 2026-11-13 || not indexed — length fix C-023 |
| C-016 | 2026-10-23 | / | Title → “Ejari Contract Online: Dubai Tenancy Contract PDF in Minutes” | 4 / 57 / 7.0% / 9.2 | 2026-11-13 || INCONCLUSIVE (3→2 on 46→69 impr) — keep |
| N-001 | 2026-10-23 | /guide/early-termination-tenancy-contract-dubai | **New article** — breaking a lease (Art. 7, no statutory penalty, termination agreement, cheques, Ejari, RDC fee, Art. 27 heirs). Corrects Bayut's “90 days, no penalty” claim | new | 2026-11-20 | |
| N-002 | 2026-10-23 | /guide/tenancy-contract-addendum-dubai | **New article** — addendum: 5 Additional Terms lines, common clauses vs legal defaults, void clauses, signing + Ejari | new | 2026-11-20 | |
| N-003 | 2026-10-23 | /guide/dubai-housing-fee | **New article** with inline calculator — 5% of Ejari rent, owners on RERA rental value, fixing a wrong fee via DM | new | 2026-11-20 | |
| N-004 | 2026-10-26 | /guide/shared-housing-dubai | **New article** — Law 4/2026: in force 8 Sep 2026 (DM Circular 1-3-1 of 7 Sep), permit, whole-building + one-category rule, no tenant subletting, fines AED 500–500k/1M, 1-year grace, tenant checklist | new | 2026-11-23 | |
| N-005 | 2026-10-26 | /guide/subletting-dubai | **New article** — Art. 24 (written consent), 8, 22, 25(1)(b), 30 quoted from dlp.dubai.gov.ae; DLD FAQ on co-occupants/no two-name Ejari | new | 2026-11-23 | |
| A-001 | 2026-10-26 | /ar/guide/shared-housing-dubai | **Arabic version** of N-004 (hreflang pair, sitemap, tests) | new | 2026-11-23 | |
| D-001 | 2026-10-26 | /guide/ejari-renewal | Depth: “Who pays for Ejari renewal?” (#who-pays-for-ejari-renewal, Art. 22 as general rule) + FAQ | 0 / 427 / 0% / 39.3 | 2026-11-16 | |
| D-002 | 2026-10-26 | /guide/dewa-transfer | Depth: FAQ for PAA query “how do i move my dewa connection when changing apartments” | 8 / 1,108 / 0.72% / 6.6 | 2026-11-16 | |
| F-001 | 2026-10-26 | /guide/dewa-premises-number, / | Fact fix: DEWA “within 24 hours” → “15 working hours” (as verified 2026-10-23 on DEWA pages; DEWA site returned 403 this run); dateModified bumped on premises-number | 257 / 14,076 / — / 5.0 | 2026-11-16 | |
| N-006 | 2026-11-02 | /guide/maintenance-landlord-tenant-dubai | **New article** — Arts. 16, 17, 18, 19, 20, 21, 34 quoted from dlp.dubai.gov.ae; RDC fees; no AED repair threshold in law | new | 2026-11-30 | |
| N-007 | 2026-11-02 | /guide/tenant-not-paying-rent-dubai | **New article** — Art. 25(1)(a) 30-day notice to pay from service, Arts. 7, 31, 34, 35; RDC fees | new | 2026-11-30 | |
| D-003 | 2026-11-02 | /guide/security-deposit-refund-dubai | Depth: RDC monetary-claim fee box (3.5%, AED 500–15,000) + Arts. 20/21; dateModified bumped | 0 / 80 / 0% / 45.1 | 2026-11-23 | |

| N-008 | 2026-11-09 | /guide/landlord-selling-property-tenant-rights | **New article** — Art. 28 (lease survives sale), amended Art. 25(2)(d) (sale ground, 12 months, notary/registered mail; Law 33/2008), notice checklist, RDC fee | new | 2026-12-07 | |
| N-009 | 2026-11-09 | /guide/ejari-co-occupants | **New article** — DLD “Manage Occupants” service steps (UAE ID + DOB, Dubai REST/Ejari, immediate), not a sublease (Art. 24/25(1)(b)) | new | 2026-12-07 | |
| A-002 | 2026-11-09 | /ar/guide/landlord-selling-property-tenant-rights | **Arabic version** of N-008 (hreflang pair, sitemap, tests) | new | 2026-12-07 | |
| D-004 | 2026-11-09 | /guide/rental-dispute | Depth/fact fix: RDC Track Your Case = mobile OR case number, Dubai REST app or website, free, instant (rdc.gov.ae/en/services/track-your-case, fetched 2026-11-09); removed unverified “login” and “SMS” claims; official link updated | 62 / 5,155 / 1.2% / 11.2 | 2026-11-30 | |
| C-017 | 2026-11-09 | /ar/guide/rental-dispute | AR title → “مركز فض المنازعات الإيجارية دبي: الرسوم وتتبع القضية” (clicks 9→0 on 663 impr; matches “رسوم مركز فض المنازعات الإيجارية دبي”, “منازعات الايجارية دبي”) | 0 / 663 / 0% / 11.8 | 2026-11-30 | |
| C-018 | 2026-11-16 | /guide/dewa-activation | Title → “DEWA Registration for New Tenant: Move-in Fees & Steps 2026” (query “dewa registration for new tenant” pos 5.2); H1 + description aligned | 3 / 909 / 0.33% / 10.1 | 2026-12-07 | |
| C-019 | 2026-11-16 | /guide/tenancy-contract-dubai | Title → “Tenancy Contract Dubai: Free PDF, Word & Filled Sample 2026” (≤60 chars, adds filled-sample differentiator) | 107 / 8,793 / 1.22% / 8.6 | 2026-12-07 | |
| C-020 | 2026-11-16 | /tools/rent-increase-calculator | Title → “RERA Calculator Dubai 2026: Rent Increase Check (Free)” (exact head query “rera calculator” 278 impr pos 9.5) | 15 / 844 / 1.78% / 12.0 | 2026-12-07 | |
| C-021 | 2026-11-16 | /guide/early-termination-tenancy-contract-dubai | Title → “Early Termination Penalty Dubai: Tenancy Contract Rules 2026” (query “penalty for early termination…”; was 64 chars) | 5 / 470 / 1.06% / 13.5 | 2026-12-07 | |
| C-022 | 2026-11-16 | /guide/ejari-cancellation | Title → “How to Cancel Ejari in Dubai REST App: Documents & Fee 2026” + H1 (queries “how to cancel ejari on dubai rest app” pos 1–1.2) | 9 / 330 / 2.73% / 22.3 | 2026-12-07 | |
| C-023 | 2026-11-16 | /guide/eviction-notice-dubai | Length fix: title 63 → 54 chars (“Eviction Notice Dubai: 12-Month Rule & 4 Legal Grounds”) | not indexed | 2026-12-07 | |
| N-010 | 2026-11-16 | /guide/tenant-rights-dubai | **New hub article** — 12 rights with article refs (Law 26/2007 Arts. 4, 6, 7, 15–17, 20–21, 25, 26, 28, 34 as amended by Law 33/2008), duties, enforcement + RDC fees, myths; links to all rights guides | new | 2026-12-14 | |
| N-011 | 2026-11-16 | /guide/verify-landlord-title-deed | **New article** — DLD Verify Title Deed (no fees, immediate, website + Dubai REST, all residency statuses, Validate Property / Owner and Property), Property Status Enquiry, amended Art. 4 owner-name rule, scam red flags | new | 2026-12-14 | |
| A-003 | 2026-11-16 | /ar/guide/maintenance-landlord-tenant-dubai | **Arabic version** of N-006 (hreflang pair, sitemap, tests, sitewide AR footer link) | new | 2026-12-14 | |
| D-005 | 2026-11-16 | /guide/ejari-check | Depth: “Before the Ejari: check the landlord’s title deed” section (#check-landlord-title-deed) + FAQ; dateModified 2026-11-16 | 34 / 853 / 3.99% / 12.5 | 2026-12-07 | |

Internal links added 2026-11-09: hub `/guides` cards for N-008/N-009; related cards into N-008 from eviction-notice, rent-increase, early-termination, tenancy-contract, security-deposit; into N-009 from subletting, shared-housing, ejari-registration, ejari-check, addendum; EN↔AR link for A-002.

Internal links added 2026-11-02: hub `/guides` cards for N-006/N-007; related cards into N-006/N-007 from security-deposit, addendum, tenancy-contract, early-termination, eviction-notice, rental-dispute, rent-increase, subletting; deposit page contextual link.

Internal links added: hub `/guides` cards for N-001..003; related cards from rental-dispute, eviction-notice, security-deposit, ejari-cancellation (→ N-001), tenancy-contract, ejari-registration, rent-increase (→ N-002), dewa-activation, dewa-transfer, ejari-renewal (→ N-003); contextual links in tenancy-contract, ejari-cancellation, dewa-activation.

Internal links added 2026-10-26: hub `/guides` cards for N-004/N-005; related cards from eviction-notice, rental-dispute (→ both), tenancy-contract, ejari-registration, ejari-check (→ N-004), addendum, early-termination (→ N-005); EN↔AR link for A-001.

Internal links added 2026-11-16: sitewide footer “Tenant rights” (EN pages) + “صيانة العقار المؤجر” (AR column); hub `/guides` cards for N-010/N-011; related cards into N-010 from eviction-notice, maintenance, security-deposit, rental-dispute, rent-increase, tenant-not-paying, landlord-selling, early-termination; into N-011 from tenancy-contract, ejari-registration, subletting (+ contextual from ejari-check). N-010 itself links to every not-indexed rights page. Fixed co-occupants CTA (said “generate contract” but linked the lawyer at lawyer price → now generator at contract price).

### Sources checked 2026-11-16
* [Law 26/2007](https://dlp.dubai.gov.ae/Legislation%20Reference/2007/Law%20No.%20%2826%29%20of%202007%20Regarding%20regulation%20between%20the%20lessor%20and%20the%20lessee.html) fetched: Arts. 6, 7, 15–24, 28, 31, 34 text. [Law 33/2008](https://dlp.dubai.gov.ae/Legislation%20Reference/2009/Law%20No.%20%2833%29%20of%202008%20Amending%20Law%20No.%20%2826%29%20of%202007.html) fetched: amended Arts. 4 (owner name if landlord is not owner), 9, 13, 14 (90 days), 25, 26, 29.
* [RDC first-instance fees](https://rdc.gov.ae/en/eservices/register-first-instance-lawsuit-rental/) fetched: 3.5% annual rent AED 500–20,000; monetary 3.5% AED 500–15,000; process service AED 100; knowledge fee AED 10; PoA AED 25.
* [DLD Verify Title Deed](https://dubailand.gov.ae/en/eservices/title-deed-verification-overview/) + form page fetched: no fees, immediate, no documents, website + Dubai REST, all residency statuses, inputs deed no./year/type (+ owner). [DLD Property Status Enquiry](https://dubailand.gov.ae/en/eservices/property-status-overview/): area + land number, immediate, website + app.
* DEWA pages 403 again (curl + WebFetch) — no new DEWA figures written; dewa-activation retitle reuses figures verified 2026-10-23.
* Noted: a DLD `ejari_unified_tenancy_contract_v3.pdf` appears in search but returns 404; our linked `media/4cglen5i/...pdf` still 200.

### Sources checked 2026-11-09
* [Law 26/2007](https://dlp.dubai.gov.ae/Legislation%20Reference/2007/Law%20No.%20%2826%29%20of%202007%20Regarding%20regulation%20between%20the%20lessor%20and%20the%20lessee.html) Art. 28, 34 (fetched); [Law 33/2008](https://dlp.dubai.gov.ae/Legislation%20Reference/2009/Law%20No.%20%2833%29%20of%202008%20Amending%20Law%20No.%20%2826%29%20of%202007.html) amended Art. 25 (owner wishes to sell = ground on expiry; 12 months; notary or registered mail) and Art. 26 (2/3-year re-let bar applies to personal-use repossession only).
* [DLD occupants registration service](https://dubailand.gov.ae/en/eservices/steps-to-manage-co-occupants-overview/) fetched: steps, UAE ID + DOB, immediate, Ejari system / Dubai REST; no fee stated on page — fee NOT claimed.
* [RDC track your case](https://rdc.gov.ae/en/services/track-your-case/) fetched: mobile or case number, free, instant, no phone number listed.
* Bounced-cheque article NOT written: only portal/law-firm sources found; Decree-Law 50/2022 text not verified.

### Sources checked 2026-11-02
* [Law 26/2007 full text](https://dlp.dubai.gov.ae/Legislation%20Reference/2007/Law%20No.%20%2826%29%20of%202007%20Regarding%20regulation%20between%20the%20lessor%20and%20the%20lessee.html) fetched: Arts. 7, 16–21, 24, 25, 31, 34, 35 quoted/paraphrased.
* [RDC first-instance fee page](https://rdc.gov.ae/en/eservices/register-first-instance-lawsuit-rental/) fetched: 3.5% of annual rent (AED 500–20,000) for eviction/renewal/rent/termination; 3.5% of claimed amount (AED 500–15,000) for monetary claims; process service AED 100.
* Competitor SERPs for maintenance and bounced cheques are law-firm/portal blogs; no official rule found for an AED repair threshold — omitted.

### Sources checked 2026-10-26
* Shared housing: [Dubai Media Office, 11 Mar 2026](https://www.mediaoffice.ae/en/news/2026/march/11-03/mohammed-bin-rashid-issues-law-regulating-the-management) (permit, fines, 6-month suspension, RDC jurisdiction, 1-year compliance, no tenant sublease); [DM Circular 1-3-1/2026 PDF](https://dmpmedia.dm.gov.ae/uploads/2026/09/1-3-1-Document.pdf) (read via pdftotext: dated 7 Sep 2026, in force 8 Sep 2026, whole building, one category, Building Platform). Space-per-occupant figures NOT stated — not verified from an official source.
* Subletting: [Law 26/2007](https://dlp.dubai.gov.ae/Legislation%20Reference/2007/Law%20No.%20%2826%29%20of%202007%20Regarding%20regulation%20between%20the%20lessor%20and%20the%20lessee.html) Arts. 8, 22, 24, 25, 30; [DLD FAQ](https://dubailand.gov.ae/en/frequently-asked-questions/) (co-occupant: no Ejari certificate; no two-name Ejari; facility-management companies may not sub-lease).
* u.ae family visa page: salary AED 4,000 or 3,000 + accommodation (28 Sep 2026 page) — GDRFA pages returned 403, so the family-visa article was NOT written.

### Sources checked 2026-10-23
* DEWA [Move-to](https://www.dewa.gov.ae/en/consumer/supply-management/transfer-of-electricity-water-move-to), [Move-in](https://www.dewa.gov.ae/en/consumer/supply-management/activation-of-electricity-water-move-in), [Move-out](https://www.dewa.gov.ae/en/consumer/supply-management/deactivation-of-electricity-water-move-out); [DEWA–Ejari integration release, Feb 2024](https://www.dewa.gov.ae/en/about-us/media-publications/latest-news/2024/02/dewa-electronically-received-data-of-over)
* [Law 26/2007](https://dlp.dubai.gov.ae/Legislation%20Reference/2007/Law%20No.%20%2826%29%20of%202007%20Regarding%20regulation%20between%20the%20lessor%20and%20the%20lessee.html), [Law 33/2008](https://dlp.dubai.gov.ae/Legislation%20Reference/2009/Law%20No.%20%2833%29%20of%202008%20Amending%20Law%20No.%20%2826%29%20of%202007.html), [Decree 43/2013](https://dlp.dubai.gov.ae/Legislation%20Reference/2013/Decree%20No.%20(43)%20of%202013%20Determining%20Rent%20Increase%20for%20Real%20Property.html)
* [DLD Unified Tenancy Contract PDF](https://dubailand.gov.ae/media/4cglen5i/ejari_unified_tenancy_contract.pdf) (5 Additional Terms lines, clauses 12–14); [DLD cancel tenancy contract](https://dubailand.gov.ae/en/eservices/cancel-tenancy-contract) (free online, AED 40 + VAT centre, owner's letter for active contract)
* [RDC first-instance fees](https://rdc.gov.ae/en/eservices/register-first-instance-lawsuit-rental/) — 3.5% of annual rent, AED 500–20,000; monetary claims cap AED 15,000; [DLD amicable settlement](https://dubailand.gov.ae/en/eservices/dispute-lawsuit-for-amicable-settlement) — half fee refunded on settlement
* Housing fee: no DM page states the rate; 5% from DM officials quoted by Gulf News (2018) and consistent portal guides (Bayut Sep 2026); [DM refund service](https://www.dm.gov.ae/easy-payments/refund-of-fines-or-already-paid-fees/)

## Content backlog (from 2026-10-23 gap research — highest first; shipped: N-004/N-005, N-006/N-007, N-008 selling + N-009 co-occupants on 2026-11-09, N-010 tenant-rights + N-011 title-deed on 2026-11-16)

| Slug | Main query | Feeds | Notes / must-verify |
|---|---|---|---|
| /guide/ejari-family-visa | ejari for family visa, attested tenancy contract gdrfa | Generator (strongest buying intent) | GDRFA page; salary thresholds via u.ae/ICP |
| /guide/maintenance-landlord-tenant-dubai | who pays maintenance dubai rental, landlord not fixing ac | AI lawyer | Arts. 16, 17, 19, 21; RDC FAQ remedies |
| /guide/bounced-rent-cheque-dubai | bounced rent cheque dubai | AI lawyer | Decriminalised 2022; Decree-Law 50/2022; RDC payment-writ; DLD news on penalty clause cut to AED 5,000 |
| /guide/tenant-not-paying-rent-dubai | tenant not paying rent dubai | AI lawyer (landlords) | Art. 25(1)(a) 30-day notice, Art. 31, Art. 34; deposit-and-offer |
| /guide/ejari-co-occupants | add family to ejari | Traffic | DLD Manage Occupants service |
| /guide/landlord-selling-property-tenant-rights | landlord selling property dubai tenant rights | AI lawyer | Art. 28, Art. 25(2)(d) |
| /guide/rent-out-property-dubai-without-agent | rent out property dubai without agent | Generator | Landlord DIY Ejari; Art. 4 |
| /guide/landlord-cut-utilities-dubai | landlord cut electricity dubai | AI lawyer | Art. 34; RDC urgent petition (DLD news) |

Arabic candidates: tenant-rights hub (حقوق المستأجر في دبي), tenant-not-paying, early-termination. Done: shared housing, selling, maintenance.

## Backlog — existing pages
* **Indexing:** requested 2026-10-23 for dubai-housing-fee, early-termination, tenancy-contract-addendum, security-deposit-refund, ejari-number, rent calculator. **Still to request next run:** /guide/eviction-notice-dubai (GSC error twice, likely daily quota), /about. Check whether requested pages got crawled.
* `/guide/ejari-renewal` — add a “Who pays for Ejari renewal?” section (2 Gulf News pages rank for it).
* `/guide/security-deposit-refund-dubai` — add RDC monetary-claim fee (3.5%, AED 500–15,000) and “rent deposit vs DEWA deposit” box.
* `/guide/dewa-premises-number`, `/index.html` still say DEWA connects “within 24 hours” (official: 15 working hours).
* `/guide/dewa-premises-number` says the number is printed on the Ejari certificate; one competitor (egsh) says it isn't — verify with a real certificate.
* Early-termination: Art. 738 of Federal Decree-Law 25/2025 (single source) — add only once verified.

## Learnings
* (2026-11-16, first evaluation of the 10-23 batch, 22-day windows 1–22 Oct vs 23 Oct–13 Nov) Titles that open with the exact head query + a concrete official hook won: RDC “Case Status, Contact Number & Filing Fee” (+200%), “What Is Ejari? Meaning, Cost…” (0→21), “Ejari Renewal Online…Documents Required” (0→16), DEWA “Deposit Moves With You” (+169%). Generic “2026: Free PDF & Word Download” on tenancy-contract did not lift clicks.
* Control in `opportunities.py evaluate` = whole site minus page; with fast-growing new pages and the 4 Nov one-day spike the control overstates the trend (+70%) — a page can be “LOSS” while its own CTR rose significantly. Next evaluations: exclude pages published after the baseline window and 2026-11-04 from the control.
* English queries land on AR pages (/ar/guide/ejari-renewal gets “how much is ejari renewal fee”, CTR 0.5%) — hreflang works but Google still serves AR; watch.

## Run log
* 2026-10-23 (setup) — baseline pulled; C-001, C-002 shipped; DEWA fee consistency test added.
* 2026-10-23 — indexing requested via Search Console (Chrome): dubai-housing-fee, early-termination, tenancy-contract-addendum, security-deposit-refund. Eviction-notice failed (GSC error); ejari-number, rent calculator, about not yet requested (Chrome disconnected).
* 2026-10-23 (growth mode) — full competitor sweep (18 clusters), titles rewritten on 14 pages (C-003..C-016), 3 new articles (N-001..003), indexing gaps found (5 URLs), playbook switched to growth mode.
* 2026-10-26 — GSC 28d (to 23 Oct): 459 clicks (+4.6%) / 24,866 impr (−3.2%) / 1.85% / pos 9.1 (28/32 indexed). BLOCKED: handoff patch from 10-26 could not be restored byte-exact from Drive (Drive text export is markdown-escaped, base64 too large to transcribe) — skipped, gsc.py rewritten from its text, N-004/N-005/A-001 and depth work redone from primary sources. Family-visa article skipped (GDRFA 403). No titles changed: all 14 are inside the 21-day cool-down (until 2026-11-13). No evaluations due. Indexing cannot be requested via API: ejari-number, eviction-notice, about, terms still 'Discovered – not indexed' → more internal links + sitemap resubmit. Next run: evaluate C-001..C-016 from 2026-11-13, write ejari-family-visa only if GDRFA/ICP sources are reachable, then maintenance-landlord / bounced-cheque from the backlog.
* 2026-11-02 — GSC 28d (3–30 Oct): 432 clicks (−1.8%) / 26,415 impr (+6.2%) / 1.64% / pos 9.2 (was 10.8); 30/35 indexed. Titles NOT changed: all inside 21-day cool-down until 2026-11-13 (no page lost >30% clicks with a significant base). Shipped N-006, N-007, D-003 + links. SKIPPED this run: Arabic page, 2nd depth upgrade, competitor SERP rotation (only maintenance + bounced-cheque queries checked) — do next run. Watch: /ar/guide/rental-dispute 8→1 clicks (not retitled yet), tenancy-contract-dubai clicks 136→110 (position improved 9.8→8.2, CTR fell; evaluate 11-13). Next run: evaluate C-001..C-016 (due 11-13), request-less indexing push for ejari-number/eviction-notice/shared-housing/about/terms via links, AR version of maintenance or tenant-rights, bounced-cheque article (need Decree-Law 50/2022 source).
* 2026-11-09 — GSC 28d (10 Oct–6 Nov): 650 clicks (+44.4%) / 26,784 impr (+8.6%) / 2.43% / pos 9.5; 31/37 indexed. Titles NOT changed on the 16 pages from 10-23 (cool-down until 11-13; no page lost >30% with a real base); only /ar/guide/rental-dispute retitled (never in the 10-23 batch). Early signals on rewrites: rental-dispute 13→62 clicks, ejari-check 12→31, dewa-transfer 5→17, ejari-cost 0→13, what-is-ejari 2→21; tenancy-contract-dubai 137→120 (pos 9.2→8.1, CTR 1.24%) — formal evaluation 11-13+. dubai-housing-fee: 56 clicks / 366 impr in first weeks. Shipped N-008, N-009, A-002, D-004, C-017 + links. Competitor SERPs checked: selling/tenant rights, bounced cheque, RDC case status (sources are portals/law-firm blogs; realestateclubdubai has a 2026 selling guide). SKIPPED: 2nd depth upgrade, bounced-cheque (no official source). Env note: unpinned `pypdf` in requirements.txt — pypdf>=6.17 raises DeprecationError in generator (`replace_contents`), 4 generator tests fail on fresh install; passed with pypdf 5.9.0. Production risk if Railway rebuilds with latest pypdf — payment-funnel code not touched by agent. Next run: evaluate C-001..C-016 (due 11-13), request-less indexing push for the 6 unindexed URLs, bounced-cheque only with Decree-Law 50/2022 source, AR for maintenance/non-payment.
* 2026-11-09 (post-deploy) — Railway deploy of 3865491 live (titles verified on 4 URLs); sitemap resubmitted (204). New URLs just discovered by Google: ejari-co-occupants unknown, selling EN/AR 'Discovered, not indexed' — recheck next run.
* 2026-11-16 — GSC 28d (17 Oct–13 Nov): 714 clicks (+54.2%) / 27,115 impr (+11.6%) / 2.63% / pos 10.0; 32/40 indexed (via API URL Inspection). First evaluation of C-001..C-016: 5 WIN, 1 LOSS-by-formula kept (premises-number, control artefact), rest neutral/inconclusive, no rollbacks. Shipped 6 titles (C-018..C-023), N-010 tenant-rights hub, N-011 verify title deed, A-003 AR maintenance, D-005 ejari-check depth, sitewide footer links. Competitor SERPs checked: tenant rights, title deed verification, dewa registration new tenant, cancel ejari dubai rest, rera calculator, tenancy contract download. BLOCKED: request-indexing has no API and Chrome not available in cloud → relied on internal links + sitemap; DEWA 403. Env: test env needed `pip install --ignore-installed blinker pillow cffi cryptography` + pypdf<6.
