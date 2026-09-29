import json
from pathlib import Path

from discord.ext import commands

from cogs._ui import make_embed


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
        note = release.get("note", "-")
        summary = release.get("summary", note)

        embed = make_embed(
            f"🚀 BotDiscord v{release['version']}",
            summary,
            user=ctx.author,
        )
        embed.add_field(name="🧩 ระบบที่เพิ่ม/ปรับปรุง", value="\n".join(f"• {item}" for item in release.get("systems", []))[:1024] or "-", inline=False)
        embed.add_field(name="⚙️ หน้าที่", value="\n".join(f"• {item}" for item in release.get("duties", []))[:1024] or "-", inline=False)
        embed.add_field(name="📝 หมายเหตุ", value=str(note)[:1024], inline=False)
        embed.add_field(name="📅 วันที่เผยแพร่", value=f"`{release['released_at']}`", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="history")
    async def show_history(self, ctx: commands.Context):
        """แสดงรายการเวอร์ชันทั้งหมด"""
        history = load_version_history()
        releases = history.get("releases", [])
        embed = make_embed("🗂️ ประวัติเวอร์ชัน BotDiscord")
        for release in releases[:20]:
            embed.add_field(
                name=f"v{release['version']}",
                value=f"{release.get('summary', release.get('note', '-'))[:180]}\n`{release['released_at']}`",
                inline=False,
            )
        if len(releases) > 20:
            embed.description = f"แสดง 20 เวอร์ชันล่าสุดจากทั้งหมด {len(releases):,} เวอร์ชัน"
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Version(bot))
