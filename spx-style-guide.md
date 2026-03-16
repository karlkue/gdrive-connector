# SPX PH Update — Style Guide

*Synthesized from 18 decks spanning Jan 2025 – Mar 2026.*
*Use this guide to review draft material and suggest improvements to match the SPX PH Update style, structure, and tone.*

---

## 1. Document Structure

Every SPX PH Update follows this section order. Sections are always present; some may be combined or expanded based on what's relevant that week.

### Slide Order (Current — 2026 Standard)

| Slide | Section | Notes |
|---|---|---|
| 1 | Title: "SPX PH Update [Date]" | Date format: `12 March 2026` (day Month year) |
| 2 | Executive Summary | 5–7 numbered sections with page refs (2026+); earlier = bullets by topic |
| 3 | Section divider: "OKR, Cost Initiatives and Budget Update" | |
| 4 | Overall OKR table | Two-status color coding |
| 5 | P&L / CPO commentary | Current month + MoM compare |
| 6+ | [Backup] Ops Stats vs Budget | Not always updated in real-time |
| next | Speed Updates | BWT trend + J&T benchmark + internal target |
| next | Operations (Last Mile / SOC×MM / First Mile) | Varies by what's notable |
| next | Coverage and Expansion | |
| next | NSS (Non-Shopee Sales) | Became a regular section mid-2025 |
| next | Loss & Claims | Always present; recent decks add AI Loss pilot slides |
| next | Technology / AI (2026+) | Control Tower, Hub Copilot, automation pilots |
| next | FinOps / User Experience (2026+) | COD exposure, buyer perception |

### Pre-2026 Slide Order

Earlier decks (Jan–Jul 2025) have a simpler flow:
1. Title → Exec Summary bullets → OKR table → CPO → Speed → Ops sections → Coverage → L&C

No NSS section in early 2025. Technology/AI sections appear only from ~Aug 2025 onwards.

---

## 2. Executive Summary Formula

### 2026 Format (Current Best Practice)

One-sentence framing paragraph, then 4–7 **numbered sections** each with a page reference.

**Template:**
```
SPX remains [overall status phrase] with [key performance dimension 1] and [key performance dimension 2].

1. [Section Name] (p.X–Y): [Key message]. [Supporting detail or implication].
2. [Section Name] (p.X–Y): [Key message]. [Supporting detail or implication].
3. [Section Name] (p.X–Y): [Key message]. [Supporting detail or implication].
...
```

**Real example (Mar 2026):**
> SPX remains operationally on track with improving speed reliability, strong productivity gains, and CPO performance ahead of plan.
>
> 1. Operations & Financial Performance (p.3–7): CPO remains below target with March outlook ~$1.6M better vs plan, driven by higher volumes and productivity improvements.
> 2. Capacity, Network & Expansion (p.8–19): Preparation underway for potential ramp to 100% SPX share, with May as the latest decision point.
> 3. Technology & AI Transformation (p.20–35): AI Control Tower pilots show ~85% delay detection accuracy and potential to reduce monitoring HC by up to ~50%.
> 4. Loss Reduction & Operational Automation (p.36–42): Early AI pilots for loss detection and investigation automation are generating progress.
> 5. Financial Controls & Risk (p.43–46): COD exposure continues to decline (₱97M) with improving remittance performance.

### 2025 Format (Earlier Decks)

Short bullet per functional area. No page references. Less strategic framing, more operational.

**Template:**
```
[Section/Function]
[1-2 sentence bullet covering key status + watchpoint or action]

Last Mile
[bullet]

First Mile
[bullet]

SOC/MM
[bullet]

Coverage and Expansion
[bullet]

Loss & Claims
[bullet]
```

**Rule of thumb:** Use the 2026 format for new material. Use 2025 format if the audience/format is clearly the older style.

### What the Opening Framing Line Should Do

Always includes one of these posture phrases:
- "SPX remains operationally on track with..."
- "Overall operation recovers after... [X]; [Y region] expected to return to normal by [timeframe]"
- "BWT improved to X.XX, with Urban BWT... being Top 3 across SPX Markets"

Then lists the 2–3 top themes for the deck.

---

## 3. OKR Table

The OKR table is the single most stable element across all 18 decks. Replicate it exactly.

### Column Structure (Exact)

```
Key Pillar | Metrics | [Month'YY] (Latest/MTD) | [Month'YY] Target
```

- "Latest/MTD" = most recent L7D or mid-month actual
- "Target" = full-month OKR target

### Status Indicators (Two Lines Always Appear)

```
Confident to be on track to meet target
Miss target to problem solve
```

No intermediate states. Each row implicitly maps to one of these.

### Metrics by Pillar (2026 Standard)

| Key Pillar | Metrics |
|---|---|
| **Maintain cost Advantage** | Overall SPX CPO ($) |
| **Improve SPX volume** | % SHP ADO |
| | % SPX LM Coverage / Buyer Coverage (w/ FEX) |
| | % SPX LM Coverage / Buyer Coverage (w/o FEX) |
| | % SPX FM Coverage / Seller Coverage |
| **Improve Logistics speed** | Average BWT SPX |
| | % urban orders delivered D+1 |
| | % urban orders delivered D+2 |
| | % non-urban orders delivered D+2 |
| | % non-urban orders delivered D+3 |
| **Improve SPX experience / quality** | 99%ile BWT |
| | % Order loss rate |
| | BSC Coverage % *(added 2026)* |
| **Enhance capabilities as standalone 3PL** | % Reverse Coverage |
| | Non Shopee ADO |
| | Non Shopee Profit per Order ($) |

**Notes:**
- CPO is always in `$0.XXX` format (3 decimal places)
- ADO is a whole number (e.g., `22,808`)
- Coverage percentages to 1 decimal (e.g., `99.8%`)
- BWT to 2 decimals (e.g., `3.15`)
- Loss rate to 2 decimal places (e.g., `0.17%`)
- New in 2026: "Cache % of platform" added under Improve SPX volume

---

## 4. P&L / CPO Section — Sentence Patterns

This section always contains two types of commentary:

### Pattern A: P&L Summary Sentence (Always First)

```
[Month] [initial/updated] P&L [better/higher] by $[X]M vs target[, CPO [X]c [lower/higher]]
```

Optionally followed by driver phrase:
```
[Month] P&L better by +$[X]M vs target mainly from [primary driver]
```

Then itemized P&L drivers:
```
+$[X]m [brief reason]
+$[X]m [brief reason]
-$[X]m [brief reason]
```

### Pattern B: CPO Component Waterfall (Always Present)

```
CPO [better/higher] by [X]c with [main driver]; [secondary driver]

FM (-0.Xc) [reason]
SOC (-0.Xc)
  0.Xc [specific sub-driver]
  0.Xc [specific sub-driver]
LH (+0.Xc) - [reason]
Hub (-0.Xc) - [reason]
LM (+0.Xc) - [reason]
Claims (+0.Xc) - [reason]
```

Then always a MoM comparison:
```
Compared to last month, CPO is [lower/higher] by [X]c with [Xc] due to [reason]; balance [from] [other reasons]
```

### Writing Rules for CPO Section

1. **Always show the sign** — `-0.3c` = cost improvement, `+0.3c` = cost increase
2. **Sub-items use indented lines without bullets**, often with `0.Xc` inline
3. **Claims always reported** with both loss rate and recovery rate
4. **One-off items** go at the end with `One-off (+/-Xc)` label
5. **FX rate note** appears at top: `*FX at [rate]`

---

## 5. Speed Section Structure

### BWT Trend Table

Always shows 4 recent weeks + J&T comparison + quarterly targets:

```
Metrics | Latest Week | J&T Latest Week | 2025/2026 Target
        | Wk of [date] | Wk of [date] | Wk of [date] | Wk of [date] | [same for J&T] | Mar'26 | Jun'26 | Sep'26 | Dec'25
Average BWT SPX | X.XX | X.XX | X.XX | X.XX | (J&T) | X.XX | X.XX | X.XX | X.XX
Average CDT SPX | ...
Urban CDT | ...
Non-urban CDT | ...
% urban orders delivered D+1 | ...
% urban orders delivered D+2 | ...
% non-urban orders delivered D+2 | ...
% non-urban orders delivered D+3 | ...
```

### Speed Commentary Sentence Patterns

**Headline:** `BWT: [status phrase]; [regional breakdown or key driver]`

Examples:
- "BWT: recovered to 3.47 Days post typhoon; improvement WoW for both urban & non urban; pending gaps on both operations & structural mapped to be closed from now till October"
- "BWT improved to 2.91, with Urban BWT & D+1% being Top 3 across SPX Markets"
- "Speed on track to meet internal targets, with some urban long tail fixes in the pipeline targeted towards increasing NDD marketability"

**Standard items in speed section:**
1. BWT headline with WoW trend and J&T gap (always: "Gap w. J&T - X.XX")
2. Regional breakdown (GMA/NCR, LUZ, VIS, MIN) with specific CDTs
3. Key lever / watchpoint
4. Ops Clock section — breakdown by leg (FM, SOC, LH/MM, Hub, LM) with COT compliance
5. "Faster Delivery Channels" update if SDD/MFM relevant

---

## 6. Operations Sections — Standard Patterns

Each ops section (Last Mile, SOC×MM, First Mile) follows the same pattern:

### Bullet Formula

```
[Region or Leg]: [Status/metric result]; [Driver]; [Plan/Action]
```

Examples:
- "SOC - Speed and Lost performance are on target, while Capacity, Reliability, and Prod impacted by April low volume and Holy Week."
- "VIS/MIN continuing to flush out backlog; DTD < 1.5"
- "Backlog in OP hubs stabilizing post-holiday; improvements seen in active fleet & processed volumes"

### Metrics Reported in Operations Sections

| LM | SOC/MM | FM |
|---|---|---|
| Active Riders (WoW%) | Sorter productivity (pph) | FM Productivity (parcels/truck) |
| Rider Productivity | SOC depart OTP | CB/DTS/WL share |
| Success Rate | RC productivity | Truck type split |
| LM Received (WoW%) | Backroom productivity | 2nd trip utilization |
| LM Delivered (WoW%) | SOC capacity | FM attendance |
| Flash rate status | OT hours | |
| DTD (Days to Deliver) | Loss per leg | |

### Regional Splits Always Shown

Tables always have columns: `PH | NCR/GMA | NOL | SOL | VIS | MIN`

---

## 7. Coverage & Expansion — Standard Format

### Buyer Coverage Bullet Pattern

```
[Region or Total]: [Coverage %] [SPX only / w/ FEX]; expected to reach [X%] by [timeframe] [after/through] [initiative]
```

### Seller Coverage Bullet Pattern

```
[%] seller coverage expected by [Month 'YY] with [initiative]; remaining issues slated for [Month], but [qualifier]
```

### Expansion items typically cover:

- New hub openings (OP hub, BSC, RC, SOC) with status: "live on [date]", "ongoing layout", "for TOR signing"
- BSC pilot results — buyer penetration % vs urban BSC benchmark
- MFM expansion status — PPH % of target, cluster count
- 3PL/J&T competitive expansion moves (especially in non-urban areas)

---

## 8. Loss & Claims Section

### Standard Bullet Patterns

**Monthly summary:**
```
[Month] [overall/MTD] loss rate at [X]%, [above/below] internal target of [Y]%[. Main driver: ...]
```

**Category breakdown:**
```
Steady loss rate decline observed for most legs over past 3 weeks, but loss CPO on upward trend for [legs]
```

**Recovery:**
```
[Month] recovery rate [X]% mapped to loss COGS. Recovery rate based on actual debit memos at [Y]%...
```

**GC/agency accountability:**
```
To date, ~[X]% of agencies signed the GC contract, with USD [Y]k GC recovery in [month]
```

### Recent Additions (2025–2026)

From 2025 Q3 onwards: AI-driven loss detection pilots appear as sub-sections:
- "AI pilots for loss detection and investigation automation"
- Framing: REACTIVE → DETECTIVE → PROACTIVE framework
- Opportunity quantified: `$[X]k+/month recovery potential`
- HC savings quantified: `[X] manhours/month (~[Y] HC/month)`

---

## 9. Technology & AI Section (2026 Standard)

Added as a standalone section from approximately Aug 2025, prominent from Oct 2025 onwards.

### Standard AI/Tech Slide Patterns

**Control Tower update:**
```
AI Control Tower [pilot status]: [pilots show X% accuracy / capability]; potential to reduce [monitoring HC / ops load] by [X%] through [mechanism]
```

**Productivity improvement:**
```
[System/Initiative]: [current vs. previous productivity]; [next step / target]
```

**Format for capability maturity:**
```
Stage 0: [Local/manual]
Stage 1: [Regional model]
Stage 2: [Locally-run solver]
Stage 3: [Algorithm-based optimizer]
```

---

## 10. NSS (Non-Shopee Sales) Section

Appears consistently from mid-2025 onwards.

**Headline format:**
```
[Month] MTD at [X]k ADO[; WTD at [Y]k driven by [driver]]; [key issue or watchpoint]
```

**Standard metrics:**
- MTD ADO (absolute number, in thousands: "12k ADO")
- Key channels: 3PF partnerships, field sales, owned DOP locations
- Churn / acquisition updates
- Competitive context (J&T/FEX aggressively locking in clients)

---

## 11. Vocabulary Reference

### Core Abbreviations (Always Use — Never Spell Out)

| Term | Meaning |
|---|---|
| BWT | Buyer Wait Time |
| CPO | Cost Per Order |
| ADO | Average Daily Orders |
| MTD | Month to Date |
| L7D | Last 7 Days |
| WoW / MoM | Week-over-Week / Month-over-Month |
| NDD | Next Day Delivery |
| D+1, D+2, D+3 | Delivered by Day+1/2/3 after pickup |
| DTD | Days to Deliver |
| COT | Cut-Off Time |
| OTP | On-Time Pickup |
| OTD | On-Time Delivery |
| CDT | Customer Delivery Time (leg metric) |
| APT | All Parcel Time |
| SDD | Same Day Delivery |

### Network / Operations Terms

| Term | Meaning |
|---|---|
| LM | Last Mile |
| FM | First Mile |
| MM | Mid Mile |
| LH | Linehaul |
| SOC | Sort Operations Center |
| RC | Regional Center |
| MFM | Metro Fulfillment Center |
| BSC | Buy Station Center |
| OP | Operator Partner (third-party hub) |
| BR | Backroom (sorting ops at hub) |
| DTS | Drop-to-Sort |
| CB | Catch-Back (rider picking up at hub) |
| WL | Wet Lease |
| RORO | Roll-on/Roll-off (inter-island shipping) |
| Sdrop | Shop Drop (delivery mode) |

### Regional Abbreviations

| Term | Meaning |
|---|---|
| PH | Philippines (national total) |
| NCR | National Capital Region |
| GMA | Greater Manila Area |
| NOL | North Luzon |
| SOL | South Luzon |
| LUZ | Luzon |
| VIS | Visayas |
| MIN | Mindanao |
| VISMIN | Visayas + Mindanao combined |

### Business Terms

| Term | Meaning |
|---|---|
| SHP | Shopee |
| J&T | J&T Express (primary competitor) |
| TTS | Competitor benchmark for speed (mystery shopping) |
| FEX | Fulfillment by Shopee Express (4PL) |
| NSS | Non-Shopee Sales |
| 3PL / 4PL | Third/Fourth Party Logistics |
| GC | Group Charge (agency accountability contract) |
| COD | Cash on Delivery |
| DM/CM | Debit Memo / Credit Memo |
| HVI | High-Value Items |
| PNR | Parcel Non-Receipt |
| IR | Incident Report |
| BSLA | [Branch-level SLA?] |
| PPH | Parcels Per Hour |
| NFTE | Non-Full-Time Employee |
| HC | Headcount |
| R&M | Repair and Maintenance |
| FTE | Full-Time Employee |
| RPO | Revenue Per Order |

### Status Phrases

| Phrase | Usage |
|---|---|
| "on track" | Meeting or beating target |
| "watchpoint" | Item to monitor, not yet at risk |
| "miss target to problem solve" | Behind OKR target |
| "confident to be on track" | Green status |
| "recovering" | Recently below target, improving |
| "flash rates" | Temporary rider incentives for high-backlog hubs |
| "VC" | Volume Control (reducing incoming to struggling hub) |
| "long tail" | Performance outliers / problematic minority |
| "flush out backlog" | Clear accumulated undelivered parcels |

---

## 12. Bullet Writing Rules

### Do This

- **Lead with the metric or outcome**: "BWT improved to 2.91..." not "We have improved BWT..."
- **Include the number inline**: "CPO at 0.776, 1.1c lower vs target" — never "CPO is better"
- **State the driver**: Always follow a metric with "driven by / due to / mainly from"
- **Use WoW/MoM comparisons**: "3.74 → 3.17 Days WoW" or "better by 2.4c MoM"
- **Regional specificity**: "NCR/LUZ have been able to recover within a few days; DTD < 1"
- **Action framing for problems**: "[Problem]; [Active verb] to [Solution/Plan]"
- **Quantify plans**: "target to reach 97.4% by Aug W2", not "target to expand coverage"

### Avoid This

- Passive voice: "has been improved" → "improved to"
- Vague attribution: "due to various factors" → name the 2-3 factors
- Future-only framing: "we will improve" → "ongoing; expect improvement by [date]"
- Round numbers for actuals: "about 78%" → "77.9%"
- Spelling out acronyms in the slide (in the audience's vocabulary already)
- Present tense for trends: "performance is recovering" → "performance recovered WoW; VIS/MIN flushing backlog"
- Opening bullet with "We" or "Our team" — lead with the metric

### Bullet Length

- **Exec Summary**: 1–2 sentences per item. Max 40 words.
- **Ops sections**: 1–3 sentences. Include metric, driver, and action.
- **OKR table footnotes**: ≤15 words. Data-only.
- **CPO waterfall**: Each line 3–8 words. No full sentences.

---

## 13. Number Formatting Rules

| What | Format | Example |
|---|---|---|
| CPO | `$0.XXX` (3 decimal places) | `$0.773` |
| CPO change | `[+/-]X.Xc` | `-1.3c`, `+0.7c` |
| P&L variance | `$[X.X]M` or `$[X]k` | `$2.0M`, `$418k` |
| ADO | Integer with comma | `2,483,527` or `23k ADO` |
| BWT | `X.XX` days | `3.15` |
| Coverage % | `XX.X%` | `99.8%` |
| Loss rate | `0.XX%` | `0.17%` |
| Delivery % | `XX.X%` | `42.3%` |
| COGS/recovery | `$XXk` | `$54.8k` |
| HC reduction | `~XX%` | `~50%` |
| Revenue | Always USD ($) unless explicitly PHP (₱) | |
| Estimates | Use `~` prefix | `~$1.6M`, `~85%` |

---

## 14. Era-Specific Notes

### Early 2025 (Jan–Apr 2025)
- Exec summary = operational bullets per leg, no strategic framing
- OKR table has fewer metrics (no BSC Coverage, no Cache %)
- CPO section focuses on holiday recovery patterns
- No NSS section; "Enhance capabilities as standalone 3PL" OKR included but small
- J&T comparisons mentioned but less data-rich

### Mid 2025 (May–Sep 2025)
- J&T benchmarking becomes much more prominent (BWT gap, Ops Clock Index)
- NSS section appears as regular fixture
- MFM expansion updates start appearing
- Eco channel + SDD faster delivery pilots begin
- Speed section adds "Faster Delivery Channels" sub-section

### Late 2025 (Oct–Dec 2025)
- Technology/AI sections appear (Control Tower, backroom optimization)
- Coverage metrics improve significantly (98–99%)
- Campaign performance (11.11, 12.12) appears as ops stress test
- NSS scaling more prominent with 3PF/DOP expansion
- Exec summary starts moving toward numbered structure

### 2026 Q1 (Jan–Mar 2026)
- Full numbered exec summary with page references
- FinOps section added (COD exposure, DM/CM processing time)
- User Experience section (buyer perception vs J&T, branding)
- AI sections more detailed (ROI quantification, stage-based maturity models)
- "100% SPX share" scenario planning becomes prominent
- Speed benchmarked against TTS mystery shopping (not just J&T)
- SOC productivity improvement via algorithm-based solver is a major highlight

---

## 15. Annotated Examples

### Example 1: Strong Exec Summary Bullet (2026 style)

✅ **Good:**
> 2. Speed Updates (p.8–19): Q1 speed performance is recovering from storm disruptions, with RC cut-off reforms and VISMIN operational adjustments expected to improve overall BWT by ~0.07 days once fully implemented.

Why it works:
- Named section with page reference
- Acknowledges headwind (storm disruptions) without being defensive
- Specific lever (RC cut-off reforms, VISMIN ops adjustments)
- Quantified outcome (~0.07 days improvement)

❌ **Weaker:**
> Speed is recovering after the storms. We are working on various improvements across different regions to improve our BWT.

### Example 2: Strong CPO Waterfall Bullet

✅ **Good:**
> FM (-0.3c)
> -0.2c better FM truck prod [762 vs 734] and MFM sorter prod [961 vs. 847]
> -0.1c lower fixed cpo w/ higher ADO

Why it works:
- Sign shows direction immediately
- Bracketed comparisons [actual vs. prior/target]
- Sub-items sum to total
- Concise — no full sentences

### Example 3: Strong Operations Bullet

✅ **Good:**
> SOC capacity well-covered for SPX demand up to 2026 with SOC 8 live in Jun'25 and full ramp-up Mar'26

Why it works:
- Leads with status conclusion ("well-covered")
- Gives horizon ("up to 2026")
- Specific milestones with dates

❌ **Weaker:**
> We are on track with SOC expansion and there should be enough capacity for the foreseeable future based on our current projections.

### Example 4: Strong Coverage Bullet

✅ **Good:**
> Jul MTD SPX LM created coverage at 96.8% with SPX-FEX at 99.5%, both exceeding H1-Jul OKR targets; to hit 97.3% by EOM by high-risk openings

Why it works:
- Two coverage figures (SPX only + with FEX)
- References OKR status
- Specific action-to-result: "by high-risk openings → 97.3% by EOM"

---

## How to Use This Guide

When reviewing draft SPX PH Update material, check against:

1. **Structure**: Does it follow the section order? Is OKR table present with correct columns?
2. **Exec Summary**: Is it numbered with page refs (2026 style)? Does the opening framing line set the posture?
3. **Numbers**: Are CPO values in `$0.XXX`? BWT in `X.XX`? Coverage in `XX.X%`?
4. **CPO section**: Does each component show sign + driver + MoM compare?
5. **Bullets**: Do they lead with metrics, not people? Include WoW/MoM? Name regions specifically?
6. **Vocabulary**: Are correct abbreviations used? Is "J&T gap" included in speed section?
7. **Era alignment**: Does the content match what a 2026 deck should look like (numbered exec, AI sections, TTS benchmark)?
