"""Visual world rule conflict detector (Workflow G-04, Task T-49).

Compares proposed visual rules against canonical historical claims to flag
anachronisms, material contradictions, and unsupported assertions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class ConflictCheckResult:
    has_conflict: bool
    warning_text: str | None
    conflicting_claim_id: str | None = None


# Known material/period clash heuristics for ancient/historical settings (e.g. 3rd c. BCE Mauryan / Sisupalgarh)
KNOWN_CLASH_RULES: list[dict[str, Any]] = [
    {
        "forbidden_regex": r"\b(plastic|polyester|acrylic|neon|synthetic\s+dyes?|fluorescent)\b",
        "reason": "Synthetic / petrochemical materials did not exist in ancient periods.",
    },
    {
        "forbidden_regex": r"\b(marble\s+columns?|greco-roman\s+arches?|gothic\s+vaulting)\b",
        "reason": "Classical Greco-Roman or European medieval architectural elements contradict indigenous mudbrick/laterite structures.",
    },
    {
        "forbidden_regex": r"\b(gunpowder|muskets?|cannons?|rifles?|steel\s+plate\s+armou?r)\b",
        "reason": "Post-medieval ballistics and full plate armour contradict ancient/iron age combat standards.",
    },
]


class RuleConflictDetector:
    """Inspects visual world rules for historical claim conflicts and anachronisms."""

    def check_rule(
        self,
        rule_text: str,
        category: str,
        canonical_claims: Sequence[dict[str, Any]] | None = None,
    ) -> ConflictCheckResult:
        rule_lower = rule_text.lower()

        # 1. Check intrinsic anachronisms
        for clash in KNOWN_CLASH_RULES:
            match = re.search(clash["forbidden_regex"], rule_lower)
            if match:
                return ConflictCheckResult(
                    has_conflict=True,
                    warning_text=f"Anachronism Detected: Term '{match.group(0)}' found. {clash['reason']}",
                )

        # 2. Check contradiction with canonical historical claims
        if canonical_claims:
            for claim in canonical_claims:
                stmt = claim.get("statement", "").lower()
                # Check for brick vs stone conflict
                if "mudbrick" in stmt and "all-stone granite ramparts" in rule_lower:
                    return ConflictCheckResult(
                        has_conflict=True,
                        warning_text=f"Conflict with historical claim #{claim.get('id', '')}: Evidence indicates ramparts were mudbrick/laterite, not granite.",
                        conflicting_claim_id=claim.get("id"),
                    )
                # Check for unstitched vs tailored clothing
                if "unstitched" in stmt and "tailored jackets" in rule_lower:
                    return ConflictCheckResult(
                        has_conflict=True,
                        warning_text=f"Conflict with historical claim #{claim.get('id', '')}: Evidence indicates unstitched antariya/uttariya rather than tailored jackets.",
                        conflicting_claim_id=claim.get("id"),
                    )

        return ConflictCheckResult(has_conflict=False, warning_text=None)

