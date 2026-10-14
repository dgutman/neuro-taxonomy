#!/usr/bin/env python3
"""
neuro-taxonomy web server.
Loads all YAML data and serves a browsable taxonomy dashboard.

Usage:
  cd web && python3 app.py
  Open http://localhost:5001
"""
import sys, os, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Ensure repo root is importable
sys.path.insert(0, str(REPO))

try:
    import yaml
except ImportError:
    print("pip install pyyaml flask flask-cors")
    sys.exit(1)

# ── Load all taxonomy data ──────────────────────────────────────────────

def load_yaml(name):
    path = REPO / name
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}

DATA = {}
for f in [
    "regions.yaml",
    "regions_mouse.yaml",
    "cell_types.yaml",
    "cell_type_profiles.yaml",
    "cell_region_distribution.yaml",
    "pathologies.yaml",
    "cross_links.yaml",
]:
    DATA[f.replace(".yaml", "")] = load_yaml(f)

# Try to load image references (may not exist)
img_refs = load_yaml("data/cell_image_references.yaml")
if img_refs:
    DATA["cell_image_references"] = img_refs

# Convert to JSON-serializable
def _to_json(obj):
    return json.loads(json.dumps(obj, default=str))

for k, v in DATA.items():
    DATA[k] = _to_json(v)

# ── Flask app ────────────────────────────────────────────────────────────

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ── API endpoints ───────────────────────────────────────────────────────

@app.route("/api/<dataset>")
def api_dataset(dataset):
    """Return a full dataset: regions, cell_types, pathologies, etc."""
    key = dataset.replace(".yaml", "").replace("/", "_")
    if key in DATA:
        return jsonify(DATA[key])
    return jsonify({"error": "not found"}), 404

@app.route("/api/search")
def api_search():
    """Search across all taxonomy data."""
    q = request.args.get("q", "").lower().strip()
    if not q:
        return jsonify([])

    results = []

    def search_in(item, path="", depth=0, max_depth=10):
        if depth > max_depth:
            return
        if isinstance(item, dict):
            # Check label, id, name, description
            label = str(item.get("label", item.get("id", item.get("name", "")))).lower()
            desc = str(item.get("description", "")).lower()
            if q in label or q in desc:
                results.append({
                    "label": item.get("label", item.get("id", item.get("name", "?"))),
                    "id": item.get("id", ""),
                    "type": path.split(".")[0] if "." in path else path,
                    "description": str(item.get("description", ""))[:200],
                })
            for k, v in item.items():
                search_in(v, f"{path}.{k}", depth + 1, max_depth)
        elif isinstance(item, list):
            for i, v in enumerate(item):
                search_in(v, f"{path}[{i}]", depth + 1, max_depth)

    for dataset_name, dataset in DATA.items():
        search_in(dataset, dataset_name)

    # Deduplicate by id, keep first
    seen = set()
    deduped = []
    for r in results:
        uid = f"{r['type']}:{r['id']}"
        if uid not in seen:
            seen.add(uid)
            deduped.append(r)

    return jsonify(deduped[:50])

@app.route("/api/stats")
def api_stats():
    """Return summary statistics."""
    def count_ids(data, key):
        items = data.get(key, [])
        return _count_recursive(items)

    def _count_recursive(items):
        total = 0
        if isinstance(items, dict):
            if "id" in items:
                total += 1
            for v in items.values():
                total += _count_recursive(v)
        elif isinstance(items, list):
            for item in items:
                total += _count_recursive(item)
        return total

    return jsonify({
        "regions": _count_recursive(DATA.get("regions", {}).get("regions", [])),
        "mouse_regions": _count_recursive(DATA.get("regions_mouse", {}).get("regions_mouse", [])),
        "cell_types": _count_recursive(DATA.get("cell_types", {}).get("cell_types", [])),
        "pathologies": _count_recursive(DATA.get("pathologies", {}).get("pathologies", [])),
        "cross_links": len(DATA.get("cross_links", {}).get("cross_links", [])),
        "cell_region_mappings": len(DATA.get("cell_region_distribution", {}).get("cell_region_distribution", [])),
        "images": len(DATA.get("cell_image_references", {})) - 1,  # exclude _sources
    })

# ── Serve the SPA ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(HERE / "static", path)

# ── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Neuro-Taxonomy Dashboard")
    print("=" * 60)
    print(f"Loaded datasets: {list(DATA.keys())}")
    print(f"Open http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
