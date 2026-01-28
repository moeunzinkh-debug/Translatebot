import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq

# កំណត់ Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# បញ្ជីកូដភាសាទាំង ៧០
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

# ហៅប្រើ Groq AI (Model: llama-3.3-70b-versatile)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌐 បញ្ជីភាសាទាំង ៧០", callback_data='list_langs')],
        [
            InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data='set_kh'),
            InlineKeyboardButton("🇺🇸 English", callback_data='set_en'),
            InlineKeyboardButton("🇹🇭 Thai", callback_data='set_th')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "🔥 **AI PRO Translator (Llama 3.3)**\n\n"
        "ខ្ញុំអាចបកប្រែពាក្យពិបាកៗ ស៊ាំៗ និង Slang បានយ៉ាងច្បាស់។\n"
        "សូមជ្រើសរើសភាសាគោលដៅរបស់អ្នក៖"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def list_langs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codes = list(LANG_CODES.keys())
    text = "🌐 **កូដភាសាសរុប ៧០:**\n\n"
    for i in range(0, len(codes), 5):
        text += " • " + ", ".join([f"/{c}" for c in codes[i:i+5]]) + "\n"
    
    back_btn = [[InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data='back_start')]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_btn))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'list_langs':
        await list_langs(update, context)
    elif query.data == 'back_start':
        await start(update, context)
    elif query.data.startswith('set_'):
        lang_code = query.data.split('_')[1]
        user_settings[user_id] = LANG_CODES.get(lang_code, "Khmer")
        await query.edit_message_text(f"✅ ភាសាគោលដៅ៖ **{user_settings[user_id]}**")

async def set_lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cmd = update.message.text.replace("/", "").lower()
    if cmd in LANG_CODES:
        user_settings[user_id] = LANG_CODES[cmd]
        await update.message.reply_text(f"✅ ភាសាគោលដៅ៖ **{LANG_CODES[cmd]}**")

async def translate_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = user_settings.get(user_id, "Khmer")
    
    try:
        # ការប្រើប្រាស់ Llama-3.3-70b-versatile
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are a master translator. Translate the text to {target}. If there are idioms, slang, or deep cultural meanings, explain them briefly and naturally in {target}."},
                {"role": "user", "content": update.message.text}
            ],
            temperature=0.3, # ទាបជាងមុនដើម្បីឱ្យការបកប្រែកាន់តែច្បាស់លាស់ (Precision)
        )
        await update.message.reply_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text("❌ មានបញ្ហាជាមួយ AI Model។ សូមឆែកមើល API Quota របស់អ្នក។")

if __name__ == '__main__':
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    for cmd in LANG_CODES.keys():
        app.add_handler(CommandHandler(cmd, set_lang_command))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), translate_ai))

    print("🚀 Bot is running with Llama 3.3-70b...")
    app.run_polling()
