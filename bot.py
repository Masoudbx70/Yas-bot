import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970

user_states = {}
verified_users = set()
unverified_message_count = {}
blacklist_users = set()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    verified_users.add(user_id)  # ثبت به عنوان احراز شده بعد از مراحل
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# دکمه احراز هویت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# مرحله 1: دریافت نام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {update.message.from_user.full_name} ({user_id}): {text}")
        keyboard = [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        user_states[user_id] = "ASK_CONTACT"
        await update.message.reply_text("شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

# مرحله 2: دریافت شماره تماس
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    if user_states.get(user_id) == "ASK_CONTACT":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"شماره تماس کاربر {update.message.from_user.full_name} ({user_id}): {contact.phone_number}")
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text("لطفا اسکرین شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید 📷")

# مرحله 3: دریافت عکس
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        photo_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=f"تصویر کاربر {update.message.from_user.full_name} ({user_id})")
        verified_users.add(user_id)
        keyboard = [[InlineKeyboardButton("لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ اطلاعات شما ثبت شد.\nبرای ورود به گروه روی دکمه زیر کلیک کنید:", reply_markup=reply_markup)
        await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 {update.message.from_user.full_name} با موفقیت احراز هویت شد و به گروه اضافه شد!")
        user_states.pop(user_id, None)

# اگر کاربر متن بجای عکس فرستاد
async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        await update.message.reply_text("⚠️ لطفا فقط تصویر ارسال کنید.")

# مدیریت پیام‌های گروه
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip().lower()

    # اگر در لیست سیاه است
    if user_id in blacklist_users:
        return

    # پاسخ محترمانه به سلام
    if message_text in ["سلام", "salam", "سلام علیکم"]:
        await update.message.reply_text(f"سلام و عرض ادب خدمت {update.effective_user.first_name} 🌹")

    # بررسی احراز هویت
    if user_id not in verified_users:
        unverified_message_count[user_id] = unverified_message_count.get(user_id, 0) + 1

        if unverified_message_count[user_id] > 3:
            blacklist_users.add(user_id)
            await context.bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"🚫 کاربر [{update.effective_user.full_name}](tg://user?id={user_id}) به دلیل عدم احراز هویت مسدود شد.",
                parse_mode="Markdown"
            )
            return

        keyboard = [[InlineKeyboardButton("احراز هویت", url="https://t.me/hostpuyanbot?start=verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("شما احراز هویت در ربات انجام نداده‌اید.\nلطفا دکمه زیر را انتخاب کنید:", reply_markup=reply_markup)

# ساخت اپلیکیشن
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.GROUPS, handle_message))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.ALL & ~filters.PHOTO & ~filters.CONTACT & ~filters.ChatType.GROUPS, handle_non_photo))
app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, group_message_handler))

if __name__ == "__main__":
    app.run_polling()
