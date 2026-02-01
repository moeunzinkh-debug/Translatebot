import os
import logging
import asyncio
import threading
import time
import tempfile
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
    "no": ("Norwegian", "🇳៴"), "cs": ("Czech", "🇨🇿"), "el": ("Greek", "🇬🇷"), "iw": ("Hebrew", "🇮🇱"), 
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

# ៣. ទាញយក API Keys ពី Environment Variables (ជាមួយកន្ទុយ S)
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# ទាញយក GROQ API Keys (អាចមានច្រើន)
GROQ_KEYS_STR = os.environ.get("GROQ_API_KEYS", "")
if GROQ_KEYS_STR:
    GROQ_KEYS = [key.strip() for key in GROQ_KEYS_STR.split(",") if key.strip()]
else:
    GROQ_KEYS = []

# ទាញយក Sea Lion API Keys (អាចមានច្រើន)
SEA_KEYS_STR = os.environ.get("SEA_LION_API_KEYS", "")
if SEA_KEYS_STR:
    SEA_KEYS = [key.strip() for key in SEA_KEYS_STR.split(",") if key.strip()]
else:
    SEA_KEYS = []

# ត្រួតពិនិត្យ Token
if not TOKEN:
    logger.error("❌ ERROR: TELEGRAM_TOKEN not found!")
    logger.info("💡 Please add TELEGRAM_TOKEN to Render Environment Variables")
    exit(1)

# Initialize AI Clients with multiple keys
client_groq_list = []
client_sealion_list = []

# Create multiple Groq clients
for i, api_key in enumerate(GROQ_KEYS):
    try:
        client = Groq(api_key=api_key)
        client_groq_list.append(client)
        logger.info(f"✅ Groq client {i+1} initialized")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Groq client {i+1}: {e}")

# Create multiple Sea Lion clients
for i, api_key in enumerate(SEA_KEYS):
    try:
        client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/", 
            api_key=api_key
        )
        client_sealion_list.append(client)
        logger.info(f"✅ Sea Lion client {i+1} initialized")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Sea Lion client {i+1}: {e}")

# Store user language preferences
user_settings = {}

# --- Flask HTTP Server for Health Checks ---
app = Flask(__name__)
start_time = time.time()

@app.route('/')
def home():
    """Home page for health checks"""
    return jsonify({
        "status": "online",
        "service": "Telegram AI Translator Bot",
        "languages": len(LANG_CODES),
        "groq_clients": len(client_groq_list),
        "sealion_clients": len(client_sealion_list),
        "uptime": round(time.time() - start_time, 2),
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
        "groq_clients": len(client_groq_list),
        "sealion_clients": len(client_sealion_list),
        "users": len(user_settings),
        "supported_languages": len(LANG_CODES),
        "groq_keys_available": len(GROQ_KEYS),
        "sealion_keys_available": len(SEA_KEYS)
    })

def run_flask_server():
    """Run Flask server in a separate thread"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# --- Helper functions for API key rotation ---
def get_groq_client():
    """Get a Groq client using round-robin selection"""
    if not client_groq_list:
        return None
    # Simple round-robin selection
    current_index = getattr(get_groq_client, 'index', 0)
    client = client_groq_list[current_index % len(client_groq_list)]
    get_groq_client.index = (current_index + 1) % len(client_groq_list)
    return client

def get_sealion_client():
    """Get a Sea Lion client using round-robin selection"""
    if not client_sealion_list:
        return None
    # Simple round-robin selection
    current_index = getattr(get_sealion_client, 'index', 0)
    client = client_sealion_list[current_index % len(client_sealion_list)]
    get_sealion_client.index = (current_index + 1) % len(client_sealion_list)
    return client

# --- SRT Translation Functions (NEW) ---
def parse_srt_content(srt_text):
    """Parse SRT content into list of subtitle entries"""
    entries = []
    blocks = srt_text.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = lines[0].strip()
                timestamp = lines[1].strip()
                text_lines = lines[2:]
                # Combine multiple text lines
                text = '\n'.join(text_lines)
                
                entries.append({
                    'index': index,
                    'timestamp': timestamp,
                    'text': text,
                    'original_block': block
                })
            except Exception as e:
                logger.warning(f"Failed to parse SRT block: {e}")
                continue
    
    return entries

def translate_srt_text(text_to_translate, target_lang):
    """Translate SRT text using appropriate AI client"""
    # Southeast Asian languages that Sea Lion handles well
    sea_langs = ["Khmer", "Thai", "Vietnamese", "Lao", "Indonesian", "Malay", "Burmese", "Filipino"]
    
    try:
        if target_lang in sea_langs:
            # Try Sea Lion first
            client = get_sealion_client()
            if client:
                try:
                    response = client.chat.completions.create(
                        model="aisingapore/Gemma-SEA-LION-v4-27B-IT",
                        messages=[{
                            "role": "user", 
                            "content": f"Translate this SRT subtitle text to {target_lang} language. Preserve any formatting markers and only output the translated text: {text_to_translate}"
                        }],
                        temperature=0.3,
                        max_tokens=300
                    )
                    result = response.choices[0].message.content.strip()
                    return result
                except Exception as e:
                    logger.warning(f"Sea Lion failed for SRT: {e}")
        
        # Use Groq as fallback or for non-SEA languages
        client = get_groq_client()
        if client:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a professional SRT subtitle translator. Translate the following subtitle text to {target_lang} language. Preserve all formatting, line breaks, and special markers. Output ONLY the translated text without explanations."
                    },
                    {
                        "role": "user", 
                        "content": text_to_translate
                    }
                ],
                temperature=0.2,
                max_tokens=300
            )
            result = response.choices[0].message.content.strip()
            return result
        
        return text_to_translate  # Return original if no client available
        
    except Exception as e:
        logger.error(f"SRT Translation error: {e}")
        return text_to_translate  # Return original on error

async def handle_srt_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle SRT file upload and translation"""
    user_id = update.effective_user.id
    target_lang, target_flag = user_settings.get(user_id, ("Khmer", "🇰🇭"))
    
    # Check if message has document
    if not update.message.document:
        await update.message.reply_text("❌ សូមផ្ញើឯកសារ SRT មួយ។")
        return
    
    document = update.message.document
    file_name = document.file_name.lower()
    
    # Check if it's an SRT file
    if not file_name.endswith('.srt'):
        await update.message.reply_text("❌ សូមផ្ញើតែឯកសារ SRT (.srt)។")
        return
    
    try:
        # Show processing message
        processing_msg = await update.message.reply_text("🔄 កំពុងដំណើរការឯកសារ SRT...")
        
        # Download the file
        file = await context.bot.get_file(document.file_id)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.srt', delete=False) as temp_file:
            file_path = temp_file.name
            await file.download_to_drive(file_path)
            
            # Read the SRT content
            with open(file_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
        
        # Parse SRT content
        entries = parse_srt_content(srt_content)
        
        if not entries:
            await update.message.reply_text("❌ មិនអាចអានឯកសារ SRT បាន។")
            return
        
        # Check file size (limit to 50 entries for free tier)
        if len(entries) > 50:
            await update.message.reply_text(
                f"⚠️ ឯកសារមាន {len(entries)} ជួរ។ កំណត់អតិបរមា 50 ជួរសម្រាប់ថ្នាក់ឥតគិតថ្លៃ។\n"
                f"សូមកាត់ឯកសារឱ្យតូចជាងនេះ។"
            )
            return
        
        # Translate each entry
        await processing_msg.edit_text(f"🔄 កំពុងបកប្រែ {len(entries)} ជួរទៅជា {target_lang}...")
        
        translated_entries = []
        for i, entry in enumerate(entries):
            # Show progress every 10 entries
            if i % 10 == 0 and i > 0:
                await processing_msg.edit_text(f"🔄 បកប្រែរួចហើយ {i}/{len(entries)} ជួរ...")
            
            translated_text = translate_srt_text(entry['text'], target_lang)
            
            # Create new entry with translated text
            translated_entries.append({
                'index': entry['index'],
                'timestamp': entry['timestamp'],
                'text': translated_text
            })
        
        # Create translated SRT content
        translated_srt = ""
        for entry in translated_entries:
            translated_srt += f"{entry['index']}\n{entry['timestamp']}\n{entry['text']}\n\n"
        
        # Create temporary file for translated SRT
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(translated_srt)
            translated_file_path = temp_file.name
        
        # Send translated file back
        with open(translated_file_path, 'rb') as f:
            # Create new file name with language code
            original_name = document.file_name.rsplit('.', 1)[0]
            new_name = f"{original_name}_{target_lang[:2].lower()}.srt"
            
            await update.message.reply_document(
                document=f,
                filename=new_name,
                caption=f"✅ បកប្រែរួចរាល់ទៅជា {target_flag} {target_lang}\n\n"
                       f"ចំនួនជួរ: {len(entries)}\n"
                       f"ប្រើ AI: {'Sea Lion' if target_lang in ['Khmer', 'Thai', 'Vietnamese', 'Lao', 'Indonesian', 'Malay', 'Burmese', 'Filipino'] else 'Groq/Llama'}"
            )
        
        # Clean up temporary files
        os.unlink(file_path)
        os.unlink(translated_file_path)
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"SRT processing error: {e}")
        await update.message.reply_text(
            "❌ កំហុសក្នុងការដំណើរការឯកសារ SRT។\n"
            "សូមព្យាយាមម្តងទៀត ឬពិនិត្យថាឯកសារត្រឹមត្រូវ។"
        )

# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_text = (
        "👋 **សួស្តី! ខ្ញុំគឺជា AI Translator Bot**\n\n"
        "🌐 **ពាក្យបញ្ជា:**\n"
        "• `/list` - មើលភាសាទាំងអស់\n"
        "• `/kh`, `/en`, `/th` - ជ្រើសរើសភាសាគោលដៅ\n"
        "• ផ្ញើសារអ្វីក៏បាន ខ្ញុំនឹងបកប្រែភ្លាម!\n\n"
        "📁 **គាំទ្រឯកសារ SRT:**\n"
        "• ផ្ញើឯកសារ .srt មក ខ្ញុំនឹងបកប្រែស្រ្តីសម្រាប់អ្នក\n\n"
        f"⚙️ **បច្ចុប្បន្ន:** ភាសាគោលដៅគឺ **ខ្មែរ 🇰🇭**\n"
        f"🔑 **API Status:** Groq({len(client_groq_list)}), Sea Lion({len(client_sealion_list)})"
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
        
        # Check which AI will be used
        sea_langs = ["Khmer", "Thai", "Vietnamese", "Lao", "Indonesian", "Malay", "Burmese", "Filipino"]
        ai_type = "Sea Lion" if lang_name in sea_langs else "Groq/Llama"
        
        await update.message.reply_text(
            f"✅ **បានកំណត់ភាសាគោលដៅ:** {flag} **{lang_name}**\n\n"
            f"ឥឡូវនេះ សារទាំងអស់នឹងត្រូវបកប្រែទៅជា **{lang_name}**។\n"
            f"⚡ **ប្រើ:** {ai_type} AI\n\n"
            f"📁 **ឯកសារ SRT:** ក៏នឹងត្រូវបានបកប្រែទៅភាសានេះដែរ។",
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
    sea_langs = ["Khmer", "Thai", "Vietnamese", "Lao", "Indonesian", "Malay", "Burmese", "Filipino"]
    
    try:
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Choose API based on language
        if target_lang in sea_langs:
            # Try Sea Lion first
            client = get_sealion_client()
            if client:
                logger.info(f"Using Sea Lion for {target_lang}")
                try:
                    response = client.chat.completions.create(
                        model="aisingapore/Gemma-SEA-LION-v4-27B-IT",
                        messages=[{
                            "role": "user", 
                            "content": f"Translate this to {target_lang} language. Output only the translation: {text_to_translate}"
                        }],
                        temperature=0.3,
                        max_tokens=200
                    )
                    result = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"Sea Lion failed: {e}, falling back to Groq")
                    client = get_groq_client()
                    if client:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"Translate to {target_lang}"},
                                {"role": "user", "content": text_to_translate}
                            ],
                            temperature=0.2,
                            max_tokens=200
                        )
                        result = response.choices[0].message.content.strip()
                    else:
                        result = "❌ មិនមាន API ដែលអាចប្រើបាន"
            else:
                # Fall back to Groq if no Sea Lion
                client = get_groq_client()
                if client:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": f"Translate to {target_lang}"},
                            {"role": "user", "content": text_to_translate}
                        ],
                        temperature=0.2,
                        max_tokens=200
                    )
                    result = response.choices[0].message.content.strip()
                else:
                    result = "❌ មិនមាន API ដែលអាចប្រើបាន"
                    
        else:
            # Use Groq for non-SEA languages
            client = get_groq_client()
            if client:
                logger.info(f"Using Groq for {target_lang}")
                response = client.chat.completions.create(
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
                result = "❌ មិនមាន Groq API ដែលអាចប្រើបាន"
        
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

**ឯកសារ SRT:**
• ផ្ញើឯកសារ .srt មក
• ប្រើពាក្យបញ្ជាជ្រើសភាសាជាមុន
• ទទួលឯកសារបកប្រែវិញ

**បច្ចេកវិជ្ជា:** AI (Groq Llama 3.3 + Sea Lion)
**API Keys:** អាចប្រើច្រើន keys សម្រាប់ភាពរលូន
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status"""
    status_text = f"""
🤖 **Bot Status**

📊 **ទិន្នន័យ:**
• អ្នកប្រើប្រាស់: {len(user_settings)}
• ភាសាដែលគាំទ្រ: {len(LANG_CODES)}
• Uptime: {round(time.time() - start_time, 1)} វិនាទី

🔑 **API Status:**
• Groq Clients: {len(client_groq_list)}/{len(GROQ_KEYS)}
• Sea Lion Clients: {len(client_sealion_list)}/{len(SEA_KEYS)}

📁 **ឯកសារ SRT:** បានគាំទ្រ

🌐 **Health Check:** http://your-render-url.onrender.com/health
"""
    await update.message.reply_text(status_text, parse_mode='Markdown')

# --- Main Function ---

def main():
    """Main function to start both Flask server and Telegram bot"""
    
    # Log initialization status
    logger.info("=" * 60)
    logger.info("🚀 Initializing Telegram AI Translator Bot")
    logger.info(f"🔑 TELEGRAM_TOKEN: {'✅' if TOKEN else '❌'}")
    logger.info(f"🤖 Groq API Keys: {len(GROQ_KEYS)} keys available, {len(client_groq_list)} clients initialized")
    logger.info(f"🦁 Sea Lion API Keys: {len(SEA_KEYS)} keys available, {len(client_sealion_list)} clients initialized")
    logger.info(f"🌐 Supported Languages: {len(LANG_CODES)}")
    logger.info("📁 SRT File Support: ✅ Enabled")
    logger.info("=" * 60)
    
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
    application.add_handler(CommandHandler("status", status_command))
    
    # Add language selection handlers
    for cmd in LANG_CODES.keys():
        application.add_handler(CommandHandler(cmd, set_lang))
    
    # Add message handler for translation
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_ai))
    
    # Add document handler for SRT files (NEW)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_srt_file))
    
    # Start the bot
    logger.info("🤖 Starting Telegram Translator Bot polling...")
    
    # Run polling with proper error handling
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            poll_interval=1.0
        )
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot stopped with error: {e}")
        raise

if __name__ == "__main__":
    # Start the bot
    main()
