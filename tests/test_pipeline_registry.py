"""Tests for pipeline step registry."""

from tcr_bcr_tools.pipeline.registry import STEP_ORDER, get_registry, get_step, list_steps


def test_registry_contains_expected_steps() -> None:
    registry = get_registry()
    expected = {
        "validate_dataset",
        "extract_annotations",
        "build_unified_table",
        "build_detection_table",
        "detection_curves",
        "expansion_concordance",
        "threshold_sweep",
        "rank_concordance",
        "weighted_rank",
        "correlation_regression",
        "roc_auc",
        "decile_information",
    }
    assert expected == set(registry.keys())


def test_list_steps_follows_execution_order() -> None:
    steps = list_steps()
    assert [step.id for step in steps] == STEP_ORDER


def test_step_metadata() -> None:
    step = get_step("build_detection_table")
    assert step.name == "Detection table"
    assert "build_unified_table" in step.dependencies
    assert callable(step.callable)


def test_dependency_chain() -> None:
    unified = get_step("build_unified_table")
    detection = get_step("build_detection_table")
    weighted = get_step("weighted_rank")
    assert "validate_dataset" in unified.dependencies
    assert unified.dependencies[-1] == "extract_annotations"
    assert "validate_dataset" in detection.dependencies
    assert weighted.dependencies[-1] == "rank_concordance"
