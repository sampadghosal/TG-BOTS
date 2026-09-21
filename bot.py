import os
import random
import asyncio
import logging
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

TOKEN = os.environ.get("TG_BOT_TOKEN")
EMOJI_POOL = ["🔥", "❤️", "👏", "🎉", "⚡", "👍", "🤩", "💯"]
OWNER_ID = 5207149515

# This variable remembers your chosen emoji. 
# If it is None, the bot uses random emojis.
CURRENT_EMOJI = None

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security: Ignore if anyone else sends /start
    if update.effective_user.id != OWNER_ID:
        return
        
    await update.message.reply_text(
        "Admin Panel Active! ⚙️\n\n"
        "To set a specific emoji for all future reactions, send:\n"
        "/set 🔥\n\n"
        "To go back to random emojis, send:\n"
        "/random"
    )

async def set_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_EMOJI
    if update.effective_user.id != OWNER_ID:
        return
    
    # Check if you actually typed an emoji after the command
    if not context.args:
        await update.message.reply_text("Please provide an emoji. Example: /set 💯")
        return
        
    CURRENT_EMOJI = context.args[0]
    await update.message.reply_text(f"✅ Active emoji locked to: {CURRENT_EMOJI}\nAll new posts will receive this reaction.")

async def set_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_EMOJI
    if update.effective_user.id != OWNER_ID:
        return
        
    CURRENT_EMOJI = None
    await update.message.reply_text("🎲 Random mode activated! The bot will now pick from the pool.")

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Telegram treats channel posts differently than group messages
    is_channel = update.channel_post is not None
    
    # If it is a group or private chat, ensure YOU are the sender
    if not is_channel:
        if update.effective_user is None or update.effective_user.id != OWNER_ID:
            return
            
    # Target the correct message object
    msg = update.channel_post if is_channel else update.message

    try:
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # Use your custom emoji, or grab a random one if in random mode
        reaction_emoji = CURRENT_EMOJI if CURRENT_EMOJI else random.choice(EMOJI_POOL)
        
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            reaction=[ReactionTypeEmoji(reaction_emoji)]
        )
    except Exception as e:
        logging.error(e)

if __name__ == '__main__':
    if not TOKEN:
        logging.error("No token found! Check your GitHub Secrets.")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Admin Panel Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("set", set_emoji))
    app.add_handler(CommandHandler("random", set_random))
    
    # Listen for normal messages and channel posts
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, auto_react))
    
    print("Advanced Admin Bot is running!")
    app.run_polling()
