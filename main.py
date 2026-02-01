import asyncio
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = "8335740705:AAFeYZinoZ3rN-_l1rW7y4DUsyWJzhvhcLI"

FREE_CHAT_DURATION = 30 * 60
PAID_30 = 30 * 60
PAID_60 = 60 * 60

# ================== DATABASE ==================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    free_used INTEGER DEFAULT 0
)
""")
conn.commit()

# ================== RUNTIME STATE ==================
waiting_males = []
waiting_females = []
active_chats = {}          # user_id -> partner_id
paid_time_balance = {}     # user_id -> seconds

# ================== HELPERS ==================
def user_free_used(user_id):
    cursor.execute(
        "SELECT free_used FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row and row[0] == 1

def mark_free_used(user1, user2):
    cursor.execute(
        "UPDATE users SET free_used = 1 WHERE user_id IN (?, ?)",
        (user1, user2)
    )
    conn.commit()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👦 Male", "👧 Female"]]
    await update.message.reply_text(
        "Welcome 👋\n\nPlease select your gender:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )

# ================== GENDER ==================
async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text not in ["👦 Male", "👧 Female"]:
        return

    gender = "male" if "Male" in text else "female"

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, gender) VALUES (?, ?)",
        (user_id, gender)
    )
    conn.commit()

    await update.message.reply_text(
        "✅ Gender saved.\n\nTap below to find a chat partner.",
        reply_markup=ReplyKeyboardMarkup(
            [["🔍 Find a chat partner"]],
            resize_keyboard=True,
        ),
    )

# ================== FIND MATCH ==================
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute(
        "SELECT gender FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text("Send /start first.")
        return

    gender = row[0]

    if gender == "male":
        if waiting_females:
            partner = waiting_females.pop(0)
            await start_chat(user_id, partner, context)
        else:
            waiting_males.append(user_id)
            await update.message.reply_text("⏳ Waiting for a female partner…")
    else:
        if waiting_males:
            partner = waiting_males.pop(0)
            await start_chat(partner, user_id, context)
        else:
            waiting_females.append(user_id)
            await update.message.reply_text("⏳ Waiting for a male partner…")

# ================== START CHAT ==================
async def start_chat(user1, user2, context):
    active_chats[user1] = user2
    active_chats[user2] = user1

    if not user_free_used(user1) and not user_free_used(user2):
        mark_free_used(user1, user2)

        await context.bot.send_message(
            user1, "💬 Connected!\n⏱ Free chat started (30 minutes)"
        )
        await context.bot.send_message(
            user2, "💬 Connected!\n⏱ Free chat started (30 minutes)"
        )

        asyncio.create_task(
            end_chat_after_time(user1, user2, context, FREE_CHAT_DURATION)
        )
    else:
        await show_paid_options(user1, user2, context)
        end_chat(user1, user2)

# ================== END CHAT TIMER ==================
async def end_chat_after_time(user1, user2, context, duration):
    await asyncio.sleep(duration)

    if user1 in active_chats and user2 in active_chats:
        await show_paid_options(user1, user2, context)
        end_chat(user1, user2)

# ================== PAID OPTIONS ==================
async def show_paid_options(user1, user2, context):
    keyboard = [
        ["⭐ 50 Stars – 30 minutes"],
        ["⭐ 90 Stars – 60 minutes"],
        ["❌ End chat"],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await context.bot.send_message(
        user1,
        "⏰ Session ended.\n\nContinue chatting?",
        reply_markup=markup,
    )
    await context.bot.send_message(
        user2,
        "⏰ Session ended.\n\nContinue chatting?",
        reply_markup=markup,
    )

# ================== RELAY ==================
async def relay_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in active_chats:
        await context.bot.send_message(active_chats[uid], update.message.text)

# ================== END CHAT ==================
def end_chat(user1, user2):
    active_chats.pop(user1, None)
    active_chats.pop(user2, None)

# ================== STARS PAYMENT ==================
async def handle_paid_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if text == "⭐ 50 Stars – 30 minutes":
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="30 Minute Chat",
            description="Continue chatting anonymously",
            payload="STARS_30",
            currency="XTR",
            prices=[LabeledPrice("30 min chat", 50)],
        )

    elif text == "⭐ 90 Stars – 60 minutes":
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="60 Minute Chat",
            description="Continue chatting anonymously",
            payload="STARS_60",
            currency="XTR",
            prices=[LabeledPrice("60 min chat", 90)],
        )

# ================== PAYMENT SUCCESS ==================
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload

    if payload == "STARS_30":
        paid_time_balance[uid] = paid_time_balance.get(uid, 0) + PAID_30
    else:
        paid_time_balance[uid] = paid_time_balance.get(uid, 0) + PAID_60

    await update.message.reply_text(
        "✅ Payment successful.\nFinding a new partner…"
    )

    await auto_rematch(uid, context)

# ================== AUTO REMATCH ==================
async def auto_rematch(uid, context):
    cursor.execute(
        "SELECT gender FROM users WHERE user_id = ?",
        (uid,)
    )
    gender = cursor.fetchone()[0]

    if gender == "male":
        if waiting_females:
            await start_paid_chat(uid, waiting_females.pop(0), context)
        else:
            waiting_males.append(uid)
    else:
        if waiting_males:
            await start_paid_chat(waiting_males.pop(0), uid, context)
        else:
            waiting_females.append(uid)

# ================== START PAID CHAT ==================
async def start_paid_chat(user1, user2, context):
    active_chats[user1] = user2
    active_chats[user2] = user1

    duration = paid_time_balance.get(user1, 0)
    paid_time_balance[user1] = 0

    await context.bot.send_message(user1, "💬 Paid chat started.")
    await context.bot.send_message(user2, "💬 Paid chat started.")

    asyncio.create_task(
        end_chat_after_time(user1, user2, context, duration)
    )

# ================== APP ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^(👦 Male|👧 Female)$"), handle_gender))
app.add_handler(MessageHandler(filters.Regex("^🔍 Find a chat partner$"), find_match))
app.add_handler(
    MessageHandler(
        filters.Regex(
            "^(⭐ 50 Stars – 30 minutes|⭐ 90 Stars – 60 minutes|❌ End chat)$"
        ),
        handle_paid_choice
    )
)
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_messages))

if __name__ == "__main__":
    app.run_polling()
