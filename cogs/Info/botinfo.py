from __future__ import annotations

import asyncio
import json
import platform
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

import discord
import psutil
from discord.ext import commands

from cogs._ui import ACCENT, make_embed


VERSION_FILE = Path(__file__).parents[2] / "version_history.json"
THAILAND = timezone(timedelta(hours=7), name="Asia/Bangkok")
THAI_WEEKDAYS = (
    "วันจันทร์",
    "วันอังคาร",
    "วันพุธ",
    "วันพฤหัสบดี",
    "วันศุกร์",
    "วันเสาร์",
    "วันอาทิตย์",
)
THAI_MONTHS = (
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)


class ResourceSnapshot(NamedTuple):
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int


def format_thai_datetime(value: datetime) -> str:
    local_time = value.astimezone(THAILAND)
    buddhist_year = local_time.year + 543
    return (
        f"{THAI_WEEKDAYS[local_time.weekday()]}ที่ {local_time.day} "
        f"{THAI_MONTHS[local_time.month - 1]} พ.ศ. {buddhist_year} "
        f"เวลา {local_time:%H:%M}"
    )


def system_resources() -> ResourceSnapshot:
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(Path(__file__).resolve().anchor)
    return ResourceSnapshot(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_used=memory.total - memory.available,
        memory_total=memory.total,
        disk_percent=disk.percent,
        disk_used=disk.used,
        disk_total=disk.total,
    )


class BotInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started_at = datetime.now(THAILAND)
        self.started_monotonic = time.monotonic()

    @commands.hybrid_command(name="botinfo", description="ดูข้อมูลและสถานะของบอท")
    async def botinfo(self, ctx: commands.Context) -> None:
        """แสดงสถานะการเชื่อมต่อและข้อมูลบอท"""
        with VERSION_FILE.open(encoding="utf-8") as file:
            version = json.load(file)["current_version"]
        resources = await asyncio.to_thread(system_resources)

        guilds = self.bot.guilds
        members = sum(guild.member_count or len(guild.members) for guild in guilds)
        cached_members = [member for guild in guilds for member in guild.members]
        online = sum(
            member.status is not discord.Status.offline
            for member in cached_members
            if not member.bot
        )
        uptime_seconds = max(0, int(time.monotonic() - self.started_monotonic))
        days, remainder = divmod(uptime_seconds, 86_400)
        hours, remainder = divmod(remainder, 3_600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{days} วัน {hours:02}:{minutes:02}:{seconds:02}" if days else f"{hours:02}:{minutes:02}:{seconds:02}"

        embed = make_embed(
            "🤖 BotDiscord • ข้อมูลระบบ",
            "สถานะการทำงานปัจจุบันของบอท",
            user=ctx.author,
        )
        embed.colour = ACCENT
        embed.add_field(name="🟢 สถานะ", value="ออนไลน์", inline=True)
        embed.add_field(name="📡 Ping", value=f"`{round(self.bot.latency * 1000)} ms`", inline=True)
        embed.add_field(name="🏷️ เวอร์ชัน", value=f"`v{version}`", inline=True)
        embed.add_field(name="🌐 เซิร์ฟเวอร์", value=f"`{len(guilds):,}`", inline=True)
        embed.add_field(name="👥 สมาชิก", value=f"`{members:,}`", inline=True)
        embed.add_field(name="🟢 ออนไลน์", value=f"`{online:,}` คนในแคช", inline=True)
        embed.add_field(
            name="🖥️ สภาพแวดล้อม",
            value=f"Python `{platform.python_version()}`\ndiscord.py `{discord.__version__}`",
            inline=True,
        )
        gib = 1024**3
        embed.add_field(
            name="📈 ทรัพยากรเครื่อง",
            value=(
                f"CPU: `{resources.cpu_percent:.1f}%`\n"
                f"RAM: `{resources.memory_percent:.1f}%` "
                f"({resources.memory_used / gib:.1f}/{resources.memory_total / gib:.1f} GB)\n"
                f"Disk: `{resources.disk_percent:.1f}%` "
                f"({resources.disk_used / gib:.1f}/{resources.disk_total / gib:.1f} GB)"
            ),
            inline=True,
        )
        embed.add_field(
            name="🕒 เริ่มทำงานเมื่อ",
            value=f"{format_thai_datetime(self.started_at)}\nเปิดมาแล้ว `{uptime}`",
            inline=False,
        )
        if self.bot.user is not None:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotInfo(bot))
