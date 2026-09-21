import os
import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters
)
from telegram.error import BadRequest

TOKEN = os.environ.get("TG_BOT_TOKEN")
OWNER_ID = 5207149515
EMOJI_POOL = ["🔥", "❤️", "👏", "🎉", "⚡", "👍", "🤩", "💯"]

# Map your specific channels for the selection menu
CHANNELS = {
    "silent_mod": "@SILENT_MOD_SG",
    "silent_jod": "@silent_jod_exe_7"
}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- STATES ---
WAITING_FOR_MESSAGE = 1

# --- DYNAMIC KEYBOARD GENERATORS ---
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Create Post", callback_data="menu_create")],
        [InlineKeyboardButton("Scheduled Posts", callback_data="dummy"), InlineKeyboardButton("Edit Post", callback_data="dummy")],
        [InlineKeyboardButton("Channel Stats", callback_data="menu_stats"), InlineKeyboardButton("Settings", callback_data="menu_settings")]
    ])

def settings_keyboard(user_data):
    # Pulls current settings from memory or defaults them
    fmt = user_data.get('fmt', 'HTML')
    silent = "ON" if user_data.get('silent', False) else "OFF"
    link = "ON" if user_data.get('link', False) else "OFF"
    react = "ON" if user_data.get('react', False) else "OFF"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Auto Formatting: {fmt}", callback_data="toggle_fmt")],
        [InlineKeyboardButton(f"Silent Broadcast: {silent}", callback_data="toggle_silent")],
        [InlineKeyboardButton(f"Link Previews: {link}", callback_data="toggle_link")],
        [InlineKeyboardButton(f"Default Reactions: {react}", callback_data="toggle_react")],
        [InlineKeyboardButton("« Back", callback_data="back_main")]
    ])

def channel_select_keyboard():
    # Matches the exact layout of your channel selection screen
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("FORWARD", callback_data="dummy"), InlineKeyboardButton("SILENT JOD EXE 7", callback_data="select_silent_jod")],
        [InlineKeyboardButton("SILENT MOD", callback_data="select_silent_mod")],
        [InlineKeyboardButton("« Back", callback_data="back_main")]
    ])

def stats_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Week", callback_data="stats_week"), InlineKeyboardButton("Month", callback_data="stats_month")],
        [InlineKeyboardButton("« Back", callback_data="back_main")]
    ])

def post_manager_keyboard(show_actions=False):
    if not show_actions:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Attach Media", callback_data="dummy")],
            [InlineKeyboardButton("Add Comments", callback_data="dummy")],
            [InlineKeyboardButton("Add Native Comments", callback_data="dummy")],
            [InlineKeyboardButton("Add Reactions", callback_data="dummy")],
            [InlineKeyboardButton("Add URL Buttons", callback_data="dummy")],
            [InlineKeyboardButton("Send Silently", callback_data="dummy")],
            [InlineKeyboardButton("Delete Message", callback_data="cancel_post")],
            [InlineKeyboardButton("↓ Show Actions", callback_data="show_actions")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Delete All", callback_data="cancel_post"), InlineKeyboardButton("Preview", callback_data="preview")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_post"), InlineKeyboardButton("Send", callback_data="send_post")]
        ])

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
        # 1. Main Navigation
        if data == "back_main":
            await query.edit_message_text(
                "Here you can create rich posts, view stats and accomplish other tasks.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
            
        elif data == "menu_settings":
            await query.edit_message_text(
                "Choose what you want to change.",
                reply_markup=settings_keyboard(ud)
            )
            
        elif data == "menu_stats":
            # Replicates the stats layout you provided
            await query.edit_message_text(
                "Stats of SILENT MOD for the last 31 day.\n\n"
                "`2026-09-11    107+105   +98.13%`\n"
                "`2026-08-01    2      0      0%`",
                parse_mode="Markdown",
                reply_markup=stats_keyboard()
            )
            
        elif data == "menu_create":
            await query.edit_message_text(
                "Choose a channel to create a new post.",
                reply_markup=channel_select_keyboard()
            )

        # 2. Settings Toggles
        elif data.startswith("toggle_"):
            if data == "toggle_fmt":
                ud['fmt'] = "Markdown" if ud.get('fmt', 'HTML') == "HTML" else "HTML"
            elif data == "toggle_silent":
                ud['silent'] = not ud.get('silent', False)
            elif data == "toggle_link":
                ud['link'] = not ud.get('link', False)
            elif data == "toggle_react":
                ud['react'] = not ud.get('react', False)
            
            # Immediately refresh the keyboard with new values
            await query.edit_message_reply_markup(reply_markup=settings_keyboard(ud))

        # 3. Post Creation Flow
        elif data.startswith("select_"):
            target = CHANNELS["silent_jod"] if "jod" in data else CHANNELS["silent_mod"]
            ud['target_channel'] = target
            name = "SILENT JOD EXE 7" if "jod" in data else "SILENT MOD"
            
            await query.edit_message_text(
                f"Here it is: \"{name}\" {target}.\n\n"
                "Send me one or multiple messages you want to include in the post. It can be anything — a text, photo, video, even a sticker."
            )
            return WAITING_FOR_MESSAGE
            
        elif data == "show_actions":
            await query.edit_message_reply_markup(reply_markup=post_manager_keyboard(show_actions=True))
            return WAITING_FOR_MESSAGE
            
        elif data == "preview":
            draft = ud.get('draft_html', "Error loading draft.")
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
            target = ud.get('target_channel')
            fmt = ud.get('fmt', 'HTML')
            
            try:
                await context.bot.send_message(chat_id=target, text=draft, parse_mode=fmt)
                name = "SILENT JOD EXE 7" if "jod" in target else "SILENT MOD"
                await query.edit_message_text(f"Done!\n\n1 message ready to be sent to {name} {target}.")
            except Exception as e:
                await query.edit_message_text(f"Error: Make sure the bot is an Admin in {target}.")
                
            await asyncio.sleep(1.5)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Here you can create rich posts, view stats and accomplish other tasks.",
                reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END

        elif data == "dummy":
             await query.answer("Menu button clicked.", show_alert=False)

    except BadRequest as e:
        # Prevents crash if the user spams a toggle button too fast
        pass

async def receive_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Save the formatting based on the user's settings choice
    fmt = context.user_data.get('fmt', 'HTML')
    context.user_data['draft_html'] = update.message.text_html if fmt == 'HTML' else update.message.text_markdown_v2
    
    target = context.user_data.get('target_channel', "Channel")
    name = "SILENT JOD EXE 7" if "jod" in target else "SILENT MOD"
    
    await update.message.reply_text(
        f"1 message ready to be sent to {name} {target}.",
        reply_markup=post_manager_keyboard(show_actions=False)
    )
    return WAITING_FOR_MESSAGE

# --- BACKGROUND AUTO-REACTOR ---
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
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Advanced Admin Interface
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_admin),
            CallbackQueryHandler(handle_callbacks)
        ],
        states={
            WAITING_FOR_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_post),
                CallbackQueryHandler(handle_callbacks)
            ]
        },
        fallbacks=[CommandHandler('start', start_admin)]
    )
    
    app.add_handler(conv_handler)
    
    # Auto-Reacts to all new posts in channels seamlessly
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_react))
    
    print("Full System Online!")
    app.run_polling()
