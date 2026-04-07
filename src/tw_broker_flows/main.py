from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any

from .broker_lookup import (
    DEFAULT_PAGE_URL,
    build_lookup_from_branch_rows,
    build_target_urls,
    fetch_lookup,
    iter_branch_rows,
    iter_company_rows,
    load_lookup_from_path,
    merge_lookup_data,
)
from .fetcher import fetch_url
from .parser import ParseError, parse_page
from .storage import (
    build_branch_reference_path,
    build_broker_reference_path,
    build_processed_csv_path,
    build_raw_html_path,
    ensure_output_dirs,
    write_branch_reference_csv,
    write_broker_reference_csv,
    write_csv,
    write_raw_html,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape Taiwan broker branch stock flow rankings.")
    parser.add_argument("--url", action="append", dest="urls", help="Source URL to scrape. Can be repeated.")
    parser.add_argument("--targets-file", help="JSON file with a top-level 'targets' list or a plain list of URLs.")
    parser.add_argument(
        "--branch-codes-file",
        help="CSV file with columns 券商中文, 分行中文, code1, code2. The scraper will build daily URLs from these rows.",
    )
    parser.add_argument("--start-date", help="Daily query start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", help="Daily query end date in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", default="data", help="Output directory. Defaults to ./data")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--lookup-js", help="Path to a local zbrokerjs.djjs file.")
    parser.add_argument("--skip-lookup", action="store_true", help="Do not resolve broker/branch names.")
    parser.add_argument(
        "--all-branches",
        action="store_true",
        help="Generate daily scrape targets from the full broker/branch lookup instead of hand-written URLs.",
    )
    parser.add_argument(
        "--metric-type",
        choices=["amount", "lots", "both"],
        default="amount",
        help="Metric type for generated daily targets.",
    )
    parser.add_argument("--base-url", default=DEFAULT_PAGE_URL, help="Base page URL used for lookup fetch and generated targets.")
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="Delay between requests. Useful for batch scans.")
    parser.add_argument("--max-targets", type=int, help="Optional limit for generated targets.")
    parser.add_argument("--export-lookup-only", action="store_true", help="Only export brokers/branches reference CSVs and exit.")
    return parser


def load_target_urls(cli_urls: list[str] | None, targets_file: str | None) -> list[str]:
    urls = list(cli_urls or [])
    if not targets_file:
        return urls

    payload = json.loads(Path(targets_file).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        urls.extend(item for item in payload if isinstance(item, str))
    elif isinstance(payload, dict):
        targets = payload.get("targets", [])
        for item in targets:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict) and isinstance(item.get("url"), str):
                urls.append(item["url"])
    return urls


def normalize_branch_source_row(row: dict[str, str]) -> dict[str, object]:
    broker_name = (row.get("券商中文") or row.get("broker_name") or "").strip()
    branch_name = (row.get("分行中文") or row.get("branch_name") or "").strip()
    code1 = (row.get("code1") or row.get("broker_code") or "").strip()
    code2 = (row.get("code2") or row.get("branch_code_raw") or row.get("branch_code") or "").strip()
    is_broker_level_raw = (row.get("is_broker_level") or "").strip().lower()

    normalized_row: dict[str, object] = {
        "券商中文": broker_name,
        "分行中文": branch_name,
        "code1": code1,
        "code2": code2,
    }

    if is_broker_level_raw:
        normalized_row["is_broker_level"] = is_broker_level_raw == "true"

    return normalized_row


def load_branch_code_rows(branch_codes_file: str | None) -> list[dict[str, object]]:
    if not branch_codes_file:
        return []

    rows: list[dict[str, object]] = []
    with Path(branch_codes_file).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for line_number, row in enumerate(reader, start=2):
            normalized_row = normalize_branch_source_row(row)
            code1 = str(normalized_row.get("code1", "")).strip()
            code2 = str(normalized_row.get("code2", "")).strip()

            if not any(str(value).strip() for value in row.values()):
                continue

            if not code1 or not code2:
                raise ValueError(f"Invalid branch codes row at line {line_number}: code1/code2 are required.")

            rows.append(normalized_row)

    return rows


def configure_logging(output_root: Path) -> Path:
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def parse_iso_date(value: str, label: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"{label} must be in YYYY-MM-DD format: {value}") from exc


def resolve_date_range(args: argparse.Namespace) -> tuple[str, str]:
    if not args.start_date or not args.end_date:
        raise ValueError("Generated daily targets require both --start-date and --end-date.")

    start_date = parse_iso_date(args.start_date, "start_date")
    end_date = parse_iso_date(args.end_date, "end_date")
    if start_date > end_date:
        raise ValueError(f"start_date must be <= end_date: {start_date} > {end_date}")

    return start_date, end_date


def load_lookup(urls: list[str], args: argparse.Namespace, branch_rows: list[dict[str, object]]) -> Any:
    broker_lookup = None
    if not args.skip_lookup:
        if args.lookup_js:
            broker_lookup = load_lookup_from_path(args.lookup_js)
        else:
            lookup_source_url = urls[0] if urls else args.base_url
            try:
                broker_lookup = fetch_lookup(lookup_source_url, timeout=args.timeout)
            except Exception as exc:  # pragma: no cover - network-path fallback
                logging.warning("Lookup JS fetch failed, continuing with codes only: %s", exc)

    if branch_rows:
        broker_lookup = merge_lookup_data(broker_lookup, build_lookup_from_branch_rows(branch_rows))

    return broker_lookup


def export_lookup_reference(output_root: Path, broker_lookup: Any) -> tuple[Path, Path] | None:
    if broker_lookup is None:
        return None

    fetched_at = datetime.now(timezone.utc).isoformat()
    broker_rows = []
    for row in iter_company_rows(broker_lookup):
        broker_rows.append({**row, "fetched_at": fetched_at})

    branch_rows = []
    for row in iter_branch_rows(broker_lookup):
        branch_rows.append({**row, "fetched_at": fetched_at})

    broker_path = build_broker_reference_path(output_root)
    branch_path = build_branch_reference_path(output_root)
    write_broker_reference_csv(broker_path, broker_rows)
    write_branch_reference_csv(branch_path, branch_rows)
    return broker_path, branch_path


def build_generated_urls(
    branch_rows: list[dict[str, object]],
    start_date: str,
    end_date: str,
    args: argparse.Namespace,
) -> list[str]:
    metric_types = ["amount", "lots"] if args.metric_type == "both" else [args.metric_type]
    urls: list[str] = []
    seen: set[str] = set()

    for metric_type in metric_types:
        for url in build_target_urls(
            branch_rows=branch_rows,
            start_date=start_date,
            end_date=end_date,
            base_url=args.base_url,
            metric_type=metric_type,
        ):
            if url not in seen:
                urls.append(url)
                seen.add(url)

    if args.max_targets is not None:
        return urls[: args.max_targets]
    return urls


def deduplicate_urls(urls: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            deduplicated.append(url)
            seen.add(url)
    return deduplicated


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    output_root = Path(args.output_dir)
    ensure_output_dirs(output_root)
    log_path = configure_logging(output_root)

    urls = load_target_urls(args.urls, args.targets_file)
    branch_rows_from_file = load_branch_code_rows(args.branch_codes_file)
    broker_lookup = load_lookup(urls, args, branch_rows_from_file)

    exported_reference = export_lookup_reference(output_root, broker_lookup)
    if exported_reference is not None:
        broker_path, branch_path = exported_reference
        logging.info(
            "Exported broker reference: brokers=%s branches=%s -> %s, %s",
            len(iter_company_rows(broker_lookup)),
            len(iter_branch_rows(broker_lookup)),
            broker_path,
            branch_path,
        )

    if args.export_lookup_only:
        logging.info("Finished lookup export only. log=%s", log_path)
        return 0

    generated_branch_rows: list[dict[str, object]] = []
    if args.all_branches:
        if broker_lookup is None:
            parser.error("All-branch daily scan requires a broker lookup. Use --lookup-js or allow lookup fetch.")
        generated_branch_rows = iter_branch_rows(broker_lookup)
        logging.info("Loaded %s broker/branch rows from lookup for daily target generation", len(generated_branch_rows))

    branch_target_rows = [*branch_rows_from_file, *generated_branch_rows]
    if branch_target_rows:
        try:
            start_date, end_date = resolve_date_range(args)
        except ValueError as exc:
            parser.error(str(exc))

        generated_urls = build_generated_urls(branch_target_rows, start_date, end_date, args)
        urls.extend(generated_urls)
        logging.info(
            "Generated %s daily targets for %s branch rows from %s to %s",
            len(generated_urls),
            len(branch_target_rows),
            start_date,
            end_date,
        )

    urls = deduplicate_urls(urls)
    if not urls:
        parser.error("No target URLs provided. Use --url, --targets-file, --branch-codes-file, or --all-branches.")

    logging.info("Starting scrape for %s targets", len(urls))

    failures = 0
    for index, url in enumerate(urls, start=1):
        try:
            fetch_result = fetch_url(url, timeout=args.timeout)
            parsed = parse_page(
                html_text=fetch_result["text"],
                source_url=url,
                fetched_at=fetch_result["fetched_at"],
                broker_lookup=broker_lookup,
            )

            trade_date = parsed["trade_date"]
            branch_code = parsed["branch_code"]
            metric_type = parsed["metric_type"]
            raw_path = build_raw_html_path(output_root, trade_date, url, branch_code, metric_type)
            csv_path = build_processed_csv_path(output_root, trade_date, url, branch_code, metric_type)

            write_raw_html(raw_path, fetch_result["content"])
            write_csv(csv_path, parsed["records"])

            logging.info(
                "[%s/%s] Parsed %s rows for branch=%s metric=%s trade_date=%s -> %s",
                index,
                len(urls),
                len(parsed["records"]),
                branch_code,
                metric_type,
                trade_date,
                csv_path,
            )
        except ParseError as exc:
            failures += 1
            logging.exception("[%s/%s] Parse failed for %s: %s", index, len(urls), url, exc)
        except Exception as exc:  # pragma: no cover - network-path fallback
            failures += 1
            logging.exception("[%s/%s] Fetch failed for %s: %s", index, len(urls), url, exc)

        if args.delay_seconds > 0 and index < len(urls):
            time.sleep(args.delay_seconds)

    logging.info("Finished. failures=%s log=%s", failures, log_path)
    return 1 if failures else 0
