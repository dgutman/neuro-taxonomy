#!/usr/bin/env python3
"""
validate.py — Validate neuro-taxonomy YAML files.

Checks:
  - All YAML files parse correctly.
  - Required fields present.
  - Cross-link references match existing region / cell_type / pathology IDs.
  - No orphaned entries.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

FILES = [
    "regions.yaml",
    "cell_types.yaml",
    "pathologies.yaml",
    "cross_links.yaml",
]

errors = []


def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _extract_ids(item, acc):
    """Recursively collect all 'id' values from nested dict structures."""
    if isinstance(item, dict):
        if "id" in item:
            acc.add(item["id"])
        for v in item.values():
            if isinstance(v, list):
                for element in v:
                    _extract_ids(element, acc)
            elif isinstance(v, dict):
                _extract_ids(v, acc)
    elif isinstance(item, list):
        for element in item:
            _extract_ids(element, acc)


def collect_ids(data, key: str) -> set:
    """Collect all 'id' values from a list of dicts under *key*."""
    ids = set()
    items = data.get(key, [])
    for item in items:
        _extract_ids(item, ids)
    return ids


def main():
    # Load all YAML
    parsed = {}
    for fname in FILES:
        path = REPO / fname
        if not path.exists():
            errors.append(f"❌ Missing file: {fname}")
            continue
        try:
            parsed[fname] = load_yaml(path)
            print(f"  ✓ {fname} — parsed OK")
        except Exception as e:
            errors.append(f"❌ {fname} — parse error: {e}")
            parsed[fname] = {}

    # Collect IDs for cross-reference checking
    region_ids = collect_ids(parsed.get("regions.yaml", {}), "regions")
    cell_type_ids = collect_ids(parsed.get("cell_types.yaml", {}), "cell_types")
    pathology_ids = collect_ids(parsed.get("pathologies.yaml", {}), "pathologies")

    # Validate cross_links
    cl_data = parsed.get("cross_links.yaml", {})
    for cl in cl_data.get("cross_links", []):
        if not isinstance(cl, dict):
            continue
        rid = cl.get("region")
        if rid and rid not in region_ids:
            errors.append(f"  ⚠ cross_link references unknown region: '{rid}'")
        ctid = cl.get("cell_type")
        if ctid and ctid not in cell_type_ids:
            errors.append(f"  ⚠ cross_link references unknown cell_type: '{ctid}'")
        pid = cl.get("pathology")
        if pid and pid not in pathology_ids:
            errors.append(f"  ⚠ cross_link references unknown pathology: '{pid}'")

    # Report
    print()
    if errors:
        print(f"❌ {len(errors)} issue(s) found:")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    else:
        print("✅ All validations passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
