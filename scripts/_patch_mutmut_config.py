"""Temporarily patch pyproject.toml for incremental mutation testing.

PATHS must be directories (not individual files) so mutmut copies the full
directory tree needed for imports. Example: src/srag/data/analytics
"""

import os
import tomllib
from pathlib import Path

import tomli_w

d = tomllib.loads(Path("pyproject.toml").read_text())
mut = d.setdefault("tool", {}).setdefault("mutmut", {})

paths = [p.strip() for p in os.environ["PATHS"].split() if p.strip()]
mut["paths_to_mutate"] = paths

# Ensure src/srag is available for imports when restricting paths
has_src = any(p.startswith("src/srag") or p.startswith("src") for p in paths)
if has_src and not any(p in ("src", "src/srag") for p in paths):
    existing = mut.get("also_copy", [])
    if "src/srag" not in existing:
        al = [*list(existing), "src/srag"]
        mut["also_copy"] = al

t = os.environ.get("TESTS", "").strip()
if t:
    existing = mut.get("pytest_add_cli_args_test_selection", [])
    if t not in existing:
        mut["pytest_add_cli_args_test_selection"] = [*existing, *t.split()]
elif "pytest_add_cli_args_test_selection" in mut:
    del mut["pytest_add_cli_args_test_selection"]

mut["backup"] = False
Path("pyproject.toml").write_text(tomli_w.dumps(d))
print(f"patched: paths={mut['paths_to_mutate']} tests={t or '(all)'}")
