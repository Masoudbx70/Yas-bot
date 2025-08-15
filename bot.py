import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========== تنظیمات ==========
TOKEN = os.getenv("BOT_TOKEN")  # توکن رو از Railway Variables می‌گیره
ADMIN_ID = 5872842793           # آی‌دی عددی مدیر
GROUP_ID = --1002483971970      # آیدی عددی گروه (تغییر بده)

# ========== متغیرهای ذخیره ==========
user_states = {}      # وضعیت کاربران در احراز هویت
group_members = {}    # اطلاعات اعضای گروه

# ================================
# 1. شروع کاربر
# ================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# ================================
# 2. کلیک روی دکمه احراز هویت
# ================================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# ================================
# 3. پردازش پیام‌ها
# ================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_NAME":
        # ارسال جواب کاربر به مدیر
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆔 {user.id}\n👤 نام: {text}\nنام کاربری: @{user.username or 'ندارد'}"
        )
        # مرحله بعد: شماره تلفن
        user_states[user_id] = "ASK_PHONE"
        keyboard = [[KeyboardButton("ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("📞 شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_PHONE":
        await update.message.reply_text("⚠️ لطفاً از دکمه ارسال شماره تماس استفاده کنید.")

# ================================
# 4. دریافت شماره تلفن
# ================================
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_PHONE":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📞 شماره تماس {user.full_name}: {contact.phone_number}"
        )
        # مرحله بعد: ارسال تصویر
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text(
            "📷 لطفاً اسکرین شات مربوط به قسمت پروژه در سایت مسکن ملی را ارسال کنید."
        )

# ================================
# 5. دریافت تصویر
# ================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_PHOTO":
        photo_file = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file,
            caption=f"📷 عکس از {user.full_name} (@{user.username or 'ندارد'})"
        )
        user_states.pop(user_id, None)  # پاک کردن وضعیت
        mark_verified(user_id)  # ثبت احراز هویت در گروه

        # دکمه لینک گروه
        keyboard = [[InlineKeyboardButton("لینک گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ احراز هویت با موفقیت انجام شد.", reply_markup=reply_markup)

# اگر کاربر به جای عکس متن فرستاد
async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_states.get(user_id) == "ASK_PHOTO":
        await update.message.reply_text("⚠️ لطفاً فقط عکس ارسال کنید.")

# ================================
# 6. مدیریت اعضای گروه
# ================================
async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        group_members[member.id] = {
            "joined": datetime.now(),
            "warned": 0,
            "verified": False
        }
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"👋 {member.full_name} خوش آمدید! لطفاً ظرف ۳ روز آینده در ربات احراز هویت کنید."
        )

# ثبت احراز هویت
def mark_verified(user_id):
    if user_id in group_members:
        group_members[user_id]["verified"] = True

# چک روزانه
async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for user_id, data in list(group_members.items()):
        if not data["verified"]:
            days_in_group = (now - data["joined"]).days
            if days_in_group < 3:
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"⚠️ <a href='tg://user?id={user_id}'>کاربر</a> هنوز احراز هویت نکرده!",
                    parse_mode="HTML"
                )
            else:
                await context.bot.ban_chat_member(GROUP_ID, user_id)
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"⛔ <a href='tg://user?id={user_id}'>کاربر</a> به دلیل عدم احراز هویت حذف شد.",
                    parse_mode="HTML"
                )
                group_members.pop(user_id, None)

# ================================
# 7. اجرای ربات
# ================================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_photo))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))

# زمان‌بندی چک روزانه
scheduler = AsyncIOScheduler()
scheduler.add_job(daily_check, "interval", days=1, args=[app])
scheduler.start()

if __name__ == "__main__":
    app.run_polling()
