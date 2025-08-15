import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970  # آیدی گروه

user_states = {}
verified_users = set()  # لیست احراز هویت شده‌ها

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# کلیک روی دکمه شیشه‌ای
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# مرحله ۱: دریافت نام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {update.message.from_user.full_name} ({user_id}): {text}")
        
        # مرحله بعد: درخواست شماره تماس
        keyboard = [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        user_states[user_id] = "ASK_CONTACT"
        await update.message.reply_text("شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

# مرحله ۲: دریافت شماره تماس
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact

    if user_states.get(user_id) == "ASK_CONTACT":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"شماره تماس کاربر {update.message.from_user.full_name} ({user_id}): {contact.phone_number}")
        
        # مرحله بعد: درخواست تصویر
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text("لطفا اسکرین شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید 📷")

# مرحله ۳: دریافت تصویر
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_states.get(user_id) == "ASK_PHOTO":
        photo_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=f"تصویر کاربر {update.message.from_user.full_name} ({user_id})")
        
        # افزودن کاربر به لیست احراز هویت شده‌ها
        verified_users.add(user_id)

        # پایان مراحل → ارسال لینک گروه
        keyboard = [[InlineKeyboardButton("لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ اطلاعات شما ثبت شد.\nبرای ورود به گروه روی دکمه زیر کلیک کنید:", reply_markup=reply_markup)
        
        # پیام خوش‌آمد به گروه
        await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 {update.message.from_user.full_name} با موفقیت احراز هویت شد و به گروه اضافه شد!")

        user_states.pop(user_id, None)

# جلوگیری از ارسال غیرعکس
async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        await update.message.reply_text("⚠️ لطفا فقط تصویر ارسال کنید.")

# مدیریت پیام‌های گروه
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip().lower()

    # اگر احراز هویت نکرده
    if user_id not in verified_users:
        keyboard = [[InlineKeyboardButton("احراز هویت", url="https://t.me/hostpuyanbot?start=verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "شما احراز هویت در ربات انجام نداده‌اید.\nلطفا دکمه زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
        return

    # اگر پیام سلام بود
    if message_text in ["سلام", "salam", "سلام علیکم"]:
        await update.message.reply_text(f"سلام و عرض ادب خدمت {update.effective_user.first_name} 🌹")

# ساخت اپلیکیشن
app = ApplicationBuilder().token(TOKEN).build()

# هندلرها
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))
app.add_handler(MessageHandler(filters.CONTACT & filters.ChatType.PRIVATE, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo))
app.add_handler(MessageHandler(filters.ALL & ~filters.PHOTO & ~filters.CONTACT & filters.ChatType.PRIVATE, handle_non_photo))
app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, group_message_handler))

if __name__ == "__main__":
    app.run_polling()
