import discord
from discord.ext import commands
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ตั้งค่า intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

class Bot(commands.Bot):
    async def setup_hook(self):
        cogs_path = Path(__file__).parent / "cogs"
        for cog_file in sorted(cogs_path.rglob("*.py")):
            if cog_file.name.startswith("_"):
                continue

            relative_path = cog_file.relative_to(cogs_path).with_suffix("")
            extension_name = "cogs." + ".".join(relative_path.parts)
            await self.load_extension(extension_name)

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


# สร้าง bot instance รองรับ >, / และการ mention บอท
bot = Bot(
    command_prefix=commands.when_mentioned_or(">", "/"),
    intents=intents,
)


@bot.event
async def on_ready():
    print(f"Bot ready: {bot.user}")


@bot.event
async def on_message(message):
    # ไม่ตอบสนองต่อตัวเอง
    if message.author == bot.user:
        return

    await bot.process_commands(message)


# รัน bot ด้วย token จากไฟล์ .env หรือ environment variable
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("ไม่พบ DISCORD_TOKEN — กรุณาตั้งค่าในไฟล์ .env")

bot.run(token)
