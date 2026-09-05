from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """แสดง latency ของบอท"""
        await ctx.send(f"🏓 Pong! {round(self.bot.latency * 1000)}ms")

    @commands.command()
    async def hello(self, ctx: commands.Context):
        """ทักทายผู้ใช้"""
        await ctx.send(f"สวัสดีครับ {ctx.author.mention}! 👋")


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
