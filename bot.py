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
KNOWN_CHANNELS = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- STATES ---
WAITING_FOR_MESSAGE, WAITING_FOR_BUTTONS = 1, 2

# --- UI KEYBOARDS ---
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
    keyboard = []
    row = []
    for chat_id, title in KNOWN_CHANNELS.items():
        row.append(InlineKeyboardButton(title, callback_data=f"select_{chat_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def post_manager_keyboard(show_actions=False):
    # Updated to activate the "Add URL Buttons" feature[span_2](start_span)[span_2](end_span)[span_3](start_span)[span_3](end_span)
    if not show_actions:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Attach Media", callback_data="dummy")],
            [InlineKeyboardButton("Add Comments", callback_data="dummy")],
            [InlineKeyboardButton("Add Native Comments", callback_data="dummy")],
            [InlineKeyboardButton("Add Reactions", callback_data="dummy")],
            [InlineKeyboardButton("Add URL Buttons", callback_data="add_url_buttons")],
            [InlineKeyboardButton("Send Silently", callback_data="dummy")],
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
    result = update.my_chat_member
    if result.chat.type == 'channel':
        if result.new_chat_member.status in ['administrator', 'creator']:
            KNOWN_CHANNELS[result.chat.id] = result.chat.title
        elif result.new_chat_member.status in ['left', 'kicked']:
            KNOWN_CHANNELS.pop(result.chat.id, None)

# --- COMMAND HANDLERS ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
        
    await update.message.reply_text(
        "Here you can create rich posts, view stats and accomplish other tasks.",
        reply_markup=main_menu_keyboard()
    )
    # Clear any old drafts
    context.user_data.pop('draft_html', None)
    context.user_data.pop('draft_markup', None)
    return ConversationHandler.END

# --- ROUTING & LOGIC ---
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    ud = context.user_data
    
    await query.answer()

    try:
        if data == "back_main":
            await query.edit_message_text("Here you can create rich posts, view stats and accomplish other tasks.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
            
        elif data == "menu_settings":
            await query.edit_message_text("Choose what you want to change.", reply_markup=settings_keyboard(ud))
            
        elif data == "menu_create":
            if not KNOWN_CHANNELS:
                await query.edit_message_text("Add me to a channel as an Admin first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="back_main")]]))
                return
            await query.edit_message_text("Choose a channel to create a new post.", reply_markup=channel_select_keyboard())

        elif data == "toggle_fmt":
            ud['fmt'] = "Markdown" if ud.get('fmt', 'HTML') == "HTML" else "HTML"
            await query.edit_message_reply_markup(reply_markup=settings_keyboard(ud))

        elif data.startswith("select_"):
            target_id = int(data.split("_")[1])
            target_name = KNOWN_CHANNELS.get(target_id, "Channel")
            ud['target_channel_id'] = target_id
            ud['target_channel_name'] = target_name
            await query.edit_message_text(f"Here it is: \"{target_name}\".\n\nSend me one or multiple messages you want to include in the post.")
            return WAITING_FOR_MESSAGE
            
        # --- URL BUTTON LOGIC ---
        elif data == "add_url_buttons":
            # Exact format instructions from the reference images[span_4](start_span)[span_4](end_span)[span_5](start_span)[span_5](end_span)
            instructions = (
                "Send me a list of URL buttons for the message. Please use this format:\n\n"
                "`Button text 1 - http://www.example.com/`\n"
                "`Button text 2 - http://www.example2.com/`\n\n"
                "Use | to add up to three buttons in one row. Example:\n\n"
                "`Button text 1 - http://www.example.com/ | Button text 2 - http://www.example2.com/`\n\n"
                "Choose 'Cancel' to back to creating of the post."
            )
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_buttons")]])
            await query.edit_message_text(instructions, reply_markup=keyboard, parse_mode="Markdown")
            return WAITING_FOR_BUTTONS

        elif data == "cancel_buttons":
            target_name = ud.get('target_channel_name', "Channel")
            await query.edit_message_text(f"1 message ready to be sent to {target_name}.", reply_markup=post_manager_keyboard(show_actions=False))
            return WAITING_FOR_MESSAGE

        elif data == "show_actions":
            await query.edit_message_reply_markup(reply_markup=post_manager_keyboard(show_actions=True))
            return WAITING_FOR_MESSAGE
            
        elif data == "preview":
            draft = ud.get('draft_html', "Error.")
            markup = ud.get('draft_markup', None)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=draft, parse_mode=ud.get('fmt', 'HTML'), reply_markup=markup)
            return WAITING_FOR_MESSAGE
            
        elif data == "cancel_post":
            ud.pop('draft_html', None)
            ud.pop('draft_markup', None)
            await query.edit_message_text("Creating of the post has been canceled.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Here you can create rich posts, view stats and accomplish other tasks.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
            
        elif data == "send_post":
            draft = ud.get('draft_html')
            target_id = ud.get('target_channel_id')
            target_name = ud.get('target_channel_name')
            fmt = ud.get('fmt', 'HTML')
            markup = ud.get('draft_markup', None)
            
            try:
                await context.bot.send_message(chat_id=target_id, text=draft, parse_mode=fmt, reply_markup=markup)
                await query.edit_message_text(f"Done!\n\n1 message ready to be sent to {target_name}.")
                # Clear draft after sending
                ud.pop('draft_html', None)
                ud.pop('draft_markup', None)
            except Exception as e:
                await query.edit_message_text("Error sending post.")
                
            await asyncio.sleep(1.5)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Here you can create rich posts, view stats and accomplish other tasks.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END

        elif data == "dummy":
             await query.answer("Feature not fully mapped.", show_alert=False)

    except BadRequest:
        pass

async def receive_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fmt = context.user_data.get('fmt', 'HTML')
    # Saves the message formatting (like <b> and <i>)[span_6](start_span)[span_6](end_span)
    context.user_data['draft_html'] = update.message.text_html if fmt == 'HTML' else update.message.text_markdown_v2
    target_name = context.user_data.get('target_channel_name', "Channel")
    
    await update.message.reply_text(f"1 message ready to be sent to {target_name}.", reply_markup=post_manager_keyboard(show_actions=False))
    return WAITING_FOR_MESSAGE

async def receive_url_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the custom button format into Telegram Inline Buttons"""
    text = update.message.text
    keyboard = []
    
    # Reads line by line, then splits by | for rows, and - for links[span_7](start_span)[span_7](end_span)
    for line in text.split('\n'):
        if not line.strip(): continue
        row = []
        for btn in line.split('|'):
            if ' - ' in btn:
                b_text, b_url = btn.split(' - ', 1)
                # Removes the optional color style if copied directly from the prompt[span_8](start_span)[span_8](end_span)
                b_url = b_url.split(' - style:')[0].strip() 
                row.append(InlineKeyboardButton(b_text.strip(), url=b_url.strip()))
        if row:
            keyboard.append(row)

    if keyboard:
        context.user_data['draft_markup'] = InlineKeyboardMarkup(keyboard)
        
    target_name = context.user_data.get('target_channel_name', "Channel")
    await update.message.reply_text(
        f"URL buttons saved!\n\n1 message ready to be sent to {target_name}.",
        reply_markup=post_manager_keyboard(show_actions=False)
    )
    return WAITING_FOR_MESSAGE

# --- BACKGROUND AUTO-REACTOR ---
async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
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
    
    app.add_handler(ChatMemberHandler(track_channels, ChatMemberHandler.MY_CHAT_MEMBER))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_admin), CallbackQueryHandler(handle_callbacks)],
        states={
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_post), CallbackQueryHandler(handle_callbacks)],
            # Routes text directly to the button parser when in the button menu
            WAITING_FOR_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url_buttons), CallbackQueryHandler(handle_callbacks)]
        },
        fallbacks=[CommandHandler('start', start_admin)]
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_react))
    
    print("Replica System Online!")
    app.run_polling()
