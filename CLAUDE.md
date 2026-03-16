# SPX PH Update — Style Review Assistant

## What this repo does

This repo connects Claude to Google Drive via a relay, enabling Claude to read Drive files on demand. It is set up specifically to help review SPX PH Update slide material against a synthesized style guide.

## Style Guide

The style guide is stored in two places:
1. **Local file**: `spx-style-guide.md` in this repo (read it with the Read tool)
2. **Google Drive doc**: Ask the owner for the Drive doc ID if you need to share it without this repo

## How to review SPX PH Update material

### Quick start (no Drive access needed)

1. Read the style guide: `spx-style-guide.md`
2. The person pastes or shares their draft material
3. Review against the guide and provide feedback in this format:

---

**Structural gaps**: [What sections are missing or out of order]

**Exec Summary**: [Is it numbered with page refs? Posture framing clear?]

**Numbers & formatting**: [CPO format, BWT decimals, coverage %, etc.]

**Bullet rewrites**: [Show 2–3 specific before/after rewrites]

**Tone / vocabulary**: [Wrong terms, passive voice, missing WoW/MoM data]

---

### With Drive access (relay configured)

If the user has configured the relay (see README.md), you can also:
- Read the latest SPX PH Update deck directly: `?action=search&query=SPX PH Update&secret=SECRET`
- Read a specific deck by file ID: `?action=read&id=FILE_ID&secret=SECRET`

### Loading the style guide from Drive (if stored there)

If the owner has uploaded the style guide to Google Drive:
```
Load the SPX style guide from Drive (ID: [ASK OWNER FOR ID]) and then review this material: [paste material]
```

## Relay API (quick reference)

```
Base URL: [set in .env as RELAY_URL]

List recent files:     GET ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
Search file content:   GET ?action=search&query=TERMS&secret=SECRET[&max=N]
Read a file:           GET ?action=read&id=FILE_ID&secret=SECRET
```

## Key context about SPX PH Updates

- **Audience**: Senior leadership (PH GM, regional ops heads)
- **Cadence**: ~weekly or bi-weekly
- **Era**: Current standard is 2026 format (numbered exec summary with page refs, AI/tech sections, FinOps)
- **Competitor benchmark**: J&T Express is the primary competitor; TTS used for mystery shopping speed benchmarks
- **Geography**: NCR/GMA, Luzon (NOL/SOL), Visayas (VIS), Mindanao (MIN) — always report regional splits
- **Currency**: Always USD ($) unless explicitly Philippine Peso (₱)

## What good feedback looks like

When reviewing material, always:
1. Show a **specific rewrite** for the weakest 2–3 bullets (before → after)
2. Reference the style guide section (e.g., "Per Section 12: bullets should lead with the metric")
3. Flag **missing data** (e.g., "Speed section is missing J&T BWT gap comparison")
4. Note **era alignment** — does the draft look like a 2026 deck or an older format?

## What not to do

- Don't soften the critique — this is exec-level material that needs to be precise
- Don't rewrite content you don't have data for — flag where data is needed
- Don't rephrase correct bullets just for variety
