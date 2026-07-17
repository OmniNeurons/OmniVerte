# file: i18n/_de.py

"""German UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows:

* **Polite-neutral software register.** The UI addresses the user impersonally
  and imperatively ("Übliche Wahl: Ihre Muttersprache"), the way software speaks
  rather than a letter. No explicit "Du"/"Sie" pronoun where German can drop it.
* **Imperative for actions, noun for objects** — the same split English makes:
  a button is "Speichern", a section title is "Sprachpaar".
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9/F11. Translating or transliterating them helps nobody and breaks
  the user's ability to search for them.
* **Console button labels stay Latin and quoted** in the OpenAI/Groq key steps —
  those consoles have no German UI, so a translated "Create new secret key" would
  name a button the user can never find. The instruction around them is German.
* **Hints keep English's register**: plain, impersonal, no invented jargon.
"""

from __future__ import annotations

LOCALE = "de"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "An",
    "common.off": "Aus",
    "common.cancel": "Abbrechen",
    "common.save": "Speichern",
    "common.pro": "Pro",
    "common.pro.tooltip": "Pro-Funktion — auf die Warteliste setzen",
    "common.help.where_key": "Wo bekomme ich einen Schlüssel?",

    # ---------- tray menu ----------
    "tray.show_window": "Fenster anzeigen",
    "tray.indicator.show": "Schwebeanzeige einblenden",
    "tray.indicator.hide": "Schwebeanzeige ausblenden",
    "tray.mode": "Aktivierung: {mode}",
    "tray.mode.keyboard": "Tastatur",
    "tray.mode.mouse": "Maus",
    "tray.keys": "Aktivierungstasten",
    "tray.keys.change": "Ändern (Taste drücken)",
    "tray.hotkey.item": "{action}: {key}",
    "tray.action.transcribe": "Transkribieren",
    "tray.action.translate": "Transkribieren und übersetzen",
    "tray.action.custom": "Transkribieren und umschreiben",
    "tray.suppress.on": "Harter Abfang: AN (Tasten werden verschluckt)",
    "tray.suppress.off": "Harter Abfang: AUS (Tasten gehen durch)",
    "tray.mouse_button": "Maustaste zur Aktivierung: {button}",
    "tray.model": "Erkennungsmethode: {model}",
    "tray.model.local": "Lokal: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "Gerät: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Hauptsprache: {language}",
    "tray.language.other": "Weitere Sprachen…",
    "tray.settings": "Einstellungen…",
    "tray.close": "Schließen",
    "tray.tooltip.loading": "Omni Verte — Modell wird geladen…",
    "tray.tooltip.failed": "Omni Verte — Modell nicht geladen (Netzwerk prüfen, in den Einstellungen neu wählen)",

    # ---------- settings: General page ----------
    "page.general.title": "Allgemein",
    "page.general.hint": "Oberflächensprache, Tastenkürzel und Verhaltensschalter. Das meiste davon ist auch über das Tray-Menü erreichbar.",

    "general.interface.title": "Oberfläche",
    "general.interface.hint": "In welcher Sprache die App mit Ihnen spricht. Getrennt von den Sprachen, in denen Sie diktieren und zwischen denen Sie übersetzen — die stehen auf der Seite „Sprachen“.",
    "general.interface.language": "Sprache",
    "general.interface.language.hint": "Wird beim Speichern übernommen.",

    "general.activation.title": "Aktivierung",
    "general.activation.hint": (
        "Wie die Aufnahme ausgelöst wird. Tastatur nutzt ein einzelnes "
        "Tastenkürzel; Maus eine frei wählbare Maustaste."
    ),
    "general.activation.keyboard": "Tastenkürzel",
    "general.activation.mouse": "Maustaste",

    # „Taste erfassen“ steht in Anführungszeichen, wie im englischen „Catch the key“.
    "general.hotkey.transcribe": "Transkribieren und einfügen",
    "general.hotkey.transcribe.hint": "Diktieren, dann die Transkription mit Grammatikkorrektur und Zeichensetzung einfügen. Klicken Sie auf „Taste erfassen“, um eine Taste zu belegen.",
    "general.hotkey.translate": "Transkribieren und übersetzen",
    "general.hotkey.translate.hint": "Diktieren, dann vor dem Einfügen in die Zweitsprache übersetzen. Klicken Sie auf „Taste erfassen“, um eine Taste zu belegen.",
    "general.hotkey.custom": "Transkribieren und in eigenem Stil umschreiben",
    "general.hotkey.custom.hint": "Diktieren, dann im unten gewählten Stil umschreiben und einfügen. Klicken Sie auf „Taste erfassen“, um eine Taste zu belegen.",

    "general.stylepair.name": "Eigener Stil",
    "general.stylepair.hint": "{key} schreibt Ihr Diktat in diesem Stil um. „Eigener“ verwendet Ihren Prompt von der Seite „Eigener Stil“.",

    "general.style.casual": "Locker",
    "general.style.professional": "Sachlich",
    "general.style.custom": "Eigener",

    "general.suppress": "Tasten hart abfangen",
    "general.suppress.hint": "Die Tastenkürzel abfangen, damit die aktive App sie nie sieht (z. B. schaltet F11 dann den Browser nicht auf Vollbild). Ausschalten, falls es zu Konflikten kommt.",

    "general.mouse.label": "Maustaste",
    "general.mouse.hint": "Zum Aufnehmen gedrückt halten.",
    "general.mouse.middle": "Mittlere",
    "general.mouse.left": "Linke",
    "general.mouse.right": "Rechte",

    "general.behaviour.title": "Verhalten",
    "general.behaviour.floating": "Schwebeanzeige",
    "general.behaviour.floating.hint": "Kleiner Statuspunkt in der Bildschirmecke.",
    "general.behaviour.double_tap": "Fenster bei Doppeltipp öffnen",
    "general.behaviour.double_tap.hint": "Die Aktivierungstaste oder ‑maustaste zweimal schnell hintereinander (innerhalb von 300 ms) drücken, um das Hauptfenster in den Vordergrund zu holen.",
    "general.behaviour.autostart": "Beim Windows-Start starten",
    "general.behaviour.autostart.hint": "Omni Verte automatisch starten, wenn Sie sich bei Windows anmelden.",

    # Werden in general.error.hotkey_empty eingesetzt; als Genitiv formuliert
    # („Taste zum Transkribieren“ wäre umständlich), daher eigene Schlüssel und
    # nicht die Zeilenbeschriftungen wiederverwendet.
    "general.action.transcribe": "zum Transkribieren",
    "general.action.translate": "zum Übersetzen",
    "general.action.custom": "für den eigenen Stil",
    "general.error.hotkey_empty": "Die Taste {action} darf nicht leer sein, wenn der Tastaturmodus gewählt ist.",
    "general.error.hotkey_duplicate": "Jede Aktion braucht eine eigene Taste — derzeit sind zwei gleich.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Sprachen",
    "page.languages.hint": "Die Übersetzung erkennt automatisch, in welche Richtung zwischen diesen beiden Sprachen umgewandelt wird.",
    "languages.pair.title": "Sprachpaar",
    "languages.primary": "Primär",
    "languages.primary.hint": "Üblicherweise Ihre Muttersprache oder meistgenutzte Sprache.",
    "languages.secondary": "Sekundär",
    "languages.secondary.hint": "Die andere Sprache, in der Sie regelmäßig schreiben oder sprechen.",
    "languages.swap": "Sprachen tauschen",
    "languages.swap.tooltip": "Primär und Sekundär tauschen",
    "languages.error.must_differ": "Primär- und Sekundärsprache müssen sich unterscheiden.",

    # ---------- app-wide ----------
    "app.tagline": "KI-Diktat · Umschreiben · Übersetzen",

    # ---------- settings: Transcription page ----------
    # „backend" wird als „Engine" wiedergegeben: diese Seite lesen auch Juristen
    # und Ärzte (siehe die Fachpakete), und „Erkennungs-Engine" ist die Wendung,
    # die auch Nicht-Entwickler kennen.
    "page.transcription.title": "Transkription",
    "page.transcription.hint": (
        "Wählen Sie, welche Spracherkennungs-Engines in welcher Reihenfolge "
        "versucht werden. Die erste Engine mit gültigen Zugangsdaten wird aktiv."
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Lokal (Whisper)",
    "transcription.backend.hint.openai": "hohe Qualität, kostenpflichtig",
    "transcription.backend.hint.groq": "am schnellsten, mit kostenlosem Kontingent",
    "transcription.backend.hint.local": "offline, nutzt lokale CPU/GPU",

    "transcription.priority.title": "Engine-Priorität",
    "transcription.priority.hint": (
        "Zum Umsortieren ziehen. Beim Start gewinnt die erste Engine mit "
        "gültigen Zugangsdaten."
    ),

    "transcription.keys.title": "API-Schlüssel",
    "transcription.keys.hint": (
        "Gespeichert im Windows Credential Manager (DPAPI-geschützt). "
        "Leer lassen, um eine Engine zu überspringen."
    ),
    "transcription.keys.get_link": "Schlüssel holen ↗",

    "transcription.keys.openai.label": "OpenAI-Schlüssel",
    "transcription.keys.openai.placeholder": "OpenAI-API-Schlüssel eingeben",
    "transcription.keys.openai.nudge": "← OpenAI-Schlüssel eingeben",
    "transcription.keys.openai.help.title": "So bekommen Sie einen OpenAI-API-Schlüssel",
    "transcription.keys.openai.help.step1": "1. Auf platform.openai.com anmelden",
    "transcription.keys.openai.help.step2": "2. „API keys“ → „Create new secret key“",
    "transcription.keys.openai.help.step3": "3. Kopieren (beginnt mit „sk-…“) und hier einfügen",
    "transcription.keys.openai.help.note": "OpenAI ist kostenpflichtig — laden Sie Guthaben auf, um es zu nutzen.",
    "transcription.keys.openai.help.link": "OpenAI-Schlüsselseite öffnen",

    "transcription.keys.groq.label": "Groq-Schlüssel",
    "transcription.keys.groq.placeholder": "Groq-API-Schlüssel eingeben",
    "transcription.keys.groq.nudge": "← Groq-Schlüssel eingeben",
    "transcription.keys.groq.help.title": "So bekommen Sie einen Groq-API-Schlüssel (kostenlos)",
    "transcription.keys.groq.help.step1": "1. Auf console.groq.com anmelden",
    "transcription.keys.groq.help.step2": "2. „API Keys“ → „Create API Key“",
    "transcription.keys.groq.help.step3": "3. Kopieren und hier einfügen",
    "transcription.keys.groq.help.link": "Groq-Konsole öffnen",

    "transcription.models.title": "Modell pro Engine",
    "transcription.models.hint": "Wird verwendet, wenn diese Engine aktiv ist.",

    "transcription.device.title": "Gerät für lokale Transkription (nur für die lokale Engine)",
    "transcription.device.hint": (
        "Wo das lokale Whisper-Modell läuft. Ohne Wirkung, wenn OpenAI oder "
        "Groq die aktive Engine ist — die transkribieren in der Cloud."
    ),
    "transcription.device.label": "Gerät",
    "transcription.device.label.hint": "CUDA ist auf unterstützten NVIDIA-GPUs deutlich schneller als CPU.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.error.priority_empty": "Die Liste der Engine-Priorität ist leer.",

    # ---------- settings: About page ----------
    "page.about.title": "Über",
    "about.version": "Version",
    "about.version.unknown": "unbekannt",
    "about.developer": "Entwickler",
    "about.email": "E-Mail",
    "about.website": "Website",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Glossar",
    "page.glossary.hint": (
        "Firmenspezifische und alltägliche Begriffe, damit die App sie erkennt und "
        "kanonisch schreibt. Standardmäßig aus. Hinweis: Wenn die ASR-Beeinflussung "
        "oder LLM-Schichten aktiv sind, werden diese Begriffe als Teil der Anfrage "
        "an Ihren Cloud-Anbieter (OpenAI/Groq) gesendet."
    ),
    "glossary.enable.title": "Glossar aktivieren",
    "glossary.enable.hint": "Hauptschalter. Aus → Verhalten identisch zu einem Build ohne diese Funktion.",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "Fachpakete",
    "glossary.packs.hint": (
        "Kuratierte Begriffssätze, damit die Erkennung Fachjargon von Anfang an "
        "trifft — die Wörter, Abkürzungen und Schreibweisen, die ein Fachgebiet "
        "standardmäßig falsch bekommt (Pfandrecht, höhere Gewalt, Anamnese, EKG, "
        "merge request, idempotent). Klicken Sie auf ein Paket, um seine Begriffe "
        "in Ihr Glossar unten zu kopieren, und bearbeiten Sie sie dann wie selbst "
        "getippte. Eine Pro-Funktion."
    ),
    "glossary.packs.language": "Paketsprache",
    "glossary.packs.language.hint": "In welcher Sprache die importierten Begriffe verfasst sind.",
    "glossary.packs.status.available": "{count} Pakete verfügbar — auf eines klicken, um seine Begriffe in die Felder unten zu kopieren.",
    "glossary.packs.status.locked": "Fachpakete sind eine Pro-Funktion. Free hält {cap} Begriffe aktiv — weniger, als jedes Paket enthält.",
    "glossary.packs.tooltip.adds": "Fügt bis zu {count} Begriffe hinzu.",
    "glossary.packs.tooltip.locked": "Fachpakete sind eine Pro-Funktion.",
    "glossary.packs.already_loaded.title": "Paket {pack} bereits geladen",
    # {language} — englischer Sprachname ("German"), kommt aus den Daten; daher
    # Klammern statt einer flektierten Formulierung.
    "glossary.packs.already_loaded.text": "Alle Begriffe aus dem Paket ({language}) sind bereits in Ihrem Glossar — nichts hinzuzufügen.",
    "glossary.packs.count.terms": "{count} Begriffe",
    "glossary.packs.count.replacements": "{count} Ersetzungen",
    "glossary.packs.count.join": " und ",
    "glossary.packs.confirm.title": "Paket {pack} laden?",
    "glossary.packs.confirm.adds": "Das fügt Ihrem Glossar {what} hinzu, in {language}.",
    "glossary.packs.confirm.skipped": "{count} bereits vorhandene werden übersprungen.",
    "glossary.packs.confirm.editable": "Sie werden als gewöhnliche Zeilen hinzugefügt, die Sie bearbeiten oder löschen können, und erst beim Speichern auf die Festplatte geschrieben.",

    # Name und Beschreibung jedes Pakets. Das ist Oberfläche — sie folgt der
    # UI-Sprache, anders als die Begriffe selbst (deren Sprache in „Paketsprache"
    # gewählt wird) und die `note` zur Jurisdiktion, die in der Sprache des
    # Pakets selbst geschrieben ist.
    "glossary.packs.legal.name": "Recht",
    "glossary.packs.legal.hint": "Vokabular aus Prozessführung, Verträgen und Gesellschaftsrecht.",
    "glossary.packs.medical.name": "Medizin",
    "glossary.packs.medical.hint": "Klinische Notizen, Diagnosen und gängige Abkürzungen.",
    "glossary.packs.it.name": "IT & Software",                                    # _KEEP_LATIN
    "glossary.packs.it.hint": "Vokabular aus Entwicklung, DevOps und Code-Review.",  # _KEEP_LATIN
    "glossary.packs.finance.name": "Finanzen & Buchhaltung",
    "glossary.packs.finance.hint": "Vokabular aus Berichtswesen, Bewertung und Transaktionen.",
    "glossary.packs.sales.name": "Vertrieb & CRM",                               # _KEEP_LATIN
    "glossary.packs.sales.hint": "Vokabular aus Pipeline, Kundenansprache und Kundenbetreuung.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Schichten",
    "glossary.layers.hint": "Jede Schicht nutzt dieselben Begriffe; einzelne Schichten lassen sich an- oder ausschalten.",
    "glossary.layers.asr": "ASR-Beeinflussung",
    "glossary.layers.asr.hint": "Lenkt die Spracherkennung zu Ihren Begriffen hin (Cloud-Prompt / lokale Hotwords).",
    "glossary.layers.correction": "LLM-Korrektur (Transkribieren)",
    "glossary.layers.correction.hint": "Die Begriffe dem Grammatikkorrektur-Prompt der Standard-Transkriptionsaktion hinzufügen.",
    "glossary.layers.rewrite": "LLM beim Übersetzen und Umschreiben",
    "glossary.layers.rewrite.hint": "Die Begriffe den Übersetzungs-/Umschreib-Prompts hinzufügen (Schaltflächen und Tastenkürzel-Aktionen).",
    "glossary.layers.fuzzy": "Unscharfe Ersetzung (Transkribieren)",
    "glossary.layers.fuzzy.hint": "Rastet ähnliche Wörter deterministisch auf kanonische Begriffe ein, nur beim Transkribieren.",
    "glossary.layers.threshold": "Unschärfe-Schwelle",
    "glossary.layers.threshold.hint": "Wie nah ein Wort an einem Begriff sein muss, damit die unscharfe Ersetzung greift (70–100; höher = strenger).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Begriffe",
    "glossary.terms.hint": "Firmenspezifische und alltägliche Begriffe, nach Gruppen. Ein Eintrag pro Zeile.",
    "glossary.terms.tab.names": "Namen & Begriffe",
    "glossary.terms.tab.replacements": "Ersetzungen",
    "glossary.terms.names": "Namen",
    "glossary.terms.names.hint": "Ihr Unternehmen, Produkte, Kunden, Partner, Lieferanten.",
    # Erfundene Firmennamen — Eigennamen, bleiben in lateinischer Schrift.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Dienste & Begriffe",
    "glossary.terms.services.hint": "Dienstnamen, Tarife, Fachbegriffe.",
    "glossary.terms.services.placeholder": "TurboDrive\nTarif Orbita",
    # {sep} ist der `=>`-Trenner (`_REPL_SEP`), damit das Beispiel nie vom
    # Parser abweicht.
    "glossary.terms.replacements.placeholder": "turbo draiw {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Ausdrückliche, immer aktive Korrekturen — eine pro Zeile als "
        "„gehört {sep} kanonisch“. Werden wörtlich angewandt (keine unscharfen "
        "Regeln), also für Wörter nutzen, die die Erkennung zuverlässig falsch hört."
    ),
    "glossary.terms.counter.unlimited": "{total} Begriffe — alle aktiv.",
    "glossary.terms.counter.used": "{total} von {cap} Begriffen genutzt · {remaining} weitere verfügbar.",
    "glossary.terms.counter.over_free": (
        "{cap} von {total} Begriffen aktiv — der Rest ist gespeichert, aber "
        "inaktiv. Pro aktiviert alle (bis zu {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap} von {total} Begriffen aktiv — nur die ersten {cap} werden genutzt "
        "(mehr verschlechtert die Erkennungsqualität)."
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "Zeile {line}: Trenner „{sep}“ fehlt — „gehört {sep} kanonisch“ verwenden",
    "glossary.replacements.error.empty_side": "Zeile {line}: beide Seiten von „{sep}“ dürfen nicht leer sein",
    "glossary.replacements.error.more": "(+{count} weitere)",
    "glossary.replacements.error.prefix": "Ersetzungen: {details}",

    # ---------- settings: Custom style page ----------
    # Diese Seite verweist auf die Umschreib-Schaltfläche im Hauptfenster; deren
    # Beschriftung ist main.button.custom, „Eigener". Hier heißt sie genauso: wird
    # die Schaltfläche umbenannt, müssen beide Seiten des Verweises zusammen
    # geändert werden.
    "page.customstyle.title": "Eigener Stil",
    "page.customstyle.hint": (
        "Wird von der Umschreib-Schaltfläche „Eigener“ verwendet. Die Anweisung "
        "unten wird zusammen mit Ihrem Quelltext wörtlich an das Modell übergeben."
    ),
    "customstyle.preset.title": "Vorlage",
    "customstyle.name": "Stilname",
    "customstyle.name.hint": "Wird als Tooltip auf der Schaltfläche „Eigener“ angezeigt.",
    "customstyle.name.placeholder": "optional — z. B. Akademisch",
    "customstyle.prompt": "Anweisung",
    "customstyle.prompt.hint": "Das Modell behandelt dies als Anweisung auf Systemebene.",
    "customstyle.prompt.placeholder": (
        "z. B. Schreibe in akademischem Register, nutze das Passiv, "
        "zitiere sorgfältig, halte die Terminologie präzise."
    ),
    "customstyle.pro_hint": (
        "✦ Das Bearbeiten der Anweisung ist eine Pro-Funktion. In Free wählen "
        "Sie unten eine Berufsvorlage und nutzen sie unverändert."
    ),
    "customstyle.templates.title": "Mit einer Vorlage beginnen",
    "customstyle.templates.hint": "Auf einen Beruf klicken, um die Felder oben zu füllen. Die Anweisung können Sie nach Bedarf anpassen.",
    "customstyle.templates.tooltip": "Die Felder oben mit der Vorlage {name} füllen",
    "customstyle.templates.replace.title": "Aktuelle Anweisung ersetzen?",
    "customstyle.templates.replace.text": "Dies überschreibt die Felder „Stilname“ und „Anweisung“ mit der Vorlage {name}.",

    # Ein `.name` pro Vorlage, in Schaltflächenreihenfolge. Englische Paare mit
    # „/" werden im Deutschen auf die geläufige Bezeichnung eingedampft. Ein
    # Klick kopiert den Namen nach CUSTOM_STYLE_NAME, also ist das auch der Name,
    # mit dem der Nutzer am Ende bleibt.
    "customstyle.templates.lawyer.name": "Jurist",
    "customstyle.templates.doctor.name": "Arzt",
    "customstyle.templates.psychotherapist.name": "Psychotherapeut",
    "customstyle.templates.financial_advisor.name": "Finanzberater",
    "customstyle.templates.recruiter.name": "Recruiter",
    "customstyle.templates.salesperson.name": "Vertriebsmitarbeiter",
    "customstyle.templates.support.name": "Support",
    "customstyle.templates.insurance_agent.name": "Versicherungsvertreter",
    "customstyle.templates.professional.name": "Sachlich / Geschäftlich",
    "customstyle.templates.programmer.name": "Programmierer / Technisch",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "Eigener Umschreibstil",
    "customstyledialog.hint": "Die Schaltfläche „Eigener“ schreibt den Quelltext nach Ihrer Anweisung unten um.",
    "customstyledialog.name": "Stilname (optional)",
    "customstyledialog.name.placeholder": "z. B. Akademisch, Toxisch, Werbetext",
    "customstyledialog.prompt": "Stilanweisung",
    "customstyledialog.prompt.placeholder": (
        "z. B. Schreibe in akademischem Register, nutze das Passiv, "
        "zitiere sorgfältig, halte die Terminologie präzise."
    ),
    "customstyledialog.preset_limit": "Das Speichern beliebig vieler eigener Stile ist eine Pro-Funktion.",

    # ---------- settings window chrome ----------
    # „Setup" vs „Settings": die Ersteinrichtung heißt „Ersteinrichtung", die
    # laufenden Einstellungen „Einstellungen", damit beide unverwechselbar sind.
    "settingswindow.title.setup": "Omni Verte — Ersteinrichtung",             # _KEEP_LATIN
    "settingswindow.title.settings": "Omni Verte — Einstellungen",            # _KEEP_LATIN
    "settingswindow.nav.general": "Allgemein",
    "settingswindow.nav.transcription": "Transkription",
    "settingswindow.nav.languages": "Sprachen",
    "settingswindow.nav.custom_style": "Eigener Stil",
    "settingswindow.nav.glossary": "Glossar",
    "settingswindow.nav.license": "Lizenz",
    "settingswindow.nav.about": "Über",
    "settingswindow.local_only": "Nur lokal verwenden",
    # Kein „&&": das Escaping ist nur nötig, um ein wörtliches „&" darzustellen,
    # und die deutschen Beschriftungen haben keins. Ein versehentliches „&&"
    # würde als sichtbares Und-Zeichen erscheinen.
    "settingswindow.save_start": "Speichern und starten",
    "settingswindow.save_apply": "Speichern und anwenden",
    "settingswindow.error.title": "Speichern nicht möglich",
    "settingswindow.error.apply_failed": "Speichern von „{page}“ fehlgeschlagen: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "Lizenz",
    "page.license.hint": "Omni Verte ist kostenlos nutzbar. Eine Pro-Lizenz schaltet mehr Funktionen frei — siehe unten.",  # _KEEP_LATIN

    "license.status.title": "Status",
    "license.status.hint": "Die Stufe, auf der dieser Rechner derzeit läuft.",
    "license.status.level": "Aktuelle Stufe: {tier}",
    "license.status.key": "(Schlüssel {key})",

    "license.benefit.glossary": "Glossar — bis zu 200 Begriffe (Free: 5) plus fertige Fachpakete",  # _KEEP_LATIN
    "license.benefit.custom_styles": "Eigene Stile — eigene Umschreibstile erstellen und bearbeiten (Free: nur Vorlagen)",  # _KEEP_LATIN
    "license.benefit.presets": "Stilvorlagen — beliebig viele speichern (Free: ein Platz)",  # _KEEP_LATIN
    "license.benefit.history": "Verlauf — unbegrenzt und durchsuchbar (Free: letzte 10)",  # _KEEP_LATIN
    "license.benefit.builds": "Signierte, sich selbst aktualisierende Builds und bevorzugter Support",

    "license.waitlist.title": "Pro kommt bald",                               # _KEEP_LATIN
    "license.waitlist.hint": "Pro ist noch nicht im Verkauf. Setzen Sie sich auf die Warteliste und erfahren Sie als Erste, wann der Verkauf startet — ohne Zahlung, ohne Verpflichtung.",  # _KEEP_LATIN
    "license.waitlist.unlocks": "Pro schaltet frei:",                        # _KEEP_LATIN
    "license.waitlist.button": "Auf die Pro-Warteliste setzen",              # _KEEP_LATIN

    "license.benefits.unlocks": "Pro schaltet frei:",                        # _KEEP_LATIN
    "license.benefits.included": "Ihre Pro-Lizenz umfasst:",                 # _KEEP_LATIN

    "license.key.title": "Lizenzschlüssel",
    "license.hint.enter": "Geben Sie den erhaltenen Lizenzschlüssel ein und klicken Sie auf „Aktivieren“.",
    "license.hint.activated": "Pro ist auf diesem Rechner aktiv. Ihr Schlüssel ist sicher gespeichert — Sie müssen ihn nicht erneut eingeben.",  # _KEEP_LATIN
    "license.hint.editing": "Geben Sie den neuen Lizenzschlüssel ein. Der aktuelle bleibt aktiv, bis der neue angenommen wird.",
    # „Get a license" öffnet die Landingpage, daher „Holen", nicht „Kaufen" —
    # bei diesem Klick wird nichts gekauft.
    "license.button.buy": "Lizenz holen",
    "license.button.change_key": "Anderen Schlüssel verwenden",
    "license.button.deactivate": "Deaktivieren",
    "license.button.activate": "Aktivieren",
    "license.toast.activated": "Pro aktiviert",                              # _KEEP_LATIN
    "license.toast.cleared": "Lizenz entfernt — zurück zu Free",             # _KEEP_LATIN

    "license.error.network": "Der Lizenzserver war nicht erreichbar. Prüfen Sie Ihre Verbindung und versuchen Sie es erneut — Ihr aktueller Status bleibt unverändert.",
    "license.error.empty_key": "Geben Sie zuerst einen Lizenzschlüssel ein.",
    "license.error.no_fingerprint": "Die Rechner-ID konnte nicht gelesen werden. Die Aktivierung benötigt Windows.",  # _KEEP_LATIN
    "license.error.local": "Aktivierung auf diesem Rechner nicht möglich.",
    "license.error.invalid_key": "Dieser Lizenzschlüssel wurde nicht gefunden. Prüfen Sie ihn und versuchen Sie es erneut.",
    # EN sagt „(Clear it there)" — Verweis auf eine Schaltfläche, die jetzt
    # „Deaktivieren" heißt. Der deutsche Text zeigt auf die tatsächliche.
    "license.error.seat_limit": "Alle Geräte für diesen Schlüssel sind belegt. Geben Sie eines frei (dort deaktivieren) und aktivieren Sie hier erneut.",
    "license.error.rate_limit": "Zu viele Aktivierungen in letzter Zeit. Bitte versuchen Sie es später erneut.",
    "license.error.inactive": "Diese Lizenz ist nicht mehr aktiv (widerrufen, erstattet oder abgelaufen).",
    "license.error.refused": "Der Lizenzserver hat die Anfrage abgelehnt. Das liegt nicht an Ihrem Schlüssel — bitte versuchen Sie es erneut oder wenden Sie sich an den Support, falls es weiterhin auftritt.",
    "license.error.unverified": "Aktiviert, aber die Lizenz konnte auf diesem Rechner nicht überprüft werden. Bitte wenden Sie sich an den Support.",
    "license.error.generic": "Aktivierung fehlgeschlagen. Bitte versuchen Sie es erneut.",

    # ---------- hotkey capture (shared settings control) ----------
    # Die Schaltfläche ist fest 140 px (_CAPTURE_BTN_WIDTH); beide Beschriftungen
    # sind darauf ausgelegt — bei einer Umformulierung erneut prüfen.
    "hotkeycapture.catch": "Taste erfassen",
    "hotkeycapture.listening": "Taste drücken…",
    "hotkeycapture.tooltip": "Klicken, dann die gewünschte Taste drücken — sie wird in dieses Feld eingetragen.",

    # ---------- history kinds (Activity Feed) ----------
    # Durchgehend Substantive, wie im englischen Register: das sind Bezeichnungen
    # eines Verlaufseintrags, keine Aktionen.
    "history.kind.transcription": "Transkription",
    "history.kind.translation": "Übersetzung",
    "history.kind.fix": "Grammatikkorrektur",
    "history.kind.casual": "Lockere Umschrift",
    "history.kind.professional": "Sachliche Umschrift",
    "history.kind.custom": "Eigene Umschrift",

    # ---------- main window ----------
    # Statusangaben sind nominal: Beschriftung neben der Anzeige, keine
    # Ich-Meldung der App („Lade Modell…“ klänge wie eine Replik).
    "main.status.ready": "Bereit",
    "main.status.recording": "Höre zu…",
    "main.status.processing": "Transkribiere…",
    "main.status.error": "Fehler",
    "main.status.loading": "Modell wird geladen…",
    "main.status.failed": "Modell nicht geladen — Netzwerk prüfen, in den Einstellungen neu wählen",

    # Schwebende Aufnahmeanzeige (ui/rec_indicator.py) — kurze Pill-Beschriftungen.
    "indicator.recording": "Höre zu",
    "indicator.processing": "Transkription",
    "indicator.loading": "Lädt",
    "indicator.nosignal": "Kein Signal",

    "main.card.original.title": "Letzte Transkription",
    "main.card.result.title": "KI-Ergebnis",
    "main.card.result.placeholder": "Hier erscheint die Übersetzung oder der umgeschriebene Text.",
    "main.card.badge.generated": "Generiert",
    "main.card.result.working": "In Arbeit… ({label})",

    "main.button.copy": "Kopieren",
    "main.button.clear": "Leeren",
    # Segmentierte Umschreib-Schaltflächen. Die Stilnamen sind dieselben Wörter
    # wie im Dropdown auf der Seite „Allgemein“ (general.style.*), damit
    # Schaltfläche und Einstellung als dasselbe gelesen werden.
    "main.button.fix_grammar": "Grammatik korrigieren",
    "main.button.casual": "Locker",
    "main.button.professional": "Sachlich",
    "main.button.custom": "Eigener",

    "main.pill.translate": "Übersetzen ({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "Übersetzt zwischen {primary} und {secondary} und erkennt die Richtung automatisch. Rechtsklick, um die Sprachen zu ändern.",
    "main.menu.pair": "{primary} ↔ {secondary}  (auto)",
    "main.menu.change_settings": "In den Einstellungen ändern",

    "main.feed.title": "Verlauf",

    "main.tooltip.theme.dark": "Zum dunklen Design wechseln",
    "main.tooltip.theme.light": "Zum hellen Design wechseln",
    "main.tooltip.settings": "Einstellungen öffnen",
    "main.tooltip.license": "Ihre Lizenz verwalten",
    "main.tooltip.no_key": "OpenAI-Schlüssel erforderlich — über Tray → Einstellungen festlegen.",
    "main.tooltip.custom.named": "Umschreiben mit: {name}",
    "main.tooltip.custom.generic": "Mit Ihrem eigenen Stil umschreiben",
    "main.tooltip.custom.unset": "Nicht konfiguriert — klicken, um einen eigenen Stil einzurichten",

    "main.hint.keyboard.transcribe": "{key} drücken, um zu diktieren und zu transkribieren.",
    "main.hint.keyboard.translate": "{key} drücken, um zu diktieren, zu transkribieren und zu übersetzen.",
    # Anführungszeichen um {style}: dort kann ein vom Nutzer erfundener Stilname
    # eingesetzt werden — eine grammatische Angleichung ist unmöglich.
    "main.hint.keyboard.custom": "{key} drücken, um zu diktieren, zu transkribieren und den Text im Stil „{style}“ zurückzugeben.",
    "main.hint.style.casual": "locker",
    "main.hint.style.professional": "sachlich",
    "main.hint.style.custom": "eigenem",
    "main.hint.mouse.dictate": "Die {button} Maustaste drücken, um zu diktieren und zu transkribieren.",
    "main.hint.mouse.hotkeys": "Legen Sie in den Einstellungen Tastenkürzel fest, um zu übersetzen oder in einem Stil umzuschreiben.",
    "main.mouse.middle": "mittlere",
    "main.mouse.left": "linke",
    "main.mouse.right": "rechte",

    "main.dialog.operation_failed": "Vorgang fehlgeschlagen",
    "main.toast.custom_style_pro": (
        "Das Bearbeiten eigener Stile ist eine Pro-Funktion. Wählen Sie eine "
        "Vorlage unter Einstellungen → Eigener Stil."
    ),
}
