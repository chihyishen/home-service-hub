#!/usr/bin/env python3
"""Guard Alembic migration integrity for every Python service.

Catches the two failure modes that have bitten this repo when PRs are
merged/reordered independently:

1. **Duplicate revision IDs** — two migration files declaring the same
   ``revision = "..."``. Alembic only warns about this and silently keeps
   one, so the other migration's DDL never runs (and ``alembic upgrade``
   later aborts with a "revision present more than once" overlap error).

2. **Multiple heads** — divergent migration branches that were never
   merged, so ``alembic upgrade head`` is ambiguous.

Pure file/graph inspection: no database connection and no app import, so
it runs fast in CI with only ``alembic`` installed.

Exit code 0 = all good; 1 = at least one service has a problem.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REVISION_RE = re.compile(r"""^revision\s*(?::[^=]+)?=\s*["']([^"']+)["']""", re.M)


def check_service(alembic_ini: Path) -> list[str]:
    """Return a list of problem strings for one service (empty == healthy)."""
    service_dir = alembic_ini.parent
    versions_dir = service_dir / "alembic" / "versions"
    problems: list[str] = []

    # 1. Duplicate revision IDs (file-based — alembic only warns on these).
    seen: dict[str, list[str]] = {}
    for path in sorted(versions_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        match = REVISION_RE.search(path.read_text(encoding="utf-8"))
        if match:
            seen.setdefault(match.group(1), []).append(path.name)
    for revision, files in sorted(seen.items()):
        if len(files) > 1:
            problems.append(
                f"duplicate revision id {revision!r} in: {', '.join(files)}"
            )

    # 2. Exactly one head (graph-based via alembic, no DB needed).
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    prev_cwd = os.getcwd()
    try:
        os.chdir(service_dir)
        script = ScriptDirectory.from_config(Config("alembic.ini"))
        heads = script.get_heads()
    finally:
        os.chdir(prev_cwd)
    if len(heads) != 1:
        problems.append(f"expected exactly 1 head, found {len(heads)}: {list(heads)}")

    return problems


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    inis = sorted(repo_root.glob("services/*/alembic.ini"))
    if not inis:
        print("No services/*/alembic.ini found", file=sys.stderr)
        return 1

    failed = False
    for ini in inis:
        service = ini.parent.name
        problems = check_service(ini)
        if problems:
            failed = True
            print(f"✗ {service}")
            for problem in problems:
                print(f"    {problem}")
        else:
            print(f"✓ {service}: single head, no duplicate revisions")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
