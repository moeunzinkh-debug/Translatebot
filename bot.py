import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# កំណត់ការបង្ហាញ Log ដើម្បីងាយស្រួលឆែកមើលកំហុសលើ Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# បញ្ជីកូដភាសាសរុប ៧០
LANG_CODES = {
    "kh": "km", "en": "en", "ch": "zh-CN", "th": "th", "vn": "vi", "jp": "ja", "kr": "ko",
    "fr": "fr", "de": "de", "ru": "ru", "es": "es", "it": "it", "in": "hi", "id": "id",
    "my": "ms", "ph": "tl", "ar": "ar", "pt": "pt", "tr": "tr", "nl": "nl", "pl": "pl",
    "sv": "sv", "da": "da", "fi": "fi", "no": "no", "cs": "cs", "el": "el", "iw": "he",
    "ro": "ro", "uk": "uk", "hu": "hu", "sk": "sk", "bg": "bg", "hr": "hr", "sr": "sr",
    "sl": "sl", "et": "et", "lv": "lv", "lt": "lt", "fa": "fa", "bn": "bn", "pa": "pa",
    "gu": "gu", "ta": "ta", "te": "te", "kn": "kn", "ml": "ml", "si": "si", "ne": "ne",
    "lo": "lo", "myan": "my", "ka": "ka", "hy": "hy", "az": "az", "kk": "kk", "uz": "uz",
    "tg": "tg", "tk": "tk", "ky": "ky", "mn": "mn", "af": "af", "sq": "sq", "am": "am",
    "eu": "eu", "be": "be", "bs": "bs", "ca": "ca", "gl": "gl", "is": "is", "sw": "sw"
}

user_settings = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 សួស្តី! ខ្ញុំជា Bot បកប្រែភាសាដែលរៀបចំសម្រាប់ Render។\n"
        "👉 វាយអក្សរដើម្បីបកប្រែ (Default: ខ្មែរ)\n"
        "👉 ប្រើ `/list` ដើម្បីមើលកូដភាសាទាំង ៧០\n"
        "👉 ឧទាហរណ៍៖ វាយ `/en` រួចផ្ញើសារដើម្បីបកប្រែជាអង់គ្លេស"
    )

async def list_languages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codes = list(LANG_CODES.keys())
    text = "🌐 **បញ្ជីកូដភាសា (៧០):**\n\n"
    for i in range(0, len(codes), 5):
        text += " • " + ", ".join([f"/{c}" for c in codes[i:i+5]]) + "\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.replace("/", "").lower()
    if command in LANG_CODES:
        user_settings[user_id] = LANG_CODES[command]
        await update.message.reply_text(f"✅ ប្តូរទៅភាសា: **{command.upper()}**")

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = user_settings.get(user_id, "km")
    try:
        translated = GoogleTranslator(source='auto', target=target).translate(update.message.text)
        await update.message.reply_text(translated)
    except Exception as e:
        logging.error(f"Translation Error: {e}")
        await update.message.reply_text("❌ មានបញ្ហាបច្ចេកទេស។")

if __name__ == '__main__':
    # ទាញយក API Token ពី Environment Variable ដែលអ្នកនឹងដាក់ក្នុង Render
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

    if not BOT_TOKEN:
        logging.error("រករង្វង់ TELEGRAM_TOKEN មិនឃើញក្នុង Environment Variables ទេ។")
        exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_languages))
    
    for cmd in LANG_CODES.keys():
        app.add_handler(CommandHandler(cmd, set_lang))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), translate_message))

    logging.info("Bot កំពុងដំណើរការលើ Render...")
    app.run_polling()
