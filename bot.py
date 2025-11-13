import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ========================== CONFIG ==========================
WELCOME_CHANNEL_ID = 1356730364566962454
LETS_GET_STARTED_CHANNEL_ID = 1356730364566962455
CREATOR_TICKETS_CATEGORY_ID = 1356730365582250139

WELCOME_MESSAGE = (
    "**🌈 Welcome to the Rainbow Nutrients Affiliate Community! 🌈**\n\n"
    "**We’re so excited to have you here — welcome to the team behind the "
    "#1 Hair Growth & Hair Care brand in the USA! 🇺🇸✨**\n\n"
    "**This is where your journey begins! 🌸 You’ve officially joined a vibrant "
    "community full of creators, health enthusiasts, and beauty lovers who are all "
    "growing — in more ways than one. 🌿**\n\n"
    f"**👉 Next step: Head over to <#{LETS_GET_STARTED_CHANNEL_ID}> "
    "to learn how to request your sample, explore content ideas, and access all the tools "
    "to kick off your Rainbow Nutrients journey! 🚀**"
)

NEW_TICKET_MESSAGE = (
    "Hey\n"
    "My name is Moiz, and I’ll be assisting you with your onboarding for Growi 🌊.\n\n"
    "Please make sure to use all the accounts when signing up with Growi that you’ll be posting from for this brand.\n\n"
    "Onboarding link: https://growi.io/o/rainbow-nutrients-ff79fb6d/c/12782?method=username\n\n"
    "If you encounter any issues or have any questions during the process, feel free to DM me directly so I can help resolve them.✨\n"
    "Growi: Content Creator Relationship Management"
)

# ========================== SETUP ==========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ========================== EVENTS ==========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Welcome messages will post in channel ID: {WELCOME_CHANNEL_ID}")


@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(WELCOME_CHANNEL_ID)
        except Exception as e:
            print(f"❌ Could not fetch welcome channel: {e}")
            return
    try:
        await channel.send(WELCOME_MESSAGE)
        print(f"✅ Posted welcome for {member}")
    except Exception as e:
        print(f"❌ Failed to post welcome: {e}")


@bot.event
async def on_guild_channel_create(channel):
    # Only text channels in the right category
    if not isinstance(channel, discord.TextChannel):
        return
    if not channel.category or channel.category.id != CREATOR_TICKETS_CATEGORY_ID:
        return

    # Wait for the ticket bot to finish setting permissions / intro message
    await asyncio.sleep(4)

    # Double check permissions before sending
    me = channel.guild.me
    perms = channel.permissions_for(me)
    if not (perms.view_channel and perms.send_messages):
        print(f"⚠️ No send permission in {channel.name} after setup")
        return

    # Send the message (no pin)
    try:
        await asyncio.sleep(10)  # this is what will add the delay.
        await channel.send(NEW_TICKET_MESSAGE)
        print(f"✅ Sent new ticket message in {channel.name}")
    except discord.HTTPException as e:
        print(f"❌ Failed to send in {channel.name}: {e}")


@bot.event
async def on_thread_create(thread: discord.Thread):
    # Support for bots that create threads instead of channels
    parent = thread.parent
    if not parent or not parent.category or parent.category.id != CREATOR_TICKETS_CATEGORY_ID:
        return

    await asyncio.sleep(4)

    try:
        await thread.send(NEW_TICKET_MESSAGE)
        print(f"✅ Sent new ticket message in thread {thread.name}")
    except Exception as e:
        print(f"❌ Could not send in thread {thread.name}: {e}")


# ========================== MAIN ==========================
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    bot.run(TOKEN)
