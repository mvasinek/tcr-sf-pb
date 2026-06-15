"""Tests for paired SF/blood detection table generation."""

import pandas as pd
import pytest

from tcr_bcr_tools.build_detection_table import (
    DETECTION_TABLE_COLUMNS,
    build_paired_detection_table,
    calculate_compartment_totals,
    filter_clone_counts,
    normalize_compartment,
)

CLONE_A = "TRA:TRAV1|TRAJ1|CAAA__TRB:TRBV1|TRBJ1|CASS1"
CLONE_B = "TRA:TRAV2|TRAJ2|CABB__TRB:missing"
CLONE_C = "TRA:missing__TRB:TRBV3|TRBJ3|CASS3"
CLONE_D = "TRA:TRAV4|TRAJ4|CADD__TRB:TRBV4|TRBJ4|CASS4"


def _clone_row(
    clonotype_key: str,
    compartment: str,
    *,
    n_cells: int = 2,
    n_paired_cells: int = 1,
    n_tra_only_cells: int = 1,
    n_trb_only_cells: int = 0,
    sample_group: str = "PM1",
    patient: str = "p1",
    cell_type: str = "CD4",
) -> dict:
    return {
        "sample_group": sample_group,
        "patient": patient,
        "compartment": compartment,
        "cell_type": cell_type,
        "clonotype_key": clonotype_key,
        "n_cells": n_cells,
        "n_paired_cells": n_paired_cells,
        "n_tra_only_cells": n_tra_only_cells,
        "n_trb_only_cells": n_trb_only_cells,
    }


@pytest.fixture
def clone_counts_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _clone_row(CLONE_A, "SF", n_cells=4, n_paired_cells=3),
            _clone_row(CLONE_A, "blood", n_cells=2, n_paired_cells=2),
            _clone_row(CLONE_B, "SF", n_cells=3, n_paired_cells=0, n_tra_only_cells=3),
            _clone_row(CLONE_C, "blood", n_cells=5, n_paired_cells=0, n_trb_only_cells=5),
            _clone_row(CLONE_D, "SF", n_cells=1, n_paired_cells=1),
            _clone_row(CLONE_D, "blood", n_cells=1, n_paired_cells=0, n_tra_only_cells=1),
            _clone_row(
                "TRA:TRAV9|TRAJ9|CAZZ__TRB:missing",
                "tissue",
                n_cells=9,
            ),
            _clone_row(
                CLONE_A,
                "SynovialFluid",
                n_cells=1,
                n_paired_cells=1,
                patient="p2",
            ),
            _clone_row(
                CLONE_B,
                "PB",
                n_cells=2,
                n_paired_cells=0,
                n_tra_only_cells=2,
                patient="p2",
            ),
        ]
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SF", "SF"),
        ("sf", "SF"),
        ("SynovialFluid", "SF"),
        ("synovial_fluid", "SF"),
        ("blood", "blood"),
        ("Blood", "blood"),
        ("PB", "blood"),
        ("peripheral_blood", "blood"),
        ("tissue", None),
    ],
)
def test_normalize_compartment(value: str, expected: str | None) -> None:
    assert normalize_compartment(value) == expected


def test_build_paired_detection_table_ignores_unsupported_compartment(
    clone_counts_df: pd.DataFrame, capsys: pytest.CaptureFixture[str]
) -> None:
    normalized = clone_counts_df.copy()
    normalized["compartment"] = normalized["compartment"].map(normalize_compartment)
    filtered = normalized.loc[normalized["compartment"].notna()].copy()

    result = build_paired_detection_table(filtered)
    assert "tissue" not in result["clonotype_key"].values
    captured = capsys.readouterr()
    assert captured.out == ""


def test_shared_clone_across_different_sample_groups() -> None:
    df = pd.DataFrame(
        [
            _clone_row("cloneA", "SF", sample_group="PM3", n_cells=10, n_paired_cells=10),
            _clone_row("cloneA", "blood", sample_group="PM6", n_cells=2, n_paired_cells=2),
        ]
    )
    result = build_paired_detection_table(df)
    row = result.iloc[0]

    assert row["patient"] == "p1"
    assert row["cell_type"] == "CD4"
    assert row["clonotype_key"] == "cloneA"
    assert row["sf_cells"] == 10
    assert row["blood_cells"] == 2
    assert row["shared_clone"] == True  # noqa: E712
    assert row["detected_in_sf"] == True  # noqa: E712
    assert row["detected_in_blood"] == True  # noqa: E712
    assert row["sf_sample_group"] == "PM3"
    assert row["blood_sample_group"] == "PM6"


def test_sf_only_clone_sample_group_metadata() -> None:
    df = pd.DataFrame(
        [_clone_row("cloneB", "SF", sample_group="PM3", n_cells=5, n_paired_cells=5)]
    )
    result = build_paired_detection_table(df)
    row = result.iloc[0]

    assert row["sf_cells"] == 5
    assert row["blood_cells"] == 0
    assert row["shared_clone"] == False  # noqa: E712
    assert row["sf_sample_group"] == "PM3"
    assert row["blood_sample_group"] == ""


def test_blood_only_clone_sample_group_metadata() -> None:
    df = pd.DataFrame(
        [_clone_row("cloneC", "blood", sample_group="PM6", n_cells=8, n_paired_cells=8)]
    )
    result = build_paired_detection_table(df)
    row = result.iloc[0]

    assert row["sf_cells"] == 0
    assert row["blood_cells"] == 8
    assert row["shared_clone"] == False  # noqa: E712
    assert row["sf_sample_group"] == ""
    assert row["blood_sample_group"] == "PM6"


def test_multiple_sample_groups_in_one_compartment() -> None:
    df = pd.DataFrame(
        [
            _clone_row("cloneA", "SF", sample_group="PM1", n_cells=3, n_paired_cells=3),
            _clone_row("cloneA", "SF", sample_group="PM3", n_cells=7, n_paired_cells=7),
            _clone_row("cloneA", "blood", sample_group="PM6", n_cells=2, n_paired_cells=2),
        ]
    )
    result = build_paired_detection_table(df)
    row = result.iloc[0]

    assert row["sf_cells"] == 10
    assert row["blood_cells"] == 2
    assert row["sf_sample_group"] == "PM1;PM3"
    assert row["blood_sample_group"] == "PM6"


def test_fractions_use_patient_level_totals_not_sample_group() -> None:
    df = pd.DataFrame(
        [
            _clone_row("cloneA", "SF", sample_group="PM1", n_cells=3, n_paired_cells=3),
            _clone_row("cloneB", "SF", sample_group="PM3", n_cells=7, n_paired_cells=7),
            _clone_row("cloneA", "blood", sample_group="PM6", n_cells=2, n_paired_cells=2),
            _clone_row("cloneC", "blood", sample_group="PM6", n_cells=8, n_paired_cells=8),
        ]
    )
    result = build_paired_detection_table(df)
    clone_a = result.loc[result["clonotype_key"] == "cloneA"].iloc[0]

    assert clone_a["sf_fraction"] == pytest.approx(3 / 10)
    assert clone_a["blood_fraction"] == pytest.approx(2 / 10)


def test_build_paired_detection_table_shared_clone(clone_counts_df: pd.DataFrame) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    result = build_paired_detection_table(df)
    shared = result.loc[result["clonotype_key"] == CLONE_A].iloc[0]

    assert shared["sf_cells"] == 4
    assert shared["blood_cells"] == 2
    assert shared["detected_in_sf"] == True  # noqa: E712
    assert shared["detected_in_blood"] == True  # noqa: E712
    assert shared["shared_clone"] == True  # noqa: E712


def test_build_paired_detection_table_sf_only_clone(clone_counts_df: pd.DataFrame) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    result = build_paired_detection_table(df)
    sf_only = result.loc[result["clonotype_key"] == CLONE_B].iloc[0]

    assert sf_only["sf_cells"] == 3
    assert sf_only["blood_cells"] == 0
    assert sf_only["detected_in_sf"] == True  # noqa: E712
    assert sf_only["detected_in_blood"] == False  # noqa: E712
    assert sf_only["shared_clone"] == False  # noqa: E712


def test_build_paired_detection_table_blood_only_clone(
    clone_counts_df: pd.DataFrame,
) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    result = build_paired_detection_table(df)
    blood_only = result.loc[result["clonotype_key"] == CLONE_C].iloc[0]

    assert blood_only["sf_cells"] == 0
    assert blood_only["blood_cells"] == 5
    assert blood_only["detected_in_sf"] == False  # noqa: E712
    assert blood_only["detected_in_blood"] == True  # noqa: E712
    assert blood_only["shared_clone"] == False  # noqa: E712


def test_build_paired_detection_table_union_not_intersection(
    clone_counts_df: pd.DataFrame,
) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    result = build_paired_detection_table(df)
    assert set(result["clonotype_key"]) == {CLONE_A, CLONE_B, CLONE_C}


def test_build_paired_detection_table_fractions(clone_counts_df: pd.DataFrame) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    totals = calculate_compartment_totals(df)
    sf_total = totals.loc[totals["compartment"] == "SF", "total_cells"].sum()
    blood_total = totals.loc[totals["compartment"] == "blood", "total_cells"].sum()

    result = build_paired_detection_table(df)
    shared = result.loc[result["clonotype_key"] == CLONE_A].iloc[0]

    assert shared["sf_fraction"] == pytest.approx(4 / sf_total)
    assert shared["blood_fraction"] == pytest.approx(2 / blood_total)


def test_build_paired_detection_table_fraction_zero_when_compartment_missing() -> None:
    df = pd.DataFrame(
        [
            _clone_row(CLONE_B, "SF", n_cells=3, n_paired_cells=0, n_tra_only_cells=3),
        ]
    )
    result = build_paired_detection_table(df)
    row = result.iloc[0]
    assert row["sf_fraction"] == pytest.approx(1.0)
    assert row["blood_fraction"] == 0.0


def test_filter_clone_counts_cell_type(clone_counts_df: pd.DataFrame) -> None:
    extended = pd.concat(
        [
            clone_counts_df,
            pd.DataFrame(
                [
                    _clone_row(
                        CLONE_A,
                        "SF",
                        cell_type="CD8",
                        n_cells=1,
                        n_paired_cells=1,
                    )
                ]
            ),
        ],
        ignore_index=True,
    )
    result = filter_clone_counts(extended, cell_type="CD4")
    assert (result["cell_type"] == "CD4").all()


def test_filter_clone_counts_sample_group(clone_counts_df: pd.DataFrame) -> None:
    extended = pd.concat(
        [
            clone_counts_df,
            pd.DataFrame(
                [
                    _clone_row(
                        CLONE_A,
                        "SF",
                        sample_group="PM2",
                        n_cells=1,
                        n_paired_cells=1,
                    )
                ]
            ),
        ],
        ignore_index=True,
    )
    result = filter_clone_counts(extended, sample_group="PM1")
    assert (result["sample_group"] == "PM1").all()


def test_filter_clone_counts_min_cells(clone_counts_df: pd.DataFrame) -> None:
    df = clone_counts_df.loc[clone_counts_df["patient"] == "p1"].copy()
    df["compartment"] = df["compartment"].map(normalize_compartment)
    df = df.loc[df["compartment"].notna() & (df["clonotype_key"] != CLONE_D)]

    filtered = filter_clone_counts(df, min_cells=3)
    result = build_paired_detection_table(filtered, min_cells=3)

    assert CLONE_D not in set(result["clonotype_key"])
    assert CLONE_B in set(result["clonotype_key"])
    assert CLONE_C in set(result["clonotype_key"])
    assert CLONE_A in set(result["clonotype_key"])


def test_build_paired_detection_table_normalizes_aliases() -> None:
    df = pd.DataFrame(
        [
            _clone_row(CLONE_A, "SynovialFluid", n_cells=2, n_paired_cells=2, patient="p2"),
            _clone_row(CLONE_B, "PB", n_cells=3, n_paired_cells=0, n_tra_only_cells=3, patient="p2"),
        ]
    )
    df["compartment"] = df["compartment"].map(normalize_compartment)
    result = build_paired_detection_table(df)

    assert list(result.columns) == DETECTION_TABLE_COLUMNS
    assert len(result) == 2
    assert result.loc[result["clonotype_key"] == CLONE_A, "sf_cells"].iloc[0] == 2
    assert result.loc[result["clonotype_key"] == CLONE_B, "blood_cells"].iloc[0] == 3


def test_warning_for_unsupported_compartment(capsys: pytest.CaptureFixture[str]) -> None:
    from tcr_bcr_tools.build_detection_table import _normalize_compartments

    df = pd.DataFrame([_clone_row(CLONE_A, "tissue", n_cells=1, n_paired_cells=1)])
    result = _normalize_compartments(df)
    assert result.empty
    assert "Warning: ignoring unsupported compartment 'tissue'" in capsys.readouterr().out
