import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970  # آیدی گروه

user_states = {}

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
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {update.message.from_user.full_name} ({user_id}): {text}")
        
        # مرحله بعد: درخواست شماره تماس
        keyboard = [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        user_states[user_id] = "ASK_CONTACT"
        await update.message.reply_text("شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact

    if user_states.get(user_id) == "ASK_CONTACT":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"شماره تماس کاربر {update.message.from_user.full_name} ({user_id}): {contact.phone_number}")
        
        # مرحله بعد: درخواست تصویر
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text("لطفا اسکرین شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید 📷")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_states.get(user_id) == "ASK_PHOTO":
        photo_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=f"تصویر کاربر {update.message.from_user.full_name} ({user_id})")
        
        # پایان مراحل → ارسال لینک گروه
        keyboard = [[InlineKeyboardButton("لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ اطلاعات شما ثبت شد.\nبرای ورود به گروه روی دکمه زیر کلیک کنید:", reply_markup=reply_markup)
        
        # ارسال پیام خوش‌آمد به گروه
        await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 {update.message.from_user.full_name} با موفقیت احراز هویت شد و به گروه اضافه شد!")

        user_states.pop(user_id, None)

async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        await update.message.reply_text("⚠️ لطفا فقط تصویر ارسال کنید.")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.ALL & ~filters.PHOTO & ~filters.CONTACT, handle_non_photo))

if __name__ == "__main__":
    app.run_polling()
