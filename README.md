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
Adapters (planned)  →  Core library  →  Analysis modules  →  Pipeline/CLI  →  GUI (planned)
```

| Layer | Status | Description |
| --- | --- | --- |
| **Adapters** | Planned | Convert 10x, BD Rhapsody, AIRR, custom inputs to standard tables |
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
combined_annotations.csv          (0.1.0)
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

Analytical modules are not launched from the GUI yet (planned for v0.5.2 Pipeline Runner).

## Local Streamlit GUI

Local bioinformatics environment at `http://localhost:8501` (not a hosted web service).

```bash
pip install -e .
streamlit run src/tcr_bcr_tools/gui/app.py
```

The GUI uses the `Workspace` API to display workspace path, project, datasets, and pipeline status. It does not run analyses yet.

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
- [ ] Pipeline runner (v0.5.2)
- [ ] Wire analyses to project manifests

### Phase 0.6.x — Adapters

- [ ] 10x adapter (`src/tcr_bcr_tools/adapters/tenx/`)
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
