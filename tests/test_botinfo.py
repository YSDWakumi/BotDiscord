from datetime import datetime
from unittest import TestCase

from cogs.Info.botinfo import THAILAND, format_thai_datetime, system_resources


class BotInfoTests(TestCase):
    def test_format_thai_datetime_uses_thai_weekday_month_and_buddhist_year(self) -> None:
        value = datetime(2026, 9, 5, 23, 48, tzinfo=THAILAND)

        self.assertEqual(
            format_thai_datetime(value),
            "วันเสาร์ที่ 5 กันยายน พ.ศ. 2569 เวลา 23:48",
        )

    def test_system_resources_returns_valid_percentages_and_capacities(self) -> None:
        resources = system_resources()

        self.assertGreaterEqual(resources.cpu_percent, 0)
        self.assertLessEqual(resources.cpu_percent, 100)
        self.assertGreaterEqual(resources.memory_percent, 0)
        self.assertLessEqual(resources.memory_percent, 100)
        self.assertGreater(resources.memory_total, 0)
        self.assertGreaterEqual(resources.memory_used, 0)
        self.assertLessEqual(resources.memory_used, resources.memory_total)
        self.assertGreaterEqual(resources.disk_percent, 0)
        self.assertLessEqual(resources.disk_percent, 100)
        self.assertGreater(resources.disk_total, 0)
        self.assertGreaterEqual(resources.disk_used, 0)
        self.assertLessEqual(resources.disk_used, resources.disk_total)
