import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ========= Config =========
# Replace these with your actual channel IDs (as integers)
# channel where the bot posts the welcome
WELCOME_CHANNEL_ID = 1356730364566962454

CHANNELS = {
    "SAMPLE":        1419231356407517184,  # 🌈-request-a-sample
    "INTRO":         1433865371080986687,  # 🎤-introductions
    "BRIEF":         1356730365015887922,  # 📚-product-brief
    "INSPO":         1356730365271867535,  # ✅-viral-inspo-channel
    "ANNOUNCEMENTS": 1356730364566962453,  # 📢-announcements
    "SQUAD":         1356730365015887928,  # 💬-squad-chat
    "VIBES":         1425642943888232488,  # 🤝-community-vibes
}

# CALENDLY_LINK = "https://calendly.com/your-link-here"  # optional

# ==========================


def ch(key: str) -> str:
    """Return a Discord channel mention like <#123>."""
    cid = CHANNELS.get(key)
    return f"<#{cid}>" if cid else "`missing-channel`"


def build_welcome_message() -> str:
    return (
        "**🚀 Welcome to Rainbow Nutrients! 🚀**\n\n"
        "You’re officially part of the **Rainbow Nutrients Affiliate Community** — home of the "
        "**#1 Hair Growth & Hair Care brand in the USA**, powered by essential vitamins for beauty "
        "and wellness from the inside out. 🌿✨\n\n"
        "**Here’s everything you need to get started ⤵️**\n\n"
        "💖 **Step 1️⃣: Request Your Sample**\n"
        f"Go to {ch('SAMPLE')} to request your Rainbow Nutrients sample. Once it arrives, you’ll be ready to "
        "start your hair growth journey and create authentic, engaging content! 🌈\n\n"
        "💬 **Step 2️⃣: Introduce Yourself**\n"
        f"Jump into {ch('INTRO')} and share your name, niche, and what excites you most about joining us — "
        "bonus points for a selfie or hair pic! 📸✨\n\n"
        "📚 **Step 3️⃣: Get Inspired**\n"
        f"Check out {ch('BRIEF')} and {ch('INSPO')} for viral content ideas, product benefits, and creative inspo "
        "from fellow affiliates. 🚀\n\n"
        "📢 **Step 4️⃣: Stay Updated**\n"
        f"Watch {ch('ANNOUNCEMENTS')} for promos, giveaways, and new campaigns so you never miss a beat! ✨\n\n"
        "🎥 **Need Help?**\n"
        f"Book a 1:1 with Rina anytime via Calendly — we’ll brainstorm, strategize, and set you up for success! 💪\n\n"
        "🌈 **Join the Fun**\n"
        f"• Chat with other creators in {ch('SQUAD')}\n"
        f"• {ch('VIBES')}\n\n"
        "Welcome again to Rainbow Nutrients, where beauty meets wellness — let’s grow, glow, and make magic together! 🌿✨"
    )


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # make sure "Server Members Intent" is enabled in the bot portal

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
        await channel.send(build_welcome_message())
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
