"""Parse sample metadata from annotation filenames."""

from pathlib import Path


def parse_filename_metadata(filename: str) -> dict[str, str]:
    """Extract GEO and sample metadata from an annotation filename.

    Expected pattern:
    GSM4859841_PM1_CD4_SF_p7_filtered_contig_annotations.csv.gz
    """
    stem = Path(filename).name
    if stem.endswith(".csv.gz"):
        stem = stem[: -len(".csv.gz")]
    elif stem.endswith(".csv"):
        stem = stem[: -len(".csv")]

    suffix = "_filtered_contig_annotations"
    if not stem.endswith(suffix):
        raise ValueError(
            f"Filename does not match expected pattern '*_filtered_contig_annotations.csv.gz': {filename}"
        )

    prefix = stem[: -len(suffix)]
    parts = prefix.split("_")
    if len(parts) < 5:
        raise ValueError(
            f"Filename does not contain enough metadata fields: {filename}"
        )

    gsm_id, sample_group, cell_type, compartment, patient = parts[:5]
    return {
        "gsm_id": gsm_id,
        "sample_group": sample_group,
        "cell_type": cell_type,
        "compartment": compartment,
        "patient": patient,
    }
