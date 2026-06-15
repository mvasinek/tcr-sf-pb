# tcr-sf-pb

Python library for analyzing TCR/BCR repertoire overlap between peripheral blood and synovial fluid in single-cell experiments.

**Repository:** [github.com/mvasinek/tcr-sf-pb](https://github.com/mvasinek/tcr-sf-pb)  
**Current version:** 0.5.1  
**License:** MIT

---

## Project overview

**tcr-sf-pb** (package name: `tcr-bcr-tools`) provides a reproducible pipeline from raw 10x-style contig annotations to quantitative concordance analyses between blood and synovial fluid (SF) T-cell clones.

The library is developed using **Specification Driven Development**: each feature has a specification in `specifications/`, a semantic version, and a git tag.

Primary reference dataset: [GSE160097](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE160097) (rheumatoid arthritis SF vs blood scRNA-seq with TCR profiling).

---

## Objectives

> The goal of the project is to investigate whether synovial TCR repertoire can be partially reconstructed from peripheral blood using clone detection, expansion analysis and probabilistic modelling.

Specific questions addressed in v0.4.x:

- Which blood clones are detected in SF?
- Do expanded blood clones correspond to expanded SF clones?
- How well does blood clone size predict SF clone size?
- Can blood features predict SF expansion (ROC/AUC)?
- How much information does blood decile structure carry about SF decile structure?

---

## Architecture

```
Raw data → Adapters → unified_annotations.csv → Pipeline/CLI → Analysis modules → GUI
```

| Layer | Status | Description |
| --- | --- | --- |
| **Adapters** | Implemented (TenX) | Convert 10x, BD Rhapsody, AIRR, custom inputs to unified schema |
| **Core library** | Implemented | Annotation extraction, clonotypes, paired detection table |
| **Analysis modules** | Implemented | Detection curves, expansion, rank, regression, ROC, deciles |
| **Pipeline** | Partial (CLI) | Each module has `python -m tcr_bcr_tools.<module>` entry point |
| **GUI** | In progress | Local Streamlit shell — orchestration only, no analytics |
| **Project management** | Implemented | `Workspace`, `Project`, `Dataset` APIs |

See [docs/architecture.md](docs/architecture.md) for details.

---

## Pipeline

```
annotations.csv.gz
        ↓
unified_annotations.csv           (0.5.3, via adapter)
        ↓
cell_receptors.csv                (0.2.0)
clone_counts.csv
        ↓
paired_detection_table.csv        (0.3.0)
        ↓
├── detection curves              (0.4.0–0.4.1)
├── expansion concordance         (0.4.2–0.4.3)
├── rank concordance              (0.4.4–0.4.5)
├── correlation / regression      (0.4.6)
├── ROC/AUC                       (0.4.7)
└── decile information            (0.4.8)
```

Pairing key for SF/blood clones: `patient + cell_type + clonotype_key`.

---

## Version history

| Version | Feature |
| --- | --- |
| 0.1.0 | Annotation extraction |
| 0.2.0 | Cell receptors and clone counts |
| 0.3.0 | Paired SF/blood detection table |
| 0.3.1 | Fix pairing key (patient, not sample_group) |
| 0.4.0 | Detection curves |
| 0.4.1 | Target abundance by bin |
| 0.4.2 | Expansion concordance |
| 0.4.3 | Threshold sweep |
| 0.4.4 | Rank and percentile concordance |
| 0.4.5 | Weighted Spearman correlation |
| 0.4.6 | Correlation and regression |
| 0.4.7 | ROC/AUC analysis |
| 0.4.8 | Decile heatmap and information metrics |

Full changelog: [CHANGELOG.md](CHANGELOG.md). Specifications: [specifications/](specifications/).

---

## Repository structure

```
tcr-sf-pb/
├── src/tcr_bcr_tools/     # Core library, analysis modules, GUI, adapters
│   ├── project/           # Workspace, project, dataset APIs
│   ├── gui/               # Local Streamlit shell
│   └── adapters/          # Input format adapters
├── tests/                 # pytest suite
├── docs/                  # Architecture and design docs
├── specifications/        # Feature specifications (SDD)
├── examples/              # Example projects (future)
├── scripts/               # Utility scripts (future)
├── outputs/               # Analysis outputs (gitignored except .gitkeep)
├── .github/               # CI workflows (future)
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── CONTRIBUTING.md
└── .gitignore
```

---

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/mvasinek/tcr-sf-pb.git
cd tcr-sf-pb
pip install -e ".[dev]"
```

---

## Quick start

Place 10x `filtered_contig_annotations.csv.gz` files in a data directory. Filename pattern:

```text
GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz
```

Run the pipeline:

```bash
# 1. Extract annotations
python -m tcr_bcr_tools.extract_annotations \
  --input-dir ./data \
  --output ./outputs/combined_annotations.csv

# 2. Build clonotype tables
python -m tcr_bcr_tools.build_clonotypes \
  --input ./outputs/combined_annotations.csv \
  --cell-output ./outputs/cell_receptors.csv \
  --clone-output ./outputs/clone_counts.csv

# 3. Build paired detection table
python -m tcr_bcr_tools.build_detection_table \
  --input ./outputs/clone_counts.csv \
  --output ./outputs/paired_detection_table.csv

# 4. Run analyses (examples)
python -m tcr_bcr_tools.detection_curves \
  --input ./outputs/paired_detection_table.csv \
  --output-dir ./outputs

python -m tcr_bcr_tools.expansion_concordance \
  --input ./outputs/paired_detection_table.csv \
  --output-dir ./outputs

python -m tcr_bcr_tools.rank_concordance \
  --input ./outputs/paired_detection_table.csv \
  --output-dir ./outputs

python -m tcr_bcr_tools.decile_information \
  --input ./outputs/paired_detection_table.csv \
  --output-dir ./outputs
```

Run tests:

```bash
pytest
```

---

## Running GUI

Local bioinformatics IDE at `http://localhost:8501`:

```bash
pip install -e .
python -m streamlit run src/tcr_bcr_tools/gui/app.py
```

The GUI provides:

- **Workspace** — open or create a workspace directory with shared `datasets/` and `projects/`
- **Projects** — browse, create, open, and delete analysis projects
- **Datasets** — register shared datasets with adapter metadata and raw directory paths

Analytical steps run through the **Pipeline Runner** — the GUI orchestrates execution but does not contain analytical logic.

## Adapter framework

Adapters convert vendor-specific raw data into a single **unified annotation schema** (`unified_annotations.csv`). Analysis modules never read 10x-specific columns directly.

```text
10x / BD / AIRR / custom  →  adapter  →  unified_annotations.csv  →  pipeline
```

**Preferred workflow** (dataset in a workspace):

```bash
python -m tcr_bcr_tools.adapters.run_adapter \
  --adapter tenx \
  --dataset ./workspace/datasets/GSE160097
```

Or via the pipeline runner step `extract_annotations`, which calls `Dataset.normalize_with_adapter()`.

**Legacy direct extraction** (still supported):

```bash
python -m tcr_bcr_tools.extract_annotations \
  --input-dir ./data \
  --output ./outputs/combined_annotations.csv
```

To add a new adapter, subclass `BaseAdapter`, implement `validate_input()` and `normalize()`, and register it in `adapters/registry.py`.

## Pipeline Runner

The pipeline layer (`src/tcr_bcr_tools/pipeline/`) provides a GUI-independent execution engine:

- **Run step** — execute one registered analytical step via `PipelineRunner.run_step()`
- **Run pipeline** — execute all steps in dependency order via `PipelineRunner.run()`
- **Dependency validation** — refuse to run a step until required upstream steps are `completed`
- **Cache** — reuse existing outputs when files are present (`needs_recompute()`); use `force_recompute=True` to ignore cache
- **Run history** — each run is recorded in `projects/<id>/logs/run_history.yaml` with Git branch, commit, and tag
- **Pipeline log** — structured log at `projects/<id>/logs/pipeline.log`

```python
from pathlib import Path
from tcr_bcr_tools.pipeline import PipelineRunner
from tcr_bcr_tools.project import Workspace

workspace = Workspace(Path("~/tcr-sf-pb-workspace"))
workspace.load()
project = workspace.open_project("JIA_Pilot")
runner = PipelineRunner(workspace, project)
runner.run_step("extract_annotations")
runner.run()
```

## Local Streamlit GUI

Local bioinformatics environment at `http://localhost:8501` (not a hosted web service).

```bash
pip install -e .
streamlit run src/tcr_bcr_tools/gui/app.py
```

The GUI uses the `Workspace` API and `PipelineRunner` to display projects, datasets, pipeline status, logs, and outputs. It does not call analytical functions directly.

### Pipeline panel (v0.5.2)

When a project is open, the **Pipeline** panel lists registered steps with status, run controls, step detail, run history, pipeline log, and an output browser.

### Workspace layout (v0.5.0)

```text
workspace/
    settings.yaml
    datasets/GSE160097/
        dataset.yaml
        raw/
        intermediate/
    projects/JIA_Pilot/
        project.yaml
        outputs/
        figures/
        logs/
        cache/
```

Create a workspace programmatically:

```python
from pathlib import Path
from tcr_bcr_tools.project import Workspace

workspace = Workspace(Path("~/tcr-sf-pb-workspace"))
workspace.load()
workspace.create_dataset("GSE160097", source="GEO", adapter="tenx")
workspace.create_project(
    "JIA_Pilot",
    name="JIA Pilot",
    datasets=["GSE160097"],
    analysis="detection",
)
```

---

## Roadmap

### Phase 0.5.x — Local Streamlit GUI and project mode

- [x] Workspace layout (`settings.yaml`, `datasets/`, `projects/`)
- [x] `Workspace`, `Project`, `Dataset` APIs
- [x] `BaseAdapter` interface
- [x] Streamlit workspace & project manager (v0.5.1)
- [x] Pipeline runner (v0.5.2)
- [x] Adapter framework and TenX adapter (v0.5.3)
- [ ] Wire adapters for BD Rhapsody, AIRR, custom

### Phase 0.6.x — Adapters

- [x] TenX adapter (`src/tcr_bcr_tools/adapters/tenx/`)
- [ ] BD Rhapsody adapter
- [ ] AIRR adapter
- [ ] Custom adapter template

### Phase 0.7.x — Multi-dataset support

- [ ] **Support for multiple datasets**
- [ ] Combine independent studies into a unified analysis after adapter normalization

```
GSE160097 + future RA dataset + future JIA dataset
        ↓
joint standardized clone table
        ↓
common analysis pipeline
```

### Phase 1.0.x — Full GUI

- [ ] Project browser and configuration UI
- [ ] Results viewer (tables and plots)
- [ ] GUI calls library/CLI only — no embedded analytics

---

## Continuous integration

The repository uses GitHub Actions to run the test suite on Python 3.11 and 3.12 for every push and pull request to `main`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
