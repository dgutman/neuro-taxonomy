# Neuro-Taxonomy

A structured taxonomy of human brain regions, cell types, and neuropathological features — designed for computational neuropathology workflows.

## Scope

- **Species:** *Homo sapiens* only
- **Domains:**
  - **Regions** — hierarchical neuroanatomy (lobes → gyri → cortical layers → subnuclei)
  - **Cell Types** — neurons (by neurotransmitter, morphology, electrophysiology), glia
  - **Pathologies** — proteinopathies, cellular phenotypes, staging schemes
- **Diseases:** All neurodegenerative disorders (AD, LBD, FTLD-TDP, FTLD-tau, PSP, CBD, MSA, ALS, HD, prion)
- **Cross-links:** Which cell types in which regions are vulnerable to which pathologies

## Format

YAML (git-friendly, machine-parseable, convertible to JSON/OWL/SQL).

## Sources

- **BDSA Schema** (`schema.bdsa.io`) — region definitions used in the BDSA platform
- **Allen Human Brain Atlas** — Fine-grained structural parcellation
- **Cell Ontology (CL)** — Standardized cell type identifiers
- **MONDO / PATO** — Disease and phenotype ontologies
- **Braak staging** (NFT, Aβ, α-synuclein)
- **Thal phases** (Aβ deposition)
- **NACC / ADNC criteria**

## Structure

```
neuro-taxonomy/
├── README.md                 ← this file
├── regions.yaml              ← hierarchical brain regions
├── cell_types.yaml           ← neuronal and glial cell types
├── pathologies.yaml          ← protein inclusions, cellular phenotypes, staging
├── cross_links.yaml          ← region ↔ cell type ↔ pathology associations
└── scripts/                  ← optional validation / conversion tools
```

## Conventions

- IDs are lowercase with underscores (e.g., `entorhinal_cortex`, `dopaminergic_neuron`, `neurofibrillary_tangle`).
- BDSA region keys (e.g., `Frontal`, `Hippocampus`) are referenced as `bdsa_region: Frontal`.
- Each entry has `id`, `label`, `description`, `xrefs` (cross-references to external ontologies), and optional `children` / `properties`.
- `status` tracks completion: `draft` | `stable` | `needs_review`.

## Usage

```bash
# Parse and validate
python3 scripts/validate.py

# Convert to JSON
python3 scripts/to_json.py

# Visualize hierarchy
python3 scripts/diagram.py
```

## See Also

- [BDSA Protocols Platform](https://schema.bdsa.io)
- [Allen Brain Atlas API](https://brain-map.org/api/index.html)
- [Cell Ontology](https://obophenotype.github.io/cell-ontology/)
