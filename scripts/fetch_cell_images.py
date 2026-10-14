#!/usr/bin/env python3
"""
fetch_cell_images.py — Query NeuroMorpho.org and other image repositories
for example cell images matching our taxonomy cell types.

Output: YAML file with curated image references for each cell type.

Sources:
  - NeuroMorpho.org: ~15,676 human neurons with PNG reconstructions
  - Allen Cell Types Database: human cortical cell morphologies
  - Human Protein Atlas: IHC protein expression in brain tissues
  - Cell Image Library (CIL): curated cell images

Usage:
  python3 scripts/fetch_cell_images.py [--update]

Output:
  data/cell_image_references.yaml  — curated image references
"""
import sys, json, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUTPUT = REPO / "data" / "cell_image_references.yaml"

# NeuroMorpho API base
NM_API = "https://neuromorpho.org/api/neuron/select"

# Mapping from our cell type IDs to NeuroMorpho query parameters.
# The API uses Solr: `q` = primary field (e.g. species:human),
# `fq` = filter queries (remaining params).  We query species first,
# then filter on brain_region, cell_type etc.
QUERY_MAP = {
    "layer_ii_iii_pyramidal": {
        "params": {"species": "human", "cell_type": "pyramidal"},
        "max": 10,
        "note": "Human neocortical pyramidal neurons (layers II–III)",
        "layer_filter": "layer 2"
    },
    "layer_v_pyramidal": {
        "params": {"species": "human", "cell_type": "pyramidal"},
        "max": 10,
        "note": "Human neocortical pyramidal neurons (layers V–VI)",
        "layer_filter": "layer 5"
    },
    "betz_cells": {
        "params": {"species": "human", "cell_type": "pyramidal", "brain_region": "motor"},
        "max": 5,
        "note": "Primary motor cortex pyramidal (includes Betz cells)"
    },
    "entorhinal_stellate_cells": {
        "params": {"species": "human", "cell_type": "stellate"},
        "max": 5,
        "note": "Human stellate neurons (entorhinal-like)"
    },
    "basket_cells_pv": {
        "params": {"species": "human", "cell_type": "interneuron"},
        "max": 10,
        "note": "Human aspiry interneurons (includes PV+ basket cells)"
    },
    "somatostatin_positive_interneurons": {
        "params": {"species": "human", "cell_type": "interneuron"},
        "max": 5,
        "note": "Human aspiry interneurons (includes SST+ Martinotti)"
    },
    "dentate_granule_cells": {
        "params": {"species": "human", "brain_region": "hippocampus"},
        "max": 5,
        "note": "Human hippocampal neurons"
    },
    "cerebellar_granule_cells": {
        "params": {"species": "mouse", "brain_region": "cerebellum", "cell_type": "granule"},
        "max": 5,
        "note": "Mouse cerebellar granule cells (few human cerebellar in NM)"
    },
    "purkinje_cells": {
        "params": {"species": "mouse", "brain_region": "cerebellum", "cell_type": "Purkinje"},
        "max": 5,
        "note": "Mouse Purkinje cells"
    },
    "striatal_medium_spiny_neurons": {
        "params": {"species": "rat", "brain_region": "striatum", "cell_type": "medium_spiny"},
        "max": 5,
        "note": "Rat striatal medium spiny neurons"
    },
    "snc_dopaminergic_neurons": {
        "params": {"species": "mouse", "brain_region": "substantia_nigra"},
        "max": 5,
        "note": "Mouse substantia nigra neurons"
    },
    "locus_coeruleus_noradrenergic": {
        "params": {"species": "rat", "brain_region": "locus_coeruleus"},
        "max": 5,
        "note": "Rat locus coeruleus neurons"
    },
    "protoplasmic_astrocytes": {
        "params": {"species": "mouse", "cell_type": "astrocyte"},
        "max": 5,
        "note": "Mouse astrocytes (NeuroMorpho has few human glia)"
    },
    "oligodendrocytes": {
        "params": {"species": "rat", "cell_type": "oligodendrocyte"},
        "max": 5,
        "note": "Rat oligodendrocytes"
    },
}


def query_neuromorpho(params, rows=5, retries=3):
    """Query the NeuroMorpho Solr API.

    Uses first param as `q` and remaining as `fq` filter queries.
    Returns (neurons_list, total_count).
    """
    items = list(params.items())
    if not items:
        return [], 0

    first_key, first_val = items[0]
    q = f"{first_key}:{first_val}"

    fq_parts = []
    for k, v in items[1:]:
        fq_parts.append(f"{k}:{v}")

    url = f"{NM_API}?q={quote(q)}&rows={rows}"
    for fq in fq_parts:
        url += f"&fq={quote(fq)}"

    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                # Check for error status
                if data.get("status") and data["status"] != 200:
                    raise URLError(f"API returned status {data['status']}: {data.get('message', '')}")
                neurons = data.get("_embedded", {}).get("neuronResources", [])
                total = data.get("page", {}).get("totalElements", len(neurons))
                return neurons, total
        except (URLError, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"    Warning: NeuroMorpho query '{url[:120]}...' error: {e}")
                return [], 0


def fetch_all_references():
    """Fetch image references for each mapped cell type."""
    references = {}

    for ct_id, spec in QUERY_MAP.items():
        print(f"  Querying {ct_id}...")
        neurons, total = query_neuromorpho(spec["params"], rows=spec["max"])

        # Apply layer filter if specified (client-side)
        layer_filter = spec.get("layer_filter", "")
        if layer_filter:
            neurons = [
                n for n in neurons
                if any(layer_filter in r.lower() for r in n.get("brain_region", []))
            ]

        images = []
        for n in neurons:
            region = n.get("brain_region", [])
            ct_labels = n.get("cell_type", [])

            images.append({
                "url": n.get("png_url", ""),
                "caption": (
                    f"{n.get('neuron_name', '')} — "
                    f"{' / '.join(ct_labels) if isinstance(ct_labels, list) else ct_labels} "
                    f"in {' / '.join(region) if isinstance(region, list) else region}"
                ),
                "source": n.get("archive", "NeuroMorpho"),
                "sex": n.get("gender", ""),
                "age": n.get("min_age", ""),
                "cell_type_labels": ct_labels,
                "region": region,
                "reference_doi": n.get("reference_doi", []),
                "nm_id": n.get("neuron_id"),
            })

        references[ct_id] = {
            "query_params": spec["params"],
            "total_available": total,
            "images_returned": len(images),
            "note": spec["note"],
            "images": images[:spec["max"]],
        }

    return references


def build_curated_references():
    """Return static curated image references from known atlases,
    plus links to relevant external databases per cell type."""
    return {
        "_sources": {
            "neuromorpho": {
                "url": "https://neuromorpho.org",
                "total_human_neurons": 15676,
                "description": "Database of 3D neuronal reconstructions with PNG images"
            },
            "human_protein_atlas": {
                "url": "https://www.proteinatlas.org",
                "brain_section_url": "https://www.proteinatlas.org/humanproteome/brain",
                "description": "IHC, IF, and RNA-seq data for protein expression in human brain regions"
            },
            "allen_cell_types": {
                "url": "https://celltypes.brain-map.org",
                "description": "Electrophysiological and morphological characterization of human cortical neurons"
            },
            "cell_image_library": {
                "url": "https://www.cellimagelibrary.org",
                "description": "Curated cell images from ASCB"
            },
            "brain_image_library": {
                "url": "https://www.brainimagelibrary.org",
                "description": "Curated neuropathology and neuroanatomy images"
            },
        },
        "_query_instructions": {
            "neuromorpho_query_example": {
                "url_template": "https://neuromorpho.org/api/neuron/select?q=species:{species}&fq=cell_type:{cell_type}&rows=10",
                "description": "Substitute species and cell_type values"
            },
            "protein_atlas_query_example": {
                "url_template": "https://www.proteinatlas.org/search/{gene}?format=json",
                "description": "Substitute a gene symbol (e.g. GFAP, SLC17A7, TH)"
            },
        }
    }


def main():
    print("=" * 60)
    print("Neuro-Taxonomy: Cell Image Reference Fetcher")
    print("=" * 60)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    print("\nFetching from NeuroMorpho...")
    auto_refs = fetch_all_references()

    print("\nAdding curated external references...")
    curated = build_curated_references()

    # Merge: auto_refs first, then curated sources
    merged = dict(auto_refs)
    merged.update(curated)

    with open(OUTPUT, "w") as f:
        yaml.dump(merged, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    total_images = sum(
        v.get("images_returned", 0) for k, v in merged.items() if not k.startswith("_")
    )
    print(f"\nWritten to {OUTPUT}")
    print(f"   Cell types auto-queried: {len(auto_refs)}")
    print(f"   Total images fetched: {total_images}")
    print(f"   External sources documented: {len(curated.get('_sources', {}))}")

    # Show some sample image URLs
    print("\nSample images:")
    shown = 0
    for ct_id, ref in sorted(merged.items()):
        if ct_id.startswith("_"):
            continue
        imgs = ref.get("images", [])
        for img in imgs[:2]:
            if shown < 6:
                print(f"  [{ct_id}] {img['url']}")
                shown += 1


if __name__ == "__main__":
    main()
