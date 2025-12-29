import logging
import os
from datetime import datetime
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image

# --- 1. KONFIGURASI ---
TELEGRAM_TOKEN = "8579079785:AAErspw7sg6lB1QhlQLGHBCwG1pRSZ_P9zg"
GEMINI_API_KEY = "AIzaSyDJGkyvo4JIFmIq_jSpgbHARW_zy9f9U34"

SAVE_DIR = "img_user"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Pakai Client Baru (google-genai)
client = genai.Client(api_key=GEMINI_API_KEY)

# Urutan model paling bandel buat akun free
AVAILABLE_MODELS = [
    'gemini-flash-latest', 'gemini-1.5-pro'
]

# KEPRIBADIAN FITO (Ini yang bikin dia kayak manusia)
SYSTEM_PROMPT = (
    "Nama lo Fito. Lo itu AI partner yang paling asik, cerdas, tapi tetap rendah hati. "
    "Gaya bicara lo santai, pake lo-gue kayak anak tongkrongan Jakarta yang pinter. "
    "Kalo jawab jangan kepanjangan kayak koran, singkat padat berisi aja kecuali diminta. "
    "Kalo liat foto, analisis dengan jeli tapi komentarin pake gaya yang seru. "
    "Jangan pernah bilang 'Saya adalah AI', lo adalah Fito, titik."
)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 2. FUNGSI PENDUKUNG ---
def simpan_ke_database(user_id, nama, pesan, role="USER", foto_path=None):
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_pesan = f"[{waktu}] {role} | ID: {user_id} | Nama: {nama} | Pesan: {pesan}"
    if foto_path:
        log_pesan += f" | FOTO: {foto_path}"
    with open("database_chat.txt", "a", encoding="utf-8") as f:
        f.write(log_pesan + "\n")

def get_gemini_response(contents):
    """Mencoba satu-satu model sampai ada yang nyaut"""
    for model_id in AVAILABLE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.8, # Biar lebih kreatif & gak kaku
                ),
                contents=contents
            )
            return response.text
        except Exception as e:
            logging.warning(f"Model {model_id} gagal/limit: {str(e)[:50]}")
            continue
    return "Duh bro, otak gue lagi nge-hang semua (Limit). Coba chat gue semenit lagi ya!"

# --- 3. LOGIKA UTAMA ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    full_name = user.first_name if user.first_name else "Sobat"
    user_text = update.message.text or update.message.caption or "Coba cek ini"
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        foto_simpan_path = None
        payload = []
        
        if update.message.photo:
            # Ambil foto kualitas tertinggi
            photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
            
            # Buat nama file unik
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{timestamp}_{user.id}.jpg"
            foto_simpan_path = os.path.join(SAVE_DIR, file_name)
            
            # Download permanen
            await photo_file.download_to_drive(foto_simpan_path)
            
            # Gunakan PIL untuk buka gambar (sesuai library baru)
            img = Image.open(foto_simpan_path)
            payload = [img, f"Dari {full_name}: {user_text}"]
            
        else:
            payload = [f"Chat dari {full_name}: {user_text}"]

        # Ambil respon dari Fito
        response_text = get_gemini_response(payload)

        # Simpan log
        simpan_ke_database(user.id, full_name, user_text, "USER", foto_simpan_path)
        simpan_ke_database("BOT_FITO", "Fito", response_text, "ASSISTANT")
        
        await update.message.reply_text(response_text)

    except Exception as e:
        logging.error(f"Global Error: {e}")
        await update.message.reply_text("Lagi pening dikit bro, coba kirim ulang chat lo!")

def main():
    # Tambahkan timeout agar koneksi lebih stabil
    app = Application.builder().token(TELEGRAM_TOKEN).connect_timeout(30).read_timeout(30).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    print("🚀 Fito On! Mode Manusiawi & Save Image Aktif.")
    app.run_polling()

if __name__ == "__main__":
    main()