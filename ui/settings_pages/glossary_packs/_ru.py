# file: ui/settings_pages/glossary_packs/_ru.py

"""Russian pack content. See the package docstring for the rules this data obeys.

Russian replacements normalize *writing* — case and hyphenation the recogniser
gets inconsistent ("экг" -> "ЭКГ", "форс мажор" -> "форс-мажор"). They never
translate: a Russian doctor says and writes "анамнез", and mapping it to
"anamnesis" would rewrite the note rather than fix a mishearing.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "ru"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Only what speech recognition genuinely gets wrong: rare terms of
            # art, abbreviations. Everyday legal words (договор, суд, иск,
            # доверенность) are left out — the recognizer already knows them,
            # and every term spends a slot of a capped bias list (ElevenLabs: 50).
            # Процесс
            "подсудность", "подведомственность", "третейский суд",
            "обеспечительные меры", "преюдиция",
            # Договорное
            "оферта", "акцепт", "цессия", "новация", "отступное", "форс-мажор",
            # Корпоративное
            "аффилированное лицо",
            # Кодексы и реквизиты. The codes are here because the replacement
            # map below produces them: a canonical the term lists never declare
            # is unreachable for the ASR-bias and LLM layers, which only ever
            # see the terms.
            "ГК РФ", "АПК РФ", "ГПК РФ", "ЕГРЮЛ", "ОГРН", "ИНН", "КПП",
        ],
        # Case/hyphenation normalization only — never a translation.
        replacements=[
            ("форс мажор", "форс-мажор"),
            ("егрюл", "ЕГРЮЛ"),
            ("огрн", "ОГРН"),
            ("инн", "ИНН"),
            ("кпп", "КПП"),
            ("гк рф", "ГК РФ"),
            ("апк рф", "АПК РФ"),
            ("гпк рф", "ГПК РФ"),
        ],
        note="Терминология РФ: ГК, АПК, ГПК.",
    ),
    "medical": PackContent(
        terms=[
            # Only specialist vocabulary and abbreviations; everyday words
            # (давление, температура, анализ крови, боль) are left out — the
            # recognizer already knows them, and the bias list is capped.
            # Анамнез / осмотр
            "анамнез", "пальпация", "перкуссия", "аускультация", "патогенез",
            "эпикриз",
            # Симптомы / находки
            "тахикардия", "брадикардия", "цианоз", "гиперемия", "гематурия",
            "кровохарканье", "миалгия", "артериальная гипертензия",
            "субфебрильная температура",
            # Исследования. The two full names are here because the
            # replacement map below produces them ("оак", "оам").
            "ЭКГ", "ЭЭГ", "МРТ", "КТ", "УЗИ",
            "общий анализ крови", "общий анализ мочи", "ФГДС", "ЭхоКГ",
            # План
            "титровать дозу", "перорально",
            # Анатомия
            "проксимальный", "дистальный", "латеральный", "медиальный",
        ],
        replacements=[
            ("экг", "ЭКГ"),
            ("ээг", "ЭЭГ"),
            ("мрт", "МРТ"),
            ("кт", "КТ"),
            ("узи", "УЗИ"),
            ("фгдс", "ФГДС"),
            ("эхокг", "ЭхоКГ"),
            ("оак", "общий анализ крови"),
            ("оам", "общий анализ мочи"),
        ],
    ),
    "it": PackContent(
        # The one pack where "Russian" is genuinely mixed: Russian devs speak
        # Russian but write tool and process names in Latin, so this list keeps
        # the Latin forms plus the Cyrillic jargon whose spelling varies
        # ("деплой", "техдолг", "продакшен").
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Жаргон, который пишут кириллицей по-своему ("деплой", "техдолг")
            "коммит", "деплой", "хотфикс", "код-ревью", "рефакторинг", "техдолг",
            "бэклог", "микросервис", "брокер сообщений", "кэш", "идемпотентность",
            "шардирование", "продакшен",
            # Инструменты и процессы, которые пишут латиницей. merge/pull
            # request are declared here, not only produced by the map below —
            # the ASR-bias and LLM layers read the term lists and nothing else.
            "merge request", "pull request",
            "Kubernetes", "Docker", "PostgreSQL", "Redis", "Kafka", "nginx",
            "Git", "GitLab", "CI/CD", "API",
        ],
        replacements=[
            ("мёрж реквест", "merge request"),
            ("мерж реквест", "merge request"),
            ("пул реквест", "pull request"),
            ("кубернетес", "Kubernetes"),
            ("кубернетис", "Kubernetes"),
            ("докер", "Docker"),
            ("постгрес", "PostgreSQL"),
            ("редис", "Redis"),
            ("кафка", "Kafka"),
            ("си ай си ди", "CI/CD"),
            ("апи", "API"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # Only borrowings, abbreviations and hyphenated forms; everyday
            # words (бюджет, прибыль, налог, выручка, баланс) are left out —
            # the recognizer already knows them, and the bias list is capped.
            # Отчётность
            "дебиторская задолженность", "кредиторская задолженность",
            "счёт-фактура",
            # Показатели. "денежный поток" stays: "кэш флоу" maps to it.
            "денежный поток", "маржинальность", "оборачиваемость",
            "ставка дисконтирования", "EBITDA", "CAPEX", "OPEX", "ROI",
            # Сделки / капитал
            "вестинг", "эскроу", "хеджирование",
            # Налоги / регулирование
            "НДС", "УСН", "ОСНО", "МСФО", "РСБУ",
        ],
        replacements=[
            ("эбитда", "EBITDA"),
            ("кэпэкс", "CAPEX"),
            ("опекс", "OPEX"),
            ("кэш флоу", "денежный поток"),
            ("ндс", "НДС"),
            ("усн", "УСН"),
            ("осно", "ОСНО"),
            ("мсфо", "МСФО"),
            ("рсбу", "РСБУ"),
        ],
        note="Налоговые термины РФ: НДС, УСН, ОСНО, РСБУ.",
    ),
    "sales": PackContent(
        terms=[
            # Only jargon and abbreviations; everyday words (клиент, сделка,
            # скидка, звонок, встреча) are left out — the recognizer already
            # knows them, and the bias list is capped.
            # Воронка
            "лид", "квалифицированный лид",
            # Работа с клиентом
            "допродажа", "кросс-продажа", "теплый лид", "дожим сделки",
            # Термины
            "УТП", "CRM", "KPI", "ЛПР",
        ],
        replacements=[
            ("утп", "УТП"),
            ("лпр", "ЛПР"),
            ("срм", "CRM"),
            ("кипиай", "KPI"),
            ("ке пи ай", "KPI"),
        ],
    ),
}
