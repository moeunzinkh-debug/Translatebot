import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# 1. Logging Configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Web Server សម្រាប់ Render Port Binding (ការពារ Timed Out)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot status: Online. Port: 8080 bound.")

def run_port_listener():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"🌍 Web Server started on port {port}")
    server.serve_forever()

# 3. បញ្ជីភាសាទាំង ៧០
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
    msg = (
        "👋 **សួស្តី! ខ្ញុំជា AI Translator Bot**\n\n"
        "ខ្ញុំអាចបកប្រែ Slang និង Idioms បានយ៉ាងឆ្លាតវៃ។\n\n"
        "🛠 **របៀបប្រើប្រាស់:**\n"
        "• ប្រើ `/list` ដើម្បីមើលភាសាទាំង ៧០\n"
        "• ប្រើ Command ភាសា (ឧទាហរណ៍: `/en`, `/kh`, `/ch`)\n"
        "• បន្ទាប់មកផ្ញើសារដែលអ្នកចង់បកប្រែ"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def list_languages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codes = sorted(LANG_CODES.keys())
    text = "🌐 **បញ្ជីភាសាដែលអាចប្រើបាន (ចុចដើម្បីប្តូរ):**\n\n"
    
    # បង្កើតជាតារាង ៥ ភាសាក្នុងមួយជួរ
    for i in range(0, len(codes), 4):
        line = " ".join([f"/{c}" for c in codes[i:i+4]])
        text += f"• {line}\n"
        
    await update.message.reply_text(text)

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.replace("/", "").lower()
    
    if command in LANG_CODES:
        lang_name = LANG_CODES[command]
        user_settings[user_id] = lang_name
        await update.message.reply_text(f"✅ ភាសាគោលដៅ៖ **{lang_name}**")

async def translate_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = user_settings.get(user_id, "Khmer")
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are a master translator. Translate the text to {target}. Explain idioms or slang naturally in {target} if found."},
                {"role": "user", "content": update.message.text}
            ],
            temperature=0.3,
        )
        await update.message.reply_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text("❌ AI កំពុងមានបញ្ហា។ សូមឆែក API Quota លើ Groq Dashboard។")

if __name__ == '__main__':
    # ១. បើក Port Listener (Threading)
    threading.Thread(target=run_port_listener, daemon=True).start()

    # ២. បង្កើត Bot Instance
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    # ៣. Register Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_languages))
    
    # Loop ដើម្បីបង្កើត Command សម្រាប់គ្រប់ភាសា
    for cmd in LANG_CODES.keys():
        app.add_handler(CommandHandler(cmd, set_lang))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), translate_ai))

    logging.info("🚀 Bot is running...")
    app.run_polling()
