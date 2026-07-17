# file: i18n/_es.py

"""Spanish UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows:

* **Impersonal, usted-neutral address** — the UI talks like software, not
  correspondence ("Normalmente su lengua materna"), never «tú» nor an explicit
  «usted».
* **Imperative for actions, noun for objects** — the same split English makes:
  a button is "Guardar", a section title is "Par de idiomas".
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9. Transliterating them helps nobody and breaks the user's ability to
  search for them.
* **Hints keep English's register**: plain, second-person-implied, no jargon the
  English didn't already use.
* **No Qt "&&" mnemonics** — Spanish uses "y", so a literal ampersand is never
  needed (a lone "&" would create an accidental accelerator).
"""

from __future__ import annotations

LOCALE = "es"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "Activado",
    "common.off": "Desactivado",
    "common.cancel": "Cancelar",
    "common.save": "Guardar",
    "common.pro": "Pro",
    "common.pro.tooltip": "Función Pro — apúntese a la lista de espera",
    "common.help.where_key": "¿Dónde consigo una clave?",

    # ---------- tray menu ----------
    "tray.show_window": "Mostrar ventana",
    "tray.indicator.show": "Mostrar indicador flotante",
    "tray.indicator.hide": "Ocultar indicador flotante",
    "tray.mode": "Activación: {mode}",
    "tray.mode.keyboard": "Teclado",
    "tray.mode.mouse": "Ratón",
    "tray.keys": "Teclas de activación",
    "tray.keys.change": "Cambiar (pulse una tecla)",
    "tray.hotkey.item": "{action}: {key}",
    "tray.action.transcribe": "Transcribir",
    "tray.action.translate": "Transcribir y traducir",
    "tray.action.custom": "Transcribir y reescribir",
    "tray.suppress.on": "Captura estricta: ACTIVADA (las teclas se absorben)",
    "tray.suppress.off": "Captura estricta: DESACTIVADA (pasan de largo)",
    "tray.mouse_button": "Botón del ratón para activar: {button}",
    "tray.model": "Método de reconocimiento: {model}",
    "tray.model.local": "Local: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "Dispositivo: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Idioma principal: {language}",
    "tray.language.other": "Otros idiomas…",
    "tray.settings": "Ajustes…",
    "tray.close": "Cerrar",
    "tray.tooltip.loading": "Omni Verte — cargando modelo…",
    "tray.tooltip.failed": "Omni Verte — el modelo no se cargó (revise la red, vuelva a elegirlo en Ajustes)",

    # ---------- settings: General page ----------
    "page.general.title": "General",
    "page.general.hint": "Idioma de la interfaz, teclas rápidas y ajustes de comportamiento. La mayoría también están en el menú de la bandeja.",

    "general.interface.title": "Interfaz",
    "general.interface.hint": "En qué idioma le habla la aplicación. Independiente de los idiomas que dicta y entre los que traduce, en la página «Idiomas».",
    "general.interface.language": "Idioma",
    "general.interface.language.hint": "Se aplica al guardar.",

    "general.activation.title": "Activación",
    "general.activation.hint": (
        "Cómo se inicia la grabación. El teclado usa una sola tecla rápida; "
        "el ratón usa un botón configurable."
    ),
    "general.activation.keyboard": "Teclas rápidas",
    "general.activation.mouse": "Botón del ratón",

    # «Capturar la tecla» — comillas angulares, como en el resto del texto;
    # en el original es “Catch the key”.
    "general.hotkey.transcribe": "Transcribir y pegar",
    "general.hotkey.transcribe.hint": "Dicte y luego pegue la transcripción con corrección gramatical y puntuación. Pulse «Capturar la tecla» para asignar una tecla.",
    "general.hotkey.translate": "Transcribir y traducir",
    "general.hotkey.translate.hint": "Dicte y luego traduzca al idioma secundario antes de pegar. Pulse «Capturar la tecla» para asignar una tecla.",
    "general.hotkey.custom": "Transcribir y reescribir en estilo personalizado",
    "general.hotkey.custom.hint": "Dicte y luego reescriba en el estilo elegido abajo y pegue. Pulse «Capturar la tecla» para asignar una tecla.",

    "general.stylepair.name": "Personalizado",
    "general.stylepair.hint": "Al pulsar {key} se reescribe lo dictado en este estilo. «Personalizado» usa su instrucción de la página Estilo personalizado.",

    "general.style.casual": "Informal",
    "general.style.professional": "Profesional",
    "general.style.custom": "Personalizado",

    "general.suppress": "Capturar las teclas de forma estricta",
    "general.suppress.hint": "Absorber las teclas rápidas para que la aplicación en primer plano no las reciba (p. ej., que F11 no ponga el navegador en pantalla completa). Desactive si causa conflictos.",

    "general.mouse.label": "Botón del ratón",
    "general.mouse.hint": "Manténgalo pulsado para grabar.",
    "general.mouse.middle": "Central",
    "general.mouse.left": "Izquierdo",
    "general.mouse.right": "Derecho",

    "general.behaviour.title": "Comportamiento",
    "general.behaviour.floating": "Indicador flotante",
    "general.behaviour.floating.hint": "Pequeño punto de estado en la esquina de la pantalla.",
    "general.behaviour.double_tap": "Abrir la ventana con doble pulsación",
    "general.behaviour.double_tap.hint": "Pulse la tecla o botón de activación dos veces seguidas (en menos de 300 ms) para traer la ventana principal al frente.",
    "general.behaviour.autostart": "Iniciar al arrancar Windows",
    "general.behaviour.autostart.hint": "Iniciar Omni Verte automáticamente al iniciar sesión en Windows.",

    # Se interpolan en general.error.hotkey_empty: «La tecla de transcripción no
    # puede estar vacía…». Por eso son claves aparte y no las etiquetas de fila.
    "general.action.transcribe": "transcripción",
    "general.action.translate": "traducción",
    "general.action.custom": "estilo personalizado",
    "general.error.hotkey_empty": "La tecla de {action} no puede estar vacía cuando está seleccionado el modo teclado.",
    "general.error.hotkey_duplicate": "Cada acción necesita una tecla distinta — ahora hay dos iguales.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Idiomas",
    "page.languages.hint": "El traductor detecta automáticamente en qué sentido convertir entre estos dos idiomas.",
    "languages.pair.title": "Par de idiomas",
    "languages.primary": "Principal",
    "languages.primary.hint": "Normalmente su lengua materna o la que más usa.",
    "languages.secondary": "Secundario",
    "languages.secondary.hint": "El otro idioma en el que escribe o habla con regularidad.",
    "languages.swap": "Intercambiar idiomas",
    "languages.swap.tooltip": "Intercambiar principal y secundario",
    "languages.error.must_differ": "Los idiomas principal y secundario deben ser distintos.",

    # ---------- app-wide ----------
    "app.tagline": "Dictado con IA · Reescritura · Traducción",

    # ---------- settings: Transcription page ----------
    # "backend" se traduce como "motor": esta página la leen abogados y médicos
    # además de desarrolladores (véanse los packs), y "motor de reconocimiento"
    # es la expresión que un no-desarrollador ya conoce.
    "page.transcription.title": "Transcripción",
    "page.transcription.hint": (
        "Elija qué motores de voz a texto probar y en qué orden. "
        "El primer motor con credenciales válidas pasa a ser el activo."
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Local (Whisper)",
    "transcription.backend.hint.openai": "alta calidad, de pago",
    "transcription.backend.hint.groq": "el más rápido, con nivel gratuito",
    "transcription.backend.hint.local": "sin conexión, usa la CPU/GPU local",

    "transcription.priority.title": "Prioridad de los motores",
    "transcription.priority.hint": (
        "Arrastre para reordenar. Al arrancar gana el primer motor con "
        "credenciales válidas."
    ),

    "transcription.keys.title": "Claves API",
    "transcription.keys.hint": (
        "Se guardan en el Administrador de credenciales de Windows (protegidas "
        "con DPAPI). Deje el campo vacío para omitir un motor."
    ),
    "transcription.keys.get_link": "Obtener una clave ↗",

    # Las listas de pasos mantienen las etiquetas de los propios consoles del
    # proveedor en latín y entre comillas — esos consoles no tienen interfaz en
    # español, así que un "Create new secret key" traducido sería un botón que
    # el usuario nunca encontraría. La instrucción alrededor va en español; lo
    # que hay que pulsar, textual.
    "transcription.keys.openai.label": "Clave de OpenAI",
    "transcription.keys.openai.placeholder": "Introduzca la clave API de OpenAI",
    "transcription.keys.openai.nudge": "← Introduzca su clave de OpenAI",
    "transcription.keys.openai.help.title": "Cómo obtener una clave API de OpenAI",
    "transcription.keys.openai.help.step1": "1. Inicie sesión en platform.openai.com",
    "transcription.keys.openai.help.step2": "2. «API keys» → «Create new secret key»",
    "transcription.keys.openai.help.step3": "3. Cópiela (empieza por «sk-…») y péguela aquí",
    "transcription.keys.openai.help.note": "OpenAI es de pago — añada saldo de facturación para usarlo.",
    "transcription.keys.openai.help.link": "Abrir la página de claves de OpenAI",

    "transcription.keys.groq.label": "Clave de Groq",
    "transcription.keys.groq.placeholder": "Introduzca la clave API de Groq",
    "transcription.keys.groq.nudge": "← Introduzca su clave de Groq",
    "transcription.keys.groq.help.title": "Cómo obtener una clave API de Groq (gratis)",
    "transcription.keys.groq.help.step1": "1. Inicie sesión en console.groq.com",
    "transcription.keys.groq.help.step2": "2. «API Keys» → «Create API Key»",
    "transcription.keys.groq.help.step3": "3. Cópiela y péguela aquí",
    "transcription.keys.groq.help.link": "Abrir la consola de Groq",

    "transcription.models.title": "Modelo por motor",
    "transcription.models.hint": "Se usa cuando ese motor está activo.",

    "transcription.device.title": "Dispositivo para la transcripción local (solo para el motor local)",
    "transcription.device.hint": (
        "Dónde se ejecuta el modelo Whisper local. No tiene efecto cuando el "
        "motor activo es OpenAI o Groq — esos transcriben en la nube."
    ),
    "transcription.device.label": "Dispositivo",
    "transcription.device.label.hint": "CUDA es mucho más rápido que la CPU en las GPU NVIDIA compatibles.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.error.priority_empty": "La lista de prioridad de motores está vacía.",

    # ---------- settings: About page ----------
    "page.about.title": "Acerca de",
    "about.version": "Versión",
    "about.version.unknown": "desconocida",
    "about.developer": "Desarrollador",
    "about.email": "Correo",
    "about.website": "Sitio web",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Glosario",
    "page.glossary.hint": (
        "Términos de su empresa y términos de uso diario para que la aplicación los reconozca y los escriba "
        "en su forma canónica. Desactivado por defecto. Nota: cuando el sesgo ASR o las capas LLM están "
        "activados, estos términos se envían a su proveedor en la nube (OpenAI/Groq) como parte de la petición."
    ),
    "glossary.enable.title": "Activar el glosario",
    "glossary.enable.hint": "Interruptor principal. Desactivado → el comportamiento es idéntico al de una compilación sin esta función.",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "Packs profesionales",
    "glossary.packs.hint": (
        "Conjuntos de términos ya preparados para que el reconocedor acierte "
        "con la jerga del sector desde el primer momento — las palabras, "
        "abreviaturas y grafías que un campo escribe mal por defecto (embargo, "
        "fuerza mayor, anamnesis, ECG, merge request, idempotente). Pulse un "
        "pack para copiar sus términos en su glosario de abajo y luego edítelos "
        "como cualquier cosa que escriba usted. Función Pro."
    ),
    "glossary.packs.language": "Idioma del pack",
    "glossary.packs.language.hint": "En qué idioma están escritos los términos importados.",
    "glossary.packs.status.available": "{count} packs disponibles — pulse uno para copiar sus términos en los campos de abajo.",
    "glossary.packs.status.locked": "Los packs profesionales son una función Pro. Free mantiene {cap} términos activos — menos de los que contiene cualquier pack.",
    "glossary.packs.tooltip.adds": "Añade hasta {count} términos.",
    "glossary.packs.tooltip.locked": "Los packs profesionales son una función Pro.",
    "glossary.packs.already_loaded.title": "El pack {pack} ya está cargado",
    # {language} — nombre del idioma en inglés ("Spanish"), viene de los datos;
    # de ahí los paréntesis, en vez de un «en español» concordado.
    "glossary.packs.already_loaded.text": "Todos los términos del pack ({language}) ya están en su glosario — no hay nada que añadir.",
    "glossary.packs.count.terms": "{count} términos",
    "glossary.packs.count.replacements": "{count} reemplazos",
    "glossary.packs.count.join": " y ",
    "glossary.packs.confirm.title": "¿Cargar el pack {pack}?",
    "glossary.packs.confirm.adds": "Esto añade {what} a su glosario, en {language}.",
    "glossary.packs.confirm.skipped": "{count} que ya están presentes se omitirán.",
    "glossary.packs.confirm.editable": "Se añaden como líneas normales que puede editar o borrar, y solo se escriben en disco al guardar.",

    # Nombre y descripción de cada pack. Es interfaz — siguen el idioma de la UI,
    # a diferencia de los términos en sí (su idioma se elige en «Idioma del
    # pack») y del `note` de jurisdicción, escrito en el idioma del propio pack.
    "glossary.packs.legal.name": "Jurídico",
    "glossary.packs.legal.hint": "Vocabulario de litigios, contratos y derecho societario.",
    "glossary.packs.medical.name": "Medicina",
    "glossary.packs.medical.hint": "Notas clínicas, diagnósticos y abreviaturas habituales.",
    "glossary.packs.it.name": "TI y software",
    "glossary.packs.it.hint": "Vocabulario de ingeniería, DevOps y revisión de código.",
    "glossary.packs.finance.name": "Finanzas y contabilidad",
    "glossary.packs.finance.hint": "Vocabulario de informes, valoración y operaciones.",
    "glossary.packs.sales.name": "Ventas y CRM",
    "glossary.packs.sales.hint": "Vocabulario de embudo, prospección y gestión de cuentas.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Capas",
    "glossary.layers.hint": "Cada capa usa los mismos términos; active o desactive cada capa por separado.",
    "glossary.layers.asr": "Sesgo del ASR",
    "glossary.layers.asr.hint": "Sesga el reconocedor de voz hacia sus términos (prompt en la nube / hotwords en local).",
    "glossary.layers.correction": "Corrección LLM (transcribir)",
    "glossary.layers.correction.hint": "Añade los términos al prompt de corrección gramatical en la acción de transcribir por defecto.",
    "glossary.layers.rewrite": "LLM en traducir y reescribir",
    "glossary.layers.rewrite.hint": "Añade los términos a los prompts de traducción y reescritura (botones manuales y acciones por tecla rápida).",
    "glossary.layers.fuzzy": "Reemplazo aproximado (transcribir)",
    "glossary.layers.fuzzy.hint": "Ajusta de forma determinista las palabras casi coincidentes a los términos canónicos, solo al transcribir.",
    "glossary.layers.threshold": "Umbral aproximado",
    "glossary.layers.threshold.hint": "Cuánto debe parecerse una palabra a un término para que se dispare el reemplazo aproximado (70–100; mayor = más estricto).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Términos",
    "glossary.terms.hint": "Palabras específicas de su empresa, por grupos. Una entrada por línea.",
    "glossary.terms.tab.names": "Nombres y términos",
    "glossary.terms.tab.replacements": "Reemplazos",
    "glossary.terms.names": "Nombres",
    "glossary.terms.names.hint": "Su empresa, productos, clientes, socios, proveedores.",
    # Nombres de empresa inventados — nombres propios, se quedan en latín.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Servicios y términos",
    "glossary.terms.services.hint": "Nombres de servicios, planes, términos del sector.",
    "glossary.terms.services.placeholder": "TurboDrive\nplan Órbita",
    # `{sep}` es el separador `=>` (`_REPL_SEP`); una forma mal oída plausible
    # en español mapeada al término canónico en latín.
    "glossary.terms.replacements.placeholder": "turbo draiv {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Correcciones explícitas y siempre activas — una por línea como "
        "«oído {sep} canónico». Se aplican al pie de la letra (sin reglas "
        "aproximadas), así que úselas para palabras que el reconocedor oye "
        "mal de forma fiable."
    ),
    "glossary.terms.counter.unlimited": "{total} términos — todos activos.",
    "glossary.terms.counter.used": "{total} de {cap} términos usados · quedan {remaining} disponibles.",
    "glossary.terms.counter.over_free": (
        "{cap} de {total} términos activos — el resto están guardados pero "
        "inactivos. Pro los activa todos (hasta {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap} de {total} términos activos — solo se usan los primeros {cap} "
        "(más empeora la calidad del reconocimiento)."
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "línea {line}: falta el separador «{sep}» — use «oído {sep} canónico»",
    "glossary.replacements.error.empty_side": "línea {line}: ambos lados de «{sep}» deben tener contenido",
    "glossary.replacements.error.more": "(+{count} más)",
    "glossary.replacements.error.prefix": "Reemplazos: {details}",

    # ---------- settings: Custom style page ----------
    "page.customstyle.title": "Estilo personalizado",
    "page.customstyle.hint": (
        "Lo usa el botón de reescritura «Personalizado». La instrucción de abajo "
        "se pasa al modelo al pie de la letra junto con su texto original."
    ),
    "customstyle.preset.title": "Preajuste",
    "customstyle.name": "Nombre del estilo",
    "customstyle.name.hint": "Se muestra como descripción emergente en el botón «Personalizado».",
    "customstyle.name.placeholder": "opcional — p. ej., Académico",
    "customstyle.prompt": "Instrucción",
    "customstyle.prompt.hint": "El modelo la trata como una directriz de nivel de sistema.",
    "customstyle.prompt.placeholder": (
        "p. ej.: Reescribe en registro académico, usa la voz pasiva, "
        "cita con cuidado, mantén la terminología precisa."
    ),
    "customstyle.pro_hint": (
        "✦ Editar la instrucción es una función Pro. En Free, elija abajo "
        "una plantilla de profesión y úsela tal cual."
    ),
    "customstyle.templates.title": "Empiece con una plantilla",
    "customstyle.templates.hint": "Pulse una profesión para rellenar los campos de arriba. Puede ajustar la instrucción según necesite.",
    "customstyle.templates.tooltip": "Rellenar los campos de arriba con la plantilla {name}",
    "customstyle.templates.replace.title": "¿Sustituir la instrucción actual?",
    "customstyle.templates.replace.text": "Esto sobrescribirá los campos Nombre del estilo e Instrucción con la plantilla {name}.",

    # Nombre de cada plantilla, en orden de botones. Un clic copia el nombre
    # resuelto en CUSTOM_STYLE_NAME, así que es también el nombre con el que el
    # usuario se queda como nombre de su estilo.
    "customstyle.templates.lawyer.name": "Abogado",
    "customstyle.templates.doctor.name": "Médico",
    "customstyle.templates.psychotherapist.name": "Psicoterapeuta",
    "customstyle.templates.financial_advisor.name": "Asesor financiero",
    "customstyle.templates.recruiter.name": "Reclutador",
    "customstyle.templates.salesperson.name": "Comercial",
    "customstyle.templates.support.name": "Soporte",
    "customstyle.templates.insurance_agent.name": "Agente de seguros",
    "customstyle.templates.professional.name": "Profesional / Negocios",
    "customstyle.templates.programmer.name": "Programador / Técnico",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "Estilo de reescritura personalizado",
    "customstyledialog.hint": "El botón «Personalizado» reescribe el texto original según su instrucción de abajo.",
    "customstyledialog.name": "Nombre del estilo (opcional)",
    "customstyledialog.name.placeholder": "p. ej.: Académico, Tóxico, Texto de marketing",
    "customstyledialog.prompt": "Instrucción del estilo",
    "customstyledialog.prompt.placeholder": (
        "p. ej.: Reescribe en registro académico, usa la voz pasiva, "
        "cita con cuidado, mantén la terminología precisa."
    ),
    "customstyledialog.preset_limit": "Guardar estilos personalizados ilimitados es una función Pro.",

    # ---------- settings window chrome ----------
    "settingswindow.title.setup": "Omni Verte — Configuración inicial",
    "settingswindow.title.settings": "Omni Verte — Ajustes",
    "settingswindow.nav.general": "General",
    "settingswindow.nav.transcription": "Transcripción",
    "settingswindow.nav.languages": "Idiomas",
    "settingswindow.nav.custom_style": "Estilo personalizado",
    "settingswindow.nav.glossary": "Glosario",
    "settingswindow.nav.license": "Licencia",
    "settingswindow.nav.about": "Acerca de",
    "settingswindow.local_only": "Usar solo en local",
    # Sin "&&": en español se usa "y", así que no hace falta un ampersand
    # literal. Un "&&" suelto se imprimiría como un ampersand visible.
    "settingswindow.save_start": "Guardar y empezar",
    "settingswindow.save_apply": "Guardar y aplicar",
    "settingswindow.error.title": "No se puede guardar",
    "settingswindow.error.apply_failed": "No se pudo guardar {page}: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "Licencia",
    "page.license.hint": "Omni Verte es gratuita. Una licencia Pro desbloquea más funciones — vea abajo.",

    "license.status.title": "Estado",
    "license.status.hint": "El nivel al que funciona ahora este equipo.",
    "license.status.level": "Nivel actual: {tier}",
    "license.status.key": "(clave {key})",

    "license.benefit.glossary": "Glosario — hasta 200 términos (Free: 5) más packs profesionales ya preparados",
    "license.benefit.custom_styles": "Estilos personalizados — cree y edite sus propios estilos de reescritura (Free: solo plantillas)",
    "license.benefit.presets": "Preajustes de estilo — guarde todos los que quiera (Free: una ranura)",
    "license.benefit.history": "Historial — ilimitado y con búsqueda (Free: últimos 10)",
    "license.benefit.builds": "Compilaciones firmadas y con actualización automática, y soporte prioritario",

    "license.waitlist.title": "Pro está por llegar",
    "license.waitlist.hint": "Pro aún no está a la venta. Apúntese a la lista de espera y será de los primeros en saber cuándo se abre — sin pago ni compromiso.",
    "license.waitlist.unlocks": "Pro desbloquea:",
    "license.waitlist.button": "Apuntarme a la lista de espera de Pro",

    "license.benefits.unlocks": "Pro desbloquea:",
    "license.benefits.included": "Su licencia Pro incluye:",

    "license.key.title": "Clave de licencia",
    "license.hint.enter": "Introduzca la clave de licencia que recibió y pulse Activar.",
    "license.hint.activated": "Pro está activo en este equipo. Su clave se guarda de forma segura — no necesita volver a introducirla.",
    "license.hint.editing": "Introduzca la nueva clave de licencia. La actual sigue activa hasta que se acepte la nueva.",
    # "Get a license" abre la página de aterrizaje, así que "Obtener", no
    # "Comprar" — con este clic no se compra nada.
    "license.button.buy": "Obtener una licencia",
    "license.button.change_key": "Usar otra clave",
    "license.button.deactivate": "Desactivar",
    "license.button.activate": "Activar",
    "license.toast.activated": "Pro activado",
    "license.toast.cleared": "Licencia borrada — de vuelta a Free",

    "license.error.network": "No se pudo contactar con el servidor de licencias. Compruebe su conexión e inténtelo de nuevo — su estado actual no cambia.",
    "license.error.empty_key": "Introduzca primero una clave de licencia.",
    "license.error.no_fingerprint": "No se pudo leer el identificador de este equipo. La activación necesita Windows.",
    "license.error.local": "No se pudo activar en este equipo.",
    "license.error.invalid_key": "No se encontró esa clave de licencia. Revísela e inténtelo de nuevo.",
    "license.error.seat_limit": "Todos los dispositivos de esta clave están en uso. Libere un dispositivo (desactívelo allí) y vuelva a activar aquí.",
    "license.error.rate_limit": "Demasiadas activaciones recientes. Inténtelo de nuevo más tarde.",
    "license.error.inactive": "Esta licencia ya no está activa (revocada, reembolsada o caducada).",
    "license.error.refused": "El servidor de licencias rechazó la petición. No es un problema con su clave — inténtelo de nuevo o contacte con soporte si persiste.",
    "license.error.unverified": "Se activó, pero no se pudo verificar la licencia en este equipo. Contacte con soporte.",
    "license.error.generic": "No se pudo activar. Inténtelo de nuevo.",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "Capturar la tecla",
    "hotkeycapture.listening": "Pulse una tecla…",
    "hotkeycapture.tooltip": "Pulse el botón y luego la tecla que quiera — se rellena este campo.",

    # ---------- history kinds (Activity Feed) ----------
    "history.kind.transcription": "Transcripción",
    "history.kind.translation": "Traducción",
    "history.kind.fix": "Corrección gramatical",
    "history.kind.casual": "Reescritura informal",
    "history.kind.professional": "Reescritura profesional",
    "history.kind.custom": "Reescritura personalizada",

    # ---------- main window ----------
    # Los estados son nominales: es la etiqueta junto al indicador, no un
    # mensaje de la aplicación sobre sí misma.
    "main.status.ready": "Listo",
    "main.status.recording": "Escuchando…",
    "main.status.processing": "Transcribiendo…",
    "main.status.error": "Error",
    "main.status.loading": "Cargando modelo…",
    "main.status.failed": "El modelo no se cargó — revise la red, vuelva a elegirlo en Ajustes",

    # Indicador flotante de grabación (ui/rec_indicator.py) — etiquetas breves.
    "indicator.recording": "Escuchando",
    "indicator.processing": "Transcribiendo",
    "indicator.loading": "Cargando",
    "indicator.nosignal": "Sin señal",

    "main.card.original.title": "Última transcripción",
    "main.card.result.title": "Resultado de IA",
    "main.card.result.placeholder": "Aquí aparecerá la traducción o el texto reescrito.",
    "main.card.badge.generated": "Generado",
    "main.card.result.working": "Procesando… ({label})",

    "main.button.copy": "Copiar",
    "main.button.clear": "Borrar",
    # Botones segmentados de reescritura. Los nombres de estilo son las mismas
    # palabras que en el desplegable de la página «General» (general.style.*),
    # para que el botón y el ajuste se lean como lo mismo.
    "main.button.fix_grammar": "Corregir gramática",
    "main.button.casual": "Informal",
    "main.button.professional": "Profesional",
    "main.button.custom": "Personalizado",

    "main.pill.translate": "Traducir ({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "Traduce entre {primary} y {secondary}, detectando el sentido automáticamente. Clic derecho para cambiar de idiomas.",
    "main.menu.pair": "{primary} ↔ {secondary}  (auto)",
    "main.menu.change_settings": "Cambiar en los ajustes",

    "main.feed.title": "Historial",

    "main.tooltip.theme.dark": "Cambiar al tema oscuro",
    "main.tooltip.theme.light": "Cambiar al tema claro",
    "main.tooltip.settings": "Abrir ajustes",
    "main.tooltip.license": "Gestionar su licencia",
    "main.tooltip.no_key": "Se necesita una clave de OpenAI — configúrela desde la bandeja → Ajustes.",
    "main.tooltip.custom.named": "Reescribir con: {name}",
    "main.tooltip.custom.generic": "Reescribir con su estilo personalizado",
    "main.tooltip.custom.unset": "Sin configurar — pulse para definir un estilo personalizado",

    "main.hint.keyboard.transcribe": "Pulse {key} para dictar y transcribir.",
    "main.hint.keyboard.translate": "Pulse {key} para dictar, transcribir y traducir.",
    # Comillas alrededor de {style}: ahí puede ir un nombre de estilo inventado
    # por el usuario, imposible de concordar con la frase.
    "main.hint.keyboard.custom": "Pulse {key} para dictar, transcribir y devolver el texto en estilo «{style}».",
    "main.hint.style.casual": "informal",
    "main.hint.style.professional": "profesional",
    "main.hint.style.custom": "personalizado",
    "main.hint.mouse.dictate": "Pulse el botón {button} del ratón para dictar y transcribir.",
    "main.hint.mouse.hotkeys": "Configure teclas rápidas en Ajustes para traducir o reescribir en un estilo.",
    "main.mouse.middle": "central",
    "main.mouse.left": "izquierdo",
    "main.mouse.right": "derecho",

    "main.dialog.operation_failed": "La operación falló",
    "main.toast.custom_style_pro": (
        "Editar estilos personalizados es una función Pro. Elija una plantilla "
        "en Ajustes → Estilo personalizado."
    ),
}
