# file: ui/settings_pages/glossary_packs/_de.py

"""German pack content. See the package docstring for the rules this data obeys.

Legal follows Germany's practice (BGB / ZPO / HGB / Handelsregister) — the
majority jurisdiction, named in the pack's note so an Austrian or Swiss user is
told rather than surprised. Austrian ABGB and Swiss OR terminology diverges.

Replacements are case normalization of abbreviations spelled out loud (BGB, USt,
EBITDA). No entry translates: a German lawyer says and writes "Verjährung".
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "de"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Verfahren
            "Klageerwiderung", "Widerklage", "Schriftsatz", "Versäumnisurteil",
            "Mahnbescheid", "Vollstreckungsbescheid", "einstweilige Verfügung",
            "Rechtshängigkeit", "Ausschlussfrist", "Streithelfer",
            "Schiedsspruch",
            # Verträge
            "Werkvertrag", "Willenserklärung", "Schuldübernahme", "Novation",
            "Leistungsstörung", "Treu und Glauben",
            # Gesellschaftsrecht
            "Stammkapital", "Geschäftsanteil", "Handelsregister",
            "BGB", "ZPO", "HGB",
        ],
        replacements=[
            ("bgb", "BGB"),
            ("zpo", "ZPO"),
            ("hgb", "HGB"),
        ],
        note="Deutsches Recht (BGB, ZPO, HGB) — nicht ABGB/OR.",
    ),
    "medical": PackContent(
        terms=[
            # Anamnese / Untersuchung
            "Anamnese", "Auskultation", "Palpation", "Perkussion",
            "Differentialdiagnose", "Ätiologie", "Pathogenese",
            # Symptome / Befunde
            "Dyspnoe", "Tachykardie", "Bradykardie", "Arrhythmie", "Zyanose",
            "Ödem", "Erythem", "Hämaturie", "Hämoptyse", "Myalgie", "Synkope",
            "Ikterus", "Hypoxie", "subfebrile Temperatur",
            # Untersuchungen
            "EKG", "EEG", "MRT", "Sonographie", "Echokardiographie",
            # Therapie
            "intramuskulär", "subkutan", "peroral",
        ],
        replacements=[
            ("ekg", "EKG"),
            ("eeg", "EEG"),
            ("mrt", "MRT"),
        ],
    ),
    "it": PackContent(
        # German developers speak German and write tool and process names in
        # Latin — the same split as the other IT packs.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Fachjargon, den die Spracherkennung leicht verfehlt
            "Branch", "Code-Review", "Refactoring", "Microservice", "idempotent",
            # Werkzeuge und Prozesse, die englisch geschrieben werden
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
            # Buchhaltung
            "Rückstellung", "Gewinn- und Verlustrechnung", "Kapitalflussrechnung",
            "Rohertrag", "Kontenabstimmung",
            # Kennzahlen
            "Betriebskapital", "Cashflow", "freier Cashflow", "Gewinnschwelle",
            "Verschuldungsgrad", "Abzinsungssatz", "Kapitalwert",
            "interner Zinsfuß", "EBITDA", "CAPEX", "OPEX", "ROI",
            # Transaktionen / Kapital
            "Verwässerung", "Due Diligence", "Treuhandkonto",
            # Steuern / Regulierung
            "Körperschaftsteuer", "IFRS", "HGB-Abschluss", "Umsatzsteuervoranmeldung",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("capex", "CAPEX"),
            ("opex", "OPEX"),
            ("roi", "ROI"),
            ("ifrs", "IFRS"),
        ],
        note="Deutsches Steuer- und Bilanzrecht (HGB, Umsatzsteuer).",
    ),
    "sales": PackContent(
        terms=[
            # Vertriebstrichter
            "Vertriebstrichter", "Kaltakquise", "Machbarkeitsnachweis",
            "Abschlussquote",
            # Kundenbeziehung
            "Einwandbehandlung", "Schmerzpunkt", "Nutzenversprechen",
            "Zusatzverkauf", "Querverkauf", "Abwanderungsrate", "Kontaktpunkt",
            # Begriffe
            "CRM", "KPI", "NPS",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
