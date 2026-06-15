# Changelog

## [Unreleased]

## [0.5.5]

### Added

- Results Browser.
- Output Registry API.
- Interactive CSV Viewer.
- Figure Gallery.
- Table Gallery.
- Search engine for outputs.
- Favorites.
- Recent outputs.
- Metadata panel.
- Output comparison.
- ZIP export.
- Project Summary dashboard.

## [0.5.4]

### Added

- Centralized validation framework.
- ValidationRule abstraction.
- ValidationReport model.
- Dataset quality scoring.
- Dataset validation dashboard.
- Quality metrics visualization.
- Validation pipeline step.
- Validation report serialization.
- Pipeline validation gate.

## [0.5.3]

### Added

- Adapter framework.
- BaseAdapter abstraction.
- Adapter registry.
- Unified annotation schema.
- TenX adapter implementation.
- Dataset validation through adapters.
- Dataset normalization through adapters.
- Adapter report output.
- Adapter CLI.
- Streamlit dataset validation and normalization controls.

### Changed

- Pipeline extraction step now uses dataset adapter normalization.
- Legacy direct extraction remains available for backward compatibility.

## [0.5.2]

### Added

- Pipeline Runner
- Pipeline registry
- PipelineStep abstraction
- Dependency management
- Run history
- Pipeline log
- Output registry
- Cache support
- Run-all execution
- Streamlit pipeline panel
- Output browser

## [0.5.1]

### Added

- Streamlit workspace manager
- Project browser
- Dataset browser
- Workspace overview
- Project overview
- Dataset overview
- Project creation dialog
- Dataset registration dialog
- Inspector panel
- Status bar
- Git information panel

## [0.5.0]

### Added

- Workspace architecture
- Project manifest
- Dataset manifest
- Workspace API
- Project API
- Dataset API
- Manifest API
- Adapter architecture
- Unified internal data model
- Streamlit GUI foundation
- Git workflow documentation
- GitHub Actions CI workflow for Python 3.11 and 3.12

## [0.4.8]

Initial public release

### Features

- annotation extraction
- unified clone table
- paired SF/blood detection table
- detection curves
- expansion concordance
- threshold sweep
- rank concordance
- weighted rank concordance
- correlation and regression analysis
- ROC/AUC analysis
- decile heatmap and information metrics

## [0.4.8] - Decile heatmap and information metrics

### Added
- Decile/bin assignment for blood and SF clone sizes.
- Decile transition matrix between blood and SF.
- Mutual information and normalized mutual information metrics.
- Conditional entropy and uncertainty reduction metrics.
- Top-decile enrichment analysis.
- Heatmap and information metric plots.
- CLI for decile information analysis.

## [0.4.7] - ROC/AUC prediction of synovial expansion

### Added
- ROC/AUC analysis for predicting SF-expanded clones from blood-derived features.
- Support for multiple blood-based predictors.
- Average precision and precision-recall curve outputs.
- Best threshold estimation using Youden J.
- Prediction score table.
- ROC, PR, AUC and score distribution plots.
- CLI for ROC/AUC analysis.

## [0.4.6] - Correlation and regression

### Added
- Correlation analysis between blood and SF clone fractions.
- Log-transformed fraction analysis with pseudocount.
- Linear regression model `log_sf_fraction ~ log_blood_fraction`.
- Regression prediction and residual export.
- Scatter, regression fit and residual plots.
- CLI for correlation and regression analysis.

## [0.4.5] - Weighted Spearman rank correlation

### Added
- Weighted Spearman correlation for clone-size concordance.
- Multiple clone-weighting strategies.
- Weighted rank correlation summary.
- Weighted Spearman bar plot by cell type.
- Clone weight distribution plot.
- CLI for weighted rank concordance analysis.

## [0.4.4] - Rank and percentile concordance

### Added
- Clone ranking by fraction.
- Clone percentile calculation.
- Pearson, Spearman and Kendall concordance.
- Percentile concordance analysis.
- Top-N overlap analysis.
- Rank scatter plot.
- Percentile heatmap.
- Top overlap curve.

## [0.4.3] - Expansion threshold sweep

### Added
- Sweep of expansion concordance metrics across multiple thresholds.
- Default threshold grids for fraction, cell-count and quantile expansion definitions.
- Global threshold sweep summary.
- Patient-level threshold sweep summary.
- Threshold sweep plots for conditional probabilities, Jaccard index and expanded clone counts.
- CLI for threshold sweep analysis.

## [0.4.2] - Expansion concordance between compartments

### Added
- Classification of expanded clones in SF and blood.
- Support for fraction, cell-count and quantile-based expansion thresholds.
- Expansion status table.
- Global expansion concordance summary.
- Patient-level expansion concordance summary.
- Expansion status bar plot.
- SF vs blood fraction scatter plot.
- Patient-level concordance matrix.

## [0.4.1] - Target abundance by clone-size bin

### Added
- Target abundance summaries by source clone-size bin.
- Mean and median target clone counts for all and detected-only clones.
- Per-bin scatter plots of source vs target clone counts.
- Per-bin boxplots of target clone counts.
- Export of bin-level visualizations under `outputs/bins/`.
- GUI-ready helper functions for bin-level visualizations.

## [0.4.0] - Detection curve summaries and plots

### Added
- Construction of detection curve point table.
- Empirical detection summaries for SF-to-blood and blood-to-SF directions.
- Default clone-size bins.
- PNG plots for detection curves.
- CLI for detection curve analysis.
- Optional filters for cell type and minimum source clone size.

## [0.3.1] - Fix paired detection grouping key

### Fixed
- Changed SF/blood clone pairing key from `sample_group + patient + cell_type + clonotype_key` to `patient + cell_type + clonotype_key`.
- Prevented different `sample_group` values from blocking shared clone detection.
- Added separate `sf_sample_group` and `blood_sample_group` metadata columns.
- Updated fraction calculation to use patient-level compartment totals.

## [0.3.0] - Build paired SF/blood detection table

### Added
- Construction of paired SF/blood clone detection table.
- Support for SF-only, blood-only and shared clones.
- Compartment normalization.
- Per-patient and per-cell-type clone fractions.
- CLI for detection table generation.
- Optional filters for cell type, sample group and minimum clone size.
- Unit tests for paired detection table generation.

## [0.2.0] - Build cell receptor and clone count tables

### Added
- Productive TCR contig filtering.
- Dominant TRA/TRB chain selection per cell.
- Construction of paired and single-chain clonotype keys.
- Export of `cell_receptors.csv`.
- Export of `clone_counts.csv`.
- Optional `--paired-only` mode for clone counting.
- Unit tests for clonotype table generation.

## [0.1.0] - Initial annotation extraction

### Added
- Recursive discovery of `annotations.csv.gz` files.
- Parsing of GEO/sample metadata from filenames.
- Combination of contig annotation files into one CSV table.
- Optional productive-only filtering.
- Basic unit tests.
