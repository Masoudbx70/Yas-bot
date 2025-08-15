import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
WEBHOOK_URL = f"https://{os.getenv('RAILWAY_STATIC_URL')}/{TOKEN}"

user_states = {}
app_tg = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {user_id}: {text}")
        await update.message.reply_text("اطلاعات شما ثبت شد ✅")
        user_states.pop(user_id, None)

app_tg.add_handler(CommandHandler("start", start))
app_tg.add_handler(CallbackQueryHandler(button_click))
app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_tg.bot)
    app_tg.update_queue.put(update)
    return "OK", 200

@flask_app.before_first_request
def set_webhook():
    app_tg.bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
