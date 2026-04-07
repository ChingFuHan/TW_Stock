from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import parse_qs, urlparse


CSV_FIELDNAMES = [
    "trade_date",
    "broker_code",
    "branch_code",
    "branch_code_raw",
    "broker_name",
    "branch_name",
    "stock_code",
    "stock_name",
    "buy_lots",
    "sell_lots",
    "net_lots",
    "buy_amount",
    "sell_amount",
    "net_amount",
    "metric_type",
    "unit_label",
    "rank_side",
    "rank_order",
    "lookback_days",
    "lookback_label",
    "column_1_label",
    "column_2_label",
    "column_3_label",
    "column_4_label",
    "source_url",
    "fetched_at",
]

BROKER_REFERENCE_FIELDNAMES = [
    "券商中文",
    "code1",
    "分行數",
    "fetched_at",
]

BRANCH_REFERENCE_FIELDNAMES = [
    "券商中文",
    "分行中文",
    "code1",
    "code2",
    "is_broker_level",
    "fetched_at",
]


def ensure_output_dirs(output_root: Path) -> None:
    (output_root / "raw").mkdir(parents=True, exist_ok=True)
    (output_root / "processed").mkdir(parents=True, exist_ok=True)
    (output_root / "logs").mkdir(parents=True, exist_ok=True)
    (output_root / "reference").mkdir(parents=True, exist_ok=True)


def target_slug(source_url: str, branch_code: str | None, metric_type: str | None) -> str:
    query = parse_qs(urlparse(source_url).query)
    parts: list[str] = []
    if branch_code:
        parts.append(branch_code)
    if metric_type:
        parts.append(metric_type)

    for key in ("a", "b", "c", "d", "e", "f"):
        value = query.get(key, [None])[0]
        if value:
            safe_value = value.replace(":", "-")
            parts.append(f"{key}-{safe_value}")

    return "__".join(parts) if parts else "target"


def build_raw_html_path(output_root: Path, trade_date: str | None, source_url: str, branch_code: str | None, metric_type: str | None) -> Path:
    date_part = (trade_date or "unknown-date").replace("-", "")
    folder = output_root / "raw" / date_part
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{target_slug(source_url, branch_code, metric_type)}.html"


def build_processed_csv_path(output_root: Path, trade_date: str | None, source_url: str, branch_code: str | None, metric_type: str | None) -> Path:
    date_part = (trade_date or "unknown-date").replace("-", "")
    folder = output_root / "processed" / date_part
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{target_slug(source_url, branch_code, metric_type)}.csv"


def write_raw_html(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def write_dict_csv(path: Path, fieldnames: list[str], records: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    write_dict_csv(path, CSV_FIELDNAMES, records)


def build_broker_reference_path(output_root: Path) -> Path:
    return output_root / "reference" / "brokers.csv"


def build_branch_reference_path(output_root: Path) -> Path:
    return output_root / "reference" / "branches.csv"


def write_broker_reference_csv(path: Path, rows: list[dict[str, object]]) -> None:
    write_dict_csv(path, BROKER_REFERENCE_FIELDNAMES, rows)


def write_branch_reference_csv(path: Path, rows: list[dict[str, object]]) -> None:
    write_dict_csv(path, BRANCH_REFERENCE_FIELDNAMES, rows)
