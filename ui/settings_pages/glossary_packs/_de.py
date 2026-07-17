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
            "Klageschrift", "Klageerwiderung", "Widerklage", "Schriftsatz",
            "Berufung", "Revision", "Beschluss", "Urteil", "Versäumnisurteil",
            "Mahnbescheid", "Vollstreckungsbescheid", "einstweilige Verfügung",
            "Arrest", "Prozesskosten", "örtliche Zuständigkeit",
            "Rechtshängigkeit", "Rechtskraft", "Verjährung", "Ausschlussfrist",
            "Sachverständigengutachten", "Kläger", "Beklagter", "Streithelfer",
            "Schiedsverfahren", "Schiedsspruch", "Zwangsvollstreckung",
            "Beweislast",
            # Verträge
            "Kaufvertrag", "Mietvertrag", "Werkvertrag", "Dienstvertrag",
            "Angebot", "Annahme", "Willenserklärung", "Vertragsstrafe",
            "Anzahlung", "Bürgschaft", "Garantie", "Abtretung",
            "Schuldübernahme", "Novation", "Kündigung", "Rücktritt",
            "Anfechtung", "Leistungsstörung", "Verzug", "höhere Gewalt",
            "Schadensersatz", "entgangener Gewinn", "Vollmacht", "Treu und Glauben",
            "Gewährleistung", "Haftungsausschluss",
            # Gesellschaftsrecht
            "Satzung", "Gesellschafterversammlung", "Aufsichtsrat",
            "Geschäftsführer", "Stammkapital", "Geschäftsanteil",
            "Handelsregister", "Gesellschaft mit beschränkter Haftung",
            "Aktiengesellschaft", "Sorgfaltspflicht", "BGB", "ZPO", "HGB",
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
            "Anamnese", "Eigenanamnese", "Familienanamnese", "Beschwerden",
            "körperliche Untersuchung", "Auskultation", "Palpation",
            "Perkussion", "Differentialdiagnose", "Begleiterkrankung",
            "Ätiologie", "Pathogenese", "Prognose", "Folgeschäden",
            "Entlassungsbericht", "Verlauf",
            # Symptome / Befunde
            "Dyspnoe", "Tachykardie", "Bradykardie", "Arrhythmie", "Zyanose",
            "Ödem", "Erythem", "Hämaturie", "Hämoptyse", "Myalgie", "Synkope",
            "Ikterus", "Blässe", "arterielle Hypertonie", "Hypotonie",
            "Hypoxie", "Fieber", "subfebrile Temperatur", "fieberfrei",
            "ohne Befund",
            # Untersuchungen
            "EKG", "EEG", "MRT", "CT", "Sonographie", "Röntgen",
            "Blutbild", "Labordiagnostik", "Biopsie", "Endoskopie",
            "Echokardiographie",
            # Therapie
            "Kontraindikation", "Prophylaxe", "nüchtern", "intravenös",
            "intramuskulär", "subkutan", "peroral", "bei Bedarf", "notfallmäßig",
            "Verlaufskontrolle",
            # Anatomie
            "anterior", "posterior", "proximal", "distal", "lateral",
            "medial", "beidseitig", "einseitig",
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
        terms=[
            # Prozess
            "Branch", "Zusammenführung", "Auslieferung", "Code-Review",
            "technische Schulden", "Refactoring", "Regression", "Störung",
            "Testumgebung", "Inbetriebnahme", "Release-Kandidat", "Build",
            # Architektur
            "Microservice", "Monolith", "Lastverteiler", "Latenz", "Durchsatz",
            "Speicherleck", "Wettlaufsituation", "Ausfallsicherheit",
            "Skalierbarkeit", "Abwärtskompatibilität", "Nachrichtenwarteschlange",
            "Zwischenspeicher", "Endpunkt", "idempotent",
            # Daten
            "Datenbank", "Index", "Migration", "Transaktion", "Sperre",
            "Replikation", "Partitionierung",
            # Betrieb
            "Überwachung", "Protokollierung", "Nachvollziehbarkeit",
            "Kennzahlen", "Modultest", "Integrationstest", "Testabdeckung",
            "Lasttest",
            # Werkzeuge und Prozesse, die englisch geschrieben werden
            "merge request", "pull request", "commit", "rollback", "hotfix",
            "sprint", "backlog", "deploy", "Kubernetes", "Docker", "PostgreSQL",
            "Redis", "Kafka", "nginx", "Git", "GitLab", "CI/CD", "API",
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
            "Verbindlichkeiten", "Forderungen", "Rückstellung", "Abschreibung",
            "Bilanz", "Gewinn- und Verlustrechnung", "Kapitalflussrechnung",
            "Hauptbuch", "Rohertrag", "Nettomarge", "Betriebsausgaben",
            "Kontenabstimmung", "Jahresabschluss", "Rechnung", "Geschäftsjahr",
            "Buchungsbeleg",
            # Kennzahlen
            "Betriebskapital", "Cashflow", "freier Cashflow", "Rentabilität",
            "Gewinnschwelle", "Liquidität", "Zahlungsfähigkeit",
            "Verschuldungsgrad", "Abzinsungssatz", "Kapitalwert",
            "interner Zinsfuß", "EBITDA", "CAPEX", "OPEX", "ROI",
            # Transaktionen / Kapital
            "Stammkapital", "Kapitalerhöhung", "Verwässerung",
            "Unternehmensbewertung", "Finanzierungsrunde",
            "Gesellschaftervereinbarung", "Due Diligence", "Dividende",
            "Absicherung", "Treuhandkonto",
            # Steuern / Regulierung
            "Umsatzsteuer", "Körperschaftsteuer", "Gewerbesteuer",
            "Wirtschaftsprüfer", "IFRS", "HGB-Abschluss", "Umsatzsteuervoranmeldung",
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
            "Interessent", "Verkaufschance", "Vertriebstrichter",
            "Verkaufsphase", "Erstkontakt", "Kaltakquise", "Angebot",
            "Kostenvoranschlag", "Vorführung", "Machbarkeitsnachweis",
            "Pilotprojekt", "Verhandlung", "Abschluss", "Verkaufszyklus",
            "Absatzprognose", "Verkaufsziel", "Abschlussquote",
            "durchschnittlicher Auftragswert",
            # Kundenbeziehung
            "Einwand", "Einwandbehandlung", "Entscheidungsträger",
            "Ansprechpartner", "Schmerzpunkt", "Nutzenversprechen",
            "Zusatzverkauf", "Querverkauf", "Verlängerung", "Kundenbindung",
            "Abwanderungsrate", "Kundenstamm", "Kontaktpunkt", "Nachfassen",
            "Inbetriebnahme beim Kunden",
            # Begriffe
            "CRM", "KPI", "NPS", "Bestellung", "Rahmenvertrag",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
