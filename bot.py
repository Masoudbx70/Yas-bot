import os
import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970  # آیدی گروه

user_states = {}
registered_users = {}  # {user_id: registration_date}

# مرحله ۱: استارت و احراز هویت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام 👋\nبرای احراز هویت در پروژه پویان بتن نیشابور، روی دکمه زیر کلیک کنید."
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# دکمه احراز هویت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام و نام خانوادگی خود را وارد کنید:")

# دریافت نام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        registered_users[user_id] = {"name": text, "date": datetime.datetime.now()}
        await context.bot.send_message(ADMIN_ID, f"👤 نام: {text}\n🆔 آیدی: {user_id}\n🔗 @{update.message.from_user.username or 'ندارد'}")
        user_states[user_id] = "ASK_PHONE"

        button = KeyboardButton("ارسال شماره تماس 📱", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("شماره تماس خود را ارسال کنید:", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_PHONE":
        await update.message.reply_text("لطفاً از دکمه مخصوص ارسال شماره استفاده کنید 📱")

    elif user_states.get(user_id) == "ASK_PHOTO":
        await update.message.reply_text("❌ لطفاً فقط عکس ارسال کنید.")

# دریافت شماره
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    phone = update.message.contact.phone_number
    registered_users[user_id]["phone"] = phone

    await context.bot.send_message(ADMIN_ID, f"📞 شماره تماس کاربر {user_id}: {phone}")
    user_states[user_id] = "ASK_PHOTO"
    await update.message.reply_text("📷 لطفاً اسکرین‌شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید:")

# دریافت عکس
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        photo_file_id = update.message.photo[-1].file_id
        registered_users[user_id]["photo"] = photo_file_id
        await context.bot.send_photo(ADMIN_ID, photo_file_id, caption=f"📷 عکس کاربر {user_id}")

        user_states.pop(user_id, None)
        # لینک گروه
        keyboard = [[InlineKeyboardButton("📌 لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ احراز هویت شما کامل شد.\nبرای ورود به گروه روی دکمه زیر کلیک کنید:", reply_markup=reply_markup)

# ارسال لیست افراد احراز نشده
async def send_unverified_list(context: ContextTypes.DEFAULT_TYPE):
    chat = await context.bot.get_chat(GROUP_ID)
    members = await context.bot.get_chat_administrators(GROUP_ID)
    member_ids = [m.user.id for m in members]

    unverified = [uid for uid in member_ids if uid not in registered_users]
    if unverified:
        text = "🚨 لیست افرادی که هنوز احراز هویت نکرده‌اند:\n"
        for uid in unverified:
            text += f"- [{uid}](tg://user?id={uid})\n"
        await context.bot.send_message(GROUP_ID, text, parse_mode="Markdown")

        # مسدود کردن بعد از 3 روز
        now = datetime.datetime.now()
        for uid in unverified:
            join_time = registered_users.get(uid, {}).get("date", now)
            if (now - join_time).days >= 3:
                await context.bot.ban_chat_member(GROUP_ID, uid)

# راه‌اندازی ربات
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# زمان‌بندی
scheduler = AsyncIOScheduler()
scheduler.add_job(send_unverified_list, "interval", days=1, args=[app])
schedu
