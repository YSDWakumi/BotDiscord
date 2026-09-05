import json
from pathlib import Path

from discord.ext import commands


VERSION_FILE = Path(__file__).parents[2] / "version_history.json"


def load_version_history() -> dict:
    with VERSION_FILE.open(encoding="utf-8") as file:
        return json.load(file)


class Version(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="version")
    async def show_version(self, ctx: commands.Context):
        """แสดงเวอร์ชัน ระบบ หน้าที่ และวันเวลาของเวอร์ชันล่าสุด"""
        history = load_version_history()
        release = history["releases"][0]
        systems = "\n".join(f"- {item}" for item in release["systems"])
        duties = "\n".join(f"- {item}" for item in release["duties"])
        note = release.get("note", "-")
        summary = release.get("summary", note)

        message = (
            f"**Bot Version {release['version']}**\n"
            f"**บทสรุป:** {summary}\n"
            f"**ระบบที่เพิ่ม:**\n{systems}\n"
            f"**หน้าที่:**\n{duties}\n"
            f"**หมายเหตุ:**\n{note}\n"
            f"**วันที่และเวลา:** `{release['released_at']}`"
        )
        await ctx.send(message)

    @commands.command(name="history")
    async def show_history(self, ctx: commands.Context):
        """แสดงรายการเวอร์ชันทั้งหมด"""
        history = load_version_history()
        releases = "\n".join(
            f"`{release['version']}` - {release['released_at']}"
            for release in history["releases"]
        )
        await ctx.send(f"**ประวัติเวอร์ชัน**\n{releases}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Version(bot))
