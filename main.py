import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793

user_states = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند",
        reply_markup=reply_markup
    )

# دکمه احراز هویت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# دریافت پیام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # مرحله ۱: دریافت نام
    if user_states.get(user_id) == "ASK_NAME":
        user_states[user_id] = {"name": text, "step": "ASK_PHONE"}
        contact_button = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("شماره تماس خود را ارسال کنید:", reply_markup=reply_markup)

    # مرحله ۳: سوال بعدی
    elif user_states.get(user_id, {}).get("step") == "ASK_EXTRA":
        user_states[user_id]["extra_info"] = text
        data = user_states[user_id]
        user = update.message.from_user
        info = (
            f"📌 اطلاعات کاربر:\n"
            f"🆔 ID: {user.id}\n"
            f"👤 نام: {user.first_name or '—'}\n"
            f"👥 نام خانوادگی: {user.last_name or '—'}\n"
            f"💬 نام کاربری: @{user.username if user.username else '—'}\n"
            f"🌐 زبان: {user.language_code or '—'}\n"
            f"🔗 لینک پروفایل: tg://user?id={user.id}\n"
            f"✏️ نام وارد شده: {data['name']}\n"
            f"📱 شماره تماس: {data['phone']}\n"
            f"📝 اطلاعات اضافه: {data['extra_info']}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=info)
        await update.message.reply_text("✅ تمام اطلاعات شما ثبت شد.")
        user_states.pop(user_id, None)

# دریافت شماره تماس
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    phone_number = update.message.contact.phone_number
    if user_states.get(user_id, {}).get("step") == "ASK_PHONE":
        user_states[user_id]["phone"] = phone_number
        user_states[user_id]["step"] = "ASK_EXTRA"
        await update.message.reply_text("✅ شماره تماس شما ثبت شد.\nحالا سوال سوم: محل کار یا توضیحات خود را وارد کنید:")

# اجرای ربات
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()
