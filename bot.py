import os
import logging
import asyncio
import threading
import time
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from openai import OpenAI

# ១. កំណត់ Logging ដើម្បីងាយស្រួលមើល Error ក្នុង Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ២. បញ្ជីភាសាទាំង ៧០ ជាមួយទង់ជាតិ
LANG_CODES = {
    "kh": ("Khmer", "🇰🇭"), "en": ("English", "🇺🇸"), "ch": ("Chinese", "🇨🇳"), "th": ("Thai", "🇹🇭"), 
    "vn": ("Vietnamese", "🇻🇳"), "jp": ("Japanese", "🇯🇵"), "kr": ("Korean", "🇰🇷"), "fr": ("French", "🇫🇷"), 
    "de": ("German", "🇩🇪"), "ru": ("Russian", "🇷🇺"), "es": ("Spanish", "🇪🇸"), "it": ("Italian", "🇮🇹"), 
    "in": ("Hindi", "🇮🇳"), "id": ("Indonesian", "🇮🇩"), "my": ("Malay", "🇲🇾"), "ph": ("Filipino", "🇵🇭"), 
    "ar": ("Arabic", "🇸🇦"), "pt": ("Portuguese", "🇵🇹"), "tr": ("Turkish", "🇹🇷"), "nl": ("Dutch", "🇳🇱"),
    "pl": ("Polish", "🇵🇱"), "sv": ("Swedish", "🇸🇪"), "da": ("Danish", "🇩🇰"), "fi": ("Finnish", "🇫🇮"), 
    "no": ("Norwegian", "🇳🇴"), "cs": ("Czech", "🇨🇿"), "el": ("Greek", "🇬🇷"), "iw": ("Hebrew", "🇮🇱"), 
    "ro": ("Romanian", "🇷🇴"), "uk": ("Ukrainian", "🇺🇦"), "hu": ("Hungarian", "🇭🇺"), "sk": ("Slovak", "🇸🇰"), 
    "bg": ("Bulgarian", "🇧🇬"), "hr": ("Croatian", "🇭🇷"), "sr": ("Serbian", "🇷🇸"), "sl": ("Slovenian", "🇸🇮"), 
    "et": ("Estonian", "🇪🇪"), "lv": ("Latvian", "🇱🇻"), "lt": ("Lithuanian", "🇱🇹"), "fa": ("Persian", "🇮🇷"),
    "bn": ("Bengali", "🇧🇩"), "pa": ("Punjabi", "🇮🇳"), "gu": ("Gujarati", "🇮🇳"), "ta": ("Tamil", "🇱🇰"), 
    "te": ("Telugu", "🇮🇳"), "kn": ("Kannada", "🇮🇳"), "ml": ("Malayalam", "🇮🇳"), "si": ("Sinhala", "🇱🇰"), 
    "ne": ("Nepali", "🇳🇵"), "lo": ("Lao", "🇱🇦"), "myan": ("Burmese", "🇲🇲"), "ka": ("Georgian", "🇬🇪"), 
    "hy": ("Armenian", "🇦🇲"), "az": ("Azerbaijani", "🇦🇿"), "kk": ("Kazakh", "🇰🇿"), "uz": ("Uzbek", "🇺🇿"), 
    "tg": ("Tajik", "🇹🇯"), "tk": ("Turkmen", "🇹🇲"), "ky": ("Kyrgyz", "🇰🇬"), "mn": ("Mongolian", "🇲🇳"),
    "af": ("Afrikaans", "🇿🇦"), "sq": ("Albanian", "🇦🇱"), "am": ("Amharic", "🇪ត"), "eu": ("Basque", "🇪🇸"), 
    "be": ("Belarusian", "🇧🇾"), "bs": ("Bosnian", "🇧🇦"), "ca": ("Catalan", "🇪🇸"), "gl": ("Galician", "🇪🇸"), 
    "is": ("Icelandic", "🇮🇸"), "sw": ("Swahili", "🇰🇪")
}

# ៣. ទាញយក API Keys ពី Environment Variables
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GRO_KEY = os.environ.get("GROQ_API_KEY")
SEA_KEY = os.environ.get("SEA_LION_API_KEY")

# ត្រួតពិនិត្យ Token
if not TOKEN:
    logger.error("❌ ERROR: TELEGRAM_TOKEN not found!")
    logger.info("💡 Please add TELEGRAM_TOKEN to Render Environment Variables")
    exit(1)

# Initialize AI Clients
client_groq = Groq(api_key=GRO_KEY) if GRO_KEY else None
client_sealion = OpenAI(
    base_url="https://api-inference.huggingface.co/v1/", 
    api_key=SEA_KEY
) if SEA_KEY else None

# Store user language preferences
user_settings = {}

# --- Flask HTTP Server for Health Checks (NEW) ---
app = Flask(__name__)
start_time = time.time()

@app.route('/')
def home():
    """Home page for health checks"""
    return jsonify({
        "status": "online",
        "service": "Telegram AI Translator Bot",
        "languages": len(LANG_CODES),
        "uptime": round(time.time() - start_time, 2),
        "telegram": "active",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy"}), 200

@app.route('/status')
def status():
    """Detailed status"""
    return jsonify({
        "telegram_bot": "running",
        "groq_api": "available" if client_groq else "unavailable",
        "sealion_api": "available" if client_sealion else "unavailable",
        "users": len(user_settings),
        "supported_languages": len(LANG_CODES)
    })

def run_flask_server():
    """Run Flask server in a separate thread"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# --- Telegram Bot Handlers (ORIGINAL - UNCHANGED) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_text = (
        "👋 **សួស្តី! ខ្ញុំគឺជា AI Translator Bot**\n\n"
        "🌐 **ពាក្យបញ្ជា:**\n"
        "• `/list` - មើលភាសាទាំងអស់\n"
        "• `/kh`, `/en`, `/th` - ជ្រើសរើសភាសាគោលដៅ\n"
        "• ផ្ញើសារអ្វីក៏បាន ខ្ញុំនឹងបកប្រែភ្លាម!\n\n"
        "⚙️ **បច្ចុប្បន្ន:** ភាសាគោលដៅគឺ **ខ្មែរ 🇰🇭**"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def list_languages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available languages"""
    codes = sorted(LANG_CODES.keys())
    text = "🌐 **បញ្ជីភាសាដែលមាន:**\n\n"
    
    # Group by 4 languages per line
    for i in range(0, len(codes), 4):
        chunk = codes[i:i+4]
        line = " | ".join([f"/{c} {LANG_CODES[c][1]}" for c in chunk])
        text += f"• {line}\n"
    
    text += "\nចុចលើពាក្យបញ្ជាដើម្បីជ្រើសរើសភាសា (ឧទាហរណ៍: `/en` សម្រាប់អង់គ្លេស)"
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's target language"""
    user_id = update.effective_user.id
    command = update.message.text.replace("/", "").lower()
    
    if command in LANG_CODES:
        lang_name, flag = LANG_CODES[command]
        user_settings[user_id] = (lang_name, flag)
        await update.message.reply_text(
            f"✅ **បានកំណត់ភាសាគោលដៅ:** {flag} **{lang_name}**\n\n"
            f"ឥឡូវនេះ សារទាំងអស់នឹងត្រូវបកប្រែទៅជា **{lang_name}**។",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ មិនស្គាល់ភាសា។ សូមប្រើ `/list` ដើម្បីមើលភាសាដែលមាន។"
        )

async def translate_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate user's message"""
    user_id = update.effective_user.id
    target_lang, target_flag = user_settings.get(user_id, ("Khmer", "🇰🇭"))
    text_to_translate = update.message.text
    
    # Southeast Asian languages that Sea Lion handles well
    sea_langs = ["Khmer", "Thai", "Vietnamese", "Lao", "Indonesian", "Malay"]
    
    try:
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Choose API based on language
        if target_lang in sea_langs and client_sealion:
            logger.info(f"Using Sea Lion for {target_lang}")
            response = client_sealion.chat.completions.create(
                model="aisingapore/Gemma-SEA-LION-v4-27B-IT",
                messages=[{
                    "role": "user", 
                    "content": f"Translate this to {target_lang} language. Output only the translation: {text_to_translate}"
                }],
                temperature=0.3,
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()
            
        elif client_groq:
            logger.info(f"Using Groq/Llama for {target_lang}")
            response = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a professional translator. Translate the user's text to {target_lang} language. Provide ONLY the translated text without any explanations, notes, or additional text."
                    },
                    {
                        "role": "user", 
                        "content": text_to_translate
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()
            
        else:
            result = "❌ កំហុស៖ មិនមាន API Key ត្រឹមត្រូវ។ សូមពិនិត្យការកំណត់។"
        
        # Send the translation
        await update.message.reply_text(f"{target_flag} {result}")
        
    except Exception as e:
        logger.error(f"Translation Error: {str(e)}")
        await update.message.reply_text(
            "⚠️ **មានបញ្ហាក្នុងការបកប្រែ**\n"
            "សូមព្យាយាមម្តងទៀត ឬផ្លាស់ប្តូរទៅភាសាផ្សេង។",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    help_text = """
📚 **ព័ត៌មានជំនួយ**

**ពាក្យបញ្ជា:**
/start - ចាប់ផ្តើមបទ
/list - មើលភាសាទាំងអស់
/help - បង្ហាញសារនេះ
/kh, /en, /th, /fr, ... - ជ្រើសរើសភាសាគោលដៅ

**របៀបប្រើ:**
1. ជ្រើសរើសភាសាដោយប្រើពាក្យបញ្ជា (ឧទាហរណ៍: `/en`)
2. ផ្ញើសារអ្វីមួយ
3. ទទួលបកប្រែភ្លាម!

**បច្ចេកវិជ្ជា:** AI (Groq Llama 3.3 + Sea Lion)
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# --- Main Function with Both Flask and Telegram Bot (MODIFIED) ---

def main():
    """Main function to start both Flask server and Telegram bot"""
    
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask HTTP server started for health checks")
    
    # Give Flask a moment to start
    time.sleep(2)
    
    # Create and configure Telegram bot application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_languages))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add language selection handlers
    for cmd in LANG_CODES.keys():
        application.add_handler(CommandHandler(cmd, set_lang))
    
    # Add message handler for translation
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_ai))
    
    # Start the bot
    logger.info("🤖 Starting Telegram Translator Bot...")
    logger.info(f"📊 Supported languages: {len(LANG_CODES)}")
    logger.info(f"🔧 Groq API: {'✅' if client_groq else '❌'}")
    logger.info(f"🐚 Sea Lion API: {'✅' if client_sealion else '❌'}")
    logger.info("=" * 50)
    logger.info("🌐 Bot is now running with HTTP health checks!")
    logger.info("💡 Access health check at: http://your-render-url.onrender.com/health")
    
    # Run polling with proper error handling
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot stopped with error: {e}")
        raise

if __name__ == "__main__":
    # Start the bot
    main()
