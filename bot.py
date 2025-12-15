import os
import json
import asyncio
from typing import Optional, List

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ========================== CONFIG (EDIT THESE) ==========================
# Optional: welcome feature
WELCOME_CHANNEL_ID = 1356730364566962454
LETS_GET_STARTED_CHANNEL_ID = 1356730364566962455

# Payments system
# If you set IDs, the bot will use them. If you leave them as 0, the bot will find by name.
PAYMENTS_CATEGORY_ID = 1450150780865871934  # admin creates category "payments"
INSTRUCTIONS_CHANNEL_ID = 1450150843658797197  # admin creates channel "instructions" inside payments category

PAYMENTS_CATEGORY_NAME = "payments"
INSTRUCTIONS_CHANNEL_NAME = "instructions"

# Roles that can view and manage payment tickets (put role ids here)
PAYMENTS_STAFF_ROLE_IDS: List[int] = [1363412581137780911
    # 123456789012345678,
]

# Optional: log channel for open and close events (0 disables logging)
PAYMENTS_LOG_CHANNEL_ID = 0

# Ticket behavior
ALLOW_ONE_OPEN_TICKET_PER_CREATOR = True
AUTO_DELETE_CLOSED_TICKETS = True
AUTO_DELETE_DELAY_SECONDS = 5

# Where to store simple bot state (panel message id, open tickets map)
STATE_FILE = "rn_state.json"

# ========================== MESSAGES ==========================
WELCOME_MESSAGE = (
    "**Welcome to the Rainbow Nutrients Affiliate Community**\n\n"
    "**We are excited to have you here. Welcome to the team behind the "
    "number one Hair Growth and Hair Care brand in the USA.**\n\n"
    "**Next step: Head over to "
    f"<#{LETS_GET_STARTED_CHANNEL_ID}> "
    "to learn how to request your sample, explore content ideas, and access the tools "
    "to kick off your Rainbow Nutrients journey.**"
)

PAYMENTS_PANEL_MESSAGE = (
    "**Payments Instructions**\n\n"
    "Click the button below to open a private payment ticket with the team.\n"
    "In the ticket, share:\n"
    "1) Campaign name\n"
    "2) Retainer amount\n"
    "3) Payout method\n"
    "4) Any proof needed (screenshots, links)\n\n"
    "A staff member will help you and close the ticket once payment is done."
)

TICKET_OPEN_MESSAGE = (
    "**Payment Ticket Opened**\n\n"
    "Please send:\n"
    "1) Campaign name\n"
    "2) Amount\n"
    "3) Payout method\n"
    "4) Any links or screenshots\n\n"
    "Staff will review and close this ticket when done."
)

# ========================== SETUP ==========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================== STATE ==========================
def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"payments_panel_message_id": 0, "open_payment_ticket_by_user": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "payments_panel_message_id" not in data:
            data["payments_panel_message_id"] = 0
        if "open_payment_ticket_by_user" not in data:
            data["open_payment_ticket_by_user"] = {}
        return data
    except Exception:
        return {"payments_panel_message_id": 0, "open_payment_ticket_by_user": {}}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


STATE = _load_state()

# ========================== HELPERS ==========================
def is_staff_member(member: discord.Member) -> bool:
    if member.guild_permissions.manage_channels or member.guild_permissions.administrator:
        return True
    if PAYMENTS_STAFF_ROLE_IDS:
        role_ids = {r.id for r in member.roles}
        return any(rid in role_ids for rid in PAYMENTS_STAFF_ROLE_IDS)
    return False


async def log_payment_event(guild: discord.Guild, text: str) -> None:
    if not PAYMENTS_LOG_CHANNEL_ID:
        return
    channel = guild.get_channel(PAYMENTS_LOG_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(PAYMENTS_LOG_CHANNEL_ID)
        except Exception:
            return
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(text)
        except Exception:
            pass


async def get_payments_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    if PAYMENTS_CATEGORY_ID:
        cat = guild.get_channel(PAYMENTS_CATEGORY_ID)
        if isinstance(cat, discord.CategoryChannel):
            return cat
        try:
            fetched = await bot.fetch_channel(PAYMENTS_CATEGORY_ID)
            if isinstance(fetched, discord.CategoryChannel):
                return fetched
        except Exception:
            return None

    for c in guild.categories:
        if c.name.lower() == PAYMENTS_CATEGORY_NAME.lower():
            return c
    return None


async def get_instructions_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if INSTRUCTIONS_CHANNEL_ID:
        ch = guild.get_channel(INSTRUCTIONS_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
        try:
            fetched = await bot.fetch_channel(INSTRUCTIONS_CHANNEL_ID)
            if isinstance(fetched, discord.TextChannel):
                return fetched
        except Exception:
            return None

    category = await get_payments_category(guild)
    if category:
        for ch in category.text_channels:
            if ch.name.lower() == INSTRUCTIONS_CHANNEL_NAME.lower():
                return ch

    for ch in guild.text_channels:
        if ch.name.lower() == INSTRUCTIONS_CHANNEL_NAME.lower():
            return ch
    return None


def build_ticket_channel_name(user: discord.abc.User) -> str:
    base = user.name.lower().replace(" ", "-")
    base = "".join(ch for ch in base if ch.isalnum() or ch == "-")[:18] or "creator"
    short = str(user.id)[-4:]
    return f"pay-{base}-{short}"


# ========================== VIEWS ==========================
class PaymentsPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Get Payment",
        style=discord.ButtonStyle.success,
        custom_id="rn_payments_open_ticket",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.user:
            await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user

        category = await get_payments_category(guild)
        if category is None:
            await interaction.response.send_message(
                "Payments category not found. Ask an admin to create a category named payments.",
                ephemeral=True,
            )
            return

        if ALLOW_ONE_OPEN_TICKET_PER_CREATOR:
            existing_channel_id = STATE["open_payment_ticket_by_user"].get(str(user.id))
            if existing_channel_id:
                existing = guild.get_channel(int(existing_channel_id))
                if isinstance(existing, discord.TextChannel):
                    await interaction.response.send_message(
                        f"You already have an open payment ticket: {existing.mention}",
                        ephemeral=True,
                    )
                    return
                STATE["open_payment_ticket_by_user"].pop(str(user.id), None)
                _save_state(STATE)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }

        overwrites[user] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )

        bot_member = guild.me
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            )

        for rid in PAYMENTS_STAFF_ROLE_IDS:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True,
                )

        if not PAYMENTS_STAFF_ROLE_IDS:
            for role in guild.roles:
                if role.permissions.manage_channels or role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                        manage_messages=True,
                    )

        channel_name = build_ticket_channel_name(user)

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason="Payment ticket opened",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to create channels. Give me Manage Channels permission.",
                ephemeral=True,
            )
            return
        except Exception:
            await interaction.response.send_message("Failed to create the ticket channel.", ephemeral=True)
            return

        STATE["open_payment_ticket_by_user"][str(user.id)] = str(ticket_channel.id)
        _save_state(STATE)

        await interaction.response.send_message(
            f"Ticket created: {ticket_channel.mention}",
            ephemeral=True,
        )

        try:
            await ticket_channel.send(
                f"{user.mention} welcome. A staff member will help you here.\n\n{TICKET_OPEN_MESSAGE}",
                view=PaymentTicketCloseView(),
            )
        except Exception:
            pass

        await log_payment_event(
            guild,
            f"Opened payment ticket {ticket_channel.mention} for {user.mention} (id {user.id})",
        )


class PaymentTicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="rn_payments_close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.user or not interaction.channel:
            await interaction.response.send_message("Cannot close this ticket here.", ephemeral=True)
            return

        member = interaction.user
        if isinstance(member, discord.User):
            member = interaction.guild.get_member(member.id)

        if not isinstance(member, discord.Member) or not is_staff_member(member):
            await interaction.response.send_message("Only staff can close this ticket.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        try:
            await interaction.response.send_message("Closing ticket...", ephemeral=True)
        except Exception:
            pass

        creator_id_to_clear: Optional[str] = None
        for uid, cid in list(STATE["open_payment_ticket_by_user"].items()):
            if str(channel.id) == str(cid):
                creator_id_to_clear = uid
                break
        if creator_id_to_clear:
            STATE["open_payment_ticket_by_user"].pop(creator_id_to_clear, None)
            _save_state(STATE)

        await log_payment_event(
            interaction.guild,
            f"Closed payment ticket {channel.mention} by {member.mention}",
        )

        try:
            await channel.send(f"Ticket closed by {member.mention}.")
        except Exception:
            pass

        if AUTO_DELETE_CLOSED_TICKETS:
            await asyncio.sleep(max(1, int(AUTO_DELETE_DELAY_SECONDS)))
            try:
                await channel.delete(reason=f"Payment ticket closed by {member}")
            except Exception:
                pass
        else:
            try:
                await channel.set_permissions(interaction.guild.default_role, view_channel=False)
            except Exception:
                pass


# ========================== SLASH COMMANDS ==========================
payments_group = app_commands.Group(name="payments", description="Payments ticket commands")


@payments_group.command(name="setup", description="Post the payments instructions panel with the button.")
@app_commands.checks.has_permissions(manage_guild=True)
async def payments_setup(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return

    guild = interaction.guild
    channel = await get_instructions_channel(guild)
    if channel is None:
        await interaction.response.send_message(
            "Instructions channel not found. Ask an admin to create channel instructions in payments category.",
            ephemeral=True,
        )
        return

    view = PaymentsPanelView()

    try:
        msg = await channel.send(PAYMENTS_PANEL_MESSAGE, view=view)
    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot send messages in the instructions channel. Fix my permissions.",
            ephemeral=True,
        )
        return
    except Exception:
        await interaction.response.send_message("Failed to post the panel.", ephemeral=True)
        return

    STATE["payments_panel_message_id"] = int(msg.id)
    _save_state(STATE)

    await interaction.response.send_message(
        f"Payments panel posted in {channel.mention}.",
        ephemeral=True,
    )


@payments_setup.error
async def payments_setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need Manage Server to run this.", ephemeral=True)
        return
    await interaction.response.send_message("Command failed.", ephemeral=True)


# ========================== EVENTS ==========================
@bot.event
async def on_ready():
    bot.tree.add_command(payments_group)
    try:
        await bot.tree.sync()
    except Exception:
        pass

    bot.add_view(PaymentsPanelView())
    bot.add_view(PaymentTicketCloseView())

    print(f"Logged in as {bot.user} (id {bot.user.id})")


@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        try:
            fetched = await bot.fetch_channel(WELCOME_CHANNEL_ID)
            if isinstance(fetched, discord.TextChannel):
                channel = fetched
        except Exception:
            return
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(WELCOME_MESSAGE)
        except Exception:
            pass


# ========================== MAIN ==========================
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    bot.run(TOKEN)
