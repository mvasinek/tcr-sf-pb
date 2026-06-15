"""Pipeline execution panel for Streamlit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from tcr_bcr_tools.gui.constants import LOG_LEVEL_FILTERS
from tcr_bcr_tools.gui.helpers import format_status
from tcr_bcr_tools.pipeline.history import load_history
from tcr_bcr_tools.pipeline import PipelineRunner, read_pipeline_log
from tcr_bcr_tools.pipeline.runner import DependencyError
from tcr_bcr_tools.project import Project, Workspace


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def render_pipeline_panel(
    workspace: Workspace,
    project: Project,
) -> None:
    """Render pipeline controls, step detail, logs, history, and outputs."""
    force_recompute = st.checkbox(
        "Force recompute",
        value=bool(st.session_state.get("force_recompute")),
        key="force_recompute",
    )
    runner = PipelineRunner(
        workspace,
        project,
        force_recompute=force_recompute,
        repo_root=_repo_root(),
    )
    states = runner.step_states()

    st.markdown("### Pipeline")
    _render_step_table(runner, states)
    _render_step_detail(states)
    _render_run_controls(runner)
    _render_output_browser(workspace, states)
    _render_history_panel(project)
    _render_log_panel(project)


def _render_step_table(
    runner: PipelineRunner,
    states: list[dict],
) -> None:
    rows = []
    for state in states:
        display, _color = format_status(str(state.get("status", "pending")))
        rows.append(
            {
                "Step": state["name"],
                "Status": display,
                "Run": state["id"],
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
    )

    selected = st.selectbox(
        "Select step for details",
        options=[state["id"] for state in states],
        format_func=lambda step_id: next(
            state["name"] for state in states if state["id"] == step_id
        ),
        key="selected_pipeline_step",
    )
    st.session_state["selected_pipeline_step"] = selected

    if st.button("▶ Run", key="run_single_step"):
        step_id = st.session_state.get("selected_pipeline_step")
        if step_id:
            _run_single_step(runner, step_id)


def _run_single_step(runner: PipelineRunner, step_id: str) -> None:
    with st.spinner(f"Running {step_id}..."):
        try:
            result = runner.run_step(step_id)
            if result["status"] == "failed":
                st.error(result.get("message", "Step failed"))
            elif result["status"] == "skipped":
                st.info("Reused existing output")
            else:
                st.success(f"Completed {step_id}")
        except DependencyError as exc:
            st.error(str(exc))


def _render_run_controls(runner: PipelineRunner) -> None:
    if st.button("▶ Run pipeline", key="run_full_pipeline"):
        states = runner.step_states()
        total = len(states)
        progress = st.progress(0.0)
        with st.spinner("Running pipeline..."):
            results = runner.run()
        completed = sum(
            1 for result in results if result.get("status") in {"completed", "skipped"}
        )
        progress.progress(min(completed / max(total, 1), 1.0))
        failed = [result for result in results if result.get("status") == "failed"]
        if failed:
            st.error(failed[0].get("message", "Pipeline failed"))
        else:
            st.success("Pipeline finished")


def _render_step_detail(states: list[dict]) -> None:
    step_id = st.session_state.get("selected_pipeline_step")
    if not step_id:
        return
    state = next((item for item in states if item["id"] == step_id), None)
    if state is None:
        return

    st.markdown("### Step detail")
    st.markdown(f"**Description:** {state.get('description', '')}")
    dependencies = state.get("dependencies", [])
    st.markdown(
        f"**Dependencies:** {', '.join(dependencies) if dependencies else '(none)'}"
    )
    outputs = state.get("outputs", {})
    if outputs:
        st.markdown("**Outputs:**")
        for category, paths in outputs.items():
            st.markdown(f"- {category}: {', '.join(paths)}")
    else:
        st.markdown("**Outputs:** (none yet)")
    runtime = state.get("runtime")
    st.markdown(f"**Runtime:** {runtime if runtime is not None else '—'}")
    st.markdown(f"**Version:** {state.get('version', '')}")
    st.markdown(f"**Last run:** {state.get('finished', '—')}")


def _render_output_browser(workspace: Workspace, states: list[dict]) -> None:
    step_id = st.session_state.get("selected_pipeline_step")
    if not step_id:
        return
    state = next((item for item in states if item["id"] == step_id), None)
    if state is None:
        return

    st.markdown("### Generated outputs")
    outputs = state.get("outputs", {})
    all_paths: list[str] = []
    for paths in outputs.values():
        all_paths.extend(paths)
    if not all_paths:
        st.caption("No registered outputs for this step.")
        return

    selected_output = st.selectbox("Output file", options=all_paths, key="output_file")
    output_path = workspace.root / selected_output
    if not output_path.exists():
        st.warning("Output file is missing on disk.")
        return

    if output_path.suffix.lower() == ".csv":
        df = pd.read_csv(output_path)
        st.dataframe(df, use_container_width=True)
    elif output_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
        st.image(str(output_path))
    else:
        st.code(str(output_path))


def _render_history_panel(project: Project) -> None:
    st.markdown("### Run history")
    records = load_history(project.logs_dir)
    if not records:
        st.caption("No runs recorded yet.")
        return
    rows = []
    for record in reversed(records[-50:]):
        rows.append(
            {
                "Date": record.get("finished", record.get("started", "")),
                "Step": record.get("step", ""),
                "Duration": record.get("duration", ""),
                "Status": record.get("status", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_log_panel(project: Project) -> None:
    st.markdown("### Pipeline log")
    level = st.selectbox("Log filter", LOG_LEVEL_FILTERS, key="log_level_filter")
    filter_level = None if level == "All" else level
    entries = read_pipeline_log(project.logs_dir, tail=200, level=filter_level)
    if not entries:
        st.caption("No log entries yet.")
        return
    lines = [
        f"{entry['timestamp']} [{entry['level']}] {entry['step']}: {entry['message']}"
        for entry in entries
    ]
    st.code("\n".join(lines))
