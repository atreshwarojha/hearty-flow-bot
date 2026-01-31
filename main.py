from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8335740705:AAFeYZinoZ3rN-_l1rW7y4DUsyWJzhvhcLI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    gender = update.message.text

    if gender == "👦 Male":
        await update.message.reply_text("Thanks! You selected Male ✅")
    elif gender == "👧 Female":
        await update.message.reply_text("Thanks! You selected Female ✅")
    else:
        await update.message.reply_text("Please choose from the buttons 🙂")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender))

app.run_polling()
