import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ========= Config =========
WELCOME_CHANNEL_ID = 1418296088871567575       # main welcome channel
LETS_GET_STARTED_CHANNEL_ID = 1418305580459757598  # "✅-lets-get-started" channel

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

# ==========================

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Welcome messages will post in channel ID: {WELCOME_CHANNEL_ID}")


@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(WELCOME_CHANNEL_ID)
        except Exception:
            print(f"❌ Could not find or access channel {WELCOME_CHANNEL_ID}")
            return

    try:
        await channel.send(WELCOME_MESSAGE)
        print(
            f"Posted welcome in #{getattr(channel, 'name', WELCOME_CHANNEL_ID)} for {member}")
    except discord.Forbidden:
        print("❌ Missing permission to send messages in the welcome channel.")
    except Exception as e:
        print(f"❌ Failed to post welcome: {e}")


def main():
    if not TOKEN:
        raise RuntimeError("Set DISCORD_TOKEN in .env")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
