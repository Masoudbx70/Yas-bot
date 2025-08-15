import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")  # توکن رو از Railway Variables می‌گیره
ADMIN_ID = 5872842793  # آی‌دی عددی مدیر

# دیکشنری برای ذخیره وضعیت کاربران
user_states = {}

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# وقتی دکمه احراز هویت رو می‌زنند
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# دریافت پیام از کاربر
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        # ارسال جواب کاربر به مدیر
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {user_id}: {text}")
        await update.message.reply_text("اطلاعات شما ثبت شد ✅")
        user_states.pop(user_id, None)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()
