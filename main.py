from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8335740705:AAFeYZinoZ3rN-_l1rW7y4DUsyWJzhvhcLI"

# In-memory storage (temporary)
users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    keyboard = [
        ["👦 Male", "👧 Female"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Hello 👋\n\nWelcome to Lonely Talks Bot 💙\n\nPlease select your gender:",
        reply_markup=reply_markup
    )

async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text not in ["👦 Male", "👧 Female"]:
        await update.message.reply_text("Please select gender using the buttons 🙂")
        return

    gender = "male" if "Male" in text else "female"

    users[user_id] = {
        "gender": gender,
        "status": "idle"
    }

    await update.message.reply_text(
        f"✅ Gender saved!\nYou selected: {gender.capitalize()}\n\nTap below when you're ready.",
        reply_markup=ReplyKeyboardMarkup(
            [["🔍 Find a chat partner"]],
            resize_keyboard=True
        )
    )

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Please start again using /start")
        return

    users[user_id]["status"] = "searching"
    await update.message.reply_text("🔍 Searching for a chat partner...")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(👦 Male|👧 Female)$"), handle_gender))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔍 Find a chat partner$"), find_match))

app.run_polling()
