import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your Paper Writing Agent.\n\n"
        "I can help you write academic papers with a team of AI agents.\n\n"
        "Commands:\n"
        "/newpaper <title> — Start a new paper\n"
        "/analyze <github_url> — Analyze your code & experiments\n"
        "/outline — Generate or show paper outline\n"
        "/write <section> — Write a section\n"
        "/review — Review current draft\n"
        "/format <style> — Format citations (ieee, apa, acm)\n"
        "/mode fast — Switch all agents to Claude Haiku\n"
        "/mode balanced — Restore default models\n"
        "/status — Show current paper state\n"
        "/cost — Show token usage for this session"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Got it: {update.message.text}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
