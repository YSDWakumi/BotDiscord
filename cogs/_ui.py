from __future__ import annotations

import discord


ACCENT = discord.Colour(0xD946EF)
SUCCESS = discord.Colour(0x22C55E)
ERROR = discord.Colour(0xEF4444)


def make_embed(
    title: str,
    description: str | None = None,
    *,
    colour: discord.Colour = ACCENT,
    user: discord.abc.User | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        colour=colour,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="BotDiscord • ศูนย์จัดการเซิร์ฟเวอร์")
    if user is not None:
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    return embed


def success_embed(title: str, description: str | None = None) -> discord.Embed:
    return make_embed(title, description, colour=SUCCESS)


def error_embed(title: str, description: str | None = None) -> discord.Embed:
    return make_embed(title, description, colour=ERROR)
