# Contact Finder — Respaid / AgentCollect Hiring Challenge

Finds the right decision-maker at each small business starting from only a **company name**
and **mailing address**, returning a confidence-scored contact or an honest
`needs_human_review` flag — never a fabricated guess.

---

## Requirements

- **Python 3.8+**
- **No external dependencies** — standard library only (`csv`, `json`, `pathlib`, `unittest`)

No `pip install` needed.

---

## How to run

Run from the repository root (so the relative paths to the fixtures resolve):

```bash
python contact_finder.py
```

This reads:
- `challenge/data/companies.csv` — the input companies
- `challenge/mocks/enrichment_responses.json` — the mock provider responses

…and writes `output.csv`, then prints a summary table to the console.

**Run the tests:**

```bash
python -m unittest test_contact_finder -v
```

8 unit tests covering the confidence caps, the cannot-verify path, suppression, and the auto-accept case.

---

## What it does

For each company row:

1. Queries three independent mock providers (`registry`, `listing`, `enrichment`)
2. Runs an **entity gate** — confirms the right business before scoring any contact
3. Identifies the best decision-maker using the persona priority (see adaptations below)
4. Computes a **confidence score (0–100)** via a gate + caps + additives model
5. Returns a verified contact if confidence ≥ 70, otherwise flags `needs_human_review` with an empty contact

It never emits a contact it can't attribute to a source, and never fabricates one.

---

## Output

`output.csv` — one row per input company:

| Column | Description |
|---|---|
| `company_name` | Input company |
| `contact_name` | Decision-maker name (empty if unverifiable) |
| `contact_role` | Role / title |
| `contact_email_or_phone` | Reachable handle (empty if flagged for review) |
| `confidence_score` | 0–100 |
| `source` | `mock://` provenance URL(s) for every emitted value |
| `needs_human_review` | `true` when confidence < 70 or no reachable handle |

**Result on the mock set:** 4 auto-accept, 26 needs-human-review across 30 companies. The high
review rate is intentional — per the clarifications, a high `needs_human_review` rate on
genuinely hard rows is a good result, not a failure.

---

## Adaptations after reading CLARIFICATIONS.md

`PLAN.md` was committed **first**, before reading the clarifications, and is left frozen as the
Stage A artifact. The clarifications were then read, and the following changes were made **in the
build** (not by editing the plan). This is the plan → build adaptation trail:

| Topic | My plan's default | Clarification said | What changed in the build |
|---|---|---|---|
| **Confidence threshold** | Assumed **75** | Use **70** (`< 70` → empty contact + `needs_human_review = true`) | Set `THRESHOLD = 70` |
| **Persona / target contact** | Size-conditional: owner for small shops, AP/Finance for larger | Explicit priority: **AP manager → owner/founder → CFO/finance → office manager** | `ROLE_PRIORITY` encodes this exact order and drives the role-match component of the score |
| **Suppression / opt-out** | Not mentioned in the plan | Must support opt-out / suppression and record provenance | Added a `SUPPRESSED` check before enrichment; suppressed companies return an empty review row |
| **Success metric** | Assumed precision over coverage | Confirmed: **precision over recall**; a confident wrong contact is worse than a miss | No change — the aggressive caps and "honest null" behavior were already the right call |
| **Allowed sources** | Business-level public / official only | Mock-only for this exercise; US B2B; business contact info only, never personal/home data | Confirmed — no scraping, business-level only, `source_url` provenance carried on every value |

The most important non-change is the success metric: the clarifications confirmed the
precision-first bet the whole design was built on, so the caps and the high review rate stayed.

---

## Confidence model

A **gate + caps + additives** structure — deliberately not a flat sum:

- **Entity gate** runs first on company name + address. A wrong company never accumulates score, so a strong contact for the wrong business can't slip through.
- **Caps** ceiling the score regardless of other signals: a single source caps at 58; a contact with no named person caps at 45. This is why a lone high-`provider_confidence` enrichment guess can never look confident.
- **Additives** (source authority, corroboration depth, role match) only fire after the gate passes and no cap is triggered.

`provider_confidence` from the enrichment provider is treated as **one weighted input, not the answer**.
Full reasoning is in `PLAN.md`.

---

## Project structure

```
PLAN.md                                   Stage A plan (committed first, before clarifications)
ABOUT.md                                  Background, AI-tool usage, adaptation notes
README.md                                 This file
contact_finder.py                         The slice
test_contact_finder.py                    8 unit tests
output.csv                                Results against the mock dataset
challenge/data/companies.csv              Input: 30 businesses (name + address only)
challenge/mocks/enrichment_responses.json Mock provider responses
```
