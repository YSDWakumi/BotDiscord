from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from cogs.Tickets.tickets import Tickets


class TicketSafetyTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tickets = Tickets(Mock())
        self.tickets.persist = AsyncMock()
        self.tickets.ensure_panel = AsyncMock()

    async def test_test_cleanup_only_removes_test_tickets_for_that_user(self) -> None:
        self.tickets.data["tickets"] = {
            "1": {"id": 1, "guild_id": 10, "user_id": 20, "is_test": True, "channel_id": 101},
            "2": {"id": 2, "guild_id": 10, "user_id": 20, "channel_id": 102},
            "3": {"id": 3, "guild_id": 11, "user_id": 20, "is_test": True, "channel_id": 103},
        }
        guild = SimpleNamespace(id=10, get_channel=Mock(return_value=None))

        await self.tickets.clear_user_test_tickets(guild, 20)

        self.assertEqual(set(self.tickets.data["tickets"]), {"2", "3"})
        self.tickets.persist.assert_awaited_once()

    async def test_reset_only_removes_tickets_from_selected_guild(self) -> None:
        self.tickets.data["tickets"] = {
            "1": {"id": 1, "guild_id": 10, "channel_id": 101},
            "2": {"id": 2, "guild_id": 11, "channel_id": 102},
        }
        self.tickets.data["history"] = [
            {"ticket_id": 1, "action": "created"},
            {"ticket_id": 2, "action": "created"},
        ]
        self.tickets.data["stats"] = {"staff": {"closed": 3}}
        self.tickets.data["last_id"] = 42
        guild = SimpleNamespace(id=10, get_channel=Mock(return_value=None))
        interaction = SimpleNamespace(guild=guild, user=SimpleNamespace(id=99))

        await self.tickets.reset_all_tickets(interaction)

        self.assertEqual(set(self.tickets.data["tickets"]), {"2"})
        self.assertEqual(self.tickets.data["history"], [{"ticket_id": 2, "action": "created"}])
        self.assertEqual(self.tickets.data["stats"], {"staff": {"closed": 3}})
        self.assertEqual(self.tickets.data["last_id"], 42)
        self.tickets.ensure_panel.assert_awaited_once()

