import asyncio
import discord
from discord.ext import commands, tasks
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ตั้งค่า intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

AUTO_UPDATE_INTERVAL_SECONDS = max(60, int(os.getenv("BOT_AUTO_UPDATE_INTERVAL_SECONDS", "300")))
AUTO_UPDATE_BRANCH = os.getenv("BOT_AUTO_UPDATE_BRANCH", "main")
PROJECT_DIR = Path(__file__).resolve().parent


def git_command() -> str | None:
    return shutil.which("git") or (
        r"C:\Program Files\Git\cmd\git.exe"
        if Path(r"C:\Program Files\Git\cmd\git.exe").exists()
        else None
    )


def update_from_github() -> bool:
    git = git_command()
    if git is None:
        raise RuntimeError("ไม่พบ Git สำหรับตรวจสอบการอัปเดต")

    branch = subprocess.run(
        [git, "branch", "--show-current"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
    ).stdout.strip()
    if branch != AUTO_UPDATE_BRANCH:
        return False

    fetch = subprocess.run(
        [git, "fetch", "origin", AUTO_UPDATE_BRANCH],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if fetch.returncode != 0:
        raise RuntimeError("ไม่สามารถตรวจสอบการอัปเดตจาก GitHub ได้")

    current = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
    ).stdout.strip()
    remote = subprocess.run(
        [git, "rev-parse", f"origin/{AUTO_UPDATE_BRANCH}"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
    ).stdout.strip()
    if current == remote:
        return False

    pull = subprocess.run(
        [git, "pull", "--ff-only", "origin", AUTO_UPDATE_BRANCH],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if pull.returncode != 0:
        raise RuntimeError("พบอัปเดตแต่ไม่สามารถดึงโค้ดใหม่ได้")
    return True


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def close(self):
        self.auto_update_task.cancel()
        await super().close()

    @tasks.loop(seconds=AUTO_UPDATE_INTERVAL_SECONDS)
    async def auto_update_task(self):
        check_time = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")
        print()
        print(f"┌─ AUTO UPDATE ───────────────────────────────────────────────")
        print(f"│ เวลา   : {check_time}")
        print("│ สถานะ : กำลังตรวจสอบ GitHub...")
        try:
            updated = await asyncio.to_thread(update_from_github)
        except (RuntimeError, OSError, subprocess.SubprocessError) as error:
            self.logger.warning("ตรวจสอบ Auto Update ไม่สำเร็จ: %s", error)
            print(f"└─ ไม่สำเร็จ: {error}")
            return
        if updated:
            print("└─ พบการอัปเดตใหม่ กำลัง Restart บอท...")
            self.logger.info("พบโค้ดใหม่จาก GitHub กำลัง Restart บอท")
            os.execv(sys.executable, [sys.executable, *sys.argv])
        print("└─ ยังไม่มีการอัปเดตใหม่")

    @auto_update_task.before_loop
    async def before_auto_update(self):
        await self.wait_until_ready()

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
        self.auto_update_task.start()


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
