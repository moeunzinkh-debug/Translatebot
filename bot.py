import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq

# 1. កំណត់ Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. បង្កើត Web Server ក្លែងក្លាយដើម្បីឆ្លើយតបទៅកាន់ Render (Port Binding)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running and port is bound!")

def run_port_listener():
    # Render ផ្ដល់ Port តាមរយៈ Environment Variable បើមិនមានទេយក 8080 ជា Default
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"🌍 Web Server started on port {port}")
    server.serve_forever()

# 3. កូដ Telegram Bot (ជាមួយ 70 ភាសា និង AI)
LANG_CODES = {
    "kh": "Khmer", "en": "English", "ch": "Chinese", "th": "Thai", "vn": "Vietnamese",
    "jp": "Japanese", "kr": "Korean", "fr": "French", "de": "German", "ru": "Russian",
    "es": "Spanish", "it": "Italian", "in": "Hindi", "id": "Indonesian", "my": "Malay",
    "ph": "Filipino", "ar": "Arabic", "pt": "Portuguese", "tr": "Turkish", "nl": "Dutch",
    "pl": "Polish", "sv": "Swedish", "da": "Danish", "fi": "Finnish", "no": "Norwegian",
    "cs": "Czech", "el": "Greek", "iw": "Hebrew", "ro": "Romanian", "uk": "Ukrainian",
    "hu": "Hungarian", "sk": "Slovak", "bg": "Bulgarian", "hr": "Croatian", "sr": "Serbian",
    "sl": "Slovenian", "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian", "fa": "Persian",
    "bn": "Bengali", "pa": "Punjabi", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "ml": "Malayalam", "si": "Sinhala", "ne": "Nepali", "lo": "Lao",
    "myan": "Burmese", "ka": "Georgian", "hy": "Armenian", "az": "Azerbaijani", "kk": "Kazakh",
    "uz": "Uzbek", "tg": "Tajik", "tk": "Turkmen", "ky": "Kyrgyz", "mn": "Mongolian",
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "eu": "Basque", "be": "Belarusian",
    "bs": "Bosnian", "ca": "Catalan", "gl": "Galician", "is": "Icelandic", "sw": "Swahili"
}

user_settings = {}
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🌐 បញ្ជីភាសាទាំង ៧០", callback_data='list_langs')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🚀 **AI Translator** ត្រៀមខ្លួនរួចរាល់!\nផ្ញើសារមកខ្ញុំដើម្បីបកប្រែ។", reply_markup=reply_markup, parse_mode='Markdown')

async def translate_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = user_settings.get(user_id, "Khmer")
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Translate to {target}: {update.message.text}"}],
            temperature=0.3,
        )
        await update.message.reply_text(completion.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ... (បន្ថែម Handler ផ្សេងៗដូចមុន)

if __name__ == '__main__':
    # កូដសំខាន់៖ បើក Port Listener ក្នុង Thread ថ្មីមួយ
    threading.Thread(target=run_port_listener, daemon=True).start()

    # បន្ទាប់មករត់ Telegram Bot
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), translate_ai))

    logging.info("🚀 Bot ដំណើរការជាមួយ Port Binding...")
    app.run_polling()
