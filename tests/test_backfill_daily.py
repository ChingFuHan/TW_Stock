import unittest

from scripts.backfill_daily import is_empty_and_recent, parse_scraper_stats


class BackfillDailyTests(unittest.TestCase):
    def test_parse_scraper_stats_reads_new_fields(self) -> None:
        output = (
            "2026-04-13 01:22:59,979 INFO Finished. "
            "page_successes=900 non_empty_pages=0 empty_pages=900 page_failures=0 db_failures=0 "
            "db_rows_attempted=0 db_rows_inserted=0 log=data\\\\logs\\\\run.log"
        )

        self.assertEqual(
            parse_scraper_stats(output),
            {
                "page_successes": 900,
                "non_empty_pages": 0,
                "empty_pages": 900,
                "page_failures": 0,
                "db_failures": 0,
                "db_rows_attempted": 0,
                "db_rows_inserted": 0,
            },
        )

    def test_parse_scraper_stats_keeps_legacy_compatibility(self) -> None:
        output = "2026-04-13 01:22:59,979 INFO Finished. successes=899 failures=1 log=data\\\\logs\\\\run.log"

        self.assertEqual(
            parse_scraper_stats(output),
            {
                "successes": 899,
                "failures": 1,
            },
        )

    def test_is_empty_and_recent_treats_non_empty_pages_as_complete(self) -> None:
        progress = {
            "completed_dates": {
                "2026-04-10": {
                    "non_empty_pages": 12,
                    "db_rows_inserted": 0,
                }
            },
            "failed_dates": {},
        }

        self.assertFalse(is_empty_and_recent(progress, "2026-04-10", retry_days=30))


if __name__ == "__main__":
    unittest.main()
