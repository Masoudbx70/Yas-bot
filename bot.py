import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793  # آیدی عددی مدیر

user_states = {}

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند",
        reply_markup=reply_markup
    )

# کلیک روی دکمه احراز هویت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام و نام خانوادگی خود را وارد کنید:")

# مدیریت پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        # ذخیره نام
        context.user_data["name"] = text
        user_states[user_id] = "ASK_PHONE"

        # ارسال دکمه درخواست شماره
        button = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("لطفاً شماره تماس خود را ارسال کنید:", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_SCREENSHOT":
        await update.message.reply_text("⚠ لطفاً فقط عکس ارسال کنید، متن پذیرفته نمی‌شود.")

# مدیریت دریافت شماره تماس
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact

    context.user_data["phone"] = contact.phone_number
    user_states[user_id] = "ASK_SCREENSHOT"

    await update.message.reply_text(
        "📷 لطفاً اسکرین‌شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید."
    )

# مدیریت دریافت عکس
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1].file_id

    if user_states.get(user_id) == "ASK_SCREENSHOT":
        name = context.user_data.get("name", "نام نامشخص")
        phone = context.user_data.get("phone", "شماره نامشخص")

        caption = f"📌 اطلاعات کاربر:\n👤 نام: {name}\n📞 شماره: {phone}\n🆔 آیدی: {user_id}"

        # ارسال عکس به ادمین
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption)

        await update.message.reply_text("✅ اطلاعات شما ثبت شد. سپاس 🙏")
        user_states.pop(user_id, None)

# ساخت برنامه
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()
