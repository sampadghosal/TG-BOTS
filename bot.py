import os
import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, ChatMemberHandler, filters
)
from telegram.error import BadRequest

TOKEN = os.environ.get("TG_BOT_TOKEN")
OWNER_ID = 5207149515
EMOJI_POOL = ["🔥", "❤️", "👏", "🎉", "⚡", "👍", "🤩", "💯"]

# The bot's live memory. It learns channels automatically.
KNOWN_CHANNELS = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- STATES ---
WAITING_FOR_MESSAGE = 1

# --- DYNAMIC KEYBOARD GENERATORS ---
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Create Post", callback_data="menu_create")],
        [InlineKeyboardButton("Scheduled Posts", callback_data="dummy"), InlineKeyboardButton("Edit Post", callback_data="dummy")],
        [InlineKeyboardButton("Channel Stats", callback_data="dummy"), InlineKeyboardButton("Settings", callback_data="menu_settings")]
    ])

def settings_keyboard(user_data):
    fmt = user_data.get('fmt', 'HTML')
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Auto Formatting: {fmt}", callback_data="toggle_fmt")],
        [InlineKeyboardButton("« Back", callback_data="back_main")]
    ])

def channel_select_keyboard():
    # Dynamically builds the buttons based on the channels the bot currently manages
    keyboard = []
    row = []
    
    for chat_id, title in KNOWN_CHANNELS.items():
        row.append(InlineKeyboardButton(title, callback_data=f"select_{chat_id}"))
        # Put 2 buttons per row to match the beautiful UI
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def post_manager_keyboard(show_actions=False):
    if not show_actions:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Attach Media", callback_data="dummy")],
            [InlineKeyboardButton("Delete Message", callback_data="cancel_post")],
            [InlineKeyboardButton("↓ Show Actions", callback_data="show_actions")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Delete All", callback_data="cancel_post"), InlineKeyboardButton("Preview", callback_data="preview")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_post"), InlineKeyboardButton("Send", callback_data="send_post")]
        ])

# --- DYNAMIC CHANNEL TRACKING ---
async def track_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listens for when you add/remove the bot as an admin in a channel"""
    result = update.my_chat_member
    if result.chat.type == 'channel':
        if result.new_chat_member.status in ['administrator', 'creator']:
            KNOWN_CHANNELS[result.chat.id] = result.chat.title
            logging.info(f"Added to channel: {result.chat.title}")
        elif result.new_chat_member.status in ['left', 'kicked']:
            KNOWN_CHANNELS.pop(result.chat.id, None)
            logging.info(f"Removed from channel: {result.chat.title}")

# --- COMMAND HANDLERS ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
        
    await update.message.reply_text(
        "Here you can create rich posts, view stats and accomplish other tasks.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# --- DYNAMIC MENU ROUTING ---
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    ud = context.user_data
    
    await query.answer()

    try:
        if data == "back_main":
            await query.edit_message_text(
                "Here you can create rich posts, view stats and accomplish other tasks.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
            
        elif data == "menu_settings":
            await query.edit_message_text("Choose what you want to change.", reply_markup=settings_keyboard(ud))
            
        elif data == "menu_create":
            if not KNOWN_CHANNELS:
                await query.edit_message_text(
                    "I am not an admin in any channels yet. Please add me to a channel as an Admin first, then try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="back_main")]])
                )
                return
                
            await query.edit_message_text(
                "Choose a channel to create a new post.",
                reply_markup=channel_select_keyboard()
            )

        elif data == "toggle_fmt":
            ud['fmt'] = "Markdown" if ud.get('fmt', 'HTML') == "HTML" else "HTML"
            await query.edit_message_reply_markup(reply_markup=settings_keyboard(ud))

        # Dynamic Channel Selection
        elif data.startswith("select_"):
            target_id = int(data.split("_")[1])
            target_name = KNOWN_CHANNELS.get(target_id, "Unknown Channel")
            
            ud['target_channel_id'] = target_id
            ud['target_channel_name'] = target_name
            
            await query.edit_message_text(
                f"Here it is: \"{target_name}\".\n\n"
                "Send me one or multiple messages you want to include in the post."
            )
            return WAITING_FOR_MESSAGE
            
        elif data == "show_actions":
            await query.edit_message_reply_markup(reply_markup=post_manager_keyboard(show_actions=True))
            return WAITING_FOR_MESSAGE
            
        elif data == "preview":
            draft = ud.get('draft_html', "Error.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=draft, parse_mode=ud.get('fmt', 'HTML'))
            return WAITING_FOR_MESSAGE
            
        elif data == "cancel_post":
            await query.edit_message_text("Creating of the post has been canceled.")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Here you can create rich posts, view stats and accomplish other tasks.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
            
        elif data == "send_post":
            draft = ud.get('draft_html')
            target_id = ud.get('target_channel_id')
            target_name = ud.get('target_channel_name')
            fmt = ud.get('fmt', 'HTML')
            
            try:
                await context.bot.send_message(chat_id=target_id, text=draft, parse_mode=fmt)
                await query.edit_message_text(f"Done!\n\n1 message ready to be sent to {target_name}.")
            except Exception as e:
                await query.edit_message_text("Error sending post.")
                
            await asyncio.sleep(1.5)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Here you can create rich posts, view stats and accomplish other tasks.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END

        elif data == "dummy":
             await query.answer("Button clicked.", show_alert=False)

    except BadRequest:
        pass

async def receive_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fmt = context.user_data.get('fmt', 'HTML')
    context.user_data['draft_html'] = update.message.text_html if fmt == 'HTML' else update.message.text_markdown_v2
    target_name = context.user_data.get('target_channel_name', "Channel")
    
    await update.message.reply_text(
        f"1 message ready to be sent to {target_name}.",
        reply_markup=post_manager_keyboard(show_actions=False)
    )
    return WAITING_FOR_MESSAGE

# --- BACKGROUND AUTO-REACTOR ---
async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    # Fallback memory: Automatically learn the channel if a post is made in it
    if chat.id not in KNOWN_CHANNELS:
        KNOWN_CHANNELS[chat.id] = chat.title

    try:
        await asyncio.sleep(random.uniform(2.0, 5.0))
        await context.bot.set_message_reaction(
            chat_id=chat.id,
            message_id=update.effective_message.message_id,
            reaction=[ReactionTypeEmoji(random.choice(EMOJI_POOL))]
        )
    except Exception as e:
        logging.error(e)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    # 1. Listens for you adding the bot to new channels
    app.add_handler(ChatMemberHandler(track_channels, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # 2. Admin Interface
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_admin), CallbackQueryHandler(handle_callbacks)],
        states={WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_post), CallbackQueryHandler(handle_callbacks)]},
        fallbacks=[CommandHandler('start', start_admin)]
    )
    app.add_handler(conv_handler)
    
    # 3. Channel Auto-Reactor
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_react))
    
    print("Dynamic System Online!")
    app.run_polling()
