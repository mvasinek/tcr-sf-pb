"""Dataset validation dashboard for Streamlit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from tcr_bcr_tools.gui.validation_helpers import severity_color, status_label
from tcr_bcr_tools.validation.validator import quality_metrics


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def render_validation_panel(dataset) -> None:
    """Render the Data Validation dashboard for one dataset."""
    st.markdown("## Data Validation")
    if st.button("Run validation", key="run_data_validation"):
        with st.spinner("Running validation..."):
            report = dataset.validate(repo_root=_repo_root())
        st.session_state["validation_report"] = report

    report = dataset.load_validation_report()
    if report is None:
        st.info("Run validation to generate a report.")
        return

    summary = report.summary
    cols = st.columns(5)
    cols[0].metric("Validation score", f"{summary.score}/100")
    cols[1].metric("Passed", summary.passed)
    cols[2].metric("Warnings", summary.warnings)
    cols[3].metric("Errors", summary.errors)
    cols[4].metric("Critical", summary.critical)

    tabs = st.tabs(["Overview", "Rules", "Quality metrics", "Plots", "Raw report"])
    df = _load_unified_frame(dataset)

    with tabs[0]:
        _render_overview_cards(dataset, df, summary.score)

    with tabs[1]:
        _render_rules_table(report)

    with tabs[2]:
        _render_quality_metrics(df)

    with tabs[3]:
        _render_plots(df)

    with tabs[4]:
        st.json(report.to_dict())


def _load_unified_frame(dataset) -> pd.DataFrame:
    if dataset.has_unified_annotations():
        return pd.read_csv(dataset.unified_annotations_path())
    return pd.DataFrame()


def _render_overview_cards(dataset, df: pd.DataFrame, score: int) -> None:
    metrics = quality_metrics(df) if not df.empty else {}
    cards = st.columns(5)
    cards[0].metric("Datasets", 1)
    cards[1].metric("Patients", metrics.get("patients", 0))
    cards[2].metric("Cells", metrics.get("cells", 0))
    cards[3].metric("Clonotypes", metrics.get("clonotypes", 0))
    cards[4].metric("Validation score", f"{score}/100")
    st.markdown(f"**Dataset:** `{dataset.dataset_id}`")
    st.markdown(f"**Adapter:** `{dataset.adapter()}`")


def _render_rules_table(report) -> None:
    rows = []
    for result in report.results:
        color = severity_color(result.severity.value)
        rows.append(
            {
                "Rule": result.rule_id,
                "Status": status_label(result.passed),
                "Severity": result.severity.value,
                "Message": result.message,
                "_color": color,
            }
        )
    table = pd.DataFrame(rows)
    st.dataframe(
        table.drop(columns=["_color"]),
        hide_index=True,
        use_container_width=True,
    )
    for row in rows:
        st.markdown(
            f":{row['_color']}[{row['Rule']}: {row['Status']} ({row['Severity']})]"
        )


def _render_quality_metrics(df: pd.DataFrame) -> None:
    if df.empty:
        st.caption("No unified annotations available.")
        return
    metrics = quality_metrics(df)
    st.markdown("### Quality metrics")
    st.markdown(f"- **Patients:** {metrics['patients']}")
    st.markdown(f"- **SF samples:** {metrics['sf_samples']}")
    st.markdown(f"- **Blood samples:** {metrics['blood_samples']}")
    st.markdown(f"- **Productive %:** {metrics['productive_fraction']:.1%}")
    st.markdown(f"- **High confidence %:** {metrics['high_confidence_fraction']:.1%}")
    st.markdown(f"- **Mean reads:** {metrics['mean_reads']}")
    st.markdown(f"- **Mean UMIs:** {metrics['mean_umis']}")
    st.markdown("**Cell types:**")
    st.json(metrics["cell_types"])


def _render_plots(df: pd.DataFrame) -> None:
    if df.empty:
        st.caption("No unified annotations available.")
        return
    patient_counts = df.groupby("patient")["barcode"].nunique().reset_index(name="cells")
    fig_patients = px.bar(patient_counts, x="patient", y="cells", title="Cells per patient")
    st.plotly_chart(fig_patients, use_container_width=True)

    compartment_counts = df["compartment"].value_counts().reset_index()
    compartment_counts.columns = ["compartment", "count"]
    fig_comp = px.bar(
        compartment_counts,
        x="compartment",
        y="count",
        title="Cells per compartment",
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    cell_type_counts = df["cell_type"].value_counts().reset_index()
    cell_type_counts.columns = ["cell_type", "count"]
    fig_cell = px.bar(
        cell_type_counts,
        x="cell_type",
        y="count",
        title="Cells per cell type",
    )
    st.plotly_chart(fig_cell, use_container_width=True)

    productive = df["productive"].fillna(False).astype(bool).value_counts().reset_index()
    productive.columns = ["productive", "count"]
    fig_prod = px.bar(
        productive,
        x="productive",
        y="count",
        title="Productive vs non-productive",
    )
    st.plotly_chart(fig_prod, use_container_width=True)

    high_conf = df["high_confidence"].fillna(False).astype(bool)
    fraction = float(high_conf.mean())
    fig_conf = px.bar(
        x=["high_confidence"],
        y=[fraction],
        title="High confidence fraction",
    )
    st.plotly_chart(fig_conf, use_container_width=True)
