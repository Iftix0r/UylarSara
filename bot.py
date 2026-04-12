import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("TELEGRAM_WEBAPP_URL", "https://sarauylar.uz")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "🏠 SaraUylar saytini ochish",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "🏡 *SaraUylar* — ko'chmas mulk e'lonlari platformasi.\n\n"
        "Quyidagi tugma orqali saytni to'g'ridan-to'g'ri Telegram ichida oching:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Buyruqlar:*\n\n"
        "/start — Botni ishga tushirish\n"
        "/help — Yordam\n",
        parse_mode="Markdown"
    )


def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
