"""Create smaller, safe CSV derivatives without modifying source datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


def optimize_csv_file(
    source: Path,
    destination: Path,
    delimiter: str = ",",
    columns: list[str] | None = None,
    dedupe_columns: list[str] | None = None,
    chunksize: int = 25_000,
) -> dict:
    source = Path(source)
    destination = Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    if chunksize < 1:
        raise ValueError("chunksize must be positive")

    destination.parent.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, ...]] = set()
    source_rows = 0
    output_rows = 0
    duplicates_removed = 0
    selected_columns = list(columns) if columns else None

    temp_path = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False,
                                dir=destination.parent, suffix=".tmp") as temp:
            temp_path = Path(temp.name)
            wrote_header = False
            for chunk in pd.read_csv(source, sep=delimiter, dtype=str, chunksize=chunksize):
                source_rows += len(chunk)
                if selected_columns is None:
                    selected_columns = list(chunk.columns)
                missing = [column for column in selected_columns if column not in chunk.columns]
                if missing:
                    raise ValueError(f"Requested columns not found: {', '.join(missing)}")

                chunk = chunk[selected_columns].fillna("")
                if dedupe_columns:
                    missing_keys = [column for column in dedupe_columns if column not in chunk.columns]
                    if missing_keys:
                        raise ValueError(f"Deduplication columns not found: {', '.join(missing_keys)}")
                    keep_rows = []
                    for row in chunk[dedupe_columns].itertuples(index=False, name=None):
                        key = tuple(str(value) for value in row)
                        if key in seen:
                            keep_rows.append(False)
                            duplicates_removed += 1
                        else:
                            seen.add(key)
                            keep_rows.append(True)
                    chunk = chunk.loc[keep_rows]

                if not chunk.empty:
                    chunk.to_csv(temp, index=False, header=not wrote_header)
                    wrote_header = True
                    output_rows += len(chunk)
            if not wrote_header:
                raise ValueError("CSV contains no readable rows")
            temp.flush()
    except Exception:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        raise

    assert temp_path is not None
    temp_path.replace(destination)
    return {
        "source": str(source),
        "destination": str(destination),
        "source_rows": source_rows,
        "output_rows": output_rows,
        "duplicates_removed": duplicates_removed,
        "source_bytes": source.stat().st_size,
        "output_bytes": destination.stat().st_size,
        "columns": selected_columns or [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--columns", help="Comma-separated columns to retain")
    parser.add_argument("--dedupe", help="Comma-separated columns used for stable deduplication")
    args = parser.parse_args()
    result = optimize_csv_file(
        args.source,
        args.destination,
        delimiter=args.delimiter,
        columns=args.columns.split(",") if args.columns else None,
        dedupe_columns=args.dedupe.split(",") if args.dedupe else None,
    )
    print(result)


if __name__ == "__main__":
    main()
