#!/usr/bin/env python3
"""to_json.py — Convert neuro-taxonomy YAML to JSON."""
import json, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    print("❌ PyYAML required: pip install pyyaml")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for fname in ["regions.yaml", "cell_types.yaml", "pathologies.yaml", "cross_links.yaml"]:
    path = REPO / fname
    if not path.exists():
        continue
    with open(path) as f:
        data = yaml.safe_load(f)
    out_path = REPO / fname.replace(".yaml", ".json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ {out_path.name}")

print("Done.")
