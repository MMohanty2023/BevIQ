import pandas as pd

from tools.optimize_csv import optimize_csv_file


def test_optimize_csv_preserves_source_and_deduplicates_to_separate_file(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "optimized.csv"
    pd.DataFrame([
        {"id": "001", "name": "A", "unused": "x"},
        {"id": "001", "name": "A", "unused": "x"},
        {"id": "002", "name": "B", "unused": "y"},
    ]).to_csv(source, index=False)
    original_bytes = source.read_bytes()

    result = optimize_csv_file(
        source,
        output,
        delimiter=",",
        columns=["id", "name"],
        dedupe_columns=["id"],
        chunksize=2,
    )

    assert source.read_bytes() == original_bytes
    assert result["source_rows"] == 3
    assert result["output_rows"] == 2
    assert result["duplicates_removed"] == 1
    optimized = pd.read_csv(output, dtype=str)
    assert list(optimized.columns) == ["id", "name"]
    assert optimized["id"].tolist() == ["001", "002"]


def test_optimize_csv_rejects_unknown_requested_column(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("id,name\n001,A\n", encoding="utf-8")

    try:
        optimize_csv_file(source, tmp_path / "optimized.csv", columns=["missing"])
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("unknown columns should fail clearly")
