#!/usr/bin/env python3
"""Brand-token drift guard — worldenergydata#908 (wh#3401 ecosystem rollout).

Any report page that DECLARES the brand (defines --navy) must match the canonical
navy/teal token values in reports/capabilities/assets/tokens.css. The generated
capability pages already single-source those tokens; this guard also covers the
non-generated atlas/index/report pages so the identity can't drift anywhere.

Pages that do NOT declare --navy (e.g. dark marine-safety pages, other intentional
designs) are exempt. Run locally and in CI:
    python scripts/enforcement/check_brand_drift.py
Exit 0 = consistent, 1 = drift.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "reports" / "capabilities" / "assets" / "tokens.css"
REPORTS = ROOT / "reports"

# Dark-themed marketing infographics use --navy as their dark BACKGROUND, so they
# cannot adopt the light brand navy by a token swap — they need a brand-accent
# design pass (tracked in worldenergydata#922). Exempt until then.
EXEMPT_PREFIXES = ("reports/modules/marketing/",)

TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})")


def norm(hexv: str) -> str:
    h = hexv.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", h):
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def root_tokens(text: str) -> dict[str, str]:
    m = re.search(r":root\s*\{([^}]*)\}", text, re.DOTALL)
    if not m:
        return {}
    return {name: norm(val) for name, val in TOKEN_RE.findall(m.group(1))}


def find_violations(canon: dict[str, str], pages: dict[str, dict[str, str]]):
    out = []
    for label, toks in pages.items():
        if "navy" not in toks:  # not a brand page -> exempt
            continue
        for name, val in toks.items():
            if name in canon and val != canon[name]:
                out.append((label, name, val, canon[name]))
    return out


def main() -> int:
    if not TOKENS.exists():
        print(f"brand guard: {TOKENS} missing", file=sys.stderr)
        return 1
    canon = root_tokens(TOKENS.read_text(encoding="utf-8"))
    pages = {
        str(p.relative_to(ROOT)): root_tokens(p.read_text(encoding="utf-8", errors="ignore"))
        for p in sorted(REPORTS.rglob("*.html"))
        if not str(p.relative_to(ROOT)).startswith(EXEMPT_PREFIXES)
    }
    checked = [lbl for lbl, t in pages.items() if "navy" in t]
    violations = find_violations(canon, pages)
    if violations:
        print("BRAND-TOKEN DRIFT — pages that declare --navy must match "
              "reports/capabilities/assets/tokens.css:\n")
        for label, name, got, want in violations:
            print(f"  x {label}: --{name} = {got} (tokens.css: {want})")
        print("\nFix the page's :root to the canonical values, or update tokens.css "
              "if the brand deliberately changed.")
        return 1
    print(f"brand guard OK — {len(checked)} brand-declaring page(s) match "
          f"tokens.css ({len(canon)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
