from pathlib import Path
import unittest

from src.tw_broker_flows.broker_lookup import load_lookup_from_path
from src.tw_broker_flows.parser import parse_page


LOOKUP_FIXTURE = Path("data/raw/samples/zbrokerjs.djjs")
AMOUNT_FIXTURE = Path("data/raw/samples/1030_1030.html")
LOTS_FIXTURE = Path("data/raw/samples/8900_8900_cE_d1.html")


class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lookup = load_lookup_from_path(LOOKUP_FIXTURE)

    def test_amount_page_parses_expected_rows(self) -> None:
        html_text = AMOUNT_FIXTURE.read_bytes().decode("big5", errors="replace")
        parsed = parse_page(
            html_text=html_text,
            source_url="https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=1030&b=1030",
            fetched_at="2026-04-07T00:00:00+00:00",
            broker_lookup=self.lookup,
        )

        self.assertEqual(parsed["trade_date"], "2026-04-02")
        self.assertEqual(parsed["metric_type"], "amount")
        self.assertEqual(parsed["broker_name"], "土銀")
        self.assertEqual(parsed["branch_name"], "土銀")
        self.assertEqual(parsed["branch_code"], "1030")
        self.assertEqual(parsed["branch_code_raw"], "1030")
        self.assertEqual(len(parsed["records"]), 100)

        records = parsed["records"]
        tsmc = next(item for item in records if item["stock_code"] == "2330")
        self.assertEqual(tsmc["stock_name"], "台積電")
        self.assertEqual(tsmc["buy_amount"], 884445)
        self.assertEqual(tsmc["sell_amount"], 11350)
        self.assertEqual(tsmc["net_amount"], 873095)

        oil = next(item for item in records if item["stock_code"] == "00642U")
        self.assertEqual(oil["stock_name"], "期元大S＆P石油")
        self.assertEqual(oil["net_amount"], -18969)

    def test_lots_page_parses_expected_rows(self) -> None:
        html_text = LOTS_FIXTURE.read_bytes().decode("big5", errors="replace")
        parsed = parse_page(
            html_text=html_text,
            source_url="https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=8900&b=8900&c=E&d=1",
            fetched_at="2026-04-07T00:00:00+00:00",
            broker_lookup=self.lookup,
        )

        self.assertEqual(parsed["trade_date"], "2026-04-02")
        self.assertEqual(parsed["metric_type"], "lots")
        self.assertEqual(parsed["broker_name"], "法銀巴黎")
        self.assertEqual(parsed["branch_name"], "法銀巴黎")
        self.assertEqual(parsed["branch_code"], "8900")
        self.assertEqual(parsed["branch_code_raw"], "8900")
        self.assertEqual(len(parsed["records"]), 100)

        records = parsed["records"]
        taiyao = next(item for item in records if item["stock_code"] == "6274")
        self.assertEqual(taiyao["stock_name"], "台燿")
        self.assertEqual(taiyao["buy_lots"], 1069)
        self.assertEqual(taiyao["sell_lots"], 1)
        self.assertEqual(taiyao["net_lots"], 1068)

        sell_row = next(item for item in records if item["stock_code"] == "0050" and item["rank_side"] == "sell_over")
        self.assertEqual(sell_row["stock_name"], "元大台灣50")
        self.assertLess(sell_row["net_lots"], 0)


if __name__ == "__main__":
    unittest.main()
