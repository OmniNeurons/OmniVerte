# file: i18n/_ru.py

"""Russian UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows, since they are the ones a reviewer will
otherwise re-litigate every time:

* **"Вы" is dropped, not capitalised.** The UI addresses the user impersonally
  ("Обычно ваш родной язык") rather than with a capital-В "Вы", which reads as
  correspondence, not software.
* **Imperative for actions, noun for objects** — the same split English makes:
  a button is "Сохранить", a section title is "Пара языков".
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Whisper, OpenAI,
  Groq, CPU, CUDA, F9. Transliterating them ("Виспер") helps nobody and breaks
  the user's ability to search for them. ``test_russian_strings_are_russian``
  knows about this and only exempts keys listed in ``_KEEP_LATIN``.
* **Hints keep English's register**: plain, second-person-implied, no jargon the
  English didn't already use.
"""

from __future__ import annotations

LOCALE = "ru"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "Вкл",
    "common.off": "Выкл",
    "common.cancel": "Отмена",
    "common.save": "Сохранить",
    "common.pro": "Pro",
    "common.pro.tooltip": "Функция Pro — записаться в лист ожидания",
    "common.help.where_key": "Где взять ключ?",

    # ---------- tray menu ----------
    "tray.show_window": "Показать окно",
    "tray.indicator.show": "Показать плавающий индикатор",
    "tray.indicator.hide": "Скрыть плавающий индикатор",
    "tray.mode": "Активация: {mode}",
    "tray.mode.keyboard": "Клавиатура",
    "tray.mode.mouse": "Мышь",
    "tray.keys": "Клавиши активации",
    "tray.keys.change": "Изменить (нажмите клавишу)",
    "tray.hotkey.item": "{action}: {key}",
    "tray.action.transcribe": "Расшифровать",
    "tray.action.translate": "Расшифровать и перевести",
    "tray.action.custom": "Расшифровать и переписать",
    "tray.suppress.on": "Жёсткий перехват: ВКЛ (клавиши поглощаются)",
    "tray.suppress.off": "Жёсткий перехват: ВЫКЛ (проходят насквозь)",
    "tray.mouse_button": "Кнопка мыши для активации: {button}",
    "tray.model": "Способ распознавания: {model}",
    "tray.model.local": "Локально: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "Устройство: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Основной язык: {language}",
    "tray.language.other": "Другие языки…",
    "tray.settings": "Настройки…",
    "tray.close": "Закрыть",
    "tray.tooltip.loading": "Omni Verte — загрузка модели…",
    "tray.tooltip.failed": "Omni Verte — модель не загрузилась (проверьте сеть, выберите заново в настройках)",

    # ---------- settings: General page ----------
    "page.general.title": "Основное",
    "page.general.hint": "Язык интерфейса, горячие клавиши и переключатели поведения. Аналогичные функции доступны в меню трея.",

    "general.interface.title": "Интерфейс",
    "general.interface.hint": "На каком языке отображаются элементы управления приложением. Не связано с языками, на которых вы диктуете и между которыми переводите, — они на странице «Языки».",
    "general.interface.language": "Язык",
    "general.interface.language.hint": "Применится при сохранении.",

    "general.activation.title": "Активация",
    "general.activation.hint": (
        "Как запускается запись. С клавиатуры — одной из горячих клавиш; "
        "мышью — по нажатию кнопки."
    ),
    "general.activation.keyboard": "Горячие клавиши",
    "general.activation.mouse": "Кнопка мыши",

    # «Поймать клавишу» — кавычки-ёлочки, как в остальном русском тексте;
    # в оригинале это “Catch the key”.
    "general.hotkey.transcribe": "Транскрибировать и вставить",
    "general.hotkey.transcribe.hint": "Продиктовать, затем вставить транскрипцию с исправлением грамматики и расстановкой знаков препинания. Нажмите «Задать», чтобы задать клавишу.",
    "general.hotkey.translate": "Транскрибировать и перевести",
    "general.hotkey.translate.hint": "Продиктовать, затем перевести на дополнительный язык и вставить. Нажмите «Задать», чтобы задать клавишу.",
    "general.hotkey.custom": "Транскрибировать и переписать в кастомный стиль",
    "general.hotkey.custom.hint": "Продиктовать, затем переписать в выбранном стиле и вставить. Нажмите «Задать», чтобы задать клавишу.",

    "general.stylepair.name": "Кастомный стиль",
    "general.stylepair.hint": "Нажатие {key} переписывает продиктованное в этом стиле. «Кастомный» использует ваш промпт со страницы «Кастомный стиль».",

    "general.style.casual": "Неформальный",
    "general.style.professional": "Деловой",
    "general.style.custom": "Кастомный",

    "general.suppress": "Перехватывать клавиши",
    "general.suppress.hint": "Перехватывать нажатие горячих клавиш, чтобы другие приложения их не получали (например, чтобы F11 не разворачивала браузер на весь экран). Выключите, если возникают конфликты.",

    "general.mouse.label": "Кнопка мыши",
    "general.mouse.hint": "Удерживайте нажатой для записи.",
    "general.mouse.middle": "Средняя",
    "general.mouse.left": "Левая",
    "general.mouse.right": "Правая",

    "general.behaviour.title": "Поведение",
    "general.behaviour.floating": "Отображать плавающий индикатор",
    "general.behaviour.floating.hint": "Небольшая точка состояния в углу экрана. Показывается во время записи и транскрипции.",
    "general.behaviour.double_tap": "Открывать окно по двойному нажатию на хоткей",
    "general.behaviour.double_tap.hint": "Нажмите клавишу или кнопку активации дважды подряд (в пределах 300 мс), чтобы вывести главное окно на передний план.",
    "general.behaviour.autostart": "Запускать вместе с Windows",
    "general.behaviour.autostart.hint": "Запускать Omni Verte автоматически при входе в Windows.",

    # Подставляются в general.error.hotkey_empty в родительном падеже:
    # «Клавиша расшифровки не может быть пустой…». Поэтому это отдельные
    # ключи, а не переиспользование подписей строк.
    "general.action.transcribe": "расшифровки",
    "general.action.translate": "перевода",
    "general.action.custom": "своего стиля",
    "general.error.hotkey_empty": "Клавиша {action} не может быть пустой, когда выбран режим клавиатуры.",
    "general.error.hotkey_duplicate": "У каждого действия должна быть своя клавиша — сейчас две совпадают.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Языки",
    "page.languages.hint": "Переводчик автоматически определяет направление между этими двумя языками.",
    "languages.pair.title": "Пара языков",
    "languages.primary": "Основной",
    "languages.primary.hint": "Обычно родной или самый используемый язык.",
    "languages.secondary": "Дополнительный",
    "languages.secondary.hint": "Второй язык, на котором вы регулярно пишете или говорите.",
    "languages.swap": "Поменять языки местами",
    "languages.swap.tooltip": "Поменять основной и дополнительный",
    "languages.error.must_differ": "Основной и дополнительный языки должны различаться.",

    # ---------- app-wide ----------
    "app.tagline": "Диктовка с AI · Автокорректировка · Перевод",

    # ---------- settings: Transcription page ----------
    # "backend" is rendered "движок" rather than "бэкенд": this page is read by
    # lawyers and doctors as well as developers (see the glossary packs), and
    # "движок распознавания" is the phrase a non-developer already knows.
    "page.transcription.title": "Транскрибация",
    "page.transcription.hint": (
        "Выберите, какие движки распознавания речи применять и в каком порядке. "
        "При запуске будет использоваться первый движок с рабочими ключами."
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Локально (Whisper)",
    "transcription.backend.hint.openai": "высокое качество, платно",
    "transcription.backend.hint.groq": "самый быстрый, есть бесплатный тариф",
    "transcription.backend.hint.local": "офлайн, использует локальный CPU/GPU",

    "transcription.priority.title": "Приоритет движков",
    "transcription.priority.hint": (
        "Перетаскивайте, чтобы изменить порядок. "
        "При запуске побеждает первый движок с рабочими ключами."
    ),

    "transcription.keys.title": "Ключи API",
    "transcription.keys.hint": (
        "Хранятся в Windows Credential Manager (защита DPAPI). "
        "Оставьте поле пустым, чтобы пропустить движок."
    ),
    "transcription.keys.get_link": "Создать ключ ↗",

    # The step lists keep the providers' own console labels in Latin and quote
    # them — those consoles have no Russian UI, so a translated "Create new
    # secret key" would be a button the user can never find. The instruction
    # around them is Russian; the thing to click is verbatim.
    "transcription.keys.openai.label": "Ключ OpenAI",
    "transcription.keys.openai.placeholder": "Введите ключ API OpenAI",
    "transcription.keys.openai.nudge": "← Введите ключ OpenAI",
    "transcription.keys.openai.help.title": "Как создать ключ API OpenAI",
    "transcription.keys.openai.help.step1": "1. Войдите на platform.openai.com",
    "transcription.keys.openai.help.step2": "2. Откройте «API keys» → «Create new secret key»",
    "transcription.keys.openai.help.step3": "3. Скопируйте его (начинается с «sk-…») и вставьте сюда",
    "transcription.keys.openai.help.note": "OpenAI платный — пополните баланс, чтобы пользоваться.",
    "transcription.keys.openai.help.link": "Открыть страницу ключей OpenAI",

    "transcription.keys.groq.label": "Ключ Groq",
    "transcription.keys.groq.placeholder": "Введите ключ API Groq",
    "transcription.keys.groq.nudge": "← Введите ключ Groq",
    "transcription.keys.groq.help.title": "Как создать ключ API Groq (бесплатно)",
    "transcription.keys.groq.help.step1": "1. Войдите на console.groq.com",
    "transcription.keys.groq.help.step2": "2. Откройте «API Keys» → «Create API Key»",
    "transcription.keys.groq.help.step3": "3. Скопируйте его и вставьте сюда",
    "transcription.keys.groq.help.link": "Открыть консоль Groq",

    "transcription.models.title": "Модель распознавания аудио для каждого движка",
    "transcription.models.hint": "Используется, когда активен этот движок.",

    "transcription.device.title": "Устройство для локального распознавания аудио (актуально только для локального движка)",
    "transcription.device.hint": (
        "Где работает локальная модель Whisper. Ни на что не влияет, когда "
        "активен движок OpenAI или Groq, — они распознают в облаке."
    ),
    "transcription.device.label": "Устройство",
    "transcription.device.label.hint": "На подходящих видеокартах NVIDIA CUDA заметно быстрее CPU.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.mic.title": "Микрофон",
    "transcription.mic.hint": (
        "С какого входа идёт запись и лёгкая подготовка звука перед распознаванием "
        "(фильтр гула и выравнивание громкости). Модель ASR не меняет."
    ),
    "transcription.mic.device.label": "Устройство ввода",
    "transcription.mic.device.hint": (
        "«По умолчанию» — как в Windows. Выберите конкретный микрофон, если "
        "пишет не тот вход, или если на столе USB-микрофон."
    ),
    "transcription.mic.device.default": "Системный по умолчанию",
    "transcription.enhance.label": "Улучшение звука",
    "transcription.enhance.hint": (
        "Лёгкое: чуть усиливает тихую речь и убирает низкий гул до передачи в модель. "
        "Выкл.: сырая запись (как раньше)."
    ),
    "transcription.enhance.off": "Выкл.",
    "transcription.enhance.light": "Лёгкое (рекомендуется)",

    "transcription.error.priority_empty": "Список приоритета движков пуст.",

    # ---------- settings: About page ----------
    "page.about.title": "О программе",
    "about.version": "Версия",
    "about.version.unknown": "неизвестно",
    "about.developer": "Разработчик",
    "about.email": "Почта",
    "about.website": "Сайт",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Глоссарий",
    "page.glossary.hint": (
        "Термины вашей компании и ежедневные термины — чтобы приложение распознавало их и писало "
        "в каноничной форме. По умолчанию выключено. Важно: когда включено "
        "слои распознавания или LLM-исправления, эти термины уходят "
        "облачному провайдеру (OpenAI/Groq) в части запроса."
    ),
    "glossary.enable.title": "Включить глоссарий",
    "glossary.enable.hint": "Главный переключатель. Выключен → поведение идентично сборке без этой функции.",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "Профессиональные наборы",
    "glossary.packs.hint": (
        "Готовые наборы терминов, чтобы распознавание сразу справлялось с "
        "профессиональным жаргоном — слова, сокращения и написания, которые "
        "в конкретной области по умолчанию выходят неверно (залог, форс-мажор, "
        "анамнез, ЭКГ, merge request, идемпотентность). Нажмите на набор, чтобы "
        "скопировать его термины в глоссарий ниже, а затем правьте их как любые "
        "свои. Функция Pro."
    ),
    "glossary.packs.language": "Язык набора",
    "glossary.packs.language.hint": "На каком языке написаны импортируемые термины.",
    "glossary.packs.status.available": "Доступно наборов: {count} — нажмите на любой, чтобы скопировать его термины в поля ниже.",
    "glossary.packs.status.locked": "Профессиональные наборы — функция Pro. На Free активными остаются {cap} терминов — меньше, чем в любом наборе.",
    "glossary.packs.tooltip.adds": "Добавит до {count} терминов.",
    "glossary.packs.tooltip.locked": "Профессиональные наборы — функция Pro.",
    "glossary.packs.already_loaded.title": "Набор {pack} уже загружен",
    # {language} — английское название языка ("Russian"), приходит из данных;
    # отсюда скобки, а не согласованное «на русском языке».
    "glossary.packs.already_loaded.text": "Все термины из набора ({language}) уже есть в глоссарии — добавлять нечего.",
    "glossary.packs.count.terms": "терминов: {count}",
    "glossary.packs.count.replacements": "замен: {count}",
    "glossary.packs.count.join": ", ",
    "glossary.packs.confirm.title": "Загрузить набор {pack}?",
    "glossary.packs.confirm.adds": "Добавит в глоссарий ({language}) — {what}.",
    "glossary.packs.confirm.skipped": "Уже присутствующих: {count} — они будут пропущены.",
    "glossary.packs.confirm.editable": "Они добавляются как обычные строки, которые можно править и удалять, и записываются на диск только при сохранении.",

    # Название и описание каждого набора. Это интерфейс — они следуют языку UI,
    # в отличие от самих терминов (их язык выбирается в «Языке набора») и от
    # `note` про юрисдикцию, который написан на языке самого набора.
    "glossary.packs.legal.name": "Юриспруденция",
    "glossary.packs.legal.hint": "Лексика судебных споров, договоров и корпоративного права.",
    "glossary.packs.medical.name": "Медицина",
    "glossary.packs.medical.hint": "Клинические записи, диагнозы и общепринятые сокращения.",
    "glossary.packs.it.name": "IT и разработка",                                  # _KEEP_LATIN
    "glossary.packs.it.hint": "Лексика разработки, DevOps и код-ревью.",          # _KEEP_LATIN
    "glossary.packs.finance.name": "Финансы и бухгалтерия",
    "glossary.packs.finance.hint": "Лексика отчётности, оценки и сделок.",
    "glossary.packs.sales.name": "Продажи и CRM",                                 # _KEEP_LATIN
    "glossary.packs.sales.hint": "Лексика воронки, холодных касаний и работы с клиентами.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Слои",
    "glossary.layers.hint": "Все слои используют одни и те же термины; включайте и выключайте их по отдельности.",
    "glossary.layers.asr": "Подсказка распознаванию",
    "glossary.layers.asr.hint": "Смещает распознавание речи в сторону ваших терминов (prompt в облаке / hotwords локально).",
    "glossary.layers.correction": "LLM-исправление (расшифровка)",
    "glossary.layers.correction.hint": "Добавлять термины в промпт исправления грамматики в стандартном действии расшифровки.",
    "glossary.layers.rewrite": "LLM в переводе и переписывании",
    "glossary.layers.rewrite.hint": "Добавлять термины в промпты перевода и переписывания (кнопки и действия по горячим клавишам).",
    "glossary.layers.fuzzy": "Нечёткая замена (расшифровка)",
    "glossary.layers.fuzzy.hint": "Детерминированно подтягивает похожие слова к каноничным терминам, только при расшифровке.",
    "glossary.layers.threshold": "Порог нечёткости",
    "glossary.layers.threshold.hint": "Насколько слово должно быть близко к термину, чтобы сработала нечёткая замена (70–100; больше = строже).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Термины",
    "glossary.terms.hint": "Слова, специфичные для вашей компании и ежедневные термины, по группам. По одной записи в строке.",
    "glossary.terms.tab.names": "Имена и термины",
    "glossary.terms.tab.replacements": "Замены",
    "glossary.terms.names": "Имена",
    "glossary.terms.names.hint": "Ваша компания, продукты, клиенты, партнёры, поставщики.",
    # Вымышленные названия компаний — имена собственные, остаются латиницей.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Сервисы и термины",
    "glossary.terms.services.hint": "Названия сервисов, тарифов, отраслевые термины.",
    "glossary.terms.services.placeholder": "TurboDrive\nтариф Орбита",
    "glossary.terms.replacements.placeholder": "турбо драйв {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Явные, всегда включённые исправления — по одному в строке в виде "
        "«услышано {sep} каноничное». Применяются буквально (без нечётких "
        "правил), поэтому используйте их для слов, которые распознавание "
        "стабильно слышит неверно."
    ),
    "glossary.terms.counter.unlimited": "Терминов: {total} — все активны.",
    "glossary.terms.counter.used": "Использовано терминов: {total} из {cap} · доступно ещё {remaining}.",
    "glossary.terms.counter.over_free": (
        "Активны {cap} из {total} терминов — остальные сохранены, но не "
        "используются. Pro активирует все (до {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "Активны {cap} из {total} терминов — используются только первые {cap} "
        "(больше — хуже качество распознавания)."
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "строка {line}: нет разделителя «{sep}» — используйте «услышано {sep} каноничное»",
    "glossary.replacements.error.empty_side": "строка {line}: обе стороны «{sep}» должны быть заполнены",
    "glossary.replacements.error.more": "(и ещё {count})",
    "glossary.replacements.error.prefix": "Замены: {details}",

    # ---------- settings: Custom style page ----------
    # Эта страница ссылается на кнопку переписывания в главном окне; её подпись
    # — main.button.custom, «Кастомный». Здесь она называется точно так же: если
    # кнопку переименуют, обе стороны ссылки надо править вместе.
    "page.customstyle.title": "Кастомный стиль",
    "page.customstyle.hint": (
        "Используется кнопкой переписывания «Кастомный». Инструкция ниже "
        "передаётся модели дословно вместе с исходным текстом."
    ),
    "customstyle.preset.title": "Пресет",
    "customstyle.name": "Название стиля",
    "customstyle.name.hint": "Показывается как подсказка на кнопке «Кастомный».",
    "customstyle.name.placeholder": "необязательно — например, Academic",
    "customstyle.prompt": "Инструкция",
    "customstyle.prompt.hint": "Модель воспринимает это как указание системного уровня.",
    "customstyle.prompt.placeholder": (
        "например: перепиши в академическом стиле, используй пассивный залог, "
        "аккуратно ссылайся на источники, сохраняй точность терминологии."
    ),
    "customstyle.pro_hint": (
        "✦ Редактирование инструкции — функция Pro. На Free выберите "
        "профессиональный шаблон ниже и используйте его как есть."
    ),
    "customstyle.templates.title": "Начните с шаблона",
    "customstyle.templates.hint": "Нажмите на профессию, чтобы заполнить поля выше. Можете исправить инструкцию по своему усмотрению.",
    "customstyle.templates.tooltip": "Заполнить поля выше шаблоном {name}",
    "customstyle.templates.replace.title": "Заменить текущую инструкцию?",
    "customstyle.templates.replace.text": "Поля «Название стиля» и «Инструкция» будут перезаписаны шаблоном {name}.",

    # Названия шаблонов, в порядке кнопок. Английские пары через «/» в русском
    # схлопываются: «клиницист» — редкое слово, «Врач» покрывает и то и другое.
    # Клик копирует название в CUSTOM_STYLE_NAME, так что это ещё и то имя, с
    # которым пользователь останется.
    "customstyle.templates.lawyer.name": "Юрист",
    "customstyle.templates.doctor.name": "Врач",
    "customstyle.templates.psychotherapist.name": "Психотерапевт",
    "customstyle.templates.financial_advisor.name": "Финансовый консультант",
    "customstyle.templates.recruiter.name": "Рекрутер",
    "customstyle.templates.salesperson.name": "Менеджер по продажам",
    "customstyle.templates.support.name": "Поддержка",
    "customstyle.templates.insurance_agent.name": "Страховой агент",
    "customstyle.templates.professional.name": "Деловой стиль",
    "customstyle.templates.programmer.name": "Программист",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "Кастомный стиль переписывания",
    "customstyledialog.hint": "Кнопка «Кастомный» переписывает исходный текст по вашей инструкции ниже.",
    "customstyledialog.name": "Название стиля (необязательно)",
    "customstyledialog.name.placeholder": "например: Academic, Toxic, Marketing copy",
    "customstyledialog.prompt": "Инструкция стиля",
    "customstyledialog.prompt.placeholder": (
        "например: перепиши в академическом стиле, используй пассивный залог, "
        "аккуратно ссылайся на источники, сохраняй точность терминологии."
    ),
    "customstyledialog.preset_limit": "Сохранение неограниченного числа своих стилей — функция Pro.",

    # ---------- settings window chrome ----------
    # "Setup" vs "Settings" is a real distinction in EN that "Настройка"/
    # "Настройки" would collapse into a one-letter difference — the first-run
    # window says "Первоначальная настройка" so the two are unmistakable.
    "settingswindow.title.setup": "Omni Verte — Первоначальная настройка",   # _KEEP_LATIN
    "settingswindow.title.settings": "Omni Verte — Настройки",               # _KEEP_LATIN
    "settingswindow.nav.general": "Основное",
    "settingswindow.nav.transcription": "Транскрипция",
    "settingswindow.nav.languages": "Языки",
    "settingswindow.nav.custom_style": "Кастомный стиль",
    "settingswindow.nav.glossary": "Глоссарий",
    "settingswindow.nav.license": "Лицензия",
    "settingswindow.nav.about": "О программе",
    "settingswindow.local_only": "Только локально",
    # No "&&" here: the escape is only needed to render a literal "&", and the
    # Russian labels have none. A stray "&&" would print as a visible ampersand.
    "settingswindow.save_start": "Сохранить и начать",
    "settingswindow.save_apply": "Сохранить и применить",
    "settingswindow.error.title": "Не удалось сохранить",
    "settingswindow.error.apply_failed": "Не удалось сохранить раздел «{page}»: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "Лицензия",
    "page.license.hint": "Omni Verte бесплатна. Лицензия Pro открывает больше функций — смотрите ниже.",  # _KEEP_LATIN

    "license.status.title": "Статус",
    "license.status.hint": "Уровень, на котором сейчас работает этот компьютер.",
    "license.status.level": "Текущий уровень: {tier}",
    "license.status.key": "(ключ {key})",

    "license.benefit.glossary": "Глоссарий — до 200 терминов (Free: 5) и готовые профессиональные наборы",  # _KEEP_LATIN
    "license.benefit.custom_styles": "Свои стили — создавайте и редактируйте собственные стили переписывания (Free: только шаблоны)",  # _KEEP_LATIN
    "license.benefit.presets": "Пресеты стилей — сохраняйте сколько угодно (Free: один слот)",  # _KEEP_LATIN
    "license.benefit.history": "История — без ограничений и с поиском (Free: последние 10)",  # _KEEP_LATIN
    "license.benefit.builds": "Подписанные сборки с автообновлением и приоритетная поддержка",

    "license.waitlist.title": "Pro скоро",                                   # _KEEP_LATIN
    "license.waitlist.hint": "Pro пока не продаётся. Запишитесь в лист ожидания — узнаете первыми, когда откроются продажи. Без оплаты и обязательств.",  # _KEEP_LATIN
    "license.waitlist.unlocks": "Что даёт Pro:",                             # _KEEP_LATIN
    "license.waitlist.button": "Записаться в лист ожидания Pro",             # _KEEP_LATIN

    "license.benefits.unlocks": "Что даёт Pro:",                             # _KEEP_LATIN
    "license.benefits.included": "Ваша лицензия Pro включает:",              # _KEEP_LATIN

    "license.key.title": "Лицензионный ключ",
    "license.hint.enter": "Введите полученный лицензионный ключ и нажмите «Активировать».",
    "license.hint.activated": "Pro активен на этом компьютере. Ключ сохранён надёжно — вводить его снова не нужно.",  # _KEEP_LATIN
    "license.hint.editing": "Введите новый лицензионный ключ. Текущий останется активным, пока новый не будет принят.",
    # "Get a license" opens the landing page, so "Получить", not "Купить" —
    # nothing is bought at this click.
    "license.button.buy": "Получить лицензию",
    "license.button.change_key": "Ввести другой ключ",
    "license.button.deactivate": "Деактивировать",
    "license.button.activate": "Активировать",
    "license.toast.activated": "Pro активирован",                            # _KEEP_LATIN
    "license.toast.cleared": "Лицензия удалена — снова Free",                # _KEEP_LATIN

    "license.error.network": "Не удалось связаться с сервером лицензий. Проверьте подключение и попробуйте ещё раз — текущий статус не изменился.",
    "license.error.empty_key": "Сначала введите лицензионный ключ.",
    "license.error.no_fingerprint": "Не удалось определить идентификатор компьютера. Активация работает только в Windows.",  # _KEEP_LATIN
    "license.error.local": "Не удалось активировать на этом компьютере.",
    "license.error.invalid_key": "Такой лицензионный ключ не найден. Проверьте его и попробуйте ещё раз.",
    # EN says "(Clear it there)" — a stale reference to a button now labelled
    # Deactivate. The Russian points at the button that actually exists.
    "license.error.seat_limit": "Все устройства для этого ключа заняты. Освободите одно (деактивируйте его там) и активируйте здесь снова.",
    "license.error.rate_limit": "Слишком много активаций за последнее время. Попробуйте позже.",
    "license.error.inactive": "Эта лицензия больше не действует: отозвана, возвращена или истекла.",
    "license.error.refused": "Сервер лицензий отклонил запрос. Дело не в вашем ключе — попробуйте ещё раз или обратитесь в поддержку, если это повторится.",
    "license.error.unverified": "Активация прошла, но проверить лицензию на этом компьютере не удалось. Обратитесь в поддержку.",
    "license.error.generic": "Не удалось активировать. Попробуйте ещё раз.",

    # ---------- hotkey capture (shared settings control) ----------
    # The button is a fixed 140px (_CAPTURE_BTN_WIDTH); both labels are sized to
    # fit it — worth re-checking if either is reworded.
    "hotkeycapture.catch": "Задать",
    "hotkeycapture.listening": "Нажмите клавишу…",
    "hotkeycapture.tooltip": "Нажмите кнопку, затем — нужную клавишу: она подставится в это поле.",

    # ---------- history kinds (Activity Feed) ----------
    # Nouns throughout, matching English's register: these are labels on a feed
    # entry, not actions. "…переписывание" is the literal rendering of the
    # rewrite kinds and reads as machinery; the style's name is what the user
    # actually picked and what they recognise here.
    "history.kind.transcription": "Транскрипция",
    "history.kind.translation": "Перевод",
    "history.kind.fix": "Исправление грамматики",
    "history.kind.casual": "Неформальный стиль",
    "history.kind.professional": "Деловой стиль",
    "history.kind.custom": "Кастомный стиль",

    # ---------- main window ----------
    # Статусы — назывные: это подпись рядом с индикатором, а не сообщение
    # приложения о себе («Загружаю модель…» звучало бы как реплика).
    "main.status.ready": "Готово",
    "main.status.recording": "Слушаю…",
    "main.status.processing": "Расшифровка…",
    "main.status.error": "Ошибка",
    "main.status.loading": "Загрузка модели…",
    "main.status.failed": "Модель не загрузилась — проверьте сеть, выберите заново в настройках",

    # Плавающий индикатор записи (ui/rec_indicator.py) — короткие подписи пилюли.
    "indicator.recording": "Слушаю",
    "indicator.processing": "Расшифровка",
    "indicator.loading": "Загрузка",
    "indicator.nosignal": "Нет сигнала",

    "main.card.original.title": "Последняя транскрипция",
    "main.card.result.title": "Результат AI",
    "main.card.result.placeholder": "Здесь появится перевод или переписанный текст.",
    "main.card.badge.generated": "Сгенерировано",
    "main.card.result.working": "Обработка… ({label})",

    "main.button.copy": "Копировать",
    "main.button.clear": "Очистить",
    # Сегментированные кнопки переписывания. Названия стилей — те же слова, что
    # в выпадающем списке на странице «Основное» (general.style.*), чтобы
    # кнопка и настройка читались как одно и то же.
    "main.button.fix_grammar": "Исправляющий грамматику",
    "main.button.casual": "Неформальный",
    "main.button.professional": "Деловой",
    "main.button.custom": "Кастомный",

    "main.pill.translate": "Перевести ({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "Переводит между {primary} и {secondary}, направление определяется автоматически. Правый клик — сменить языки.",
    "main.menu.pair": "{primary} ↔ {secondary}  (авто)",
    "main.menu.change_settings": "Изменить в настройках",

    "main.feed.title": "История",

    "main.tooltip.theme.dark": "Переключить на тёмную тему",
    "main.tooltip.theme.light": "Переключить на светлую тему",
    "main.tooltip.settings": "Открыть настройки",
    "main.tooltip.license": "Управление лицензией",
    "main.tooltip.no_key": "Нужен ключ OpenAI — задайте его через трей → «Настройки».",
    "main.tooltip.custom.named": "Переписать в стиле: {name}",
    "main.tooltip.custom.generic": "Переписать в вашем стиле",
    "main.tooltip.custom.unset": "Не настроено — нажмите, чтобы задать свой стиль",

    "main.hint.keyboard.transcribe": "Нажмите {key}, чтобы продиктовать и расшифровать.",
    "main.hint.keyboard.translate": "Нажмите {key}, чтобы продиктовать, расшифровать и перевести.",
    # Кавычки вокруг {style}: туда может подставиться название стиля,
    # придуманное пользователем, — согласовать его с «стиле» невозможно.
    "main.hint.keyboard.custom": "Нажмите {key}, чтобы продиктовать, расшифровать и вернуть текст в стиле «{style}».",
    "main.hint.style.casual": "Неформальный",
    "main.hint.style.professional": "Деловой",
    "main.hint.style.custom": "Кастомный",
    # {button} — в винительном падеже, чтобы согласоваться с «кнопку».
    "main.hint.mouse.dictate": "Нажмите {button} кнопку мыши, чтобы продиктовать и расшифровать.",
    "main.hint.mouse.hotkeys": "Задайте горячие клавиши в настройках, чтобы переводить или переписывать в стиле.",
    "main.mouse.middle": "среднюю",
    "main.mouse.left": "левую",
    "main.mouse.right": "правую",

    "main.dialog.operation_failed": "Не удалось выполнить",
    "main.toast.custom_style_pro": (
        "Редактирование своих стилей — функция Pro. Выберите шаблон "
        "на странице «Кастомный стиль» в настройках."
    ),
}
