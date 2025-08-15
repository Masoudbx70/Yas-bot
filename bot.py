import os
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ========== تنظیمات ==========
TOKEN = os.getenv("BOT_TOKEN")  # توکن از Railway Variables
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970

# ========== دیتابیس ==========
def init_db():
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            joined_at TEXT,
            verified INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_member(user_id, full_name, username):
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO members (user_id, full_name, username, joined_at, verified)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username, datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()

def verify_member(user_id):
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    c.execute("UPDATE members SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_unverified_members():
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, joined_at FROM members WHERE verified = 0")
    rows = c.fetchall()
    conn.close()
    return rows

def remove_member(user_id):
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ========== وضعیت موقت احراز هویت ==========
user_states = {}

# ========== هندلرها ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام! لطفاً برای احراز هویت روی دکمه زیر کلیک کنید 👇",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام و نام خانوادگی خود را وارد کنید:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 {text}\n🆔 {user.id}\n📛 نام کاربری: @{user.username or 'ندارد'}"
        )
        user_states[user_id] = "ASK_PHONE"
        keyboard = [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("شماره تماس خود را ارسال کنید:", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_PHONE":
        await update.message.reply_text("لطفاً شماره خود را از دکمه ارسال شماره تماس بفرستید.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_PHONE":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"☎️ شماره تماس {user.full_name}: {contact.phone_number}"
        )
        user_states[user_id] = "ASK_PHOTO"
        await update.message.reply_text("📷 لطفاً عکس اسکرین‌ شات پروژه را ارسال کنید:")

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
        verify_member(user_id)
        user_states.pop(user_id, None)

        keyboard = [[InlineKeyboardButton("ورود به گروه", url="https://t.me/+gZ6LwhT4cQpmYWJk")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ احراز هویت با موفقیت انجام شد.", reply_markup=reply_markup)

async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        add_member(member.id, member.full_name, member.username)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"👋 {member.full_name} خوش آمدید! لطفاً ظرف ۳ روز آینده در ربات احراز هویت کنید."
        )

# چک روزانه
async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for user_id, full_name, joined_at in get_unverified_members():
        join_time = datetime.fromisoformat(joined_at)
        days_in_group = (now - join_time).days

        if days_in_group < 3:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⚠️ <a href='tg://user?id={user_id}'>{full_name}</a> هنوز احراز هویت نکرده!",
                parse_mode="HTML"
            )
        else:
            await context.bot.ban_chat_member(GROUP_ID, user_id)
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⛔ <a href='tg://user?id={user_id}'>{full_name}</a> به دلیل عدم احراز هویت حذف شد.",
                parse_mode="HTML"
            )
            remove_member(user_id)

# ========== اجرای ربات ==========
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_check, "interval", days=1, args=[app])
    scheduler.start()

    app.run_polling()
