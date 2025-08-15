import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = os.getenv("BOT_TOKEN")  # توکن ربات رو توی Railway ست کن
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970

user_states = {}
user_data = {}
verified_users = {}

# مرحله اول: شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# کلیک روی دکمه احراز هویت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# دریافت نام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        user_data[user_id] = {"name": text}
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"کاربر {update.message.from_user.full_name} ({user_id})\nنام: {text}")

        # سوال شماره تماس
        user_states[user_id] = "ASK_PHONE"
        keyboard = [[KeyboardButton("ارسال شماره تماس 📱", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_PHONE":
        await update.message.reply_text("لطفا از دکمه ارسال شماره تماس استفاده کنید 📱")

    elif user_states.get(user_id) == "ASK_IMAGE":
        await update.message.reply_text("⚠️ لطفا فقط تصویر ارسال کنید")

# دریافت شماره تماس
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    phone = update.message.contact.phone_number
    user_data[user_id]["phone"] = phone
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"کاربر {update.message.from_user.full_name} ({user_id})\nشماره تماس: {phone}")

    # سوال تصویر
    user_states[user_id] = "ASK_IMAGE"
    await update.message.reply_text("لطفا اسکرین شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید")

# دریافت تصویر
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_IMAGE":
        photo_file = await update.message.photo[-1].get_file()
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file.file_id, caption=f"تصویر از {update.message.from_user.full_name} ({user_id})")

        # اتمام مراحل
        verified_users[user_id] = datetime.now()
        user_states.pop(user_id, None)
        await update.message.reply_text(
            "✅ احراز هویت شما با موفقیت انجام شد",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
            )
        )

# چک روزانه
async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    members_to_warn = []

    for user_id, join_time in user_data.items():
        if user_id not in verified_users:
            days_passed = (now - join_time["join_date"]).days
            if days_passed < 3:
                members_to_warn.append(user_id)
            else:
                try:
                    await context.bot.ban_chat_member(GROUP_ID, user_id)
                    await context.bot.send_message(GROUP_ID, f"🚫 کاربر <a href='tg://user?id={user_id}'>این کاربر</a> به دلیل عدم احراز هویت مسدود شد", parse_mode="HTML")
                except:
                    pass

    if members_to_warn:
        mention_list = "\n".join([f"<a href='tg://user?id={uid}'>این کاربر</a>" for uid in members_to_warn])
        await context.bot.send_message(GROUP_ID, f"⚠️ این کاربران هنوز احراز هویت نکرده‌اند و تا ۳ روز فرصت دارند:\n{mention_list}", parse_mode="HTML")

# شروع برنامه
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# زمان‌بندی چک روزانه
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: app.job_queue.run_once(daily_check, 0), "interval", days=1)
scheduler.start()

if __name__ == "__main__":
    app.run_polling()
