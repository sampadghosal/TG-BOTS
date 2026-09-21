import os
import random
import asyncio
import logging
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

TOKEN = os.environ.get("TG_BOT_TOKEN")
EMOJI_POOL = ["🔥", "❤️", "👏", "🎉", "⚡", "👍", "🤩", "💯"]

# Locked strictly to your User ID
OWNER_ID = 5207149515

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Updated welcome message since you already have your ID
    await update.message.reply_text(
        "Bot is active! 🚀\n\nI am now securely locked to your account. I will only react to messages sent by you."
    )

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security: If the message is not from you, do nothing.
    if update.effective_user.id != OWNER_ID:
        return

    try:
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            reaction=[ReactionTypeEmoji(random.choice(EMOJI_POOL))]
        )
    except Exception as e:
        logging.error(e)

if __name__ == '__main__':
    if not TOKEN:
        logging.error("No token found! Check your GitHub Secrets.")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Listen for the /start command
    app.add_handler(CommandHandler("start", start_command))
    
    # Listen for normal messages from you
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, auto_react))
    
    print("Advanced Bot is running and locked to owner!")
    app.run_polling()
