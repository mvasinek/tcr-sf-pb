"""Tests for filename metadata parsing."""

import pytest

from tcr_bcr_tools.metadata import parse_filename_metadata


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz",
            {
                "gsm_id": "GSM4859841",
                "sample_group": "PM1",
                "cell_type": "CD4",
                "compartment": "SF",
                "patient": "p7",
            },
        ),
        (
            "GSM4859842_PM4_CD4_blood_p1_filtered_contig_annotations.csv.gz",
            {
                "gsm_id": "GSM4859842",
                "sample_group": "PM4",
                "cell_type": "CD4",
                "compartment": "blood",
                "patient": "p1",
            },
        ),
        (
            "/data/nested/GSM4859835_PM1_CD4_SF_p1_filtered_contig_annotations.csv.gz",
            {
                "gsm_id": "GSM4859835",
                "sample_group": "PM1",
                "cell_type": "CD4",
                "compartment": "SF",
                "patient": "p1",
            },
        ),
    ],
)
def test_parse_filename_metadata(filename: str, expected: dict[str, str]) -> None:
    assert parse_filename_metadata(filename) == expected


def test_parse_filename_metadata_invalid_name() -> None:
    with pytest.raises(ValueError):
        parse_filename_metadata("invalid_file.csv.gz")
