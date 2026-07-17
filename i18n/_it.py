# file: i18n/_it.py

"""Italian UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows, mirroring ``_ru.py``:

* **Impersonal software register**, not a letter. The UI addresses the user
  through the imperative and impersonal forms ("Di solito la tua lingua
  madre"), never a formal "Lei" that would read as correspondence.
* **Imperative for actions, noun for objects** — the same split English makes:
  a button is "Salva", a section title is "Coppia di lingue".
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9/F11. The providers' console button labels stay Latin and quoted —
  those consoles have no Italian UI.
* **Hints keep English's register**: plain, second-person-implied, no jargon the
  English didn't already use.
"""

from __future__ import annotations

LOCALE = "it"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "On",
    "common.off": "Off",
    "common.cancel": "Annulla",
    "common.save": "Salva",
    "common.pro": "Pro",
    "common.pro.tooltip": "Funzione Pro — iscriviti alla lista d'attesa",
    "common.help.where_key": "Dove trovo una chiave?",

    # ---------- tray menu ----------
    "tray.show_window": "Mostra finestra",
    "tray.indicator.show": "Mostra indicatore fluttuante",
    "tray.indicator.hide": "Nascondi indicatore fluttuante",
    "tray.mode": "Modalità di attivazione: {mode}",
    "tray.mode.keyboard": "Tastiera",
    "tray.mode.mouse": "Mouse",
    "tray.keys": "Tasti di attivazione",
    "tray.keys.change": "Cambia (premi un tasto)",
    "tray.hotkey.item": "{action}: {key}",
    "tray.action.transcribe": "Trascrivi",
    "tray.action.translate": "Trascrivi + traduci",
    "tray.action.custom": "Trascrivi + stile",
    "tray.suppress.on": "Cattura totale: ON (tasti intercettati)",
    "tray.suppress.off": "Cattura totale: OFF (tasti lasciati passare)",
    "tray.mouse_button": "Pulsante del mouse per l'attivazione: {button}",
    "tray.model": "Metodo di trascrizione: {model}",
    "tray.model.local": "Locale: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "Dispositivo in uso: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Lingua principale: {language}",
    "tray.language.other": "Altre lingue…",
    "tray.settings": "Impostazioni…",
    "tray.close": "Chiudi",
    "tray.tooltip.loading": "Omni Verte — caricamento del modello…",
    "tray.tooltip.failed": "Omni Verte — modello non caricato (controlla la rete, riseleziona nelle impostazioni)",

    # ---------- settings: General page ----------
    "page.general.title": "Generale",
    "page.general.hint": "Lingua dell'interfaccia, tasti di scelta rapida e opzioni di comportamento. La maggior parte è raggiungibile anche dal tray.",

    "general.interface.title": "Interfaccia",
    "general.interface.hint": "In che lingua l'app comunica con te. È indipendente dalle lingue che detti e tra cui traduci, che stanno nella pagina «Lingue».",
    "general.interface.language": "Lingua",
    "general.interface.language.hint": "Applicata al salvataggio.",

    "general.activation.title": "Attivazione",
    "general.activation.hint": (
        "Come si avvia la registrazione. Con la tastiera basta un tasto di scelta rapida; "
        "con il mouse si usa un pulsante configurabile."
    ),
    "general.activation.keyboard": "Tasti di scelta rapida",
    "general.activation.mouse": "Pulsante del mouse",

    # «Cattura il tasto» — le virgolette caporali seguono il resto del testo
    # italiano; in originale è “Catch the key”.
    "general.hotkey.transcribe": "Trascrivi + incolla",
    "general.hotkey.transcribe.hint": "Detta, poi incolla la trascrizione con correzione grammaticale e punteggiatura. Clicca «Cattura il tasto» per assegnare un tasto.",
    "general.hotkey.translate": "Trascrivi + traduci",
    "general.hotkey.translate.hint": "Detta, poi traduci nella lingua secondaria prima di incollare. Clicca «Cattura il tasto» per assegnare un tasto.",
    "general.hotkey.custom": "Trascrivi + riscrivi nello stile personalizzato",
    "general.hotkey.custom.hint": "Detta, poi riscrivi nello stile scelto qui sotto e incolla. Clicca «Cattura il tasto» per assegnare un tasto.",

    "general.stylepair.name": "Personalizzato",
    "general.stylepair.hint": "Premendo {key} il dettato viene riscritto in questo stile. «Personalizzato» usa il tuo prompt dalla pagina «Stile personalizzato».",

    "general.style.casual": "Informale",
    "general.style.professional": "Professionale",
    "general.style.custom": "Personalizzato",

    "general.suppress": "Cattura totale dei tasti",
    "general.suppress.hint": "Intercetta i tasti di scelta rapida così l'app in primo piano non li riceve (per esempio F11 non manda il browser a schermo intero). Disattiva se causa conflitti.",

    "general.mouse.label": "Pulsante del mouse",
    "general.mouse.hint": "Tieni premuto per registrare.",
    "general.mouse.middle": "Centrale",
    "general.mouse.left": "Sinistro",
    "general.mouse.right": "Destro",

    "general.behaviour.title": "Comportamento",
    "general.behaviour.floating": "Indicatore fluttuante",
    "general.behaviour.floating.hint": "Piccolo punto di stato in un angolo dello schermo.",
    "general.behaviour.double_tap": "Apri la finestra con doppio tocco",
    "general.behaviour.double_tap.hint": "Premi il tasto o il pulsante di attivazione due volte in rapida successione (entro 300 ms) per portare in primo piano la finestra principale.",
    "general.behaviour.autostart": "Avvia all'accensione di Windows",
    "general.behaviour.autostart.hint": "Avvia Omni Verte automaticamente quando accedi a Windows.",

    # Inseriti in general.error.hotkey_empty. Chiavi separate dalle etichette
    # delle righe: l'errore nomina l'azione ("Il tasto di Traduci non può
    # essere vuoto") e una lingua deve poter flettere il nome in quel contesto.
    "general.action.transcribe": "Trascrivi",
    "general.action.translate": "Traduci",
    "general.action.custom": "Stile personalizzato",
    "general.error.hotkey_empty": "Il tasto di «{action}» non può essere vuoto quando è selezionata la modalità tastiera.",
    "general.error.hotkey_duplicate": "Ogni azione richiede un tasto distinto — al momento due coincidono.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Lingue",
    "page.languages.hint": "La traduzione rileva automaticamente in quale verso convertire tra queste due lingue.",
    "languages.pair.title": "Coppia di lingue",
    "languages.primary": "Principale",
    "languages.primary.hint": "Di solito la tua lingua madre o quella che usi di più.",
    "languages.secondary": "Secondaria",
    "languages.secondary.hint": "L'altra lingua in cui scrivi o parli abitualmente.",
    "languages.swap": "Scambia le lingue",
    "languages.swap.tooltip": "Scambia principale e secondaria",
    "languages.error.must_differ": "La lingua principale e quella secondaria devono essere diverse.",

    # ---------- app-wide ----------
    "app.tagline": "Dettatura con AI · Riscrittura · Traduzione",

    # ---------- settings: Transcription page ----------
    # "backend" reso "motore" invece di "backend": questa pagina la leggono
    # anche avvocati e medici (vedi i pacchetti professionali), e "motore di
    # riconoscimento" è la formula che un non sviluppatore già conosce.
    "page.transcription.title": "Trascrizione",
    "page.transcription.hint": (
        "Scegli quali motori di riconoscimento vocale provare e in quale ordine. "
        "All'avvio viene usato il primo motore con credenziali valide."
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Locale (Whisper)",
    "transcription.backend.hint.openai": "alta qualità, a pagamento",
    "transcription.backend.hint.groq": "il più veloce, con piano gratuito",
    "transcription.backend.hint.local": "offline, usa CPU/GPU locale",

    "transcription.priority.title": "Priorità dei motori",
    "transcription.priority.hint": (
        "Trascina per riordinare. All'avvio vince il primo motore con credenziali valide."
    ),

    "transcription.keys.title": "Chiavi API",
    "transcription.keys.hint": (
        "Salvate in Windows Credential Manager (protette da DPAPI). "
        "Lascia vuoto per saltare un motore."
    ),
    "transcription.keys.get_link": "Ottieni una chiave ↗",

    # Le liste di passaggi mantengono in latino, tra virgolette, le etichette dei
    # pulsanti delle console dei provider — quelle console non hanno UI italiana,
    # quindi un "Create new secret key" tradotto sarebbe un pulsante introvabile.
    "transcription.keys.openai.label": "Chiave OpenAI",
    "transcription.keys.openai.placeholder": "Inserisci la chiave API OpenAI",
    "transcription.keys.openai.nudge": "← Inserisci la tua chiave OpenAI",
    "transcription.keys.openai.help.title": "Come ottenere una chiave API OpenAI",
    "transcription.keys.openai.help.step1": "1. Accedi su platform.openai.com",
    "transcription.keys.openai.help.step2": "2. «API keys» → «Create new secret key»",
    "transcription.keys.openai.help.step3": "3. Copiala (inizia con «sk-…») e incollala qui",
    "transcription.keys.openai.help.note": "OpenAI è a pagamento — aggiungi credito per usarla.",
    "transcription.keys.openai.help.link": "Apri la pagina delle chiavi OpenAI",

    "transcription.keys.groq.label": "Chiave Groq",
    "transcription.keys.groq.placeholder": "Inserisci la chiave API Groq",
    "transcription.keys.groq.nudge": "← Inserisci la tua chiave Groq",
    "transcription.keys.groq.help.title": "Come ottenere una chiave API Groq (gratuita)",
    "transcription.keys.groq.help.step1": "1. Accedi su console.groq.com",
    "transcription.keys.groq.help.step2": "2. «API Keys» → «Create API Key»",
    "transcription.keys.groq.help.step3": "3. Copiala e incollala qui",
    "transcription.keys.groq.help.link": "Apri la console Groq",

    "transcription.models.title": "Modello per ogni motore",
    "transcription.models.hint": "Usato quando quel motore è attivo.",

    "transcription.device.title": "Dispositivo per la trascrizione locale (solo per il motore locale)",
    "transcription.device.hint": (
        "Dove gira il modello Whisper on-device. Non ha effetto quando è attivo "
        "OpenAI o Groq — quelli trascrivono nel cloud."
    ),
    "transcription.device.label": "Dispositivo",
    "transcription.device.label.hint": "CUDA è molto più veloce della CPU sulle GPU NVIDIA supportate.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.error.priority_empty": "L'elenco di priorità dei motori è vuoto.",

    # ---------- settings: About page ----------
    "page.about.title": "Informazioni",
    "about.version": "Versione",
    "about.version.unknown": "sconosciuta",
    "about.developer": "Sviluppatore",
    "about.email": "Email",
    "about.website": "Sito web",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Glossario",
    "page.glossary.hint": (
        "Termini specifici della tua azienda e termini d'uso quotidiano, così l'app li riconosce e li scrive in forma canonica. "
        "Disattivato di default. Nota: quando sono attivi il bias ASR o i livelli LLM, questi termini "
        "vengono inviati al tuo provider cloud (OpenAI/Groq) come parte della richiesta."
    ),
    "glossary.enable.title": "Abilita glossario",
    "glossary.enable.hint": "Interruttore principale. Off → il comportamento è identico a una build senza questa funzione.",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "Pacchetti professionali",
    "glossary.packs.hint": (
        "Set di termini curati, perché il riconoscimento azzecchi subito il "
        "gergo di settore — le parole, le sigle e le grafie che un ambito "
        "sbaglia di default (pegno, forza maggiore, anamnesi, ECG, merge "
        "request, idempotente). Clicca un pacchetto per copiarne i termini nel "
        "tuo glossario qui sotto, poi modificali come qualsiasi cosa tu abbia "
        "digitato. Una funzione Pro."
    ),
    "glossary.packs.language": "Lingua del pacchetto",
    "glossary.packs.language.hint": "In quale lingua sono scritti i termini importati.",
    "glossary.packs.status.available": "{count} pacchetti disponibili — clicca su uno per copiarne i termini nei campi qui sotto.",
    "glossary.packs.status.locked": "I pacchetti professionali sono una funzione Pro. Free mantiene attivi {cap} termini — meno di quanti ne contenga qualsiasi pacchetto.",
    "glossary.packs.tooltip.adds": "Aggiunge fino a {count} termini.",
    "glossary.packs.tooltip.locked": "I pacchetti professionali sono una funzione Pro.",
    "glossary.packs.already_loaded.title": "Pacchetto {pack} già caricato",
    # {language} — nome inglese della lingua ("Italian"), viene dai dati;
    # da qui le parentesi, non un concordato «in italiano».
    "glossary.packs.already_loaded.text": "Ogni termine del pacchetto ({language}) è già nel tuo glossario — niente da aggiungere.",
    "glossary.packs.count.terms": "{count} termini",
    "glossary.packs.count.replacements": "{count} sostituzioni",
    "glossary.packs.count.join": " e ",
    "glossary.packs.confirm.title": "Caricare il pacchetto {pack}?",
    "glossary.packs.confirm.adds": "Aggiunge {what} al tuo glossario, in ({language}).",
    "glossary.packs.confirm.skipped": "{count} già presenti verranno saltati.",
    "glossary.packs.confirm.editable": "Vengono aggiunti come normali righe che puoi modificare o eliminare, e scritti su disco solo al salvataggio.",

    # Nome e descrizione di ogni pacchetto. Sono interfaccia — seguono la lingua
    # della UI, a differenza dei termini stessi (la cui lingua si sceglie in
    # «Lingua del pacchetto») e della `note` sulla giurisdizione, scritta nella
    # lingua del pacchetto stesso.
    "glossary.packs.legal.name": "Legale",
    "glossary.packs.legal.hint": "Lessico di contenzioso, contratti e diritto societario.",
    "glossary.packs.medical.name": "Medico",
    "glossary.packs.medical.hint": "Note cliniche, diagnosi e sigle comuni.",
    "glossary.packs.it.name": "IT e software",                                    # _KEEP_LATIN
    "glossary.packs.it.hint": "Lessico di sviluppo, DevOps e code review.",       # _KEEP_LATIN
    "glossary.packs.finance.name": "Finanza e contabilità",
    "glossary.packs.finance.hint": "Lessico di reportistica, valutazione e operazioni.",
    "glossary.packs.sales.name": "Vendite e CRM",                                 # _KEEP_LATIN
    "glossary.packs.sales.hint": "Lessico di pipeline, contatto commerciale e gestione clienti.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Livelli",
    "glossary.layers.hint": "Ogni livello usa gli stessi termini; attiva o disattiva i singoli livelli.",
    "glossary.layers.asr": "Bias ASR",
    "glossary.layers.asr.hint": "Orienta il riconoscimento vocale verso i tuoi termini (prompt nel cloud / hotwords in locale).",
    "glossary.layers.correction": "Correzione LLM (trascrizione)",
    "glossary.layers.correction.hint": "Aggiunge i termini al prompt di correzione grammaticale nell'azione di trascrizione predefinita.",
    "glossary.layers.rewrite": "LLM in traduzione e riscrittura",
    "glossary.layers.rewrite.hint": "Aggiunge i termini ai prompt di traduzione e riscrittura (pulsanti manuali + azioni con tasti di scelta rapida).",
    "glossary.layers.fuzzy": "Sostituzione fuzzy (trascrizione)",
    "glossary.layers.fuzzy.hint": "Riconduce in modo deterministico le parole quasi uguali ai termini canonici, solo in trascrizione.",
    "glossary.layers.threshold": "Soglia fuzzy",
    "glossary.layers.threshold.hint": "Quanto una parola deve essere vicina a un termine perché scatti la sostituzione fuzzy (70–100; più alto = più severo).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Termini",
    "glossary.terms.hint": "Parole specifiche della tua azienda, raggruppate. Una voce per riga.",
    "glossary.terms.tab.names": "Nomi e termini",
    "glossary.terms.tab.replacements": "Sostituzioni",
    "glossary.terms.names": "Nomi",
    "glossary.terms.names.hint": "La tua azienda, i prodotti, i clienti, i partner, i fornitori.",
    # Nomi di aziende inventati — nomi propri, restano in latino.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Servizi e termini",
    "glossary.terms.services.hint": "Nomi di servizi, piani, termini di settore.",
    "glossary.terms.services.placeholder": "TurboDrive\npiano Orbita",
    "glossary.terms.replacements.placeholder": "turbo draiv {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Correzioni esplicite, sempre attive — una per riga come «sentito {sep} canonico». "
        "Applicate alla lettera (senza regole fuzzy), quindi usale per le parole che il "
        "riconoscimento sente male in modo costante."
    ),
    "glossary.terms.counter.unlimited": "{total} termini — tutti attivi.",
    "glossary.terms.counter.used": "{total} di {cap} termini usati · altri {remaining} disponibili.",
    "glossary.terms.counter.over_free": (
        "{cap} di {total} termini attivi — gli altri sono salvati ma inattivi. "
        "Pro li attiva tutti (fino a {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap} di {total} termini attivi — vengono usati solo i primi {cap} "
        "(di più peggiora la qualità del riconoscimento)."
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "riga {line}: manca il separatore «{sep}» — usa «sentito {sep} canonico»",
    "glossary.replacements.error.empty_side": "riga {line}: entrambi i lati di «{sep}» devono essere compilati",
    "glossary.replacements.error.more": "(+{count} altri)",
    "glossary.replacements.error.prefix": "Sostituzioni: {details}",

    # ---------- settings: Custom style page ----------
    "page.customstyle.title": "Stile personalizzato",
    "page.customstyle.hint": (
        "Usato dal pulsante di riscrittura «Personalizzato». L'istruzione qui sotto "
        "viene passata alla lettera al modello insieme al testo di origine."
    ),
    "customstyle.preset.title": "Preset",
    "customstyle.name": "Nome dello stile",
    "customstyle.name.hint": "Mostrato come tooltip sul pulsante «Personalizzato».",
    "customstyle.name.placeholder": "facoltativo — es. Accademico",
    "customstyle.prompt": "Istruzione",
    "customstyle.prompt.hint": "Il modello la tratta come una direttiva di livello sistema.",
    "customstyle.prompt.placeholder": (
        "es. Riscrivi in registro accademico, usa la forma passiva, "
        "cita con cura, mantieni la terminologia precisa."
    ),
    "customstyle.pro_hint": (
        "✦ Modificare l'istruzione è una funzione Pro. Con Free scegli un "
        "modello professionale qui sotto e usalo così com'è."
    ),
    "customstyle.templates.title": "Parti da un modello",
    "customstyle.templates.hint": "Clicca una professione per compilare i campi qui sopra. Puoi ritoccare l'istruzione come serve.",
    "customstyle.templates.tooltip": "Compila i campi qui sopra con il modello {name}",
    "customstyle.templates.replace.title": "Sostituire l'istruzione attuale?",
    "customstyle.templates.replace.text": "Questo sovrascrive i campi «Nome dello stile» e «Istruzione» con il modello {name}.",

    # Un `.name` per modello, in ordine di pulsante. Un clic copia il nome
    # risolto in CUSTOM_STYLE_NAME, quindi è anche il nome con cui l'utente
    # resta come nome del proprio stile.
    "customstyle.templates.lawyer.name": "Avvocato",
    "customstyle.templates.doctor.name": "Medico / Clinico",
    "customstyle.templates.psychotherapist.name": "Psicoterapeuta",
    "customstyle.templates.financial_advisor.name": "Consulente finanziario",
    "customstyle.templates.recruiter.name": "Recruiter",
    "customstyle.templates.salesperson.name": "Venditore",
    "customstyle.templates.support.name": "Assistenza",
    "customstyle.templates.insurance_agent.name": "Agente assicurativo",
    "customstyle.templates.professional.name": "Professionale / Business",
    "customstyle.templates.programmer.name": "Programmatore / Tecnico",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "Stile di riscrittura personalizzato",
    "customstyledialog.hint": "Il pulsante «Personalizzato» riscrive il testo di origine seguendo la tua istruzione qui sotto.",
    "customstyledialog.name": "Nome dello stile (facoltativo)",
    "customstyledialog.name.placeholder": "es. Accademico, Tossico, Testo di marketing",
    "customstyledialog.prompt": "Istruzione dello stile",
    "customstyledialog.prompt.placeholder": (
        "es. Riscrivi in registro accademico, usa la forma passiva, "
        "cita con cura, mantieni la terminologia precisa."
    ),
    "customstyledialog.preset_limit": "Salvare stili personalizzati illimitati è una funzione Pro.",

    # ---------- settings window chrome ----------
    "settingswindow.title.setup": "Omni Verte — Configurazione iniziale",
    "settingswindow.title.settings": "Omni Verte — Impostazioni",
    "settingswindow.nav.general": "Generale",
    "settingswindow.nav.transcription": "Trascrizione",
    "settingswindow.nav.languages": "Lingue",
    "settingswindow.nav.custom_style": "Stile personalizzato",
    "settingswindow.nav.glossary": "Glossario",
    "settingswindow.nav.license": "Licenza",
    "settingswindow.nav.about": "Informazioni",
    "settingswindow.local_only": "Usa solo in locale",
    # Niente "&&" qui: l'escape serve solo a rendere una "&" letterale, e le
    # etichette italiane non ne hanno. Una "&&" vagante stamperebbe una
    # e commerciale visibile.
    "settingswindow.save_start": "Salva e avvia",
    "settingswindow.save_apply": "Salva e applica",
    "settingswindow.error.title": "Impossibile salvare",
    "settingswindow.error.apply_failed": "Impossibile salvare «{page}»: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "Licenza",
    "page.license.hint": "Omni Verte è gratuita. Una licenza Pro sblocca altre funzioni — vedi sotto.",

    "license.status.title": "Stato",
    "license.status.hint": "Il livello a cui gira attualmente questo computer.",
    "license.status.level": "Livello attuale: {tier}",
    "license.status.key": "(chiave {key})",

    "license.benefit.glossary": "Glossario — fino a 200 termini (Free: 5) più pacchetti professionali pronti all'uso",
    "license.benefit.custom_styles": "Stili personalizzati — crea e modifica i tuoi stili di riscrittura (Free: solo modelli)",
    "license.benefit.presets": "Preset di stile — salvane quanti vuoi (Free: uno slot)",
    "license.benefit.history": "Cronologia — illimitata e ricercabile (Free: ultimi 10)",
    "license.benefit.builds": "Build firmate con aggiornamento automatico e supporto prioritario",

    "license.waitlist.title": "Pro sta arrivando",
    "license.waitlist.hint": "Pro non è ancora in vendita. Iscriviti alla lista d'attesa e sarai tra i primi a saperlo quando apre — nessun pagamento, nessun impegno.",
    "license.waitlist.unlocks": "Pro sblocca:",
    "license.waitlist.button": "Iscriviti alla lista d'attesa Pro",

    "license.benefits.unlocks": "Pro sblocca:",
    "license.benefits.included": "La tua licenza Pro include:",

    "license.key.title": "Chiave di licenza",
    "license.hint.enter": "Inserisci la chiave di licenza che hai ricevuto, poi clicca Attiva.",
    "license.hint.activated": "Pro è attivo su questo computer. La tua chiave è archiviata in modo sicuro — non devi inserirla di nuovo.",
    "license.hint.editing": "Inserisci la nuova chiave di licenza. Quella attuale resta attiva finché la nuova non viene accettata.",
    # "Get a license" apre la landing page, quindi "Ottieni", non "Acquista" —
    # con questo clic non si compra nulla.
    "license.button.buy": "Ottieni una licenza",
    "license.button.change_key": "Usa un'altra chiave",
    "license.button.deactivate": "Disattiva",
    "license.button.activate": "Attiva",
    "license.toast.activated": "Pro attivato",
    "license.toast.cleared": "Licenza rimossa — di nuovo Free",

    "license.error.network": "Impossibile raggiungere il server delle licenze. Controlla la connessione e riprova — il tuo stato attuale non cambia.",
    "license.error.empty_key": "Inserisci prima una chiave di licenza.",
    "license.error.no_fingerprint": "Impossibile leggere l'ID di questo computer. L'attivazione richiede Windows.",
    "license.error.local": "Impossibile attivare su questo computer.",
    "license.error.invalid_key": "Chiave di licenza non trovata. Controllala e riprova.",
    # EN dice "(Clear it there)" — un riferimento datato a un pulsante ora
    # etichettato Disattiva. L'italiano punta al pulsante che esiste davvero.
    "license.error.seat_limit": "Tutti i dispositivi di questa chiave sono in uso. Libera un dispositivo (disattivalo lì), poi attiva di nuovo qui.",
    "license.error.rate_limit": "Troppe attivazioni di recente. Riprova più tardi.",
    "license.error.inactive": "Questa licenza non è più attiva (revocata, rimborsata o scaduta).",
    "license.error.refused": "Il server delle licenze ha rifiutato la richiesta. Non è un problema della tua chiave — riprova o contatta l'assistenza se persiste.",
    "license.error.unverified": "Attivata, ma non è stato possibile verificare la licenza su questo computer. Contatta l'assistenza.",
    "license.error.generic": "Impossibile attivare. Riprova.",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "Cattura il tasto",
    "hotkeycapture.listening": "Premi un tasto…",
    "hotkeycapture.tooltip": "Clicca, poi premi il tasto che vuoi — verrà inserito in questo campo.",

    # ---------- history kinds (Activity Feed) ----------
    "history.kind.transcription": "Trascrizione",
    "history.kind.translation": "Traduzione",
    "history.kind.fix": "Correzione grammaticale",
    "history.kind.casual": "Riscrittura informale",
    "history.kind.professional": "Riscrittura professionale",
    "history.kind.custom": "Riscrittura personalizzata",

    # ---------- main window ----------
    # Gli stati sono nominali: è l'etichetta accanto all'indicatore, non un
    # messaggio dell'app su di sé.
    "main.status.ready": "Pronto",
    "main.status.recording": "In ascolto…",
    "main.status.processing": "Trascrizione…",
    "main.status.error": "Errore",
    "main.status.loading": "Caricamento del modello…",
    "main.status.failed": "Modello non caricato — controlla la rete, riseleziona nelle impostazioni",

    # Indicatore di registrazione fluttuante (ui/rec_indicator.py) — etichette brevi.
    "indicator.recording": "In ascolto",
    "indicator.processing": "Trascrizione",
    "indicator.loading": "Caricamento",
    "indicator.nosignal": "Nessun segnale",

    "main.card.original.title": "Ultima trascrizione",
    "main.card.result.title": "Risultato AI",
    "main.card.result.placeholder": "Qui apparirà la traduzione o il testo riscritto.",
    "main.card.badge.generated": "Generato",
    "main.card.result.working": "In elaborazione… ({label})",

    "main.button.copy": "Copia",
    "main.button.clear": "Cancella",
    # Pulsanti segmentati di riscrittura. I nomi degli stili sono le stesse
    # parole del menu a discesa nella pagina «Generale» (general.style.*),
    # così pulsante e impostazione si leggono come la stessa cosa.
    "main.button.fix_grammar": "Correggi grammatica",
    "main.button.casual": "Informale",
    "main.button.professional": "Professionale",
    "main.button.custom": "Personalizzato",

    "main.pill.translate": "Traduci ({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "Traduce tra {primary} e {secondary}, rilevando automaticamente il verso. Clic destro per cambiare lingue.",
    "main.menu.pair": "{primary} ↔ {secondary}  (auto)",
    "main.menu.change_settings": "Cambia nelle impostazioni",

    "main.feed.title": "Cronologia",

    "main.tooltip.theme.dark": "Passa al tema scuro",
    "main.tooltip.theme.light": "Passa al tema chiaro",
    "main.tooltip.settings": "Apri le impostazioni",
    "main.tooltip.license": "Gestisci la tua licenza",
    "main.tooltip.no_key": "Serve una chiave OpenAI — impostala dal tray → «Impostazioni».",
    "main.tooltip.custom.named": "Riscrivi usando: {name}",
    "main.tooltip.custom.generic": "Riscrivi con il tuo stile personalizzato",
    "main.tooltip.custom.unset": "Non configurato — clicca per impostare uno stile personalizzato",

    "main.hint.keyboard.transcribe": "Premi {key} per dettare e trascrivere.",
    "main.hint.keyboard.translate": "Premi {key} per dettare, trascrivere e tradurre.",
    # Virgolette intorno a {style}: lì può finire un nome di stile inventato
    # dall'utente, impossibile da concordare con «stile».
    "main.hint.keyboard.custom": "Premi {key} per dettare, trascrivere e restituire il testo in stile «{style}».",
    "main.hint.style.casual": "informale",
    "main.hint.style.professional": "professionale",
    "main.hint.style.custom": "personalizzato",
    "main.hint.mouse.dictate": "Premi il pulsante {button} del mouse per dettare e trascrivere.",
    "main.hint.mouse.hotkeys": "Imposta i tasti di scelta rapida nelle impostazioni per tradurre o riscrivere in uno stile.",
    "main.mouse.middle": "centrale",
    "main.mouse.left": "sinistro",
    "main.mouse.right": "destro",

    "main.dialog.operation_failed": "Operazione non riuscita",
    "main.toast.custom_style_pro": (
        "Modificare gli stili personalizzati è una funzione Pro. Scegli un modello "
        "in Impostazioni → Stile personalizzato."
    ),
}
