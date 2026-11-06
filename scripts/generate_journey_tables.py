"""Regenerate the journey tables in docs/product/JOURNEY_MANIFEST.md (section 8).

Source: packages/domain/journey_manifest.yaml. Run from the repo root:

    python scripts/generate_journey_tables.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packages/domain/journey_manifest.yaml"
SPEC = ROOT / "docs/product/JOURNEY_MANIFEST.md"
BEGIN = "<!-- BEGIN GENERATED: journey tables -->"
END = "<!-- END GENERATED: journey tables -->"
RELEASE_LABEL = {"v1": "V1", "v1_v2": "V1→V2", "v2": "V2"}


def _applies(applicability: dict) -> str:
    if applicability["modes"] == "all":
        return "all"
    text = ", ".join(applicability["modes"])
    for condition in applicability.get("unless_any", []):
        ((name, values),) = condition.items()
        text += f"; unless {name}: {', '.join(values)}"
    return text


def _check(check: dict) -> str:
    return "M" if check["kind"] == "manual_with_evidence" else f"S `{check['key']}`"


def render(manifest: dict) -> str:
    lines: list[str] = []
    for section in manifest["sections"]:
        lines += [
            f"### {section['id'][4:]} {section['title']} — {section['release_label']}",
            "",
            "| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for g in section["groups"]:
            caps = g["act_capability"]
            if g["approval_capability"]:
                caps += f" / {g['approval_capability']}"
            lines.append(
                f"| `{g['id']}` | {g['title']} | {RELEASE_LABEL[g['release']]} "
                f"| {g['na'].replace('_', ' ')} | {_applies(g['applicability'])} | {caps} "
                f"| {_check(g['completion_check'])} | {', '.join(g['studio_tools'])} "
                f"| {', '.join(g['requirements'])} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    spec = SPEC.read_text(encoding="utf-8")
    head, rest = spec.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    SPEC.write_text(f"{head}{BEGIN}\n\n{render(manifest)}\n{END}{tail}", encoding="utf-8")
    groups = sum(len(s["groups"]) for s in manifest["sections"])
    print(f"{groups} groups written to {SPEC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
