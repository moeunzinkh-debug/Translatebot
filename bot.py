import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# កំណត់ការបង្ហាញ Log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# បញ្ជីកូដភាសាសរុប ៧០ (សម្រាប់ AI យល់ន័យ)
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

# ហៅប្រើ Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **AI Translator Bot (70 Languages)**\n"
        "ខ្ញុំអាចបកប្រែ Slang, Idioms និងអត្ថបទធម្មតាបានយ៉ាងឆ្លាតវៃ។\n\n"
        "👉 ប្រើ `/list` ដើម្បីមើលភាសាទាំងអស់\n"
        "👉 ប្រើ `/en`, `/kh`, `/th` ដើម្បីប្តូរភាសា\n"
        "👉 ផ្ញើសារដើម្បីបកប្រែភ្លាមៗ!"
    )

async def list_langs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codes = list(LANG_CODES.keys())
    text = "🌐 **បញ្ជីកូដភាសាទាំង ៧០:**\n\n"
    for i in range(0, len(codes), 5):
        text += " • " + ", ".join([f"/{c}" for c in codes[i:i+5]]) + "\n"
    await update.message.reply_text(text)

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.replace("/", "").lower()
    if command in LANG_CODES:
        user_settings[user_id] = LANG_CODES[command]
        await update.message.reply_text(f"✅ ភាសាគោលដៅ: **{LANG_CODES[command]}**")

async def translate_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text_input = update.message.text
    target_lang = user_settings.get(user_id, "Khmer")

    try:
        # Prompt សម្រាប់ឱ្យ AI យល់ Slang/Idioms
        prompt = (
            f"You are a professional translator. Translate the following text into {target_lang}. "
            f"If the text contains slang, idioms, or cultural expressions, translate the meaning naturally "
            f"and provide a very brief explanation in {target_lang} if necessary. "
            f"Text: '{text_input}'"
        )
        
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4, # កម្រិតច្បាស់លាស់
        )
        
        result = completion.choices[0].message.content
        await update.message.reply_text(result)
        
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text("❌ AI កំពុងមានបញ្ហា ឬ API Key ខុស។")

if __name__ == '__main__':
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_langs))
    
    for cmd in LANG_CODES.keys():
        app.add_handler(CommandHandler(cmd, set_lang))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), translate_ai))

    print("🚀 Bot កំពុងដំណើរការជាមួយ ៧០ ភាសា...")
    app.run_polling()
