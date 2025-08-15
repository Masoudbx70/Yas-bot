import os
import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.helpers import mention_html
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= تنظیمات =================
TOKEN = os.getenv("BOT_TOKEN")  # توکن از Railway Variables
ADMIN_ID = 5872842793           # آیدی عددی مدیر
GROUP_ID = -1002483971970       # آیدی عددی گروه

# ================= دیتابیس =================
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    joined TIMESTAMP,
    verified INTEGER DEFAULT 0,
    warned INTEGER DEFAULT 0
)
""")
conn.commit()

def add_member(user_id, full_name, username):
    c.execute("""
        INSERT OR REPLACE INTO members (user_id, full_name, username, joined, verified, warned)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, full_name, username, datetime.now(), 0, 0))
    conn.commit()

def set_verified(user_id):
    c.execute("UPDATE members SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_unverified():
    c.execute("SELECT user_id, full_name, joined, warned FROM members WHERE verified = 0")
    return c.fetchall()

def delete_member(user_id):
    c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
    conn.commit()

# ================= شروع کاربر =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام، این ربات برای احراز هویت شما طراحی شده و اطلاعات شما محفوظ خواهد ماند.",
        reply_markup=reply_markup
    )

# ================= کلیک روی دکمه احراز هویت =================
user_states = {}

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# ================= دریافت نام =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆔 {user.id}\n👤 نام: {text}\nنام کاربری: @{user.username or 'ندارد'}"
        )
        user_states[user_id] = "ASK_PHONE"
        keyboard = [[KeyboardButton("ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("📞 شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

# ================= دریافت شماره =================
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_PHONE":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📞 شماره تماس {user.full_name}: {contact.phone_number}"
        )
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text(
            "📷 لطفاً اسکرین شات مربوط به قسمت پروژه را ارسال کنید."
        )

# ================= دریافت عکس =================
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
        user_states.pop(user_id, None)
        set_verified(user_id)

        keyboard = [[InlineKeyboardButton("ورود به گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ احراز هویت با موفقیت انجام شد.", reply_markup=reply_markup)

# ================= عضو جدید =================
async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        add_member(member.id, member.full_name, member.username)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"👋 {member.full_name} خوش آمدید! لطفاً ظرف ۳ روز آینده در ربات احراز هویت کنید."
        )

# ================= چک روزانه =================
async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for user_id, full_name, joined, warned in get_unverified():
        days_in_group = (now - datetime.fromisoformat(joined)).days
        if days_in_group < 3:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⚠️ {mention_html(user_id, full_name)} هنوز احراز هویت نکرده!",
                parse_mode="HTML"
            )
        else:
            try:
                await context.bot.ban_chat_member(GROUP_ID, user_id)
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"⛔ {mention_html(user_id, full_name)} به دلیل عدم احراز هویت حذف شد.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ban error: {e}")
            delete_member(user_id)

# ================= اجرای ربات =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))
app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))

# اجرای چک روزانه هر 24 ساعت
app.job_queue.run_repeating(daily_check, interval=86400, first=10)

if __name__ == "__main__":
    app.run_polling()
