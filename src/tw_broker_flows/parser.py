from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlparse

from .broker_lookup import LookupData, normalize_branch_code, resolve_names


GEN_FUND_COMBO_PATTERN = re.compile(r"GenFundCorpCombo\('([^']*)','([^']*)','frm'\)")
LOOKBACK_PATTERN = re.compile(r'name="S1".*?<option value="(\d+)" selected>([^<]+)</option>', re.S)
TRADE_DATE_PATTERN = re.compile(r"資料日期：(\d{8})")
UNIT_PATTERN = re.compile(r"單位：([^／<\s]+)")
STOCK_SCRIPT_PATTERN = re.compile(r"GenLink2stk\('AS([^']+)','([^']+)'\)")
DIRECT_STOCK_PATTERN = re.compile(r"^([0-9A-Z]{4,6})\s*(.+)$")


class ParseError(Exception):
    """Raised when the expected page structure cannot be parsed."""


@dataclass
class TableNode:
    attrs: dict[str, str]
    rows: list[list[list[str]]] = field(default_factory=list)
    children: list["TableNode"] = field(default_factory=list)


class NestedTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root_tables: list[TableNode] = []
        self._stack: list[TableNode] = []
        self._current_row: list[list[str]] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        normalized_attrs = {key: value or "" for key, value in attrs}

        if normalized_tag == "table":
            node = TableNode(attrs=normalized_attrs)
            if self._stack:
                self._stack[-1].children.append(node)
            else:
                self.root_tables.append(node)
            self._stack.append(node)
        elif normalized_tag == "tr" and self._stack:
            self._current_row = []
            self._stack[-1].rows.append(self._current_row)
        elif normalized_tag in {"td", "th"} and self._stack and self._current_row is not None:
            self._current_cell = []
            self._current_row.append(self._current_cell)

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"td", "th"}:
            self._current_cell = None
        elif normalized_tag == "tr":
            self._current_row = None
        elif normalized_tag == "table" and self._stack:
            self._stack.pop()


def flatten_tables(tables: list[TableNode]) -> list[TableNode]:
    flattened: list[TableNode] = []
    for table in tables:
        flattened.append(table)
        flattened.extend(flatten_tables(table.children))
    return flattened


def normalize_cell(cell_chunks: list[str]) -> str:
    return " ".join("".join(cell_chunks).replace("\xa0", " ").split())


def parse_trade_date(text: str) -> str | None:
    match = TRADE_DATE_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1)
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def parse_unit_label(text: str) -> str | None:
    match = UNIT_PATTERN.search(text)
    return match.group(1) if match else None


def parse_metric_type(text: str) -> str:
    if 'value="B"  checked' in text or 'value="B" checked' in text:
        return "amount"
    if 'value="E"  checked' in text or 'value="E" checked' in text:
        return "lots"
    if "買進金額" in text:
        return "amount"
    if "買進張數" in text:
        return "lots"
    raise ParseError("Could not determine metric type from page.")


def parse_selected_codes(text: str, source_url: str) -> tuple[str | None, str | None]:
    combo_match = GEN_FUND_COMBO_PATTERN.search(text)
    if combo_match:
        return combo_match.group(1), combo_match.group(2)

    query = parse_qs(urlparse(source_url).query)
    broker_code = query.get("a", [None])[0]
    branch_code = query.get("b", [None])[0]
    return broker_code, branch_code


def parse_lookback(text: str) -> tuple[str | None, str | None]:
    match = LOOKBACK_PATTERN.search(text)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def parse_number(value: str) -> int | None:
    cleaned = value.replace(",", "").strip()
    if not cleaned or cleaned in {"--", "N/A"}:
        return None
    return int(cleaned)


def parse_stock_identity(cell_text: str) -> tuple[str | None, str | None]:
    script_match = STOCK_SCRIPT_PATTERN.search(cell_text)
    if script_match:
        return script_match.group(1), script_match.group(2)

    direct_text = cell_text.strip()
    direct_match = DIRECT_STOCK_PATTERN.match(direct_text)
    if direct_match:
        return direct_match.group(1), direct_match.group(2).strip()

    if direct_text:
        return None, direct_text

    return None, None


def find_rank_tables(html_text: str) -> list[tuple[str, list[str], TableNode]]:
    parser = NestedTableParser()
    parser.feed(html_text)

    candidates: list[tuple[str, list[str], TableNode]] = []
    for table in flatten_tables(parser.root_tables):
        if len(table.rows) < 3:
            continue

        header_1 = [normalize_cell(cell) for cell in table.rows[0] if normalize_cell(cell)]
        header_2 = [normalize_cell(cell) for cell in table.rows[1] if normalize_cell(cell)]

        if len(header_1) != 1 or len(header_2) != 4:
            continue

        section_label = header_1[0]
        if section_label not in {"買超", "賣超"}:
            continue

        if "差額" not in header_2:
            continue

        candidates.append((section_label, header_2, table))

    if len(candidates) < 2:
        raise ParseError("Could not find the expected buy/sell rank tables.")

    return candidates


def parse_page(
    html_text: str,
    source_url: str,
    fetched_at: str,
    broker_lookup: LookupData | None = None,
) -> dict[str, object]:
    trade_date = parse_trade_date(html_text)
    unit_label = parse_unit_label(html_text)
    metric_type = parse_metric_type(html_text)
    broker_code, branch_code_raw = parse_selected_codes(html_text, source_url)
    branch_code = normalize_branch_code(branch_code_raw)
    lookback_days, lookback_label = parse_lookback(html_text)

    broker_name = None
    branch_name = None
    if broker_lookup is not None:
        broker_name, branch_name = resolve_names(broker_lookup, broker_code, branch_code_raw)

    records: list[dict[str, object]] = []

    for section_label, column_labels, table in find_rank_tables(html_text):
        rank_side = "buy_over" if section_label == "買超" else "sell_over"
        rank_order = 0
        for row in table.rows[2:]:
            if len(row) != 4:
                continue

            cells = [normalize_cell(cell) for cell in row]
            stock_code, stock_name = parse_stock_identity(cells[0])
            buy_value = parse_number(cells[1])
            sell_value = parse_number(cells[2])
            net_value = parse_number(cells[3])

            if stock_name is None and stock_code is None:
                continue

            if section_label == "賣超" and net_value is not None and net_value > 0:
                net_value = -net_value
            if section_label == "買超" and net_value is not None and net_value < 0:
                net_value = abs(net_value)

            rank_order += 1
            record: dict[str, object] = {
                "trade_date": trade_date,
                "broker_code": broker_code,
                "branch_code": branch_code,
                "branch_code_raw": branch_code_raw,
                "broker_name": broker_name,
                "branch_name": branch_name,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "buy_lots": buy_value if metric_type == "lots" else None,
                "sell_lots": sell_value if metric_type == "lots" else None,
                "net_lots": net_value if metric_type == "lots" else None,
                "buy_amount": buy_value if metric_type == "amount" else None,
                "sell_amount": sell_value if metric_type == "amount" else None,
                "net_amount": net_value if metric_type == "amount" else None,
                "metric_type": metric_type,
                "unit_label": unit_label,
                "rank_side": rank_side,
                "rank_order": rank_order,
                "lookback_days": lookback_days,
                "lookback_label": lookback_label,
                "column_1_label": column_labels[0],
                "column_2_label": column_labels[1],
                "column_3_label": column_labels[2],
                "column_4_label": column_labels[3],
                "source_url": source_url,
                "fetched_at": fetched_at,
            }
            records.append(record)

    if not records:
        raise ParseError("No stock flow rows were parsed from the page.")

    return {
        "trade_date": trade_date,
        "unit_label": unit_label,
        "metric_type": metric_type,
        "broker_code": broker_code,
        "branch_code": branch_code,
        "branch_code_raw": branch_code_raw,
        "broker_name": broker_name,
        "branch_name": branch_name,
        "lookback_days": lookback_days,
        "lookback_label": lookback_label,
        "records": records,
    }
