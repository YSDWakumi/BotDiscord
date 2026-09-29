import discord
from discord.ext import commands

from cogs._ui import ACCENT, make_embed


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """แสดง latency ของบอท"""
        latency = round(self.bot.latency * 1000)
        embed = make_embed("🏓 ตรวจสอบการเชื่อมต่อ", f"ตอบสนองใน **{latency} ms**", user=ctx.author)
        embed.colour = discord.Colour.green() if latency < 150 else ACCENT
        await ctx.send(embed=embed)

    @commands.command()
    async def hello(self, ctx: commands.Context):
        """ทักทายผู้ใช้"""
        await ctx.send(embed=make_embed(
            "👋 สวัสดีครับ",
            f"ยินดีต้อนรับ {ctx.author.mention} มีอะไรให้ช่วยบอกได้เลยนะครับ",
            user=ctx.author,
        ))

    @commands.hybrid_command(name="help", description="ดูคำสั่งและวิธีใช้งานบอท")
    async def help_command(self, ctx: commands.Context):
        """แสดงรายการคำสั่งที่ใช้งานได้"""
        embed = make_embed(
            "✨ ศูนย์ช่วยเหลือ BotDiscord",
            "ใช้ Slash Command หรือพิมพ์ Prefix `>` ก็ได้\n"
            "จะเรียกด้วยการแท็กบอทแล้วตามด้วยคำสั่งก็ได้ เช่น `@BotDiscord help`",
            user=ctx.author,
        )
        embed.add_field(
            name="🎫 Ticket",
            value=(
                "`/ticket` เปิดเมนูจัดการ Ticket\n"
                "`/ticket claim` รับเรื่อง  •  `/ticket close` ปิดเรื่อง\n"
                "`/ticket add` เพิ่มผู้เล่น  •  `/ticket transcript` สร้าง Transcript"
            ),
            inline=False,
        )
        embed.add_field(
            name="📊 เซิร์ฟเวอร์และบอท",
            value=(
                "`/dashboard show` ดูสถิติเซิร์ฟเวอร์\n"
                "`/botinfo` ดูสถานะบอท\n"
                "`>ping` ตรวจสอบการตอบสนอง"
            ),
            inline=False,
        )
        embed.add_field(
            name="ℹ️ ข้อมูลเวอร์ชัน",
            value="`>version` เวอร์ชันล่าสุด  •  `>history` ประวัติอัปเดต",
            inline=False,
        )
        if self.bot.user is not None:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
