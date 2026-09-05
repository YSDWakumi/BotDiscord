import asyncio
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands


THAILAND = timezone(timedelta(hours=7), name="Asia/Bangkok")
PINK = discord.Colour(0xFF00F7)
BANNER_URL = "https://cdn.discordapp.com/attachments/1533456998656639166/1545597127864877098/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f776174747061642d6d656469612d736572766963652f53746f7279496d6167652f53447a42367565753750636b47673d3d2d313235303830333631312e313730346236396665663633666430613931323033343.gif?ex=6a9cb8ff&is=6a9b677f&hm=5c73ed8650c626c83c44e40c15593e905b839ca07709c8f9077b664b9a522670"
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "tickets"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

TICKET_TYPES = {
    "problem": {
        "label": "แจ้งปัญหาภายในเกม",
        "emoji": "🛠️",
        "prefix": "bug",
        "description": "แจ้งปัญหาที่พบในเกม",
        "fields": ["ปัญหาที่พบ", "เกิดขึ้นวันที่/เวลา", "รายละเอียดปัญหา", "หลักฐาน (ถ้ามี)"],
    },
    "report": {
        "label": "แจ้งผู้เล่น",
        "emoji": "👤",
        "prefix": "report",
        "description": "รายงานพฤติกรรมหรือผู้เล่น",
        "fields": ["ชื่อผู้เล่นที่ต้องการแจ้ง", "เหตุผล", "วันที่/เวลาที่เกิดเหตุ", "รายละเอียดเหตุการณ์", "หลักฐาน (ถ้ามี)"],
    },
    "payment": {
        "label": "ปัญหาการเติมเงิน",
        "emoji": "💰",
        "prefix": "payment",
        "description": "แจ้งปัญหาการชำระเงินหรือสินค้า",
        "fields": ["ช่องทางการเติมเงิน", "รายการที่ซื้อ", "วันที่/เวลาที่เติม", "รายละเอียดปัญหา", "หลักฐานการชำระเงิน"],
    },
    "rollback": {
        "label": "แจ้งของหาย / Item Rollback",
        "emoji": "📦",
        "prefix": "item",
        "description": "แจ้งไอเทมหายหรือขอ rollback",
        "fields": ["สิ่งของที่หาย", "จำนวน", "วันที่/เวลาที่หาย", "รายละเอียด", "หลักฐาน (ถ้ามี)"],
    },
    "account": {
        "label": "ปัญหาบัญชี",
        "emoji": "🔐",
        "prefix": "account",
        "description": "แจ้งปัญหาบัญชีหรือการเข้าสู่ระบบ",
        "fields": ["ประเภทบัญชี/ปัญหา", "รายละเอียด", "หลักฐาน (ถ้ามี)"],
    },
    "event": {
        "label": "แจ้งปัญหา Event / Reward",
        "emoji": "🏆",
        "prefix": "event",
        "description": "แจ้งปัญหา event หรือรางวัล",
        "fields": ["ชื่อ Event", "Reward ที่ควรได้รับ", "วันที่/เวลาที่เกิดปัญหา", "รายละเอียด", "หลักฐาน (ถ้ามี)"],
    },
    "support": {
        "label": "ติดต่อทีมงาน",
        "emoji": "💬",
        "prefix": "ticket",
        "description": "ติดต่อทีมงานเรื่องทั่วไป",
        "fields": ["หัวข้อ", "รายละเอียด", "หลักฐาน (ถ้ามี)"],
    },
    "other": {
        "label": "ปัญหาอื่น ๆ",
        "emoji": "❓",
        "prefix": "ticket",
        "description": "แจ้งเรื่องอื่น ๆ ที่ไม่มีในรายการ",
        "fields": ["หัวข้อ", "รายละเอียด", "หลักฐาน (ถ้ามี)"],
    },
}

PRIORITIES = {"low": ("🟢", "LOW"), "normal": ("🟡", "NORMAL"), "high": ("🟠", "HIGH"), "urgent": ("🔴", "URGENT")}


def env_int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class TicketConfig:
    panel_channel_id = env_int("TICKET_PANEL_CHANNEL_ID", 1457333540135108761)
    category_id = env_int("TICKET_CATEGORY_ID")
    staff_role_id = env_int("TICKET_STAFF_ROLE_ID")
    log_channel_id = env_int("TICKET_LOG_CHANNEL_ID")
    max_per_user = max(1, env_int("TICKET_MAX_PER_USER", 1))
    cooldown_seconds = max(0, env_int("TICKET_COOLDOWN_SECONDS", 60))
    delete_delay = max(0, env_int("TICKET_DELETE_DELAY_SECONDS", 5))


def now_iso() -> str:
    return datetime.now(THAILAND).isoformat(timespec="seconds")


def display_time(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).astimezone(THAILAND).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9ก-๙_-]+", "-", value).strip("-").lower()
    return value[:24] or "user"


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        raise RuntimeError(f"ไฟล์ข้อมูล Ticket เสียหาย: {path}")


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        info = TICKET_TYPES[ticket_type]
        super().__init__(title=info["label"][:45])
        self.ticket_type = ticket_type
        self.inputs: list[discord.ui.TextInput] = []
        for index, label in enumerate(info["fields"]):
            field = discord.ui.TextInput(
                label=label[:45],
                style=discord.TextStyle.paragraph if index > 0 else discord.TextStyle.short,
                required=label != "หลักฐาน (ถ้ามี)" and label != "หลักฐานการชำระเงิน",
                max_length=1000,
            )
            self.inputs.append(field)
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog is None:
            await interaction.response.send_message("ระบบ Ticket ยังไม่พร้อมใช้งาน", ephemeral=True)
            return
        details = {field.label: str(field.value) for field in self.inputs}
        await cog.create_ticket(interaction, self.ticket_type, details)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=data["label"], value=key, emoji=data["emoji"], description=data["description"][:100])
            for key, data in TICKET_TYPES.items()
        ]
        super().__init__(placeholder="เลือกประเภท Ticket ที่ต้องการติดต่อ", options=options, custom_id="ticket:type")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketModal(self.values[0]))


class TicketTypeButton(discord.ui.Button):
    def __init__(self, ticket_type: str, row: int):
        info = TICKET_TYPES[ticket_type]
        super().__init__(
            label=info["label"][:80],
            emoji=info["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket:type:{ticket_type}",
            row=row,
        )
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketModal(self.ticket_type))


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

    @discord.ui.button(label="ทดสอบ Ticket", emoji="🧪", style=discord.ButtonStyle.secondary, custom_id="ticket:test")
    async def test_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.create_test_ticket(interaction)


class RatingView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        for score in range(1, 6):
            button = discord.ui.Button(label=str(score), emoji="⭐", style=discord.ButtonStyle.secondary, custom_id=f"ticket:rating:{ticket_id}:{score}")
            button.callback = self.make_callback(score)
            self.add_item(button)

    def make_callback(self, score: int):
        async def callback(interaction: discord.Interaction) -> None:
            cog = interaction.client.get_cog("Tickets")
            if cog:
                await cog.rate_ticket(interaction, self.ticket_id, score)
        return callback


class ResetTicketView(discord.ui.View):
    def __init__(self, cog: "Tickets", user_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("เฉพาะผู้ที่เริ่มคำสั่งนี้เท่านั้นที่ยืนยันได้", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ยืนยัน Reset ทั้งหมด", emoji="⚠️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.reset_all_tickets(interaction)
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(content="รีเซ็ตระบบ Ticket ทั้งหมดเรียบร้อยแล้ว", view=self)
        self.stop()

    @discord.ui.button(label="ยกเลิก", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="ยกเลิกการ Reset ระบบ Ticket แล้ว", view=None)
        self.stop()


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def action(self, interaction: discord.Interaction, action: str) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.handle_action(interaction, action)

    @discord.ui.button(label="รับเรื่อง", emoji="🖐️", style=discord.ButtonStyle.primary, custom_id="ticket:claim")
    async def claim(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.action(interaction, "claim")

    @discord.ui.button(label="เพิ่มผู้เล่น", emoji="👥", style=discord.ButtonStyle.secondary, custom_id="ticket:add")
    async def add(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_message("ใช้ `/ticket add @ผู้เล่น` เพื่อเพิ่มผู้เล่น", ephemeral=True)

    @discord.ui.button(label="เปลี่ยนสถานะ", emoji="📌", style=discord.ButtonStyle.secondary, custom_id="ticket:status")
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_message("ใช้ `/ticket status` เพื่อเปลี่ยนสถานะ", ephemeral=True)

    @discord.ui.button(label="Transcript", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="ticket:transcript")
    async def transcript(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.action(interaction, "transcript")

    @discord.ui.button(label="ปิด Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button):
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await interaction.response.send_modal(CloseTicketModal(cog))


class CloseTicketModal(discord.ui.Modal, title="ปิด Ticket"):
    reason = discord.ui.TextInput(label="เหตุผลที่ปิด", placeholder="เช่น แก้ปัญหาให้ผู้เล่นเรียบร้อยแล้ว", max_length=500)

    def __init__(self, cog: "Tickets"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.close_ticket(interaction, str(self.reason))


class Tickets(commands.Cog):
    ticket = app_commands.Group(name="ticket", description="จัดการ Ticket")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_lock = asyncio.Lock()
        self.data: dict[str, Any] = {"tickets": {}, "history": [], "stats": {}, "panel_message_id": None}
        self.created_at: dict[tuple[int, int], datetime] = {}
        self.panel_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        self.data = load_json(DATA_DIR / "tickets.json", self.data)
        if not isinstance(self.data, dict):
            raise RuntimeError("ไฟล์ข้อมูล Ticket ต้องเป็น JSON object")
        if not isinstance(self.data.get("tickets"), dict):
            raise RuntimeError("ฟิลด์ tickets ในไฟล์ข้อมูลต้องเป็น object")
        self.data.setdefault("tickets", {})
        self.data.setdefault("history", [])
        self.data.setdefault("stats", {})
        self.bot.add_view(TicketPanel())
        self.bot.add_view(TicketControls())
        for record in self.data["tickets"].values():
            record.setdefault("closed_at", None)
            record.setdefault("close_reason", None)
            record.setdefault("staff_id", None)
            record.setdefault("priority", "normal")
            record.setdefault("rating", None)
            record.setdefault("messages", [])
            if record.get("status") == "🔴 ปิด Ticket" and record.get("rating") is None:
                self.bot.add_view(RatingView(int(record["id"])))
        self.panel_task = asyncio.create_task(self.ensure_panel())

    async def cog_unload(self) -> None:
        if self.panel_task:
            self.panel_task.cancel()

    async def persist(self) -> None:
        async with self.data_lock:
            save_json(DATA_DIR / "tickets.json", self.data)
            save_json(DATA_DIR / "ticket_history.json", self.data["history"])
            save_json(DATA_DIR / "ticket_counter.json", {"last_id": max([int(i) for i in self.data["tickets"]] or [0])})

    async def ensure_panel(self) -> None:
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(TicketConfig.panel_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(
            title="🎀 ˚₊‧ ศูนย์ช่วยเหลือ ♡ ‧₊˚ 🎀",
            description="สวัสดีค่าา~ 👋🏻💗\n\nหากคุณมีปัญหา หรือต้องการติดต่อทีมงาน\nสามารถเปิด Ticket เพื่อแจ้งเรื่องกับเราได้เลยนะคะ ✨",
            colour=PINK,
        )
        embed.set_image(url=BANNER_URL)
        await channel.purge(limit=None, reason="รีเฟรช Ticket panel")
        message = await channel.send(embed=embed, view=TicketPanel())
        self.data["panel_message_id"] = message.id
        await self.persist()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return
        record = self.ticket_record(message.channel)
        if record is None:
            return
        record.setdefault("messages", []).append({
            "id": message.id,
            "author_id": message.author.id,
            "author": str(message.author),
            "content": message.clean_content,
            "attachments": [{"filename": attachment.filename, "url": attachment.url} for attachment in message.attachments],
            "created_at": message.created_at.isoformat(),
        })
        await self.persist()

    def is_staff(self, member: discord.Member) -> bool:
        return member.guild_permissions.manage_channels or bool(TicketConfig.staff_role_id and member.get_role(TicketConfig.staff_role_id))

    def ticket_record(self, channel: discord.TextChannel) -> dict[str, Any] | None:
        for record in self.data["tickets"].values():
            if record.get("channel_id") == channel.id:
                return record
        if channel.topic:
            ticket_id = re.search(r"ticket_id=(\d+)", channel.topic)
            if ticket_id:
                record = self.data["tickets"].get(ticket_id.group(1))
                if record:
                    return record
        match = re.search(r"(?:ticket|closed|bug|report|payment|item|account|event)-(\d+)", channel.name)
        return self.data["tickets"].get(match.group(1)) if match else None

    async def staff_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not self.is_staff(interaction.user):
            await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะ Staff", ephemeral=True)
            return False
        if not isinstance(interaction.channel, discord.TextChannel) or not self.ticket_record(interaction.channel):
            await interaction.response.send_message("ใช้คำสั่งนี้ในห้อง Ticket เท่านั้น", ephemeral=True)
            return False
        return True

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        ticket_type: str,
        details: dict[str, str],
        *,
        ignore_limits: bool = False,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("ใช้ระบบ Ticket ได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if ignore_limits:
            await self.clear_user_tickets(guild, interaction.user.id)
        if not ignore_limits and TicketConfig.cooldown_seconds:
            latest_created: datetime | None = None
            for record in self.data["tickets"].values():
                if record.get("guild_id") != guild.id or record.get("user_id") != interaction.user.id:
                    continue
                created_at = record.get("created_at")
                if not isinstance(created_at, str):
                    continue
                try:
                    created = datetime.fromisoformat(created_at)
                except ValueError:
                    continue
                if latest_created is None or created > latest_created:
                    latest_created = created
            if latest_created is not None:
                elapsed = (datetime.now(THAILAND) - latest_created.astimezone(THAILAND)).total_seconds()
                if elapsed < TicketConfig.cooldown_seconds:
                    remaining = max(1, int(TicketConfig.cooldown_seconds - elapsed))
                    await interaction.followup.send(
                        f"กรุณารออีก {remaining} วินาทีก่อนสร้าง Ticket ใหม่",
                        ephemeral=True,
                    )
                    return
        active = [
            record for record in self.data["tickets"].values()
            if record["guild_id"] == guild.id
            and record["user_id"] == interaction.user.id
            and record["status"] != "🔴 ปิด Ticket"
        ]
        if not ignore_limits and len(active) >= TicketConfig.max_per_user:
            await interaction.followup.send("คุณมี Ticket ที่ยังเปิดอยู่ครบจำนวนสูงสุดแล้ว", ephemeral=True)
            return
        category = guild.get_channel(TicketConfig.category_id) if TicketConfig.category_id else None
        staff_role = guild.get_role(TicketConfig.staff_role_id) if TicketConfig.staff_role_id else None
        counter = max([int(i) for i in self.data["tickets"]] or [0]) + 1
        info = TICKET_TYPES[ticket_type]
        name = f"{info['prefix']}-{counter:04d}-{safe_name(interaction.user.display_name)}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        channel = await guild.create_text_channel(name, category=category if isinstance(category, discord.CategoryChannel) else None, overwrites=overwrites, topic=f"ticket_id={counter};ticket_owner={interaction.user.id}", reason="สร้าง Ticket")
        record = {
            "id": counter, "guild_id": guild.id, "channel_id": channel.id, "user_id": interaction.user.id,
            "username": str(interaction.user), "type": ticket_type, "details": details, "staff_id": None,
            "created_at": now_iso(), "closed_at": None, "close_reason": None, "status": "🟢 รอทีมงานรับเรื่อง",
            "priority": "normal", "rating": None,
        }
        self.data["tickets"][str(counter)] = record
        self.data["history"].append({"action": "created", "ticket_id": counter, "at": now_iso(), "user_id": interaction.user.id})
        await self.persist()
        embed = self.ticket_embed(record, interaction.user.mention)
        message = "สร้าง Ticket ทดสอบแล้ว" if ignore_limits else "สร้าง Ticket แล้ว"
        await interaction.followup.send(f"{message}: {channel.mention}", ephemeral=True)
        ticket_message = await channel.send(embed=embed, view=TicketControls())
        record["message_id"] = ticket_message.id
        await self.persist()
        if staff_role:
            await channel.send(f"🔔 {staff_role.mention} มี Ticket ใหม่", allowed_mentions=discord.AllowedMentions(roles=True))

    async def clear_user_tickets(self, guild: discord.Guild, user_id: int) -> None:
        records = [
            (ticket_id, record)
            for ticket_id, record in self.data["tickets"].items()
            if record.get("guild_id") == guild.id and record.get("user_id") == user_id
        ]
        known_channel_ids = {record.get("channel_id") for _, record in records}
        orphan_channels = [
            channel for channel in guild.text_channels
            if channel.topic and f"ticket_owner={user_id}" in channel.topic
            and channel.id not in known_channel_ids
        ]
        for ticket_id, record in records:
            channel = guild.get_channel(record.get("channel_id", 0))
            if isinstance(channel, discord.TextChannel):
                await channel.delete(reason="ล้าง Ticket เดิมเพื่อทดสอบระบบ")
            self.data["tickets"].pop(ticket_id, None)
        for channel in orphan_channels:
            await channel.delete(reason="ล้างห้อง Ticket ค้างเพื่อทดสอบระบบ")
        self.data["history"] = [
            event for event in self.data["history"]
            if event.get("user_id") != user_id
        ]
        await self.persist()

    async def create_test_ticket(self, interaction: discord.Interaction) -> None:
        await self.create_ticket(
            interaction,
            "other",
            {
                "หัวข้อ": "ทดสอบระบบ Ticket",
                "รายละเอียด": "Ticket นี้สร้างจากเมนูทดสอบ สามารถใช้ทดสอบ Claim, Status, Transcript และ Close ได้",
                "หลักฐาน (ถ้ามี)": "-",
            },
            ignore_limits=True,
        )

    def ticket_embed(self, record: dict[str, Any], opener: str | None = None) -> discord.Embed:
        info = TICKET_TYPES[record["type"]]
        emoji, priority = PRIORITIES[record["priority"]]
        embed = discord.Embed(title=f"{info['emoji']} Ticket #{record['id']:04d}", colour=PINK)
        embed.set_image(url=BANNER_URL)
        embed.add_field(name="ผู้เปิด", value=opener or f"<@{record['user_id']}>", inline=True)
        embed.add_field(name="ประเภท", value=f"{info['emoji']} {info['label']}", inline=True)
        status = record["status"]
        if status == "รอทีมงานรับเรื่อง":
            status = "🟢 รอทีมงานรับเรื่อง"
        embed.add_field(name="สถานะ", value=status, inline=True)
        embed.add_field(name="ผู้รับผิดชอบ", value=f"<@{record['staff_id']}>" if record["staff_id"] else "ยังไม่มี", inline=True)
        embed.add_field(name="Priority", value=f"{emoji} {priority}", inline=True)
        embed.add_field(name="สร้างเมื่อ", value=display_time(record["created_at"]), inline=True)
        embed.add_field(name="รายละเอียด", value="\n".join(f"**{key}:** {value or '-'}" for key, value in record["details"].items())[:1024], inline=False)
        return embed

    async def update_ticket_embed(self, channel: discord.TextChannel, record: dict[str, Any]) -> None:
        message_id = record.get("message_id")
        message = None
        if message_id:
            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                message = None
        if message is None:
            async for candidate in channel.history(limit=30, oldest_first=True):
                if candidate.author.id == self.bot.user.id and candidate.embeds:
                    if candidate.embeds[0].title and f"#{record['id']:04d}" in candidate.embeds[0].title:
                        message = candidate
                        break
        if message:
            await message.edit(embed=self.ticket_embed(record), view=TicketControls())

    async def handle_action(self, interaction: discord.Interaction, action: str) -> None:
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record is None:
            return
        if action in {"claim", "transcript"}:
            await interaction.response.defer(ephemeral=True)
        if action == "claim":
            record["staff_id"] = interaction.user.id
            record["status"] = "🔵 กำลังตรวจสอบ"
            stats = self.data["stats"].setdefault(str(interaction.user.id), {"claimed": 0, "closed": 0, "total_rating": 0, "rating_count": 0})
            stats["claimed"] += 1
            await self.persist()
            await self.update_ticket_embed(interaction.channel, record)
            await interaction.channel.edit(name=f"🔵・{interaction.channel.name.split('・')[-1]}")
            await interaction.followup.send(f"🖐️ {interaction.user.mention} รับเรื่อง Ticket นี้แล้ว", ephemeral=False)
        elif action == "transcript":
            file = await self.make_transcript(interaction.channel, record)
            await interaction.followup.send("สร้าง Transcript แล้ว", file=file, ephemeral=True)
        else:
            return

    async def make_transcript(self, channel: discord.TextChannel, record: dict[str, Any]) -> discord.File:
        rows = []
        async for message in channel.history(limit=None, oldest_first=True):
            content = html.escape(message.clean_content).replace("\n", "<br>")
            attachments = "".join(
                f'<a class="attachment" href="{html.escape(attachment.url, quote=True)}" target="_blank">'
                f"📎 {html.escape(attachment.filename)}</a>"
                for attachment in message.attachments
            )
            avatar = message.author.display_avatar.url
            rows.append(
                '<article class="message">'
                f'<img class="avatar" src="{html.escape(str(avatar), quote=True)}" alt="">'
                '<div class="message-body">'
                f'<div class="author">{html.escape(message.author.display_name)} '
                f'<span>{display_time(message.created_at.replace(tzinfo=timezone.utc).isoformat())}</span></div>'
                f'<div class="content">{content or "<span class=\"muted\">(ไม่มีข้อความ)</span>"}</div>'
                f'<div class="attachments">{attachments}</div>'
                "</div></article>"
            )
        info = TICKET_TYPES[record["type"]]
        priority_emoji, priority_label = PRIORITIES[record["priority"]]
        details = "".join(
            f'<div class="detail"><strong>{html.escape(key)}</strong><br>{html.escape(value or "-")}</div>'
            for key, value in record["details"].items()
        )
        body = f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Transcript Ticket #{record["id"]:04d}</title>
<style>
:root {{ color-scheme: dark; --pink: #ff00f7; --panel: #171923; --card: #20232f; --muted: #a9afc1; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0d0f16; color: #f4f5fb; font: 15px/1.6 "Segoe UI", Tahoma, sans-serif; }}
.container {{ max-width: 980px; margin: 32px auto; padding: 0 18px 40px; }}
.hero {{ background: linear-gradient(135deg, #42104c, #171923 65%); border: 1px solid #5d2b68; border-radius: 18px; padding: 28px; box-shadow: 0 12px 35px #0007; }}
h1 {{ margin: 0 0 6px; font-size: 28px; }} h2 {{ margin: 0 0 16px; font-size: 18px; }}
.subtitle, .muted, small {{ color: var(--muted); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 22px; }}
.stat, .details, .conversation {{ background: var(--panel); border: 1px solid #2d3140; border-radius: 14px; padding: 18px; }}
.stat b {{ display: block; color: #fff; font-size: 16px; margin-top: 3px; }}
.details {{ margin-top: 16px; }} .detail {{ padding: 10px 0; border-bottom: 1px solid #2d3140; }} .detail:last-child {{ border: 0; }}
.conversation {{ margin-top: 16px; }} .message {{ display: flex; gap: 12px; padding: 16px 0; border-bottom: 1px solid #2d3140; }} .message:last-child {{ border: 0; }}
.avatar {{ width: 38px; height: 38px; border-radius: 50%; object-fit: cover; background: #343847; }} .message-body {{ min-width: 0; flex: 1; }}
.author {{ font-weight: 700; color: #ff9df7; }} .author span {{ color: var(--muted); font-size: 12px; font-weight: 400; margin-left: 8px; }}
.content {{ margin-top: 4px; overflow-wrap: anywhere; }} .attachment {{ display: inline-block; margin: 8px 8px 0 0; padding: 5px 9px; border-radius: 8px; background: #303548; color: #b9c7ff; text-decoration: none; }}
.footer {{ color: var(--muted); text-align: center; margin-top: 22px; font-size: 12px; }}
@media (max-width: 600px) {{ .container {{ margin-top: 12px; }} .hero {{ padding: 20px; }} h1 {{ font-size: 23px; }} }}
</style>
</head>
<body><main class="container">
<header class="hero">
<img src="{BANNER_URL}" alt="Ticket banner" style="display:block;width:100%;max-height:220px;object-fit:cover;border-radius:12px;margin-bottom:18px;">
<div class="subtitle">🎀 KaoHorm Ticket System</div>
<h1>{info["emoji"]} Ticket #{record["id"]:04d}</h1>
<div class="subtitle">Transcript สรุปประวัติการติดต่อทีมงาน</div>
<div class="grid">
<div class="stat">ผู้เปิด<b>{html.escape(record["username"])}</b></div>
<div class="stat">ประเภท<b>{html.escape(info["label"])}</b></div>
<div class="stat">สถานะ<b>{html.escape(record["status"])}</b></div>
<div class="stat">Priority<b>{priority_emoji} {priority_label}</b></div>
<div class="stat">สร้างเมื่อ<b>{html.escape(display_time(record["created_at"]))}</b></div>
<div class="stat">ปิดเมื่อ<b>{html.escape(display_time(record.get("closed_at")))}</b></div>
</div></header>
<section class="details"><h2>📋 รายละเอียด Ticket</h2>{details}</section>
<section class="conversation"><h2>💬 ข้อความทั้งหมด</h2>{''.join(rows) or '<p class="muted">ไม่มีข้อความ</p>'}</section>
<div class="footer">สร้างโดย Ticket System • Ticket #{record["id"]:04d}</div>
</main></body></html>"""
        path = TRANSCRIPT_DIR / f"ticket-{record['id']:04d}.html"
        path.write_text(body, encoding="utf-8")
        return discord.File(path, filename=path.name)

    async def close_ticket(self, interaction: discord.Interaction, reason: str) -> None:
        if not await self.staff_check(interaction):
            return
        channel = interaction.channel
        record = self.ticket_record(channel)
        if record is None:
            return
        if record.get("status") == "🔴 ปิด Ticket":
            await interaction.response.send_message("Ticket นี้ปิดไปแล้ว", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        record.update({"status": "🔴 ปิด Ticket", "closed_at": now_iso(), "close_reason": reason})
        if record["staff_id"]:
            stats = self.data["stats"].setdefault(str(record["staff_id"]), {"claimed": 0, "closed": 0, "total_rating": 0, "rating_count": 0})
            stats["closed"] += 1
        file = await self.make_transcript(channel, record)
        channel = await channel.edit(name=f"🔒・closed-{record['id']:04d}-{safe_name(record['username'].split('#')[0])}")
        await interaction.followup.send("✅ ปิด Ticket แล้ว และสร้าง Transcript เรียบร้อย", ephemeral=True)
        await channel.send(embed=discord.Embed(
            title="✅ Ticket ได้รับการแก้ไขแล้ว",
            description=f"Ticket ID: #{record['id']:04d}\nเหตุผลที่ปิด: {reason}\n\nห้องนี้จะถูกลบอัตโนมัติใน {TicketConfig.delete_delay} วินาที",
            colour=discord.Colour.green(),
        ).set_image(url=BANNER_URL))
        opener = interaction.guild.get_member(record["user_id"]) if interaction.guild else None
        if opener is None and interaction.guild:
            try:
                opener = await interaction.guild.fetch_member(record["user_id"])
            except discord.NotFound:
                self.bot.logger.warning("ไม่พบผู้เปิด Ticket #%04d ในเซิร์ฟเวอร์", record["id"])
        if opener is not None:
            try:
                await opener.send(
                    f"Ticket #{record['id']:04d} ของคุณถูกปิดแล้ว กรุณาให้คะแนนการบริการ",
                    view=RatingView(record["id"]),
                )
            except discord.Forbidden:
                self.bot.logger.warning("ไม่สามารถส่งแบบประเมิน Ticket #%04d ทาง DM ได้", record["id"])
        log_channel = interaction.guild.get_channel(TicketConfig.log_channel_id) if interaction.guild else None
        if isinstance(log_channel, discord.TextChannel):
            log_embed = discord.Embed(
                title=f"🔒 ปิด Ticket #{record['id']:04d}",
                description="บันทึกการปิด Ticket และ Transcript",
                colour=discord.Colour.green(),
                timestamp=datetime.now(timezone.utc),
            )
            log_embed.set_image(url=BANNER_URL)
            log_embed.add_field(name="ผู้เปิด", value=f"<@{record['user_id']}>", inline=True)
            log_embed.add_field(name="ผู้รับเรื่อง", value=f"<@{record['staff_id']}>" if record["staff_id"] else "ยังไม่มี", inline=True)
            log_embed.add_field(name="ประเภท", value=TICKET_TYPES[record["type"]]["label"], inline=True)
            log_embed.add_field(name="เหตุผลที่ปิด", value=reason[:1024], inline=False)
            await log_channel.send(embed=log_embed, file=file)
        self.data["history"].append({
            "action": "closed",
            "ticket_id": record["id"],
            "at": record["closed_at"],
            "user_id": interaction.user.id,
            "reason": reason,
        })
        await self.persist()
        if TicketConfig.delete_delay:
            await asyncio.sleep(TicketConfig.delete_delay)
        await channel.delete(reason=f"ปิด Ticket โดย {interaction.user}")

    async def rate_ticket(self, interaction: discord.Interaction, ticket_id: int, score: int) -> None:
        record = self.data["tickets"].get(str(ticket_id))
        if not record or interaction.user.id != record["user_id"] or record["rating"] is not None:
            await interaction.response.send_message("ไม่สามารถให้คะแนน Ticket นี้ได้", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        record["rating"] = score
        staff_id = str(record["staff_id"] or "unassigned")
        stats = self.data["stats"].setdefault(staff_id, {"claimed": 0, "closed": 0, "total_rating": 0, "rating_count": 0})
        stats["total_rating"] += score
        stats["rating_count"] += 1
        await self.persist()
        await interaction.followup.send(f"ขอบคุณสำหรับคะแนน {score} ดาวนะคะ 💗", ephemeral=True)

    def ticket_channel(self, interaction: discord.Interaction) -> discord.TextChannel | None:
        return interaction.channel if isinstance(interaction.channel, discord.TextChannel) and self.ticket_record(interaction.channel) else None

    @ticket.command(name="claim", description="รับเรื่อง Ticket")
    async def ticket_claim(self, interaction: discord.Interaction):
        await self.handle_action(interaction, "claim")

    @ticket.command(name="test", description="ล้าง Ticket เดิมของคุณและสร้าง Ticket ทดสอบใหม่")
    async def ticket_test(self, interaction: discord.Interaction):
        await self.create_test_ticket(interaction)

    @ticket.command(name="unclaim", description="ยกเลิกรับเรื่อง")
    async def ticket_unclaim(self, interaction: discord.Interaction):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record:
            record.update({"staff_id": None, "status": "🟢 รอทีมงานรับเรื่อง"})
            await self.persist()
            await self.update_ticket_embed(interaction.channel, record)
            await interaction.response.send_message("ยกเลิกการรับเรื่องแล้ว")

    @ticket.command(name="transcript", description="สร้าง Transcript")
    async def ticket_transcript(self, interaction: discord.Interaction):
        await self.handle_action(interaction, "transcript")

    @ticket.command(name="close", description="ปิด Ticket พร้อมเหตุผล")
    async def ticket_close(self, interaction: discord.Interaction):
        if not await self.staff_check(interaction):
            return
        await interaction.response.send_modal(CloseTicketModal(self))

    @ticket.command(name="add", description="เพิ่มผู้เล่นใน Ticket")
    @app_commands.describe(member="ผู้เล่นที่ต้องการเพิ่ม")
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        if not await self.staff_check(interaction):
            return
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"เพิ่ม {member.mention} แล้ว")

    @ticket.command(name="remove", description="ลบผู้เล่นจาก Ticket")
    @app_commands.describe(member="ผู้เล่นที่ต้องการลบ")
    async def ticket_remove(self, interaction: discord.Interaction, member: discord.Member):
        if not await self.staff_check(interaction):
            return
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"ลบ {member.mention} แล้ว")

    @ticket.command(name="delete", description="ลบ Ticket")
    async def ticket_delete(self, interaction: discord.Interaction):
        if not await self.staff_check(interaction):
            return
        channel = interaction.channel
        await interaction.response.send_message("กำลังลบ Ticket...", ephemeral=True)
        await channel.delete(reason=f"ลบโดย {interaction.user}")

    @ticket.command(name="reopen", description="เปิด Ticket ที่ปิดแล้ว")
    async def ticket_reopen(self, interaction: discord.Interaction):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record is None or record["status"] != "🔴 ปิด Ticket":
            await interaction.response.send_message("Ticket นี้ยังไม่อยู่ในสถานะปิด", ephemeral=True)
            return
        record.update({"status": "🟢 รอทีมงานรับเรื่อง", "closed_at": None, "close_reason": None})
        await interaction.channel.edit(name=f"🟢・ticket-{record['id']:04d}-{safe_name(record['username'].split('#')[0])}")
        await self.persist()
        await interaction.response.send_message("🔓 เปิด Ticket ใหม่แล้ว")

    @ticket.command(name="status", description="เปลี่ยนสถานะ Ticket")
    @app_commands.choices(status=[
        app_commands.Choice(name="🟢 รอทีมงาน", value="🟢 รอทีมงานรับเรื่อง"),
        app_commands.Choice(name="🔵 กำลังตรวจสอบ", value="🔵 กำลังตรวจสอบ"),
        app_commands.Choice(name="🟡 รอข้อมูลจากผู้เล่น", value="🟡 รอข้อมูลจากผู้เล่น"),
        app_commands.Choice(name="🟣 ส่งต่อทีมงานระดับสูง", value="🟣 ส่งต่อทีมงานระดับสูง"),
        app_commands.Choice(name="✅ แก้ไขแล้ว", value="✅ แก้ไขแล้ว"),
    ])
    async def ticket_status(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record:
            record["status"] = status.value
            await self.persist()
            await self.update_ticket_embed(interaction.channel, record)
            await interaction.response.send_message(f"เปลี่ยนสถานะเป็น {status.value} แล้ว")

    @ticket.command(name="priority", description="เปลี่ยน Priority Ticket")
    @app_commands.choices(priority=[
        app_commands.Choice(name="🟢 LOW", value="low"),
        app_commands.Choice(name="🟡 NORMAL", value="normal"),
        app_commands.Choice(name="🟠 HIGH", value="high"),
        app_commands.Choice(name="🔴 URGENT", value="urgent"),
    ])
    async def ticket_priority(self, interaction: discord.Interaction, priority: app_commands.Choice[str]):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record:
            record["priority"] = priority.value
            await self.persist()
            await self.update_ticket_embed(interaction.channel, record)
            await interaction.response.send_message(f"ตั้ง Priority เป็น {PRIORITIES[priority.value][1]} แล้ว")

    @ticket.command(name="note", description="บันทึก Staff Note ที่ผู้เล่นมองไม่เห็น")
    @app_commands.describe(note="ข้อความ Staff Note")
    async def ticket_note(self, interaction: discord.Interaction, note: str):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record:
            record.setdefault("staff_notes", []).append({"author_id": interaction.user.id, "note": note, "at": now_iso()})
            await self.persist()
            await interaction.response.send_message("บันทึก Staff Note แล้ว", ephemeral=True)

    @ticket.command(name="rename", description="เปลี่ยนชื่อห้อง Ticket")
    @app_commands.describe(name="ชื่อใหม่ของห้องโดยไม่ต้องใส่ emoji")
    async def ticket_rename(self, interaction: discord.Interaction, name: str):
        if not await self.staff_check(interaction):
            return
        clean = safe_name(name)
        await interaction.channel.edit(name=clean)
        await interaction.response.send_message(f"เปลี่ยนชื่อห้องเป็น `{clean}` แล้ว")

    @ticket.command(name="history", description="ดูประวัติ Ticket")
    async def ticket_history(self, interaction: discord.Interaction):
        if not await self.staff_check(interaction):
            return
        record = self.ticket_record(interaction.channel)
        if record:
            events = [event for event in self.data["history"] if event.get("ticket_id") == record["id"]]
            text = "\n".join(f"`{event['at']}` {event['action']}" for event in events) or "ยังไม่มีประวัติ"
            await interaction.response.send_message(text[:1900], ephemeral=True)

    @ticket.command(name="reset", description="รีเซ็ต Ticket ทั้งหมดและล้างข้อมูล")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_reset(self, interaction: discord.Interaction):
        warning = (
            "⚠️ **ยืนยันการ Reset ระบบ Ticket ทั้งหมดหรือไม่?**\n"
            "การทำงานนี้จะลบห้อง Ticket ทั้งหมด ล้างข้อมูล ประวัติ คะแนน และรีเซ็ตเลข Ticket เป็น #0001"
        )
        await interaction.response.send_message(
            warning,
            ephemeral=True,
            view=ResetTicketView(self, interaction.user.id),
        )

    async def reset_all_tickets(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            return
        ticket_channel_ids = {
            int(record["channel_id"])
            for record in self.data["tickets"].values()
            if record.get("guild_id") == guild.id and record.get("channel_id")
        }
        for channel_id in ticket_channel_ids:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.delete(reason=f"Reset Ticket โดย {interaction.user}")
        self.data = {"tickets": {}, "history": [], "stats": {}, "panel_message_id": None}
        await self.persist()
        await self.ensure_panel()


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
