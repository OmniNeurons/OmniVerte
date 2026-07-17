# file: i18n/_fr.py

"""French UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows:

* **Impersonal software register.** The UI addresses the user with an implicit
  vouvoiement ("Généralement votre langue maternelle"), staying software-like
  rather than epistolary — matching the tone of English and ``_ru.py``.
* **Imperative for actions, noun for objects** — the same split English makes:
  a button is "Enregistrer", a section title is "Paire de langues".
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9/F11. Transliterating them helps nobody and breaks searchability.
* **Provider console labels stay Latin and quoted.** The OpenAI/Groq consoles
  have no French UI, so their button names ("Create new secret key", …) are
  kept verbatim in quotes; the instruction around them is French.
* **Hints keep English's register**: plain, impersonal, no invented jargon.
* **Typography**: plain ASCII quotes and colons are used throughout for safety;
  French guillemets « » are used only where they read naturally.
"""

from __future__ import annotations

LOCALE = "fr"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "Activé",
    "common.off": "Désactivé",
    "common.cancel": "Annuler",
    "common.save": "Enregistrer",
    "common.pro": "Pro",
    "common.pro.tooltip": "Fonctionnalité Pro — rejoindre la liste d'attente",
    "common.help.where_key": "Où obtenir une clé ?",

    # ---------- tray menu ----------
    "tray.show_window": "Afficher la fenêtre",
    "tray.indicator.show": "Afficher l'indicateur flottant",
    "tray.indicator.hide": "Masquer l'indicateur flottant",
    "tray.mode": "Mode d'activation : {mode}",
    "tray.mode.keyboard": "Clavier",
    "tray.mode.mouse": "Souris",
    "tray.keys": "Touches d'activation",
    "tray.keys.change": "Modifier (appuyez sur une touche)",
    "tray.hotkey.item": "{action} : {key}",
    "tray.action.transcribe": "Transcrire",
    "tray.action.translate": "Transcrire et traduire",
    "tray.action.custom": "Transcrire et réécrire",
    "tray.suppress.on": "Capture forcée : ACTIVÉE (touches interceptées)",
    "tray.suppress.off": "Capture forcée : DÉSACTIVÉE (touches transmises)",
    "tray.mouse_button": "Bouton de souris pour l'activation : {button}",
    "tray.model": "Méthode de transcription : {model}",
    "tray.model.local": "Local : {model}",
    "tray.model.openai": "OpenAI API : {model}",
    "tray.model.groq": "Groq : {model}",
    "tray.device": "Appareil utilisé : {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Langue principale : {language}",
    "tray.language.other": "Autres langues…",
    "tray.settings": "Paramètres…",
    "tray.close": "Fermer",
    "tray.tooltip.loading": "Omni Verte — chargement du modèle…",
    "tray.tooltip.failed": "Omni Verte — échec du modèle (vérifiez le réseau, resélectionnez dans les paramètres)",

    # ---------- settings: General page ----------
    "page.general.title": "Général",
    "page.general.hint": "Langue de l'interface, raccourcis clavier et options de comportement. La plupart sont aussi accessibles depuis la zone de notification.",

    "general.interface.title": "Interface",
    "general.interface.hint": "La langue dans laquelle l'application s'adresse à vous. Distincte des langues que vous dictez et entre lesquelles vous traduisez, sur la page Langues.",
    "general.interface.language": "Langue",
    "general.interface.language.hint": "Appliquée à l'enregistrement.",

    "general.activation.title": "Activation",
    "general.activation.hint": (
        "Comment l'enregistrement est déclenché. Le clavier utilise un raccourci ; "
        "la souris utilise un bouton configurable."
    ),
    "general.activation.keyboard": "Raccourcis clavier",
    "general.activation.mouse": "Bouton de souris",

    # « Attraper la touche » — la formule reprend le “Catch the key” anglais.
    "general.hotkey.transcribe": "Transcrire et coller",
    "general.hotkey.transcribe.hint": "Dictez, puis collez la transcription avec correction grammaticale et ponctuation. Cliquez sur « Attraper la touche » pour définir une touche.",
    "general.hotkey.translate": "Transcrire et traduire",
    "general.hotkey.translate.hint": "Dictez, puis traduisez vers la langue secondaire avant de coller. Cliquez sur « Attraper la touche » pour définir une touche.",
    "general.hotkey.custom": "Transcrire et réécrire dans un style personnalisé",
    "general.hotkey.custom.hint": "Dictez, puis réécrivez dans le style choisi ci-dessous et collez. Cliquez sur « Attraper la touche » pour définir une touche.",

    "general.stylepair.name": "Personnalisé",
    "general.stylepair.hint": "Appuyer sur {key} réécrit votre dictée dans ce style. « Personnalisé » utilise votre instruction de la page Style personnalisé.",

    "general.style.casual": "Décontracté",
    "general.style.professional": "Professionnel",
    "general.style.custom": "Personnalisé",

    "general.suppress": "Capture forcée des touches",
    "general.suppress.hint": "Interceptez les raccourcis pour que l'application active ne les reçoive jamais (par ex. F11 ne mettra pas le navigateur en plein écran). Désactivez en cas de conflit.",

    "general.mouse.label": "Bouton de souris",
    "general.mouse.hint": "Maintenu enfoncé pour enregistrer.",
    "general.mouse.middle": "Milieu",
    "general.mouse.left": "Gauche",
    "general.mouse.right": "Droit",

    "general.behaviour.title": "Comportement",
    "general.behaviour.floating": "Indicateur flottant",
    "general.behaviour.floating.hint": "Petit point d'état dans le coin de l'écran.",
    "general.behaviour.double_tap": "Ouvrir la fenêtre par double appui",
    "general.behaviour.double_tap.hint": "Appuyez deux fois rapidement (en moins de 300 ms) sur la touche/le bouton d'activation pour amener la fenêtre principale au premier plan.",
    "general.behaviour.autostart": "Lancer au démarrage de Windows",
    "general.behaviour.autostart.hint": "Démarrer Omni Verte automatiquement à votre connexion à Windows.",

    # Interpolés dans general.error.hotkey_empty. Le français forme
    # « Le raccourci de transcription… » — d'où « de … », pour lire naturellement
    # dans ce cadre ; ce sont des clés distinctes, pas les libellés de lignes.
    "general.action.transcribe": "de transcription",
    "general.action.translate": "de traduction",
    "general.action.custom": "de style personnalisé",
    "general.error.hotkey_empty": "Le raccourci {action} ne peut pas être vide lorsque le mode clavier est sélectionné.",
    "general.error.hotkey_duplicate": "Chaque action a besoin d'un raccourci distinct — deux sont actuellement identiques.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Langues",
    "page.languages.hint": "La traduction détecte automatiquement le sens de conversion entre ces deux langues.",
    "languages.pair.title": "Paire de langues",
    "languages.primary": "Principale",
    "languages.primary.hint": "Généralement votre langue maternelle ou la plus utilisée.",
    "languages.secondary": "Secondaire",
    "languages.secondary.hint": "L'autre langue dans laquelle vous écrivez ou parlez régulièrement.",
    "languages.swap": "Intervertir les langues",
    "languages.swap.tooltip": "Intervertir principale et secondaire",
    "languages.error.must_differ": "Les langues principale et secondaire doivent être différentes.",

    # ---------- app-wide ----------
    "app.tagline": "Dictée par IA · Réécriture · Traduction",

    # ---------- settings: Transcription page ----------
    # "backend" est rendu par « moteur » : cette page est lue par des juristes et
    # des médecins autant que par des développeurs (voir les packs métier), et
    # « moteur de reconnaissance » est la formule qu'un non-développeur connaît.
    "page.transcription.title": "Transcription",
    "page.transcription.hint": (
        "Choisissez quels moteurs de reconnaissance vocale essayer et dans quel ordre. "
        "Le premier moteur disposant d'identifiants valides devient le moteur actif."
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Local (Whisper)",
    "transcription.backend.hint.openai": "haute qualité, payant",
    "transcription.backend.hint.groq": "le plus rapide, offre gratuite disponible",
    "transcription.backend.hint.local": "hors ligne, utilise le CPU/GPU local",

    "transcription.priority.title": "Priorité des moteurs",
    "transcription.priority.hint": (
        "Faites glisser pour réordonner. Au démarrage, le premier moteur "
        "disposant d'identifiants valides l'emporte."
    ),

    "transcription.keys.title": "Clés API",
    "transcription.keys.hint": (
        "Stockées dans le Gestionnaire d'identifiants Windows (protection DPAPI). "
        "Laissez vide pour ignorer un moteur."
    ),
    "transcription.keys.get_link": "Obtenir une clé ↗",

    # Les listes d'étapes gardent en latin, entre guillemets, les libellés des
    # consoles des fournisseurs : ces consoles n'ont pas d'UI française, donc un
    # « Create new secret key » traduit désignerait un bouton introuvable.
    "transcription.keys.openai.label": "Clé OpenAI",
    "transcription.keys.openai.placeholder": "Saisissez la clé API OpenAI",
    "transcription.keys.openai.nudge": "← Saisissez votre clé OpenAI",
    "transcription.keys.openai.help.title": "Obtenir une clé API OpenAI",
    "transcription.keys.openai.help.step1": "1. Connectez-vous sur platform.openai.com",
    "transcription.keys.openai.help.step2": "2. « API keys » → « Create new secret key »",
    "transcription.keys.openai.help.step3": "3. Copiez-la (commence par « sk-… ») et collez-la ici",
    "transcription.keys.openai.help.note": "OpenAI est payant — ajoutez du crédit de facturation pour l'utiliser.",
    "transcription.keys.openai.help.link": "Ouvrir la page des clés OpenAI",

    "transcription.keys.groq.label": "Clé Groq",
    "transcription.keys.groq.placeholder": "Saisissez la clé API Groq",
    "transcription.keys.groq.nudge": "← Saisissez votre clé Groq",
    "transcription.keys.groq.help.title": "Obtenir une clé API Groq (gratuit)",
    "transcription.keys.groq.help.step1": "1. Connectez-vous sur console.groq.com",
    "transcription.keys.groq.help.step2": "2. « API Keys » → « Create API Key »",
    "transcription.keys.groq.help.step3": "3. Copiez-la et collez-la ici",
    "transcription.keys.groq.help.link": "Ouvrir la console Groq",

    "transcription.models.title": "Modèle par moteur",
    "transcription.models.hint": "Utilisé lorsque ce moteur est actif.",

    "transcription.device.title": "Appareil de transcription locale (uniquement pour le moteur local)",
    "transcription.device.hint": (
        "Où s'exécute le modèle Whisper local. Sans effet lorsque OpenAI "
        "ou Groq est le moteur actif — ceux-là transcrivent dans le cloud."
    ),
    "transcription.device.label": "Appareil",
    "transcription.device.label.hint": "CUDA est nettement plus rapide que le CPU sur les GPU NVIDIA compatibles.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.error.priority_empty": "La liste de priorité des moteurs est vide.",

    # ---------- settings: About page ----------
    "page.about.title": "À propos",
    "about.version": "Version",
    "about.version.unknown": "inconnue",
    "about.developer": "Développeur",
    "about.email": "E-mail",
    "about.website": "Site web",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Glossaire",
    "page.glossary.hint": (
        "Termes propres à votre entreprise et termes quotidiens, pour que l'application les reconnaisse et les écrive sous leur forme canonique. "
        "Désactivé par défaut. À noter : lorsque le biais ASR ou les couches LLM sont activés, ces termes sont "
        "envoyés à votre fournisseur cloud (OpenAI/Groq) dans le cadre de la requête."
    ),
    "glossary.enable.title": "Activer le glossaire",
    "glossary.enable.hint": "Interrupteur principal. Désactivé → comportement identique à une version sans cette fonctionnalité.",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "Packs métier",
    "glossary.packs.hint": (
        "Ensembles de termes prêts à l'emploi pour que la reconnaissance maîtrise "
        "d'emblée le jargon d'un domaine — les mots, abréviations et orthographes "
        "qu'un métier écrit mal par défaut (lien, force majeure, anamnèse, ECG, "
        "merge request, idempotent). Cliquez sur un pack pour copier ses termes "
        "dans votre glossaire ci-dessous, puis modifiez-les comme tout ce que "
        "vous avez saisi vous-même. Fonctionnalité Pro."
    ),
    "glossary.packs.language": "Langue du pack",
    "glossary.packs.language.hint": "La langue dans laquelle les termes importés sont écrits.",
    "glossary.packs.status.available": "{count} packs disponibles — cliquez sur l'un d'eux pour copier ses termes dans les champs ci-dessous.",
    "glossary.packs.status.locked": "Les packs métier sont une fonctionnalité Pro. Free garde {cap} termes actifs — moins que n'en contient n'importe quel pack.",
    "glossary.packs.tooltip.adds": "Ajoute jusqu'à {count} termes.",
    "glossary.packs.tooltip.locked": "Les packs métier sont une fonctionnalité Pro.",
    "glossary.packs.already_loaded.title": "Pack {pack} déjà chargé",
    # {language} — nom anglais de la langue ("French"), venu des données ;
    # d'où les parenthèses, plutôt qu'un « en français » accordé.
    "glossary.packs.already_loaded.text": "Tous les termes du pack ({language}) figurent déjà dans votre glossaire — rien à ajouter.",
    "glossary.packs.count.terms": "{count} termes",
    "glossary.packs.count.replacements": "{count} remplacements",
    "glossary.packs.count.join": " et ",
    "glossary.packs.confirm.title": "Charger le pack {pack} ?",
    "glossary.packs.confirm.adds": "Ceci ajoute {what} à votre glossaire, en {language}.",
    "glossary.packs.confirm.skipped": "{count} déjà présents seront ignorés.",
    "glossary.packs.confirm.editable": "Ils sont ajoutés comme des lignes ordinaires que vous pouvez modifier ou supprimer, et ne sont écrits sur le disque qu'à l'enregistrement.",

    # Nom et description de chaque pack. C'est de l'interface — ils suivent la
    # langue de l'UI, contrairement aux termes eux-mêmes (dont la langue se
    # choisit dans « Langue du pack ») et au `note` sur la juridiction, écrit
    # dans la langue du pack lui-même.
    "glossary.packs.legal.name": "Juridique",
    "glossary.packs.legal.hint": "Vocabulaire du contentieux, des contrats et du droit des sociétés.",
    "glossary.packs.medical.name": "Médical",
    "glossary.packs.medical.hint": "Notes cliniques, diagnostics et abréviations courantes.",
    "glossary.packs.it.name": "Informatique et logiciel",
    "glossary.packs.it.hint": "Vocabulaire de l'ingénierie, du DevOps et de la revue de code.",
    "glossary.packs.finance.name": "Finance et comptabilité",
    "glossary.packs.finance.hint": "Vocabulaire du reporting, de la valorisation et des transactions.",
    "glossary.packs.sales.name": "Ventes et CRM",
    "glossary.packs.sales.hint": "Vocabulaire du pipeline, de la prospection et de la gestion de comptes.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Couches",
    "glossary.layers.hint": "Chaque couche utilise les mêmes termes ; activez ou désactivez-les individuellement.",
    "glossary.layers.asr": "Biais ASR",
    "glossary.layers.asr.hint": "Oriente la reconnaissance vocale vers vos termes (prompt dans le cloud / hotwords en local).",
    "glossary.layers.correction": "Correction LLM (transcription)",
    "glossary.layers.correction.hint": "Ajoute les termes au prompt de correction grammaticale de l'action de transcription par défaut.",
    "glossary.layers.rewrite": "LLM en traduction et réécriture",
    "glossary.layers.rewrite.hint": "Ajoute les termes aux prompts de traduction/réécriture (boutons manuels + actions par raccourci).",
    "glossary.layers.fuzzy": "Remplacement approché (transcription)",
    "glossary.layers.fuzzy.hint": "Aligne de façon déterministe les mots presque corrects sur les termes canoniques, transcription seulement.",
    "glossary.layers.threshold": "Seuil d'approximation",
    "glossary.layers.threshold.hint": "À quel point un mot doit être proche d'un terme pour déclencher le remplacement approché (70–100 ; plus élevé = plus strict).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Termes",
    "glossary.terms.hint": "Mots propres à votre entreprise, par groupes. Une entrée par ligne.",
    "glossary.terms.tab.names": "Noms et termes",
    "glossary.terms.tab.replacements": "Remplacements",
    "glossary.terms.names": "Noms",
    "glossary.terms.names.hint": "Votre entreprise, vos produits, clients, partenaires, fournisseurs.",
    # Noms d'entreprises fictifs — noms propres, ils restent en latin.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Services et termes",
    "glossary.terms.services.hint": "Noms de services, forfaits, termes du domaine.",
    "glossary.terms.services.placeholder": "TurboDrive\nforfait Orbite",
    # {sep} est le séparateur `=>` (`_REPL_SEP`), passé pour que l'exemple ne
    # puisse jamais diverger de l'analyseur.
    "glossary.terms.replacements.placeholder": "turbo draïve {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Corrections explicites, toujours actives — une par ligne sous la forme « entendu {sep} canonique ». "
        "Appliquées littéralement (sans règles approchées), donc à réserver aux mots "
        "que la reconnaissance entend mal de façon fiable."
    ),
    "glossary.terms.counter.unlimited": "{total} termes — tous actifs.",
    "glossary.terms.counter.used": "{total} termes sur {cap} utilisés · {remaining} encore disponibles.",
    "glossary.terms.counter.over_free": (
        "{cap} termes sur {total} actifs — le reste est enregistré mais inactif. "
        "Pro les active tous (jusqu'à {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap} termes sur {total} actifs — seuls les {cap} premiers sont utilisés "
        "(au-delà, la qualité de reconnaissance se dégrade)."
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "ligne {line} : séparateur « {sep} » manquant — utilisez « entendu {sep} canonique »",
    "glossary.replacements.error.empty_side": "ligne {line} : les deux côtés de « {sep} » doivent être remplis",
    "glossary.replacements.error.more": "(+{count} de plus)",
    "glossary.replacements.error.prefix": "Remplacements : {details}",

    # ---------- settings: Custom style page ----------
    "page.customstyle.title": "Style personnalisé",
    "page.customstyle.hint": (
        "Utilisé par le bouton de réécriture Personnalisé. L'instruction ci-dessous est transmise "
        "telle quelle au modèle, avec votre texte source."
    ),
    "customstyle.preset.title": "Préréglage",
    "customstyle.name": "Nom du style",
    "customstyle.name.hint": "Affiché comme infobulle sur le bouton Personnalisé.",
    "customstyle.name.placeholder": "facultatif — par ex. Académique",
    "customstyle.prompt": "Instruction",
    "customstyle.prompt.hint": "Le modèle traite ceci comme une directive de niveau système.",
    "customstyle.prompt.placeholder": (
        "par ex. Réécris dans un registre académique, utilise la voix passive, "
        "cite avec soin, garde une terminologie précise."
    ),
    "customstyle.pro_hint": (
        "✦ Modifier l'instruction est une fonctionnalité Pro. En Free, choisissez "
        "un modèle métier ci-dessous et utilisez-le tel quel."
    ),
    "customstyle.templates.title": "Partir d'un modèle",
    "customstyle.templates.hint": "Cliquez sur un métier pour remplir les champs ci-dessus. Vous pouvez ajuster l'instruction selon vos besoins.",
    "customstyle.templates.tooltip": "Remplir les champs ci-dessus avec le modèle {name}",
    "customstyle.templates.replace.title": "Remplacer l'instruction actuelle ?",
    "customstyle.templates.replace.text": "Ceci écrasera les champs Nom du style et Instruction avec le modèle {name}.",

    # Un `.name` par modèle, dans l'ordre des boutons. Le clic copie le nom
    # résolu dans CUSTOM_STYLE_NAME, c'est donc aussi le nom avec lequel
    # l'utilisateur reste.
    "customstyle.templates.lawyer.name": "Juriste",
    "customstyle.templates.doctor.name": "Médecin / Clinicien",
    "customstyle.templates.psychotherapist.name": "Psychothérapeute",
    "customstyle.templates.financial_advisor.name": "Conseiller financier",
    "customstyle.templates.recruiter.name": "Recruteur",
    "customstyle.templates.salesperson.name": "Commercial",
    "customstyle.templates.support.name": "Support",
    "customstyle.templates.insurance_agent.name": "Agent d'assurance",
    "customstyle.templates.professional.name": "Professionnel / Affaires",
    "customstyle.templates.programmer.name": "Programmeur / Technique",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "Style de réécriture personnalisé",
    "customstyledialog.hint": "Le bouton Personnalisé réécrit le texte source selon votre instruction ci-dessous.",
    "customstyledialog.name": "Nom du style (facultatif)",
    "customstyledialog.name.placeholder": "par ex. Académique, Toxique, Texte marketing",
    "customstyledialog.prompt": "Instruction de style",
    "customstyledialog.prompt.placeholder": (
        "par ex. Réécris dans un registre académique, utilise la voix passive, "
        "cite avec soin, garde une terminologie précise."
    ),
    "customstyledialog.preset_limit": "Enregistrer un nombre illimité de styles personnalisés est une fonctionnalité Pro.",

    # ---------- settings window chrome ----------
    "settingswindow.title.setup": "Omni Verte — Configuration",
    "settingswindow.title.settings": "Omni Verte — Paramètres",
    "settingswindow.nav.general": "Général",
    "settingswindow.nav.transcription": "Transcription",
    "settingswindow.nav.languages": "Langues",
    "settingswindow.nav.custom_style": "Style personnalisé",
    "settingswindow.nav.glossary": "Glossaire",
    "settingswindow.nav.license": "Licence",
    "settingswindow.nav.about": "À propos",
    "settingswindow.local_only": "Utiliser en local uniquement",
    # Pas de « && » ici : le français relie par « et », donc aucune esperluette
    # à échapper. Un « && » ou « & » isolé s'afficherait ou créerait un
    # accélérateur souligné involontaire.
    "settingswindow.save_start": "Enregistrer et démarrer",
    "settingswindow.save_apply": "Enregistrer et appliquer",
    "settingswindow.error.title": "Enregistrement impossible",
    "settingswindow.error.apply_failed": "Échec de l'enregistrement de {page} : {error}",

    # ---------- settings: License page ----------
    "page.license.title": "Licence",
    "page.license.hint": "Omni Verte est gratuit. Une licence Pro débloque plus de fonctionnalités — voir ci-dessous.",

    "license.status.title": "Statut",
    "license.status.hint": "Le niveau auquel cette machine fonctionne actuellement.",
    "license.status.level": "Niveau actuel : {tier}",
    "license.status.key": "(clé {key})",

    "license.benefit.glossary": "Glossaire — jusqu'à 200 termes (Free : 5) plus des packs métier prêts à l'emploi",
    "license.benefit.custom_styles": "Styles personnalisés — créez et modifiez vos propres styles de réécriture (Free : modèles uniquement)",
    "license.benefit.presets": "Préréglages de style — enregistrez-en autant que vous voulez (Free : un seul emplacement)",
    "license.benefit.history": "Historique — illimité et consultable (Free : les 10 derniers)",
    "license.benefit.builds": "Versions signées à mise à jour automatique et support prioritaire",

    "license.waitlist.title": "Pro arrive bientôt",
    "license.waitlist.hint": "Pro n'est pas encore en vente. Rejoignez la liste d'attente et soyez le premier informé de son ouverture — sans paiement ni engagement.",
    "license.waitlist.unlocks": "Pro débloque :",
    "license.waitlist.button": "Rejoindre la liste d'attente Pro",

    "license.benefits.unlocks": "Pro débloque :",
    "license.benefits.included": "Votre licence Pro comprend :",

    "license.key.title": "Clé de licence",
    "license.hint.enter": "Saisissez la clé de licence reçue, puis cliquez sur Activer.",
    "license.hint.activated": "Pro est actif sur cette machine. Votre clé est stockée en toute sécurité — inutile de la saisir à nouveau.",
    "license.hint.editing": "Saisissez la nouvelle clé de licence. L'actuelle reste active jusqu'à ce que la nouvelle soit acceptée.",
    "license.button.buy": "Obtenir une licence",
    "license.button.change_key": "Utiliser une autre clé",
    "license.button.deactivate": "Désactiver",
    "license.button.activate": "Activer",
    "license.toast.activated": "Pro activé",
    "license.toast.cleared": "Licence effacée — retour à Free",

    "license.error.network": "Impossible de joindre le serveur de licences. Vérifiez votre connexion et réessayez — votre statut actuel est inchangé.",
    "license.error.empty_key": "Saisissez d'abord une clé de licence.",
    "license.error.no_fingerprint": "Impossible de lire l'identifiant de cette machine. L'activation nécessite Windows.",
    "license.error.local": "Impossible d'activer sur cette machine.",
    "license.error.invalid_key": "Cette clé de licence est introuvable. Vérifiez-la et réessayez.",
    # L'anglais dit « (Clear it there) » — une référence à un bouton désormais
    # nommé Désactiver. Le français pointe vers le bouton qui existe réellement.
    "license.error.seat_limit": "Tous les appareils de cette clé sont utilisés. Libérez-en un (désactivez-le là-bas), puis activez à nouveau ici.",
    "license.error.rate_limit": "Trop d'activations récemment. Veuillez réessayer plus tard.",
    "license.error.inactive": "Cette licence n'est plus active (révoquée, remboursée ou expirée).",
    "license.error.refused": "Le serveur de licences a refusé la requête. Cela ne vient pas de votre clé — veuillez réessayer, ou contactez le support si le problème persiste.",
    "license.error.unverified": "Activé, mais la licence n'a pas pu être vérifiée sur cette machine. Veuillez contacter le support.",
    "license.error.generic": "Activation impossible. Veuillez réessayer.",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "Attraper la touche",
    "hotkeycapture.listening": "Appuyez sur une touche…",
    "hotkeycapture.tooltip": "Cliquez, puis appuyez sur la touche voulue — elle remplit ce champ.",

    # ---------- history kinds (Activity Feed) ----------
    "history.kind.transcription": "Transcription",
    "history.kind.translation": "Traduction",
    "history.kind.fix": "Correction grammaticale",
    "history.kind.casual": "Réécriture décontractée",
    "history.kind.professional": "Réécriture professionnelle",
    "history.kind.custom": "Réécriture personnalisée",

    # ---------- main window ----------
    # Statuts en tournure nominale : c'est une étiquette à côté de l'indicateur,
    # pas un message de l'application sur elle-même.
    "main.status.ready": "Prêt",
    "main.status.recording": "À l'écoute…",
    "main.status.processing": "Transcription…",
    "main.status.error": "Erreur",
    "main.status.loading": "Chargement du modèle…",
    "main.status.failed": "Échec du modèle — vérifiez le réseau, resélectionnez dans les paramètres",

    # Indicateur d'enregistrement flottant (ui/rec_indicator.py) — libellés courts.
    "indicator.recording": "À l'écoute",
    "indicator.processing": "Transcription",
    "indicator.loading": "Chargement",
    "indicator.nosignal": "Pas de signal",

    "main.card.original.title": "Dernière transcription",
    "main.card.result.title": "Résultat IA",
    "main.card.result.placeholder": "La traduction ou le texte réécrit apparaîtra ici.",
    "main.card.badge.generated": "Généré",
    "main.card.result.working": "Traitement… ({label})",

    "main.button.copy": "Copier",
    "main.button.clear": "Effacer",
    "main.button.fix_grammar": "Corriger la grammaire",
    "main.button.casual": "Décontracté",
    "main.button.professional": "Professionnel",
    "main.button.custom": "Personnalisé",

    "main.pill.translate": "Traduire ({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "Traduit entre {primary} et {secondary}, en détectant le sens automatiquement. Clic droit pour changer de langues.",
    "main.menu.pair": "{primary} ↔ {secondary}  (auto)",
    "main.menu.change_settings": "Modifier dans les paramètres",

    "main.feed.title": "Historique",

    "main.tooltip.theme.dark": "Passer au thème sombre",
    "main.tooltip.theme.light": "Passer au thème clair",
    "main.tooltip.settings": "Ouvrir les paramètres",
    "main.tooltip.license": "Gérer votre licence",
    "main.tooltip.no_key": "Clé OpenAI requise — définissez-la via la zone de notification → Paramètres.",
    "main.tooltip.custom.named": "Réécrire avec : {name}",
    "main.tooltip.custom.generic": "Réécrire avec votre style personnalisé",
    "main.tooltip.custom.unset": "Non configuré — cliquez pour définir un style personnalisé",

    "main.hint.keyboard.transcribe": "Appuyez sur {key} pour dicter et transcrire.",
    "main.hint.keyboard.translate": "Appuyez sur {key} pour dicter, transcrire et traduire.",
    # Guillemets autour de {style} : un nom de style inventé par l'utilisateur
    # peut s'y insérer — impossible de l'accorder dans la phrase.
    "main.hint.keyboard.custom": "Appuyez sur {key} pour dicter, transcrire et renvoyer le texte dans le style « {style} ».",
    "main.hint.style.casual": "décontracté",
    "main.hint.style.professional": "professionnel",
    "main.hint.style.custom": "personnalisé",
    "main.hint.mouse.dictate": "Appuyez sur le bouton {button} de la souris pour dicter et transcrire.",
    "main.hint.mouse.hotkeys": "Définissez des raccourcis clavier dans les paramètres pour traduire ou réécrire dans un style.",
    "main.mouse.middle": "du milieu",
    "main.mouse.left": "gauche",
    "main.mouse.right": "droit",

    "main.dialog.operation_failed": "Échec de l'opération",
    "main.toast.custom_style_pro": (
        "Modifier les styles personnalisés est une fonctionnalité Pro. Choisissez un modèle "
        "dans Paramètres → Style personnalisé."
    ),
}
