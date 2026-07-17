# file: i18n/_en.py

"""English UI strings — the source of truth.

A string exists here first; every other locale module is a translation of this
one. The catalog tests key off that: any key here that a translation lacks is a
missing translation, and any key a translation has that is *not* here is dead.

Keep this file grouped by UI area and ordered the way the user meets the strings
(app chrome, then main window, then settings pages in sidebar order, then tray).
See the package docstring for the key-naming and no-lookups-at-import rules.
"""

from __future__ import annotations

LOCALE = "en"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    # Reused across pages; a key lives here only when the SAME sentence is
    # genuinely meant in every place it appears. Two labels that merely happen
    # to read alike today get their own keys, so a copy edit to one cannot
    # silently rewrite the other.
    "common.on": "On",
    "common.off": "Off",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.pro": "Pro",
    "common.pro.tooltip": "Pro feature — join the waitlist",
    "common.help.where_key": "Where do I get a key?",

    # ---------- tray menu ----------
    # pystray, not Qt — but the same catalog. Everything here is a named format
    # template rather than a concatenation, because word order moves between
    # languages and a translator must be able to move the value with it.
    #
    # The tray shows CANONICAL values verbatim in a few places on purpose:
    # model names (large-v3), device names (cuda/cpu) and the dictation language
    # pair (English/Russian, which are config values — see languages_page).
    "tray.show_window": "Show window",
    "tray.indicator.show": "Show floating indicator",
    "tray.indicator.hide": "Hide floating indicator",
    "tray.mode": "Activation mode: {mode}",
    "tray.mode.keyboard": "Keyboard",
    "tray.mode.mouse": "Mouse",
    "tray.keys": "Activation keys",
    "tray.keys.change": "Change (press a key)",
    "tray.hotkey.item": "{action}: {key}",
    # Action names for the hotkey submenu. Keyed from HOTKEY_ACTIONS'
    # `label_key` in services/audio_writer.py.
    "tray.action.transcribe": "Transcribe",
    "tray.action.translate": "Transcribe + translate",
    "tray.action.custom": "Transcribe + style",
    "tray.suppress.on": "Hard-capture: ON (keys swallowed)",
    "tray.suppress.off": "Hard-capture: OFF (pass-through)",
    "tray.mouse_button": "Mouse activation button: {button}",
    "tray.model": "Transcription method: {model}",
    "tray.model.local": "Local: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "Using device: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "Primary language: {language}",
    "tray.language.other": "Other languages…",
    "tray.settings": "Settings…",
    "tray.close": "Close",
    "tray.tooltip.loading": "Omni Verte — loading model…",
    "tray.tooltip.failed": "Omni Verte — model failed (check network, re-pick in Settings)",

    # ---------- settings: General page ----------
    "page.general.title": "General",
    "page.general.hint": "Interface language, hotkeys, and behaviour toggles. Most of these are also reachable from the tray.",

    # The interface language. A separate axis from the Languages page, which is
    # about what you DICTATE — a Russian speaker may well want an English UI.
    # The picker's item labels are native language names (data, in i18n), not
    # catalog strings: it must be readable by someone who cannot read the
    # language currently active.
    "general.interface.title": "Interface",
    "general.interface.hint": "How the app talks to you. Separate from the languages you dictate and translate between, on the Languages page.",
    "general.interface.language": "Language",
    "general.interface.language.hint": "Applied when you save.",

    "general.activation.title": "Activation",
    "general.activation.hint": (
        "How recording is triggered. Keyboard captures a single hotkey; "
        "mouse uses a configurable mouse button."
    ),
    "general.activation.keyboard": "Keyboard hotkeys",
    "general.activation.mouse": "Mouse button",

    "general.hotkey.transcribe": "Transcribe + paste",
    "general.hotkey.transcribe.hint": "Dictate, then paste the transcription with grammar correction and punctuation. Click “Catch the key” to grab a key.",
    "general.hotkey.translate": "Transcribe + translate",
    "general.hotkey.translate.hint": "Dictate, then translate to the secondary language before pasting. Click “Catch the key” to grab a key.",
    "general.hotkey.custom": "Transcribe + rewrite custom style",
    "general.hotkey.custom.hint": "Dictate, then rewrite using the style chosen below and paste. Click “Catch the key” to grab a key.",

    # The `[F11] Custom → [ style ▾ ]` panel. {key} is the live hotkey, so the
    # copy stays right after a rebind.
    "general.stylepair.name": "Custom",
    "general.stylepair.hint": "Pressing {key} rewrites your dictation in this style. “Custom” uses your prompt from the Custom style page.",

    # Rewrite styles the custom hotkey can apply. Labels only — the stored
    # values (casual/professional/custom) are canonical and live in the page.
    "general.style.casual": "Casual",
    "general.style.professional": "Professional",
    "general.style.custom": "Custom",

    "general.suppress": "Hard-capture keys",
    "general.suppress.hint": "Swallow the hotkeys so the focused app never sees them (e.g. F11 won't fullscreen the browser). Turn off if it causes conflicts.",

    "general.mouse.label": "Mouse button",
    "general.mouse.hint": "Pressed and held to record.",
    "general.mouse.middle": "Middle",
    "general.mouse.left": "Left",
    "general.mouse.right": "Right",

    "general.behaviour.title": "Behaviour",
    "general.behaviour.floating": "Floating indicator",
    "general.behaviour.floating.hint": "Small status dot in the corner of the screen.",
    "general.behaviour.double_tap": "Open window on double-tap",
    "general.behaviour.double_tap.hint": "Press the activation key/button twice quickly (within 300ms) to bring the main window to the front.",
    "general.behaviour.autostart": "Launch on Windows startup",
    "general.behaviour.autostart.hint": "Start Omni Verte automatically when you sign in to Windows.",

    # Action names, interpolated into general.error.hotkey_empty. Separate keys
    # rather than reusing the row labels: the error names the action ("Translate
    # hotkey can't be empty"), and a language that inflects the name in that
    # frame must be free to.
    "general.action.transcribe": "Transcribe",
    "general.action.translate": "Translate",
    "general.action.custom": "Custom-style",
    "general.error.hotkey_empty": "{action} hotkey can't be empty when keyboard mode is selected.",
    "general.error.hotkey_duplicate": "Each action needs a distinct hotkey — two are currently the same.",

    # ---------- settings: Languages page ----------
    "page.languages.title": "Languages",
    "page.languages.hint": "Translate auto-detects which way to convert between these two languages.",
    "languages.pair.title": "Translation pair",
    "languages.primary": "Primary",
    "languages.primary.hint": "Usually your native or most-used language.",
    "languages.secondary": "Secondary",
    "languages.secondary.hint": "The other language you regularly write or speak in.",
    "languages.swap": "Swap languages",
    "languages.swap.tooltip": "Swap primary and secondary",
    "languages.error.must_differ": "Primary and Secondary languages must differ.",

    # ---------- app-wide ----------
    # `app.title` already exists; the tagline joins it here because it is brand
    # copy rather than page copy — the About card and the main window's header
    # (ui/main_window.py) show the same line.
    "app.tagline": "AI Dictation · Rewrite · Translate",

    # ---------- settings: Transcription page ----------
    "page.transcription.title": "Transcription",
    "page.transcription.hint": (
        "Choose which speech-to-text backends to try and in what order. "
        "The first backend with valid credentials becomes the active one."
    ),

    # Backend display names + one-line pitches. The names are proper nouns and
    # stay Latin in every locale — add `transcription.backend.name.openai` and
    # `transcription.backend.name.groq` to _KEEP_LATIN in tests/test_i18n_catalog.py.
    # The `.name.` / `.hint.` split (rather than `...openai` / `...openai.hint`)
    # exists so those _KEEP_LATIN prefixes cannot also swallow the hints, which
    # very much are translated.
    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "Local (Whisper)",
    "transcription.backend.hint.openai": "high quality, paid",
    "transcription.backend.hint.groq": "fastest, free tier available",
    "transcription.backend.hint.local": "offline, uses local CPU/GPU",

    "transcription.priority.title": "Backend priority",
    "transcription.priority.hint": (
        "Drag to reorder. The first backend with valid credentials wins at startup."
    ),

    "transcription.keys.title": "API keys",
    "transcription.keys.hint": (
        "Stored in the Windows Credential Manager (DPAPI-protected). "
        "Leave empty to skip a backend."
    ),
    "transcription.keys.get_link": "Get a key ↗",

    "transcription.keys.openai.label": "OpenAI key",
    "transcription.keys.openai.placeholder": "Enter OpenAI API key",
    "transcription.keys.openai.nudge": "← Enter your OpenAI key",
    "transcription.keys.openai.help.title": "Getting an OpenAI API key",
    "transcription.keys.openai.help.step1": "1. Sign in at platform.openai.com",
    "transcription.keys.openai.help.step2": "2. API keys → Create new secret key",
    "transcription.keys.openai.help.step3": "3. Copy it (starts with “sk-…”) and paste it here",
    "transcription.keys.openai.help.note": "OpenAI is paid — add billing credit to use it.",
    "transcription.keys.openai.help.link": "Open OpenAI keys page",

    "transcription.keys.groq.label": "Groq key",
    "transcription.keys.groq.placeholder": "Enter Groq API key",
    "transcription.keys.groq.nudge": "← Enter your Groq key",
    "transcription.keys.groq.help.title": "Getting a Groq API key (free)",
    "transcription.keys.groq.help.step1": "1. Sign in at console.groq.com",
    "transcription.keys.groq.help.step2": "2. API Keys → Create API Key",
    "transcription.keys.groq.help.step3": "3. Copy it and paste it here",
    "transcription.keys.groq.help.link": "Open Groq console",

    "transcription.models.title": "Model per backend",
    "transcription.models.hint": "Used when that backend is active.",

    "transcription.device.title": "Local transcription device (only for local backend)",
    "transcription.device.hint": (
        "Where the on-device Whisper model runs. Has no effect when OpenAI "
        "or Groq is the active backend — those transcribe in the cloud."
    ),
    "transcription.device.label": "Device",
    "transcription.device.label.hint": "CUDA is significantly faster than CPU on supported NVIDIA GPUs.",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA (GPU)",

    "transcription.error.priority_empty": "Backend priority list is empty.",

    # ---------- settings: About page ----------
    # Values on this page (version string, AppUserModelID, developer name, email
    # address, website URL) are data and never enter the catalog. The
    # "AppUserModelID" label is literal too — it is the Windows API term.
    "page.about.title": "About",
    "about.version": "Version",
    "about.version.unknown": "unknown",
    "about.developer": "Developer",
    "about.email": "Email",
    "about.website": "Website",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "Glossary",
    "page.glossary.hint": (
        "Company-specific terms and daily terms so the app recognises and writes them canonically. "
        "Off by default. Note: when ASR bias or LLM layers are on, these terms are "
        "sent to your cloud provider (OpenAI/Groq) as part of the request."
    ),
    "glossary.enable.title": "Enable glossary",
    "glossary.enable.hint": "Master switch. Off → behaviour is identical to a build without the feature.",

    # ---------- settings: Glossary → profession packs ----------
    # Three language axes meet on this card, and only the first is the catalog's:
    #   * a pack's `name`/`hint` are chrome and follow the UI locale — below;
    #   * its *terms* follow the card's own "Pack language" picker — pack data;
    #   * its `note` (jurisdiction) is written in the pack's own language, so the
    #     German pack's note is German — also pack data, also not here.
    "glossary.packs.title": "Profession packs",
    "glossary.packs.hint": (
        "Curated term sets so the recogniser nails domain jargon out of the "
        "box — the words, abbreviations and spellings a field gets wrong by "
        "default (lien, force majeure, anamnesis, ECG, merge request, "
        "idempotent). Click a pack to copy its terms into your glossary "
        "below, then edit them like anything you typed yourself. A Pro feature."
    ),
    # Label only. The combo's userData is a locale CODE and the item labels are
    # native language names (data, picked to name a *term* language) — neither
    # is translated.
    "glossary.packs.language": "Pack language",
    "glossary.packs.language.hint": "Which language the imported terms are written in.",
    "glossary.packs.status.available": "{count} packs available — click one to copy its terms into the boxes below.",
    "glossary.packs.status.locked": "Profession packs are a Pro feature. Free keeps {cap} terms active — fewer than any pack holds.",
    # Appended after `glossary.packs.<id>.hint`, which supplies the leading sentence.
    "glossary.packs.tooltip.adds": "Adds up to {count} terms.",
    "glossary.packs.tooltip.locked": "Profession packs are a Pro feature.",
    "glossary.packs.already_loaded.title": "{pack} pack already loaded",
    "glossary.packs.already_loaded.text": "Every term in the {language} pack is already in your glossary — nothing to add.",
    # `count.terms` / `count.replacements` are fragments joined by `count.join`
    # into the `{what}` of `confirm.adds`. A locale that cannot decline a bare
    # "{count} terms" for every count is free to re-shape all three — that is
    # exactly why the join is a key and not a hard-coded separator.
    "glossary.packs.count.terms": "{count} terms",
    "glossary.packs.count.replacements": "{count} replacements",
    "glossary.packs.count.join": " and ",
    "glossary.packs.confirm.title": "Load the {pack} pack?",
    "glossary.packs.confirm.adds": "This adds {what} to your glossary, in {language}.",
    "glossary.packs.confirm.skipped": "{count} already present will be skipped.",
    "glossary.packs.confirm.editable": "They are added as ordinary lines you can edit or delete, and are only written to disk when you save.",

    # One `<pack_id>.name` + `<pack_id>.hint` per pack, keyed off `PackMeta.pack_id`
    # in ui/settings_pages/glossary_packs/_meta.py (which holds these keys, not the
    # text). Grouped by pack rather than `glossary.packs.name.<id>` /
    # `.hint.<id>`, because `glossary.packs.hint` above is already a leaf — a
    # `.hint.<id>` subtree would make `hint` both a leaf and an interior node, and
    # read as "the hint's legal" instead of "the legal pack's hint".
    "glossary.packs.legal.name": "Legal",
    "glossary.packs.legal.hint": "Litigation, contracts and corporate law vocabulary.",
    "glossary.packs.medical.name": "Medical",
    "glossary.packs.medical.hint": "Clinical notes, diagnoses and common abbreviations.",
    "glossary.packs.it.name": "IT & Software",
    "glossary.packs.it.hint": "Engineering, DevOps and code-review vocabulary.",
    "glossary.packs.finance.name": "Finance & Accounting",
    "glossary.packs.finance.hint": "Reporting, valuation and deal vocabulary.",
    "glossary.packs.sales.name": "Sales & CRM",
    "glossary.packs.sales.hint": "Pipeline, outreach and account-management vocabulary.",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "Layers",
    "glossary.layers.hint": "Each layer uses the same terms; turn individual layers on or off.",
    "glossary.layers.asr": "ASR bias",
    "glossary.layers.asr.hint": "Bias the speech recogniser toward your terms (cloud prompt / local hotwords).",
    "glossary.layers.correction": "LLM correction (transcribe)",
    "glossary.layers.correction.hint": "Add the terms to the grammar-correction prompt on the default transcribe action.",
    "glossary.layers.rewrite": "LLM in translate & rewrite",
    "glossary.layers.rewrite.hint": "Add the terms to the translate/rewrite prompts (manual buttons + hotkey actions).",
    "glossary.layers.fuzzy": "Fuzzy replace (transcribe)",
    "glossary.layers.fuzzy.hint": "Deterministically snap near-miss words to canonical terms, transcribe only.",
    "glossary.layers.threshold": "Fuzzy threshold",
    "glossary.layers.threshold.hint": "How close a word must be to a term before fuzzy replace fires (70–100; higher = stricter).",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "Terms",
    "glossary.terms.hint": "Company-specific words, grouped. One entry per line.",
    "glossary.terms.tab.names": "Names & terms",
    "glossary.terms.tab.replacements": "Replacements",
    "glossary.terms.names": "Names",
    "glossary.terms.names.hint": "Your company, products, clients, partners, vendors.",
    # Placeholder examples: invented company names. Latin in every locale — they
    # are proper nouns, so `_ru.py` keeps them verbatim (needs a `_KEEP_LATIN`
    # entry).
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "Services & terms",
    "glossary.terms.services.hint": "Service names, plans, domain terms.",
    "glossary.terms.services.placeholder": "TurboDrive\nтариф Орбита",
    # `{sep}` is the `=>` separator (`_REPL_SEP`), passed in so the example can
    # never drift from the parser.
    "glossary.terms.replacements.placeholder": "турбо драйв {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "Explicit, always-on fixes — one per line as 'heard {sep} canonical'. "
        "Applied verbatim (no fuzzy rules), so use them for words the recogniser "
        "reliably mishears."
    ),
    "glossary.terms.counter.unlimited": "{total} terms — all active.",
    "glossary.terms.counter.used": "{total} of {cap} terms used · {remaining} more available.",
    "glossary.terms.counter.over_free": (
        "{cap} of {total} terms active — the rest are saved but inactive. "
        "Pro activates all of them (up to {pro_cap})."
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap} of {total} terms active — only the first {cap} are used "
        "(more degrades recognition quality)."
    ),

    # ---------- settings: Glossary → validation ----------
    # `{line}` is 1-based; the per-line errors are joined into `error.prefix`.
    "glossary.replacements.error.missing_sep": "line {line}: missing '{sep}' separator — use 'heard {sep} canonical'",
    "glossary.replacements.error.empty_side": "line {line}: both sides of '{sep}' must be non-empty",
    "glossary.replacements.error.more": "(+{count} more)",
    "glossary.replacements.error.prefix": "Replacements: {details}",

    # ---------- settings: Custom style page ----------
    # A template's `name` is chrome and lives here; its `prompt` is model input
    # and stays English in the templates module. See its docstring for why.
    "page.customstyle.title": "Custom style",
    "page.customstyle.hint": (
        "Used by the Custom rewrite button. The instruction below is fed verbatim "
        "to the model along with your source text."
    ),
    "customstyle.preset.title": "Preset",
    "customstyle.name": "Style name",
    "customstyle.name.hint": "Shown as the tooltip on the Custom button.",
    "customstyle.name.placeholder": "optional — e.g. Academic",
    "customstyle.prompt": "Instruction",
    "customstyle.prompt.hint": "The model treats this as a system-level direction.",
    "customstyle.prompt.placeholder": (
        "e.g. Rewrite in an academic register, use passive voice, "
        "cite carefully, keep terminology precise."
    ),
    "customstyle.pro_hint": (
        "✦ Editing the instruction is a Pro feature. On Free, pick a "
        "profession template below and use it as-is."
    ),
    "customstyle.templates.title": "Start from a template",
    "customstyle.templates.hint": "Click a profession to fill the fields above. You can tweak the instruction as needed.",
    "customstyle.templates.tooltip": "Fill the fields above with the {name} template",
    "customstyle.templates.replace.title": "Replace current instruction?",
    "customstyle.templates.replace.text": "This will overwrite the Style name and Instruction fields with the {name} template.",

    # One `.name` per template, in button order; the key lives in the
    # StyleTemplate. Grouped per template (not `customstyle.templates.name.<id>`)
    # to match `glossary.packs.<id>.name` — see the comment there for what forces
    # it. A click copies the resolved name into CUSTOM_STYLE_NAME, so these are
    # what a user ends up with as their style's name.
    "customstyle.templates.lawyer.name": "Lawyer",
    "customstyle.templates.doctor.name": "Doctor / Clinician",
    "customstyle.templates.psychotherapist.name": "Psychotherapist",
    "customstyle.templates.financial_advisor.name": "Financial Advisor",
    "customstyle.templates.recruiter.name": "Recruiter",
    "customstyle.templates.salesperson.name": "Salesperson",
    "customstyle.templates.support.name": "Support",
    "customstyle.templates.insurance_agent.name": "Insurance Agent",
    "customstyle.templates.professional.name": "Professional / Business",
    "customstyle.templates.programmer.name": "Programmer / Technical",

    # ---------- Custom style dialog (gear button, main window) ----------
    # Deliberately its own namespace rather than reusing `customstyle.*`: the
    # dialog and the settings page merely happen to say similar things today,
    # and a copy edit to one must not silently rewrite the other.
    "customstyledialog.title": "Custom rewrite style",
    "customstyledialog.hint": "The Custom button rewrites the source text using your instruction below.",
    "customstyledialog.name": "Style name (optional)",
    "customstyledialog.name.placeholder": "e.g. Academic, Toxic, Marketing copy",
    "customstyledialog.prompt": "Style instruction",
    "customstyledialog.prompt.placeholder": (
        "e.g. Rewrite in an academic register, use passive voice, "
        "cite carefully, keep terminology precise."
    ),
    "customstyledialog.preset_limit": "Saving unlimited custom styles is a Pro feature.",

    # ---------- settings window chrome ----------
    # Nav labels are display text only — FluentWindow routes on PAGE_ID
    # (page.objectName()), so these are safe to translate. They deliberately get
    # their own keys rather than reusing the pages' PAGE_TITLE_KEY: a sidebar
    # entry and a page heading are free to word differently as the UI grows.
    "settingswindow.title.setup": "Omni Verte — Setup",
    "settingswindow.title.settings": "Omni Verte — Settings",
    "settingswindow.nav.general": "General",
    "settingswindow.nav.transcription": "Transcription",
    "settingswindow.nav.languages": "Languages",
    "settingswindow.nav.custom_style": "Custom style",
    "settingswindow.nav.glossary": "Glossary",
    "settingswindow.nav.license": "License",
    "settingswindow.nav.about": "About",
    "settingswindow.local_only": "Use Local Only",
    # `&&` is Qt mnemonic escaping — it renders as a single literal "&". A lone
    # "&" here would silently turn the next letter into an underlined
    # accelerator, so every locale that wants an ampersand must double it.
    "settingswindow.save_start": "Save && Start",
    "settingswindow.save_apply": "Save && Apply",
    "settingswindow.error.title": "Can't save",
    "settingswindow.error.apply_failed": "Failed to save {page}: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "License",
    "page.license.hint": "Omni Verte is free to use. A Pro license unlocks more features — see below.",

    # Status card — shown in both waitlist and activation modes.
    # `license.status.level` takes the tier name already capitalised by the
    # caller ("Free"/"Pro"); the tier is what the product is sold as and is not
    # translated in any locale.
    "license.status.title": "Status",
    "license.status.hint": "The level this machine currently runs at.",
    "license.status.level": "Current level: {tier}",
    "license.status.key": "(key {key})",

    # Pro benefits — one line each; the caller adds the bullet indent.
    "license.benefit.glossary": "Glossary — up to 200 terms (Free: 5) plus ready-made profession packs",
    "license.benefit.custom_styles": "Custom styles — create and edit your own rewrite styles (Free: templates only)",
    "license.benefit.presets": "Style presets — save as many as you like (Free: one slot)",
    "license.benefit.history": "History — unlimited and searchable (Free: last 10)",
    "license.benefit.builds": "Signed, auto-updating builds and priority support",

    # Waitlist mode (PRO_SALES_OPEN = False).
    "license.waitlist.title": "Pro is coming",
    "license.waitlist.hint": "Pro isn't on sale yet. Join the waitlist and you'll be first to know when it opens — no payment, no commitment.",
    "license.waitlist.unlocks": "Pro unlocks:",
    "license.waitlist.button": "Join the Pro waitlist",

    # Lead-in above the benefit list on the key card. Two keys, not one reused
    # with a different tone: before activation the list argues for buying, after
    # it inventories what was bought.
    "license.benefits.unlocks": "Pro unlocks:",
    "license.benefits.included": "Your Pro license includes:",

    # Activation mode (PRO_SALES_OPEN = True) — the card's three states.
    "license.key.title": "License key",
    "license.hint.enter": "Enter the license key you received, then click Activate.",
    "license.hint.activated": "Pro is active on this machine. Your key is stored securely — you don't need to enter it again.",
    "license.hint.editing": "Enter the new license key. The current one stays active until the new one is accepted.",
    "license.button.buy": "Get a license",
    "license.button.change_key": "Use a different key",
    "license.button.deactivate": "Deactivate",
    "license.button.activate": "Activate",
    "license.toast.activated": "Pro activated",
    "license.toast.cleared": "License cleared — back to Free",

    # Activation failures. One message per condition `_message_for` resolves;
    # the conditions themselves (kinds, error codes, HTTP statuses) are wire
    # data from the Worker and never appear here.
    "license.error.network": "Couldn't reach the license server. Check your connection and try again — your current status is unchanged.",
    "license.error.empty_key": "Enter a license key first.",
    "license.error.no_fingerprint": "Couldn't read this machine's ID. Activation needs Windows.",
    "license.error.local": "Couldn't activate on this machine.",
    "license.error.invalid_key": "That license key wasn't found. Check it and try again.",
    "license.error.seat_limit": "All devices for this key are in use. Free a device (Clear it there), then activate here again.",
    "license.error.rate_limit": "Too many activations recently. Please try again later.",
    "license.error.inactive": "This license is no longer active (revoked, refunded or expired).",
    "license.error.refused": "The license server refused the request. This isn't a problem with your key — please try again, or contact support if it persists.",
    "license.error.unverified": "Activated, but the license couldn't be verified on this machine. Please contact support.",
    "license.error.generic": "Couldn't activate. Please try again.",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "Catch the key",
    "hotkeycapture.listening": "Press a key…",
    "hotkeycapture.tooltip": "Click, then press the key you want — it fills this field.",

    # ---------- history kinds (Activity Feed) ----------
    # Display labels only. The kind strings they are keyed by
    # ("transcription", "fix", …) are data — stored on every entry and compared
    # against — and live in ui/history_manager.py, not here.
    "history.kind.transcription": "Transcription",
    "history.kind.translation": "Translation",
    "history.kind.fix": "Grammar correction",
    "history.kind.casual": "Casual rewrite",
    "history.kind.professional": "Professional rewrite",
    "history.kind.custom": "Custom rewrite",

    # ---------- main window ----------
    # The long-lived window: unlike a settings page it is never rebuilt, so
    # `MainWindow._tr` registers each of these against its widget and replays
    # them on a language switch. Anything computed from live state (the status
    # label, the Result card's title, the translate pill) is re-rendered by that
    # window's own repaint functions instead.
    #
    # The window's title is `app.title` and its tagline `app.tagline` — the same
    # brand copy the About card shows, not a second copy of it. The Activity
    # Feed's row labels are the `history.kind.*` block above.

    "main.status.ready": "Ready",
    "main.status.recording": "Listening…",
    "main.status.processing": "Transcribing…",
    "main.status.error": "Error",
    "main.status.loading": "Loading model…",
    "main.status.failed": "Model failed — check network, re-pick in Settings",

    # Floating recording indicator (ui/rec_indicator.py) — single-word pill
    # labels, uppercased by the widget's font. "nosignal" is the dead/switched-
    # mic cue that motivated the pill redesign; it must read as an alarm.
    "indicator.recording": "Listening",
    "indicator.processing": "Transcribing",
    "indicator.loading": "Loading",
    "indicator.nosignal": "No signal",

    "main.card.original.title": "Latest transcription",
    # The Original card has no placeholder key: its empty state is the
    # hotkey-hints block below, which _refresh_settings_labels() writes before
    # the window is ever shown.
    "main.card.result.title": "AI result",
    "main.card.result.placeholder": "Translation or rewritten text will appear here.",
    "main.card.badge.generated": "Generated",
    # `{label}` is the finished title (a `history.kind.*` label, plus the
    # language direction for a translation), shown while the operation runs.
    "main.card.result.working": "Working… ({label})",

    "main.button.copy": "Copy",
    "main.button.clear": "Clear",
    "main.button.fix_grammar": "Fix grammar",
    "main.button.casual": "Casual",
    "main.button.professional": "Professional",
    "main.button.custom": "Custom",

    # The pill's label leads with the verb so it reads as an action like its
    # neighbours (Fix grammar, Casual…); the pair is a parenthetical qualifier.
    # `{primary}`/`{secondary}` are 2-letter codes derived from the configured
    # language pair (EN, RU) — config values, Latin in every locale. "auto" is
    # not spelled out here (the ↔ carries it, the tooltip states it) to keep the
    # pill from ballooning.
    "main.pill.translate": "Translate ({primary} ↔ {secondary})",
    # Tooltip on the pill; `{primary}`/`{secondary}` are the full English
    # language names straight out of config (Latin in every locale, like the
    # menu below). Spells out what the ↔ means and how to change the pair.
    "main.pill.translate.tooltip": "Translates between {primary} and {secondary}, detecting the direction automatically. Right-click to change languages.",
    # Right-click on the pill. `{primary}`/`{secondary}` here are the full
    # English language names straight out of config, for the same reason.
    "main.menu.pair": "{primary} ↔ {secondary}  (auto)",
    "main.menu.change_settings": "Change in settings",

    "main.feed.title": "History",

    # A whole sentence per direction rather than "Switch to {theme} theme":
    # light/dark are canonical THEME values, and a language that inflects the
    # adjective inside the frame cannot work with a hole punched in it.
    "main.tooltip.theme.dark": "Switch to dark theme",
    "main.tooltip.theme.light": "Switch to light theme",
    "main.tooltip.settings": "Open settings",
    "main.tooltip.license": "Manage your license",
    "main.tooltip.no_key": "OpenAI key required — set it via tray → Settings.",
    # `{name}` is the user's own style name — data, never translated.
    "main.tooltip.custom.named": "Rewrite using: {name}",
    "main.tooltip.custom.generic": "Rewrite using your custom style",
    "main.tooltip.custom.unset": "Not configured — click to set up a custom style",

    # Empty-state onboarding in the Original card: which hotkey does what. One
    # key per line, joined with "\n" by the window — the newline stays out of
    # the catalog, where a translator could lose it. `{key}` is a live hotkey
    # name (F9/F10/F11), Latin everywhere.
    "main.hint.keyboard.transcribe": "Press {key} to dictate and transcribe.",
    "main.hint.keyboard.translate": "Press {key} to dictate, transcribe, and translate.",
    "main.hint.keyboard.custom": "Press {key} to dictate, transcribe, and return in {style} style.",
    # `{style}` above: the two built-in styles, or — when the custom hotkey is
    # set to "custom" — the user's own CUSTOM_STYLE_NAME, verbatim. Separate
    # from `general.style.*`, which names the same three in a dropdown: this is
    # a word inside a sentence and a locale must be free to case and decline it
    # accordingly.
    "main.hint.style.casual": "casual",
    "main.hint.style.professional": "professional",
    "main.hint.style.custom": "custom",
    "main.hint.mouse.dictate": "Press the {button} mouse button to dictate and transcribe.",
    "main.hint.mouse.hotkeys": "Set keyboard hotkeys in Settings to translate or rewrite in a style.",
    # `{button}` above. Same three buttons as `general.mouse.*`, and same reason
    # for the split: those are standalone dropdown items, these are mid-sentence.
    "main.mouse.middle": "middle",
    "main.mouse.left": "left",
    "main.mouse.right": "right",

    "main.dialog.operation_failed": "Operation failed",
    "main.toast.custom_style_pro": (
        "Editing custom styles is a Pro feature. Pick a template "
        "in Settings → Custom style."
    ),
}
