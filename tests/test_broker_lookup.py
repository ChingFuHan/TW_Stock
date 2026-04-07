from pathlib import Path
import unittest

from src.tw_broker_flows.broker_lookup import (
    build_lookup_from_branch_rows,
    build_target_urls,
    iter_branch_rows,
    iter_company_rows,
    load_lookup_from_path,
    normalize_branch_code,
    resolve_names,
)


FIXTURE = Path("data/raw/samples/zbrokerjs.djjs")


class BrokerLookupTests(unittest.TestCase):
    def test_lookup_resolves_company_and_branch_names(self) -> None:
        lookup = load_lookup_from_path(FIXTURE)

        broker_name, branch_name = resolve_names(lookup, "1030", "1030")
        self.assertEqual(broker_name, "土銀")
        self.assertEqual(branch_name, "土銀")

        broker_name, branch_name = resolve_names(lookup, "8900", "8900")
        self.assertEqual(broker_name, "法銀巴黎")
        self.assertEqual(branch_name, "法銀巴黎")

    def test_lookup_exposes_all_company_and_branch_rows(self) -> None:
        lookup = load_lookup_from_path(FIXTURE)

        companies = iter_company_rows(lookup)
        branches = iter_branch_rows(lookup)

        self.assertEqual(len(companies), 81)
        self.assertEqual(len(branches), 843)

        tulyin = next(row for row in companies if row["code1"] == "1030")
        self.assertEqual(tulyin["券商中文"], "土銀")
        self.assertGreater(tulyin["分行數"], 1)

        paris = next(row for row in branches if row["code1"] == "8900" and row["code2"] == "8900")
        self.assertEqual(paris["分行中文"], "法銀巴黎")
        self.assertTrue(paris["is_broker_level"])

        hex_branch = next(row for row in branches if row["code2"] == "0031003000320041")
        self.assertEqual(normalize_branch_code(str(hex_branch["code2"])), "102A")
        self.assertEqual(hex_branch["分行中文"], "合庫-新竹")

    def test_lookup_builds_daily_target_urls(self) -> None:
        lookup = load_lookup_from_path(FIXTURE)
        branch_rows = iter_branch_rows(lookup)

        urls = build_target_urls(
            branch_rows=branch_rows,
            start_date="2026-04-02",
            end_date="2026-04-02",
            metric_type="amount",
        )

        self.assertEqual(len(urls), 843)
        self.assertTrue(urls[0].startswith("https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?"))
        self.assertIn("a=1030", "".join(urls))
        self.assertIn("b=1030", "".join(urls))
        self.assertTrue(all("c=B" in url and "e=2026-04-02" in url and "f=2026-04-02" in url for url in urls[:10]))

    def test_lookup_can_be_rebuilt_from_branch_source_rows(self) -> None:
        rows = [
            {"券商中文": "土銀", "分行中文": "土銀", "code1": "1030", "code2": "1030"},
            {"券商中文": "法銀巴黎", "分行中文": "法銀巴黎", "code1": "8900", "code2": "8900"},
        ]

        lookup = build_lookup_from_branch_rows(rows)

        broker_name, branch_name = resolve_names(lookup, "8900", "8900")
        self.assertEqual(broker_name, "法銀巴黎")
        self.assertEqual(branch_name, "法銀巴黎")

    def test_normalize_branch_code_decodes_hex_style_values(self) -> None:
        self.assertEqual(normalize_branch_code("0031003000320041"), "102A")
        self.assertEqual(normalize_branch_code("1030"), "1030")


if __name__ == "__main__":
    unittest.main()
