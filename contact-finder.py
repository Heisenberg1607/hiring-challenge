"""
Contact Finder - Stage B slice
================================
Reads challenge/data/companies.csv and challenge/mocks/enrichment_responses.json.
For each company, queries the three mock providers (registry, listing, enrichment),
runs the confidence model from PLAN.md, and writes output.csv.

Confidence model (from plan, adapted to clarifications):
  Entity check  -> caps -> additives -> threshold(70)

Adaptations from clarifications:
  - Threshold: 70 (plan assumed 75)
  - Persona priority: AP manager > owner/founder > CFO > office manager
  - Suppression / opt-out check added (compliance requirement)
  - Precision over coverage confirmed: high needs_human_review rate is a good result
"""

import csv
import json
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
THRESHOLD = 70  # from clarifications (plan assumed 75, adapted)

DATA_PATH  = Path("challenge/data/companies.csv")
MOCKS_PATH = Path("challenge/mocks/enrichment_responses.json")
OUTPUT_PATH = Path("output.csv")

# Suppression list: companies that have opted out (compliance requirement from clarifications).
# In production this is loaded from a database; here it is an empty set.
SUPPRESSED = set()

# Role priority order from clarifications:
#   AP manager / accounts payable first
#   owner / founder for small businesses
#   CFO / finance lead for larger ones
#   office manager as fallback
ROLE_PRIORITY = {
    "ap manager":              4,
    "accounts payable":        4,
    "accounts payable manager": 4,
    "owner":                   3,
    "founder":                 3,
    "president":               3,
    "cfo":                     2,
    "chief financial officer": 2,
    "finance lead":            2,
    "controller":              2,
    "office manager":          1,
    "manager":                 1,
}


# ── Helpers ────────────────────────────────────────────────────────────────

def role_score(role):
    """Map a role string to its priority score (0 if unknown)."""
    if not role:
        return 0
    lower = role.lower().strip()
    for keyword, score in ROLE_PRIORITY.items():
        if keyword in lower:
            return score
    return 0


def names_agree(name_a, name_b):
    """True if both names share the same first token (first-name match)."""
    if not name_a or not name_b:
        return False
    return name_a.strip().split()[0].lower() == name_b.strip().split()[0].lower()


# ── Confidence model ────────────────────────────────────────────────────────

def compute_confidence(registry, listing, enrichment, contact_name, contact_role):
    """
    Gate + caps + additives model (from PLAN.md).

    Caps  (ceiling the score regardless of everything else):
      - No named person at all        -> cap at 45
      - Only one source has a person  -> cap at 58

    Additives (sum, then apply caps):
      - Registry name present         -> +40  (highest authority source)
      - Listing name corroborates     -> +20  (independent agreement)
      - Listing name present but different -> +5 (weak)
      - Enrichment contact present    -> provider_confidence * 0.20  (input, not truth)
      - Role match                    -> scaled by priority (max ~14)
    """
    score = 0
    sources_with_person = 0

    # Registry: highest authority
    if registry and registry.get("name"):
        score += 40
        sources_with_person += 1

    # Listing corroboration
    if listing:
        if listing.get("name"):
            if names_agree(registry.get("name") if registry else None, listing.get("name")):
                score += 20  # same person confirmed by an independent source
            else:
                score += 5   # listing has a name but it doesn't match registry
            sources_with_person += 1
        elif listing.get("phone"):
            score += 3   # phone only, no person name

    # Enrichment: treat provider_confidence as weighted input, never adopt as-is
    if enrichment:
        if enrichment.get("email") or enrichment.get("phone"):
            pconf = enrichment.get("provider_confidence", 50)
            score += int(pconf * 0.20)
            sources_with_person += 1

    # Role match additive (asymmetric: confirmed high-priority role boosts strongly)
    rs = role_score(contact_role)
    if rs > 0:
        score += int(rs * 3.5)   # max role contribution ~14 pts (AP manager = 4 * 3.5)

    # ── Apply caps ─────────────────────────────────────────────────────────
    if not contact_name:
        score = min(score, 45)          # no named person at all
    elif sources_with_person <= 1:
        score = min(score, 58)          # single-source corroboration cap

    return min(int(score), 100)


# ── Per-company pipeline ────────────────────────────────────────────────────

def process_company(company, mock_data):
    """Run the full gate -> person -> confidence pipeline for one row."""
    company_name = company["company_name"]

    # Suppression check (opt-out compliance)
    if company_name in SUPPRESSED:
        return _empty_row(company_name)

    # Entity check
    # Note: mock contract resolves entity by exact company_name key and carries
    # no address field. In production the entity gate also validates against the
    # mailing address (plan section: "anchor on name + address"). Adaptation
    # noted in ABOUT.md.
    mock = mock_data.get(company_name)
    if not mock:
        return _empty_row(company_name)  # cannot-verify

    registry   = mock.get("registry")    # None if provider returned nothing
    listing    = mock.get("listing")
    enrichment = mock.get("enrichment")

    # ── Identify best contact ───────────────────────────────────────────────
    contact_name   = None
    contact_role   = None
    contact_handle = None
    sources        = []

    # Registry: authoritative; name + role
    if registry:
        if registry.get("name"):
            contact_name = registry["name"]
            contact_role = registry.get("role")
        if registry.get("source_url"):
            sources.append(registry["source_url"])

    # Listing: corroboration; phone as fallback handle
    if listing:
        if listing.get("name") and not contact_name:
            contact_name = listing["name"]          # fallback if registry had no name
        if listing.get("phone") and not contact_handle:
            contact_handle = listing["phone"]
        if listing.get("source_url"):
            sources.append(listing["source_url"])

    # Enrichment: email preferred over phone; overrides listing phone
    if enrichment:
        if enrichment.get("email"):
            contact_handle = enrichment["email"]    # prefer direct email
        elif enrichment.get("phone") and not contact_handle:
            contact_handle = enrichment["phone"]
        if enrichment.get("source_url"):
            sources.append(enrichment["source_url"])

    # ── Score and decide ───────────────────────────────────────────────────
    confidence   = compute_confidence(registry, listing, enrichment, contact_name, contact_role)
    needs_review = confidence < THRESHOLD or not contact_handle

    return {
        "company_name":          company_name,
        "contact_name":          contact_name   or "",
        "contact_role":          contact_role   or "",
        "contact_email_or_phone": contact_handle if not needs_review else "",
        "confidence_score":      confidence,
        "source":                " | ".join(sources),
        "needs_human_review":    needs_review,
    }


def render_table(results, max_width=40):
    """Render results as an aligned ASCII table for the console (stdlib only)."""
    cols = [
        ("company_name", "Company"),
        ("contact_name", "Contact"),
        ("contact_role", "Role"),
        ("contact_email_or_phone", "Email/Phone"),
        ("confidence_score", "Conf"),
        ("needs_human_review", "Review"),
    ]

    def cell(row, key):
        val = row[key]
        if key == "needs_human_review":
            return "yes" if val else "no"
        text = str(val)
        return text if len(text) <= max_width else text[: max_width - 1] + "…"

    widths = {}
    for key, header in cols:
        body = max((len(cell(r, key)) for r in results), default=0)
        widths[key] = max(len(header), body)

    def line(char="─", left="├", mid="┼", right="┤"):
        return left + mid.join(char * (widths[k] + 2) for k, _ in cols) + right

    def fmt(values):
        return "│ " + " │ ".join(
            v.ljust(widths[k]) for (k, _), v in zip(cols, values)
        ) + " │"

    print(line("─", "┌", "┬", "┐"))
    print(fmt([h for _, h in cols]))
    print(line())
    for r in results:
        print(fmt([cell(r, k) for k, _ in cols]))
    print(line("─", "└", "┴", "┘"))


def _empty_row(company_name):
    """Cannot-verify or suppressed: return empty contact, flag for review."""
    return {
        "company_name":          company_name,
        "contact_name":          "",
        "contact_role":          "",
        "contact_email_or_phone": "",
        "confidence_score":      0,
        "source":                "",
        "needs_human_review":    True,
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    with open(DATA_PATH) as f:
        companies = list(csv.DictReader(f))

    with open(MOCKS_PATH) as f:
        mock_data = json.load(f)

    results = [process_company(c, mock_data) for c in companies]

    fields = [
        "company_name", "contact_name", "contact_role",
        "contact_email_or_phone", "confidence_score",
        "source", "needs_human_review",
    ]
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    render_table(results)

    auto   = sum(1 for r in results if not r["needs_human_review"])
    review = sum(1 for r in results if r["needs_human_review"])

    print(f"Processed : {len(results)} companies")
    print(f"Auto-accept : {auto}")
    print(f"Human review: {review}")
    print(f"Output      : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()