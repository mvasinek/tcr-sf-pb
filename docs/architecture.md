# Architecture

This document describes the architecture of **tcr-sf-pb** (package name: `tcr-bcr-tools`).

## Design principles

- **Specification Driven Development** — each feature has a spec, version, commit, and git tag.
- **Separation of concerns** — adapters, core library, pipeline, and GUI are distinct layers.
- **Reproducibility** — one analysis = one project with explicit inputs, outputs, and configuration.
- **Extensibility** — new input formats and analysis modules plug in without rewriting existing code.

## Layer overview

```
┌─────────────────────────────────────────────────────────────┐
│              Local Streamlit GUI                            │
│         localhost:8501 · orchestration only                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Workspace / Project / Dataset                  │
│         manifests · settings · artifact directories         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Pipeline / CLI                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Analysis modules                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Core library                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Adapters                                       │
└───────────────────────────────────────────────────────────────┘
```

## Workspace

A **workspace** is the top-level directory for all local work. Implemented in `src/tcr_bcr_tools/project/workspace.py`.

```
workspace/
    settings.yaml
    datasets/
    projects/
    cache/
    logs/
```

`Workspace` API:

- `load()` / `save()` — workspace settings
- `list_projects()` / `list_datasets()`
- `create_project()` / `create_dataset()`
- `open_project()` / `open_dataset()`

## Projects

A **project** is one analysis. It references shared datasets but never stores a copy of raw data.

```
projects/JIA_Pilot/
    project.yaml
    outputs/
    figures/
    logs/
    cache/
```

`Project` API:

- `load()` / `save()`
- `set_status()` / `get_status()`
- `add_output()` / `add_figure()` / `add_log()`

Example `project.yaml`:

```yaml
project:
  name: JIA Pilot
  description: Pilot analysis of GSE160097
  created: 2026-06-16
  modified: 2026-06-16
tool:
  version: 0.5.0
datasets:
  - GSE160097
adapter: tenx
analysis: detection
status:
  extract_annotations: done
  paired_detection: done
  roc_auc: pending
```

## Datasets

A **dataset** is a shared study (e.g. GSE160097). Multiple projects may reference the same dataset.

```
datasets/GSE160097/
    dataset.yaml
    raw/
    intermediate/
```

`Dataset` API:

- `load()` / `save()`
- `validate()`
- `adapter()` / `get_adapter()`
- `validate_with_adapter()` / `normalize_with_adapter()`
- `has_unified_annotations()`

Example `dataset.yaml`:

```yaml
dataset:
  id: GSE160097
  title: GSE160097
  source: GEO
  adapter: tenx
  created: 2026-06-16
files:
  raw: raw/
  intermediate: intermediate/
```

## Adapters

Adapters convert external formats into the unified annotation schema. Analysis modules must not read raw vendor files directly.

```
Raw data → Adapter → Unified schema → Pipeline → Results
```

```
src/tcr_bcr_tools/adapters/
    base.py
    registry.py
    schema.py
    validation.py
    run_adapter.py
    tenx/
    bdrhapsody/
    airr/
    custom/
```

`BaseAdapter` methods:

- `validate_input(dataset_path)` — check raw inputs
- `extract_metadata(file_path)` — parse per-file metadata
- `normalize(dataset_path, output_path)` — write `unified_annotations.csv`
- `get_output_schema()` — required unified columns

`Adapter` registry:

- `register_adapter()` / `get_adapter()` / `list_adapters()`

Dataset integration (`Dataset` API):

- `get_adapter()` — resolve adapter from `dataset.yaml`
- `validate_with_adapter()` — validate raw files
- `normalize_with_adapter()` — write `intermediate/unified_annotations.csv` and `adapter_report.yaml`

## Unified annotation schema

All adapter output uses `REQUIRED_COLUMNS` in `adapters/schema.py` (written to `datasets/<id>/intermediate/unified_annotations.csv`):

| Column | Description |
| --- | --- |
| `dataset_id` | Source dataset identifier |
| `source_file` | Original input filename |
| `sample_id` | Sample / GSM id |
| `patient` | Patient id |
| `sample_group` | Sample group (e.g. PM1) |
| `compartment` | blood, SF, etc. |
| `cell_type` | CD4, CD8, Treg, … |
| `barcode` | Cell barcode |
| `contig_id` | Contig identifier |
| `chain` | TRA, TRB, … |
| `v_gene`, `d_gene`, `j_gene`, `c_gene` | Gene assignments |
| `cdr3`, `cdr3_nt` | CDR3 sequence |
| `productive`, `full_length`, `high_confidence`, `is_cell` | QC flags |
| `umis`, `reads` | Expression support |
| `raw_clonotype_id`, `raw_consensus_id` | Platform clone ids |
| `adapter_name`, `adapter_version` | Provenance |

Optional columns: `platform`, `study_id`, `disease`, `tissue`, `timepoint`, `condition`, `batch`, `library_id`.

Multi-dataset analyses combine standardized tables after adapter normalization:

```
GSE160097 + future RA + future JIA
        ↓
joint standardized clone table
        ↓
common analysis pipeline
```

Legacy `UNIFIED_TABLE_COLUMNS` in `project/internal_model.py` remains for downstream clone-level summaries.

## Local Streamlit GUI

```bash
streamlit run src/tcr_bcr_tools/gui/app.py
```

The GUI displays workspace, project, dataset, and status. It calls `Workspace` / `Project` APIs only — **no analytical logic in the GUI**.

## Current analysis modules

Legacy CLIs under `src/tcr_bcr_tools/` remain available. Future releases will route them through project manifests.

## Git workflow

| Rule | Value |
| --- | --- |
| Main branch | `main` |
| Feature branches | `feature/x.y.z` (e.g. `feature/0.5.1`) |
| Releases | annotated tag `vx.y.z` after merge |
| CI | `.github/workflows/ci.yml` on every push/PR to `main` |

Development flow:

1. Create `feature/x.y.z` from `main`
2. Implement per specification in `specifications/`
3. Open pull request; CI must pass
4. Merge to `main`
5. Tag release: `git tag -a vx.y.z -m "Release vx.y.z"`

## Release process

1. Bump version in `pyproject.toml` and `src/tcr_bcr_tools/__init__.py`
2. Update `CHANGELOG.md`
3. Run `pytest` locally
4. Merge to `main` and verify GitHub Actions
5. Create annotated tag and push: `git push origin main --tags`

## Testing

Unit tests in `tests/` include `test_workspace.py`, `test_project.py`, and `test_dataset.py` for manifest and filesystem layout.

## Outputs

Project `outputs/`, `figures/`, and `logs/` are never committed to git.
