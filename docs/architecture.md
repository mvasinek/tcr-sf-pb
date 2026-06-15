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
│                         GUI (future)                        │
│              orchestration only, no analytics               │
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
│              Adapters (planned)                               │
│   tenx · bdrhapsody · airr · custom → standard format        │
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

Supporting modules: `metadata`, `io`, `clone_bins`.

## Adapters (planned)

```
adapters/
    tenx/          # 10x Genomics filtered_contig_annotations
    bdrhapsody/    # BD Rhapsody
    airr/          # AIRR rearrangement tables
    custom/        # User-defined mappings
```

Each adapter converts raw inputs into a **standard internal representation**:

- combined annotation table
- cell receptors
- clone counts
- paired detection table

Analysis modules operate only on this standardized format.

## Project management (planned)

Each analysis is a self-contained **project**:

```
project/
    project.yaml      # configuration, paths, dataset references
    raw/              # immutable input data (symlinks or copies)
    intermediate/     # tables produced by early pipeline steps
    outputs/            # analysis CSVs and summaries
    figures/            # plots
    logs/               # run logs
    cache/              # optional cached computations
```

`project.yaml` will define:

- input adapter and paths
- patient / sample metadata
- which pipeline steps to run
- analysis parameters (thresholds, cell types, etc.)

The CLI and future GUI will read `project.yaml` and execute the pipeline reproducibly.

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

## GUI (planned)

The GUI will:

- create and open projects
- configure pipeline steps
- launch analyses and display outputs

The GUI **must not** implement analytical logic. It calls the same functions and CLIs as the command-line workflow.

## Outputs

Analysis results are written under `outputs/` (or project-specific output directories). These files are **not versioned** in git. Only `.gitkeep` is tracked to preserve the directory layout.

## Testing

Unit tests live in `tests/` and mirror analysis modules. Integration tests may use small synthetic fixtures only — no large datasets in the repository.
