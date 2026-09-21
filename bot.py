import os
import random
import asyncio
import logging
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# This exactly matches the name in your GitHub Vault
TOKEN = os.environ.get("TG_BOT_TOKEN")
EMOJI_POOL = ["🔥", "❤️", "👏", "🎉", "⚡", "👍", "🤩", "💯"]

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    app.add_handler(MessageHandler(filters.ALL, auto_react))
    print("Advanced Bot is running 24/7 on GitHub Actions!")
    app.run_polling()
