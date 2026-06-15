"""Tests for cell receptor and clone count table generation."""

import pandas as pd
import pytest

from tcr_bcr_tools.build_clonotypes import (
    CLONE_COUNT_COLUMNS,
    CELL_RECEPTOR_COLUMNS,
    build_cell_receptors,
    build_clone_counts,
    build_clonotype_key,
    filter_productive_tcr_contigs,
    select_dominant_chain,
)

SOURCE = "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz"
METADATA = {
    "source_file": SOURCE,
    "gsm_id": "GSM4859841",
    "sample_group": "PM1",
    "cell_type": "CD4",
    "compartment": "SF",
    "patient": "p7",
}


def _contig_row(
    barcode: str,
    chain: str,
    *,
    cdr3: str | None = "CAVSDYGQNFVF",
    umis: int = 5,
    reads: int = 100,
    v_gene: str = "TRAV1",
    j_gene: str = "TRAJ1",
    is_cell: bool = True,
    high_confidence: bool = True,
    full_length: bool = True,
    productive: bool = True,
) -> dict:
    return {
        **METADATA,
        "barcode": barcode,
        "is_cell": is_cell,
        "contig_id": f"{barcode}_contig",
        "high_confidence": high_confidence,
        "length": 500,
        "chain": chain,
        "v_gene": v_gene,
        "d_gene": None,
        "j_gene": j_gene,
        "c_gene": "TRAC" if chain == "TRA" else "TRBC1",
        "full_length": full_length,
        "productive": productive,
        "cdr3": cdr3,
        "cdr3_nt": "TGTGCTGTGAGTGATGATGGGCAATTTTGTGTTT",
        "reads": reads,
        "umis": umis,
        "raw_clonotype_id": "clonotype1",
        "raw_consensus_id": "clonotype1_consensus_1",
    }


@pytest.fixture
def annotation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _contig_row("CELL-1", "TRA", cdr3="CAAA", umis=10, reads=100, v_gene="TRAV1", j_gene="TRAJ1"),
            _contig_row("CELL-1", "TRA", cdr3="CABB", umis=5, reads=200, v_gene="TRAV2", j_gene="TRAJ2"),
            _contig_row("CELL-1", "TRB", cdr3="CASS1", umis=8, reads=80, v_gene="TRBV1", j_gene="TRBJ1"),
            _contig_row("CELL-1", "TRB", cdr3="CASS2", umis=12, reads=60, v_gene="TRBV2", j_gene="TRBJ2"),
            _contig_row("CELL-2", "TRA", cdr3="CACC", umis=7, reads=70),
            _contig_row("CELL-3", "TRB", cdr3="CASS3", umis=6, reads=60, v_gene="TRBV3", j_gene="TRBJ3"),
            _contig_row("CELL-4", "TRA", cdr3=None, productive=False),
            _contig_row("CELL-5", "Multi", cdr3=None, productive=None, full_length=False),
            _contig_row("CELL-6", "TRA", cdr3="CADD", umis=4, reads=40),
            _contig_row("CELL-6", "TRA", cdr3="CADD", umis=4, reads=50),
            _contig_row("CELL-6", "TRA", cdr3="CADE", umis=4, reads=50),
        ]
    )


def test_filter_productive_tcr_contigs(annotation_df: pd.DataFrame) -> None:
    filtered = filter_productive_tcr_contigs(annotation_df)
    assert set(filtered["barcode"]) == {"CELL-1", "CELL-2", "CELL-3", "CELL-6"}
    assert set(filtered["chain"]) == {"TRA", "TRB"}
    assert filtered["cdr3"].notna().all()


def test_select_dominant_chain_by_umis(annotation_df: pd.DataFrame) -> None:
    filtered = filter_productive_tcr_contigs(annotation_df)
    tra = select_dominant_chain(filtered, "TRA")
    trb = select_dominant_chain(filtered, "TRB")

    cell1_tra = tra.loc[tra["barcode"] == "CELL-1"].iloc[0]
    cell1_trb = trb.loc[trb["barcode"] == "CELL-1"].iloc[0]
    assert cell1_tra["cdr3"] == "CAAA"
    assert cell1_trb["cdr3"] == "CASS2"


def test_select_dominant_chain_tie_break_reads(annotation_df: pd.DataFrame) -> None:
    filtered = filter_productive_tcr_contigs(annotation_df)
    tra = select_dominant_chain(filtered, "TRA")
    cell6_tra = tra.loc[tra["barcode"] == "CELL-6"].iloc[0]
    assert cell6_tra["reads"] == 50
    assert cell6_tra["cdr3"] == "CADD"


def test_select_dominant_chain_tie_break_cdr3(annotation_df: pd.DataFrame) -> None:
    filtered = filter_productive_tcr_contigs(annotation_df)
    tied = filtered.loc[filtered["barcode"] == "CELL-6"].copy()
    tied = tied.loc[tied["reads"] == 50]
    assert len(tied) == 2
    tra = select_dominant_chain(filtered, "TRA")
    cell6_tra = tra.loc[tra["barcode"] == "CELL-6"].iloc[0]
    assert cell6_tra["cdr3"] == "CADD"


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            {
                "has_tra": True,
                "has_trb": True,
                "tra_v_gene": "TRAV1",
                "tra_j_gene": "TRAJ1",
                "tra_cdr3": "CAAA",
                "trb_v_gene": "TRBV2",
                "trb_j_gene": "TRBJ2",
                "trb_cdr3": "CASS2",
            },
            "TRA:TRAV1|TRAJ1|CAAA__TRB:TRBV2|TRBJ2|CASS2",
        ),
        (
            {
                "has_tra": True,
                "has_trb": False,
                "tra_v_gene": "TRAV1",
                "tra_j_gene": "TRAJ1",
                "tra_cdr3": "CACC",
                "trb_v_gene": pd.NA,
                "trb_j_gene": pd.NA,
                "trb_cdr3": pd.NA,
            },
            "TRA:TRAV1|TRAJ1|CACC__TRB:missing",
        ),
        (
            {
                "has_tra": False,
                "has_trb": True,
                "tra_v_gene": pd.NA,
                "tra_j_gene": pd.NA,
                "tra_cdr3": pd.NA,
                "trb_v_gene": "TRBV3",
                "trb_j_gene": "TRBJ3",
                "trb_cdr3": "CASS3",
            },
            "TRA:missing__TRB:TRBV3|TRBJ3|CASS3",
        ),
    ],
)
def test_build_clonotype_key(row: dict, expected: str) -> None:
    assert build_clonotype_key(pd.Series(row)) == expected


def test_build_cell_receptors(annotation_df: pd.DataFrame) -> None:
    result = build_cell_receptors(annotation_df)
    assert list(result.columns) == CELL_RECEPTOR_COLUMNS
    assert len(result) == 4

    cell1 = result.loc[result["barcode"] == "CELL-1"].iloc[0]
    assert cell1["tra_cdr3"] == "CAAA"
    assert cell1["trb_cdr3"] == "CASS2"
    assert cell1["has_tra"] is True or cell1["has_tra"] == True  # noqa: E712
    assert cell1["has_trb"] is True or cell1["has_trb"] == True  # noqa: E712
    assert cell1["is_paired"] is True or cell1["is_paired"] == True  # noqa: E712
    assert cell1["clonotype_key"] == "TRA:TRAV1|TRAJ1|CAAA__TRB:TRBV2|TRBJ2|CASS2"

    cell2 = result.loc[result["barcode"] == "CELL-2"].iloc[0]
    assert cell2["has_tra"] is True or cell2["has_tra"] == True  # noqa: E712
    assert cell2["has_trb"] is False or cell2["has_trb"] == False  # noqa: E712
    assert cell2["clonotype_key"] == "TRA:TRAV1|TRAJ1|CACC__TRB:missing"

    cell3 = result.loc[result["barcode"] == "CELL-3"].iloc[0]
    assert cell3["has_tra"] is False or cell3["has_tra"] == False  # noqa: E712
    assert cell3["has_trb"] is True or cell3["has_trb"] == True  # noqa: E712
    assert cell3["clonotype_key"] == "TRA:missing__TRB:TRBV3|TRBJ3|CASS3"


def test_build_clone_counts(annotation_df: pd.DataFrame) -> None:
    cell_df = build_cell_receptors(annotation_df)
    result = build_clone_counts(cell_df)

    assert list(result.columns) == CLONE_COUNT_COLUMNS
    assert len(result) == 4

    paired = result.loc[
        result["clonotype_key"] == "TRA:TRAV1|TRAJ1|CAAA__TRB:TRBV2|TRBJ2|CASS2"
    ].iloc[0]
    assert paired["n_cells"] == 1
    assert paired["n_paired_cells"] == 1
    assert paired["n_tra_only_cells"] == 0
    assert paired["n_trb_only_cells"] == 0

    tra_only = result.loc[
        result["clonotype_key"] == "TRA:TRAV1|TRAJ1|CACC__TRB:missing"
    ].iloc[0]
    assert tra_only["n_cells"] == 1
    assert tra_only["n_paired_cells"] == 0
    assert tra_only["n_tra_only_cells"] == 1
    assert tra_only["n_trb_only_cells"] == 0


def test_build_clone_counts_paired_only(annotation_df: pd.DataFrame) -> None:
    cell_df = build_cell_receptors(annotation_df)
    result = build_clone_counts(cell_df, paired_only=True)

    assert len(result) == 1
    assert result.iloc[0]["n_cells"] == 1
    assert result.iloc[0]["n_paired_cells"] == 1
    assert result.iloc[0]["n_tra_only_cells"] == 0
    assert result.iloc[0]["n_trb_only_cells"] == 0
