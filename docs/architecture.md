# Architecture

This document describes the current and planned architecture of **tcr-sf-pb** (package name: `tcr-bcr-tools`).

## Design principles

- **Specification Driven Development** — each feature has a spec, version, commit, and git tag.
- **Separation of concerns** — adapters, core library, pipeline, and GUI are distinct layers.
- **Reproducibility** — one analysis = one project with explicit inputs, outputs, and configuration.
- **Extensibility** — new input formats and analysis modules plug in without rewriting existing code.

## Layer overview

```
┌─────────────────────────────────────────────────────────────┐
│              Local Streamlit GUI (in progress)              │
│         localhost:8501 · orchestration only                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Pipeline / CLI                           │
│         composes analysis steps, writes outputs             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Analysis modules (current)                     │
│  detection curves · expansion · rank · ROC · deciles · …   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Core library                              │
│   clonotypes · detection table · metadata · I/O helpers     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Adapters (planned)                             │
│   tenx · bdrhapsody · airr · custom → standard format       │
└───────────────────────────────────────────────────────────────┘
```

## Current modules (`src/tcr_bcr_tools/`)

| Module | Role |
| --- | --- |
| `extract_annotations` | Load and merge 10x-style contig annotation files |
| `build_clonotypes` | Cell-level receptors and clone counts |
| `build_detection_table` | Paired SF/blood detection table |
| `detection_curves` | Empirical detection curves |
| `bin_visualizations` | Per-bin target abundance plots |
| `expansion_concordance` | Binary expansion concordance |
| `threshold_sweep` | Expansion threshold sensitivity |
| `rank_concordance` | Rank and percentile concordance |
| `weighted_rank_concordance` | Weighted Spearman correlation |
| `correlation_regression` | Continuous blood → SF regression |
| `roc_auc_analysis` | Predict SF expansion from blood |
| `decile_information` | Decile transition and information metrics |
| `gui` | Local Streamlit shell (v0.5.0 foundation) |

Supporting modules: `metadata`, `io`, `clone_bins`.

## Local Streamlit GUI

The GUI is a **local** application for bioinformatics workflows — not a hosted web service.

```bash
streamlit run src/tcr_bcr_tools/gui/app.py
```

Runs at `http://localhost:8501`.

Current shell (`src/tcr_bcr_tools/gui/app.py`):

- workspace path selection
- project selector
- create / open project placeholders
- project overview, outputs list, logs placeholder

**Rule:** the GUI must not contain analytical logic. It will call library functions and CLIs only.

## Workspace layout (planned)

A workspace groups shared datasets and multiple analysis projects:

```
workspace/
    settings.yaml

    datasets/
        GSE160097/
            raw/
            metadata.yaml

    projects/
        JIA_GSE160097/
            project.yaml
            intermediate/
            outputs/
            figures/
            logs/
            cache/
```

- **`settings.yaml`** — workspace-level defaults (paths, adapters, display options).
- **`datasets/`** — shared raw data and metadata, reusable across projects.
- **`projects/`** — one subdirectory per analysis.

## Project principle

**Each analysis = one project.**

Every project has its own:

| Path / file | Purpose |
| --- | --- |
| `project.yaml` | Manifest: dataset refs, pipeline steps, parameters |
| `intermediate/` | Early pipeline tables |
| `outputs/` | CSV summaries and result tables |
| `figures/` | Plots |
| `logs/` | Run logs |
| `cache/` | Optional cached computations |

Datasets in `workspace/datasets/` may be shared by multiple projects. Project outputs are never committed to git.

## Adapters

Adapters convert external formats into the **standard internal representation**. Analysis modules must not depend on the original file format.

```
src/tcr_bcr_tools/adapters/
    tenx/          # 10x Genomics filtered_contig_annotations
    bdrhapsody/    # BD Rhapsody
    airr/          # AIRR rearrangement tables
    custom/        # User-defined mappings
```

Each adapter produces:

- combined annotation table
- cell receptors
- clone counts
- paired detection table (via core pipeline)

Downstream analysis modules consume only these standardized tables.

## Multi-dataset analyses (planned)

Independent studies can be combined after adapter normalization:

```
GSE160097
    +
future RA dataset
    +
future JIA dataset
        ↓
joint standardized clone table
        ↓
common analysis pipeline
```

Requirements:

- harmonized metadata schema (patient, compartment, cell type)
- consistent `clonotype_key` definition
- dataset identifier column for stratified analyses

## Outputs

Analysis results are written under project `outputs/` or workspace-level output directories. These files are **not versioned** in git.

## Testing

Unit tests live in `tests/` and mirror analysis modules. Integration tests use small synthetic fixtures only — no large datasets in the repository.
