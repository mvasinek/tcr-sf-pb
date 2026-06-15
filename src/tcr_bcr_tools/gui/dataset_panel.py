"""Dataset overview and adapter controls."""

from __future__ import annotations

import streamlit as st

from tcr_bcr_tools.project import Dataset


def render_dataset_panel(dataset: Dataset) -> None:
    """Render dataset metadata, adapter validation, and normalization controls."""
    st.subheader("Dataset overview")
    meta = dataset.metadata()
    st.markdown(f"**Dataset ID:** {meta.get('id', dataset.dataset_id)}")
    st.markdown(f"**Source:** {meta.get('source', '')}")
    st.markdown(f"**Adapter:** {dataset.adapter()}")
    st.markdown(f"**Number of files:** {dataset.count_raw_files()}")
    st.markdown(f"**Raw directory:** `{dataset.raw_dir}`")
    st.markdown(f"**Intermediate directory:** `{dataset.intermediate_dir}`")

    raw_source = dataset.raw_source_path()
    if raw_source:
        st.markdown(f"**Registered raw source:** `{raw_source}`")

    st.markdown(
        f"**Unified output exists:** "
        f"{'yes' if dataset.has_unified_annotations() else 'no'}"
    )

    _render_adapter_controls(dataset)

    if dataset.manifest_path.exists():
        with st.expander("dataset.yaml"):
            st.json(dataset.load())


def _render_adapter_controls(dataset: Dataset) -> None:
    st.markdown("### Adapter")
    if st.button("Validate dataset", key="validate_dataset"):
        with st.spinner("Validating dataset..."):
            result = dataset.validate_with_adapter()
        st.markdown(
            f"**Validation status:** {'valid' if result.valid else 'invalid'}"
        )
        st.markdown(f"**Detected files:** {len(result.detected_files)}")
        if result.detected_files:
            for path in result.detected_files:
                st.markdown(f"- `{path.name}`")
        for warning in result.warnings:
            st.warning(warning)
        for error in result.errors:
            st.error(error)

    if st.button("Normalize dataset", key="normalize_dataset"):
        with st.spinner("Normalizing dataset..."):
            try:
                output = dataset.normalize_with_adapter()
                st.success(f"Wrote `{output}`")
            except (ValueError, NotImplementedError) as exc:
                st.error(str(exc))
