from __future__ import annotations

import asyncio
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


ADMIN_IDS = {
    1451929812594725136,
    1451181216010207304,
    1451178608914726943,
}
TICKETS_FILE = Path(__file__).resolve().parents[2] / "data" / "tickets" / "tickets.json"
STAT_CHANNEL_NAMES = {
    "members": "👥 สมาชิก",
    "bots": "🤖 บอท",
    "online": "🟢 ออนไลน์",
    "voice": "🔊 อยู่ใน Voice",
    "closed_tickets": "🔒 Ticket ปิดแล้ว",
    "admins": "🛡️ Admin",
}


class Dashboard(commands.Cog):
    dashboard = app_commands.Group(name="dashboard", description="แสดงข้อมูล Dashboard ของเซิร์ฟเวอร์")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        self.update_task = asyncio.create_task(self.update_stats_when_ready())

    async def cog_unload(self) -> None:
        if self.update_task:
            self.update_task.cancel()

    async def update_stats_when_ready(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.recreate_stat_channels(guild)

    async def recreate_stat_channels(self, guild: discord.Guild) -> None:
        category = await self.get_dashboard_category(guild)
        for channel in category.voice_channels:
            await channel.delete(reason="รีเซ็ตห้องสถิติ Dashboard เมื่อบอทเริ่มทำงาน")
        await self.update_stat_channels(guild)

    async def get_dashboard_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        category = discord.utils.find(
            lambda channel: isinstance(channel, discord.CategoryChannel)
            and channel.name.casefold() == "dashboard",
            guild.categories,
        )
        if category is None:
            category = await guild.create_category("Dashboard", reason="สร้างหมวดหมู่ Dashboard")
        return category

    async def get_dashboard_channel(self, guild: discord.Guild) -> discord.TextChannel:
        category = await self.get_dashboard_category(guild)

        channel = discord.utils.find(
            lambda item: item.name.casefold() == "dashboard" and item.category_id == category.id,
            guild.text_channels,
        )
        if channel is None:
            channel = await guild.create_text_channel(
                "dashboard",
                category=category,
                reason="สร้างห้อง Dashboard",
            )
        return channel

    async def update_stat_channels(self, guild: discord.Guild) -> None:
        category = await self.get_dashboard_category(guild)
        members = guild.members
        values = {
            "members": len(members),
            "bots": sum(member.bot for member in members),
            "online": sum(
                member.status is not discord.Status.offline
                for member in members
                if not member.bot
            ),
            "voice": sum(
                member.voice is not None
                for member in members
                if not member.bot
            ),
            "closed_tickets": self.closed_ticket_count(guild.id),
            "admins": sum(member.id in ADMIN_IDS for member in members),
        }
        existing = {
            channel.name.split("・", 1)[0]: channel
            for channel in category.voice_channels
            if "・" in channel.name
        }
        for key, label in STAT_CHANNEL_NAMES.items():
            channel = existing.get(label)
            name = f"{label}・{values[key]:,}"
            if channel is None:
                await guild.create_voice_channel(
                    name,
                    category=category,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(
                            connect=False,
                            view_channel=True,
                        )
                    },
                    reason="สร้างห้องสถิติ ServerStats",
                )
            elif channel.name != name:
                await channel.edit(name=name, reason="อัปเดตสถิติ ServerStats")

    @staticmethod
    def closed_ticket_count(guild_id: int) -> int:
        if not TICKETS_FILE.exists():
            return 0
        with TICKETS_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
        return sum(
            record.get("guild_id") == guild_id
            and record.get("status") == "🔴 ปิด Ticket"
            for record in data.get("tickets", {}).values()
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self.update_stat_channels(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self.update_stat_channels(member.guild)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.status != after.status:
            await self.update_stat_channels(after.guild)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if before.channel != after.channel:
            await self.update_stat_channels(member.guild)

    @dashboard.command(name="show", description="แสดงข้อมูลสมาชิกและห้อง Ticket")
    async def dashboard_show(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return

        members = guild.members
        bots = sum(member.bot for member in members)
        online = sum(
            member.status is not discord.Status.offline
            for member in members
            if not member.bot
        )
        admins = [member for member in members if member.id in ADMIN_IDS]
        admin_text = "\n".join(
            f"{member.mention} (`{member.id}`)" for member in admins
        ) or "ไม่พบ Admin ที่อยู่ในเซิร์ฟเวอร์"

        embed = discord.Embed(
            title="📊 Server Dashboard",
            description=f"ข้อมูลปัจจุบันของ **{guild.name}**",
            colour=discord.Colour.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="👥 คนในเซิร์ฟเวอร์", value=f"`{len(members):,}` คน", inline=True)
        embed.add_field(name="🤖 บอทในเซิร์ฟเวอร์", value=f"`{bots:,}` ตัว", inline=True)
        embed.add_field(name="🟢 คนออนไลน์", value=f"`{online:,}` คน", inline=True)
        embed.add_field(name="🔊 คนอยู่ใน Voice", value=f"`{sum(member.voice is not None for member in members if not member.bot):,}` คน", inline=True)
        embed.add_field(name="🔒 Ticket ที่ปิดแล้ว", value=f"`{self.closed_ticket_count(guild.id):,}` Ticket", inline=True)
        embed.add_field(name="🛡️ Admin", value=admin_text, inline=False)
        embed.set_footer(text=f"Guild ID: {guild.id}")
        dashboard_channel = await self.get_dashboard_channel(guild)
        await dashboard_channel.send(embed=embed)
        await self.update_stat_channels(guild)
        await interaction.response.send_message(
            f"อัปเดต Dashboard ในห้อง {dashboard_channel.mention} แล้ว",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dashboard(bot))
