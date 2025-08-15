import os
import sqlite3
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

# ===== تنظیمات =====
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970  # آیدی گروه

# ===== پایگاه داده =====
DB_FILE = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS members (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        joined_at TEXT,
        verified INTEGER DEFAULT 0,
        warned INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def add_member(user_id, full_name, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO members (user_id, full_name, username, joined_at) VALUES (?, ?, ?, ?)",
              (user_id, full_name, username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def mark_verified(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE members SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_unverified():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, joined_at, warned FROM members WHERE verified = 0")
    data = c.fetchall()
    conn.close()
    return data

def remove_member(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ===== وضعیت موقت کاربران =====
user_states = {}

# ===== توابع ربات =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "سلام! لطفاً برای احراز هویت روی دکمه زیر بزنید."
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
    user = update.message.from_user

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆔 {user.id}\n👤 نام: {text}\nنام کاربری: @{user.username or 'ندارد'}"
        )
        user_states[user_id] = "ASK_PHONE"
        keyboard = [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("شماره تماس خود را ارسال کنید", reply_markup=reply_markup)

    elif user_states.get(user_id) == "ASK_PHONE":
        await update.message.reply_text("⚠️ لطفاً از دکمه ارسال شماره تماس استفاده کنید.")

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
        await update.message.reply_text("📷 لطفاً عکس پروژه مسکن ملی خود را ارسال کنید.")

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
        mark_verified(user_id)
        user_states.pop(user_id, None)
        await update.message.reply_text("✅ احراز هویت شما با موفقیت انجام شد.")

async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if user_states.get(update.message.from_user.id) == "ASK_PHOTO":
        await update.message.reply_text("⚠️ لطفاً عکس ارسال کنید.")

async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        add_member(member.id, member.full_name, member.username)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"👋 {member.full_name} خوش آمدید! لطفاً ظرف ۳ روز آینده در ربات احراز هویت کنید."
        )

async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    unverified = get_unverified()
    for user_id, joined_at, warned in unverified:
        join_date = datetime.fromisoformat(joined_at)
        days_in_group = (now - join_date).days

        if days_in_group < 3:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⚠️ <a href='tg://user?id={user_id}'>کاربر</a> هنوز احراز هویت نکرده!",
                parse_mode="HTML"
            )
        else:
            await context.bot.ban_chat_member(GROUP_ID, user_id)
            remove_member(user_id)
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⛔ <a href='tg://user?id={user_id}'>کاربر</a> به دلیل عدم احراز هویت حذف شد.",
                parse_mode="HTML"
            )

# ===== اجرای ربات =====
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_photo))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_check, "interval", days=1, args=[app])
    scheduler.start()

    app.run_polling()
