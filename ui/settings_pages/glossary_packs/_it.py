# file: ui/settings_pages/glossary_packs/_it.py

"""Italian pack content. See the package docstring for the rules this data obeys.

Legal follows Italy's practice (Codice civile / Codice di procedura civile /
Registro delle imprese), named in the pack's note. Swiss Italian practice
diverges.

Replacements are case normalization of abbreviations spelled out loud (IVA,
EBITDA, CRM). No entry translates: an Italian doctor says and writes "dispnea".

Note the module name collides with nothing: this is the *Italian* locale, while
the IT & Software pack is keyed "it" inside PACKS. Unfortunate but real — "it"
is both the ISO code for Italian and the shorthand for information technology.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "it"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Procedura
            "atto di citazione", "comparsa di risposta", "domanda riconvenzionale",
            "ricorso per cassazione", "decreto ingiuntivo",
            "provvedimento cautelare", "sequestro conservativo",
            "litispendenza", "consulenza tecnica d'ufficio", "terzo chiamato",
            "lodo arbitrale",
            # Contratti
            "clausola penale", "caparra confirmatoria", "fideiussione",
            "cessione del credito", "accollo", "novazione",
            "forza maggiore", "caso fortuito", "lucro cessante",
            "danno emergente",
            # Societario
            "Registro delle imprese", "diligenza dovuta", "partita IVA",
            # Declared because the replacement below produces it: a canonical the
            # term lists never name is unreachable for the ASR-bias and LLM
            # layers, which read the terms and nothing else.
            "Codice civile",
        ],
        replacements=[
            ("codice civile", "Codice civile"),
        ],
        note="Diritto italiano (Codice civile, c.p.c., Registro delle imprese).",
    ),
    "medical": PackContent(
        terms=[
            # Anamnesi / esame
            "anamnesi", "anamnesi patologica remota", "esame obiettivo",
            "comorbidità", "eziologia", "patogenesi",
            # Sintomi / segni
            "dispnea", "tachicardia", "bradicardia", "aritmia", "cianosi",
            "eritema", "ematuria", "emottisi", "mialgia", "ittero",
            "ipossia", "febbricola", "apiretico",
            # Esami
            "ECG", "EEG", "RM", "TC", "emocromo", "esami ematochimici",
            "ecocardiogramma",
            # Terapia
            "profilassi", "follow-up clinico",
        ],
        replacements=[
            ("ecg", "ECG"),
            ("eeg", "EEG"),
        ],
    ),
    "it": PackContent(
        # Italian developers speak Italian and write tool and process names in
        # Latin — the same split as the other IT packs.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Gergo che il riconoscimento vocale sbaglia facilmente
            "refactoring", "throughput", "microservizio", "idempotente",
            # Strumenti e processi scritti in inglese
            "merge request", "pull request", "commit", "rollback", "hotfix",
            "backlog", "deploy", "Kubernetes", "Docker", "PostgreSQL", "Redis",
            "Kafka", "nginx", "Git", "GitLab", "CI/CD", "API",
        ],
        replacements=[
            ("kubernetes", "Kubernetes"),
            ("postgres", "PostgreSQL"),
            ("ci cd", "CI/CD"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # Contabilità
            "ratei e risconti", "stato patrimoniale", "rendiconto finanziario",
            "libro mastro", "riconciliazione bancaria", "prima nota",
            # Indicatori
            "tasso di attualizzazione", "valore attuale netto",
            "tasso interno di rendimento",
            "EBITDA", "CAPEX", "OPEX", "ROI",
            # Operazioni / capitale
            "round di finanziamento", "patto parasociale", "due diligence",
            # Fiscale / regolamentare
            "IVA", "IRES", "IRAP", "revisione legale dei conti", "IFRS",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("capex", "CAPEX"),
            ("opex", "OPEX"),
            ("roi", "ROI"),
            ("iva", "IVA"),
            ("ires", "IRES"),
            ("irap", "IRAP"),
        ],
        note="Fiscalità italiana: IVA, IRES, IRAP.",
    ),
    "sales": PackContent(
        terms=[
            # Imbuto
            "imbuto di vendita", "chiamata a freddo", "prova di fattibilità",
            # Relazione con il cliente
            "proposta di valore", "vendita aggiuntiva", "vendita incrociata",
            "tasso di abbandono",
            # Termini
            "CRM", "KPI", "NPS", "contratto quadro",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
