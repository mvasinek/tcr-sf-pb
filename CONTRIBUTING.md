# Contributing

Thank you for contributing to **tcr-sf-pb**. This project follows **Specification Driven Development**.

## Workflow

1. **Specification** — Every new feature must have a specification in `specifications/` before implementation begins.
2. **Feature branch** — Create a dedicated branch for each feature (e.g. `feature/0.4.9-my-feature`).
3. **Implementation** — Implement the feature in the core library under `src/tcr_bcr_tools/`.
4. **Tests** — Add or update tests in `tests/`. All tests must pass before merge.
5. **Documentation** — Update `README.md`, `CHANGELOG.md`, and version in `pyproject.toml` and `src/tcr_bcr_tools/__init__.py`.
6. **Pull request** — Open a pull request for review before merging to the main branch.
7. **Release tag** — Each released version must have an annotated git tag (e.g. `v0.4.9`).

## Versioning

We use [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

Examples: `0.4.8`, `0.4.9`, `0.5.0`, `1.0.0`

## Architecture rules

- **Analytical logic belongs in the core library** (`src/tcr_bcr_tools/`).
- **GUI must not contain analytical logic** — it should call library functions and CLIs only.
- **Adapters** convert external formats to the internal standard; analysis modules consume only the standard format.
- **Outputs** are written to project `outputs/` directories and are not committed to git.

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Specifications

Feature specifications live in `specifications/`. Name files as:

```
MAJOR.MINOR.PATCH_short_description.md
```

Example: `0.4.8_decile_information.md`
