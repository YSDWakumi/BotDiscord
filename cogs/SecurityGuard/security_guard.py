from __future__ import annotations

import discord
from discord.ext import commands


PROTECTED_CHANNEL_ID = 1545738839241527356
EXEMPT_USER_IDS = {407131716830887936, 1438439831502979082}


class SecurityGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def warning_embed(self) -> discord.Embed:
        warning = discord.Embed(
            title="🚫 ห้ามพิมพ์หรือส่งข้อความในห้องนี้โดยเด็ดขาด! 🚫",
            description=(
                "ห้องนี้ใช้สำหรับตรวจจับบอทหรือบัญชีที่อาจถูกแฮ็ก "
                "หากส่งข้อความ ระบบจะตรวจสอบและเตะออกทันที"
            ),
            colour=discord.Colour.red(),
        )
        warning.add_field(
            name="⚠️ คำเตือน",
            value="ห้ามส่งข้อความในห้องนี้โดยเด็ดขาด!",
            inline=False,
        )
        warning.set_footer(text="Security Guard")
        return warning

    async def refresh_warning(self) -> None:
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(PROTECTED_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            self.bot.logger.warning("ไม่พบช่องเฝ้าระวัง %s", PROTECTED_CHANNEL_ID)
            return
        try:
            handled_members: set[int] = set()
            async for old_message in channel.history(limit=None):
                if old_message.author.id == self.bot.user.id:
                    try:
                        await old_message.delete()
                    except discord.NotFound:
                        pass
                elif (
                    not old_message.author.bot
                    and old_message.author.id not in EXEMPT_USER_IDS
                    and isinstance(old_message.author, discord.Member)
                    and old_message.author.id not in handled_members
                ):
                    handled_members.add(old_message.author.id)
                    try:
                        await old_message.delete()
                    except discord.NotFound:
                        pass
                    if old_message.author.kickable:
                        try:
                            await old_message.author.kick(
                                reason="ส่งข้อความในช่องเฝ้าระวังก่อนบอทเริ่มทำงาน"
                            )
                        except discord.Forbidden:
                            self.bot.logger.warning(
                                "ไม่มีสิทธิ์เตะสมาชิกย้อนหลัง %s (%s)",
                                old_message.author,
                                old_message.author.id,
                            )
            await channel.send(embed=self.warning_embed())
        except discord.Forbidden:
            self.bot.logger.warning(
                "ไม่มีสิทธิ์จัดการข้อความในช่องเฝ้าระวัง %s",
                PROTECTED_CHANNEL_ID,
            )

    async def cog_load(self) -> None:
        self.bot.loop.create_task(self.refresh_warning())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            message.author.bot
            or message.channel.id != PROTECTED_CHANNEL_ID
            or message.author.id in EXEMPT_USER_IDS
        ):
            return
        if not isinstance(message.author, discord.Member):
            return

        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            self.bot.logger.warning(
                "ไม่มีสิทธิ์ลบข้อความในช่องเฝ้าระวัง %s",
                PROTECTED_CHANNEL_ID,
            )

        try:
            await message.channel.send(embed=self.warning_embed(), delete_after=10)
        except discord.Forbidden:
            self.bot.logger.warning(
                "ไม่มีสิทธิ์ส่งข้อความเตือนในช่องเฝ้าระวัง %s",
                PROTECTED_CHANNEL_ID,
            )

        if not message.author.kickable:
            self.bot.logger.warning(
                "ไม่สามารถเตะสมาชิก %s (%s) ได้ เนื่องจากลำดับ Role หรือสิทธิ์",
                message.author,
                message.author.id,
            )
            return
        try:
            await message.author.kick(reason="ส่งข้อความในช่องเฝ้าระวังความปลอดภัย")
        except discord.Forbidden:
            self.bot.logger.warning(
                "ไม่มีสิทธิ์เตะสมาชิก %s (%s)",
                message.author,
                message.author.id,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SecurityGuard(bot))
