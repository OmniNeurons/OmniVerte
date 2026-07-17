# file: i18n/_ja.py

"""Japanese UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows:

* **Neutral software register.** Titles and buttons are concise noun-style
  labels (設定, 保存, キャンセル); hints use polite で・ます where it reads
  naturally, matching the impersonal tone of ``_en.py`` / ``_ru.py``.
* **No spaces between words.** Japanese does not separate words with spaces, so
  placeholders sit directly against the surrounding characters (「{key}を押す」).
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9/F11. Transliterating them would break search and help nobody.
* **Provider console labels stay verbatim** and are quoted with 「」: the OpenAI
  and Groq consoles have no Japanese UI, so a translated button label would be
  one the user can never find.
* **Standard software terminology**: 設定, 保存, キャンセル, ショートカットキー,
  文字起こし (transcribe), 翻訳 (translate), 書き換え (rewrite), 用語集
  (glossary), ライセンス, 有効化 (activate) — kept consistent across the file.
"""

from __future__ import annotations

LOCALE = "ja"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "オン",
    "common.off": "オフ",
    "common.cancel": "キャンセル",
    "common.save": "保存",
    "common.pro": "Pro",
    "common.pro.tooltip": "Pro機能 — ウェイトリストに登録",
    "common.help.where_key": "キーの入手方法は?",

    # ---------- tray menu ----------
    "tray.show_window": "ウィンドウを表示",
    "tray.indicator.show": "フローティングインジケーターを表示",
    "tray.indicator.hide": "フローティングインジケーターを非表示",
    "tray.mode": "起動方法: {mode}",
    "tray.mode.keyboard": "キーボード",
    "tray.mode.mouse": "マウス",
    "tray.keys": "起動キー",
    "tray.keys.change": "変更(キーを押す)",
    "tray.hotkey.item": "{action}: {key}",
    "tray.action.transcribe": "文字起こし",
    "tray.action.translate": "文字起こし + 翻訳",
    "tray.action.custom": "文字起こし + スタイル変換",
    "tray.suppress.on": "強制キャプチャ: オン(キーを遮断)",
    "tray.suppress.off": "強制キャプチャ: オフ(キーを通過)",
    "tray.mouse_button": "起動用マウスボタン: {button}",
    "tray.model": "文字起こし方法: {model}",
    "tray.model.local": "ローカル: {model}",
    "tray.model.openai": "OpenAI API: {model}",
    "tray.model.groq": "Groq: {model}",
    "tray.device": "使用デバイス: {device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "主要言語: {language}",
    "tray.language.other": "その他の言語…",
    "tray.settings": "設定…",
    "tray.close": "終了",
    "tray.tooltip.loading": "Omni Verte — モデルを読み込み中…",
    "tray.tooltip.failed": "Omni Verte — モデルの読み込みに失敗(ネットワークを確認し、設定で選び直してください)",

    # ---------- settings: General page ----------
    "page.general.title": "一般",
    "page.general.hint": "インターフェース言語、ショートカットキー、動作の切り替え。これらの多くはトレイからも操作できます。",

    "general.interface.title": "インターフェース",
    "general.interface.hint": "アプリの表示言語です。口述や翻訳に使う言語とは別で、それらは「言語」ページで設定します。",
    "general.interface.language": "言語",
    "general.interface.language.hint": "保存時に適用されます。",

    "general.activation.title": "起動",
    "general.activation.hint": (
        "録音を開始する方法です。キーボードは単一のショートカットキーで、"
        "マウスは設定可能なマウスボタンで開始します。"
    ),
    "general.activation.keyboard": "キーボードショートカット",
    "general.activation.mouse": "マウスボタン",

    "general.hotkey.transcribe": "文字起こし + 貼り付け",
    "general.hotkey.transcribe.hint": "口述すると、文法補正と句読点を付けた文字起こしを貼り付けます。「キーを取得」をクリックしてキーを割り当てます。",
    "general.hotkey.translate": "文字起こし + 翻訳",
    "general.hotkey.translate.hint": "口述すると、副言語に翻訳してから貼り付けます。「キーを取得」をクリックしてキーを割り当てます。",
    "general.hotkey.custom": "文字起こし + カスタムスタイルに書き換え",
    "general.hotkey.custom.hint": "口述すると、下で選んだスタイルに書き換えて貼り付けます。「キーを取得」をクリックしてキーを割り当てます。",

    "general.stylepair.name": "カスタム",
    "general.stylepair.hint": "{key}を押すと、口述内容をこのスタイルに書き換えます。「カスタム」は「カスタムスタイル」ページのプロンプトを使います。",

    "general.style.casual": "カジュアル",
    "general.style.professional": "ビジネス",
    "general.style.custom": "カスタム",

    "general.suppress": "キーを強制キャプチャ",
    "general.suppress.hint": "ショートカットキーを遮断し、フォーカス中のアプリに渡さないようにします(例: F11でブラウザが全画面にならない)。競合が起きる場合はオフにしてください。",

    "general.mouse.label": "マウスボタン",
    "general.mouse.hint": "押し続けている間、録音します。",
    "general.mouse.middle": "中ボタン",
    "general.mouse.left": "左ボタン",
    "general.mouse.right": "右ボタン",

    "general.behaviour.title": "動作",
    "general.behaviour.floating": "フローティングインジケーター",
    "general.behaviour.floating.hint": "画面の隅に表示される小さなステータスドットです。",
    "general.behaviour.double_tap": "ダブルタップでウィンドウを開く",
    "general.behaviour.double_tap.hint": "起動キー/ボタンを素早く2回(300ミリ秒以内)押すと、メインウィンドウを前面に表示します。",
    "general.behaviour.autostart": "Windows起動時に自動起動",
    "general.behaviour.autostart.hint": "Windowsにサインインしたとき、Omni Verteを自動的に起動します。",

    # Action names interpolated into general.error.hotkey_empty. Kept as their
    # own keys (not the row labels) so the error frame can name the action
    # naturally in Japanese ("〜の…").
    "general.action.transcribe": "文字起こし",
    "general.action.translate": "翻訳",
    "general.action.custom": "カスタムスタイル",
    "general.error.hotkey_empty": "キーボードモードを選択した場合、{action}のショートカットキーを空にはできません。",
    "general.error.hotkey_duplicate": "各アクションには別々のショートカットキーが必要です — 現在2つが重複しています。",

    # ---------- settings: Languages page ----------
    "page.languages.title": "言語",
    "page.languages.hint": "翻訳は、この2つの言語間のどちら向きに変換するかを自動判別します。",
    "languages.pair.title": "翻訳ペア",
    "languages.primary": "主要",
    "languages.primary.hint": "通常は母語や最もよく使う言語です。",
    "languages.secondary": "副",
    "languages.secondary.hint": "日常的に書いたり話したりするもう一方の言語です。",
    "languages.swap": "言語を入れ替え",
    "languages.swap.tooltip": "主要言語と副言語を入れ替え",
    "languages.error.must_differ": "主要言語と副言語は異なる必要があります。",

    # ---------- app-wide ----------
    "app.tagline": "AI口述 · 書き換え · 翻訳",

    # ---------- settings: Transcription page ----------
    # "backend" is rendered "エンジン" (engine) rather than "バックエンド": this
    # page is read by non-developers (lawyers, doctors — see the glossary packs),
    # and "認識エンジン" is the phrase they already know.
    "page.transcription.title": "文字起こし",
    "page.transcription.hint": (
        "どの音声認識エンジンを、どの順番で試すかを選びます。"
        "有効な認証情報を持つ最初のエンジンが使われます。"
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "ローカル(Whisper)",
    "transcription.backend.hint.openai": "高品質、有料",
    "transcription.backend.hint.groq": "最速、無料枠あり",
    "transcription.backend.hint.local": "オフライン、ローカルのCPU/GPUを使用",

    "transcription.priority.title": "エンジンの優先順位",
    "transcription.priority.hint": (
        "ドラッグして並べ替えます。起動時、有効な認証情報を持つ最初のエンジンが選ばれます。"
    ),

    "transcription.keys.title": "APIキー",
    "transcription.keys.hint": (
        "Windows資格情報マネージャーに保存されます(DPAPIで保護)。"
        "空欄にするとそのエンジンをスキップします。"
    ),
    "transcription.keys.get_link": "キーを取得 ↗",

    # The step lists keep the providers' own console labels in Latin and quote
    # them with 「」 — those consoles have no Japanese UI, so a translated label
    # would be a button the user can never find.
    "transcription.keys.openai.label": "OpenAIキー",
    "transcription.keys.openai.placeholder": "OpenAI APIキーを入力",
    "transcription.keys.openai.nudge": "← OpenAIキーを入力",
    "transcription.keys.openai.help.title": "OpenAI APIキーの取得方法",
    "transcription.keys.openai.help.step1": "1. platform.openai.com にサインイン",
    "transcription.keys.openai.help.step2": "2.「API keys」→「Create new secret key」",
    "transcription.keys.openai.help.step3": "3. コピーして(「sk-…」で始まります)ここに貼り付け",
    "transcription.keys.openai.help.note": "OpenAIは有料です — 利用にはクレジットの追加が必要です。",
    "transcription.keys.openai.help.link": "OpenAIのキーページを開く",

    "transcription.keys.groq.label": "Groqキー",
    "transcription.keys.groq.placeholder": "Groq APIキーを入力",
    "transcription.keys.groq.nudge": "← Groqキーを入力",
    "transcription.keys.groq.help.title": "Groq APIキーの取得方法(無料)",
    "transcription.keys.groq.help.step1": "1. console.groq.com にサインイン",
    "transcription.keys.groq.help.step2": "2.「API Keys」→「Create API Key」",
    "transcription.keys.groq.help.step3": "3. コピーしてここに貼り付け",
    "transcription.keys.groq.help.link": "Groqコンソールを開く",

    "transcription.models.title": "エンジンごとのモデル",
    "transcription.models.hint": "そのエンジンが有効なときに使われます。",

    "transcription.device.title": "ローカル文字起こし用デバイス(ローカルエンジンのみ)",
    "transcription.device.hint": (
        "端末上のWhisperモデルを動かす場所です。OpenAIやGroqが有効な"
        "エンジンのときは影響しません — それらはクラウドで文字起こしします。"
    ),
    "transcription.device.label": "デバイス",
    "transcription.device.label.hint": "対応するNVIDIA GPUでは、CUDAはCPUより大幅に高速です。",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA(GPU)",

    "transcription.error.priority_empty": "エンジンの優先順位リストが空です。",

    # ---------- settings: About page ----------
    "page.about.title": "情報",
    "about.version": "バージョン",
    "about.version.unknown": "不明",
    "about.developer": "開発者",
    "about.email": "メール",
    "about.website": "ウェブサイト",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "用語集",
    "page.glossary.hint": (
        "会社固有の用語や日常的な用語を登録し、アプリが正しく認識して定型どおりに書けるようにします。"
        "既定ではオフです。注意: ASRバイアスやLLMのレイヤーがオンのとき、これらの用語は"
        "リクエストの一部としてクラウドプロバイダー(OpenAI/Groq)に送信されます。"
    ),
    "glossary.enable.title": "用語集を有効化",
    "glossary.enable.hint": "マスタースイッチです。オフ → 動作はこの機能のないビルドと同一になります。",

    # ---------- settings: Glossary → profession packs ----------
    # Three language axes meet on this card, only the first is the catalog's:
    #   * a pack's name/hint are chrome and follow the UI locale — below;
    #   * its *terms* follow the card's own "Pack language" picker — pack data;
    #   * its note (jurisdiction) is written in the pack's own language.
    "glossary.packs.title": "職業別パック",
    "glossary.packs.hint": (
        "厳選された用語セットで、認識エンジンが最初から分野の専門用語を正しく"
        "扱えるようにします — その分野が既定で取り違える単語、略語、表記です"
        "(先取特権、不可抗力、既往歴、心電図、merge request、冪等)。パックを"
        "クリックすると用語が下の用語集にコピーされ、自分で入力した内容と同じ"
        "ように編集できます。Pro機能です。"
    ),
    # Label only. The combo's userData is a locale CODE and the item labels are
    # native language names (data) — neither is translated.
    "glossary.packs.language": "パックの言語",
    "glossary.packs.language.hint": "インポートする用語がどの言語で書かれているか。",
    "glossary.packs.status.available": "{count}個のパックが利用可能 — いずれかをクリックすると用語が下のボックスにコピーされます。",
    "glossary.packs.status.locked": "職業別パックはPro機能です。Freeでは{cap}件の用語が有効なまま — どのパックの収録数よりも少なくなります。",
    "glossary.packs.tooltip.adds": "最大{count}件の用語を追加します。",
    "glossary.packs.tooltip.locked": "職業別パックはPro機能です。",
    "glossary.packs.already_loaded.title": "{pack}パックは読み込み済み",
    # {language} is the English language name ("Japanese") from data; hence the
    # parenthetical form rather than an inflected "in Japanese".
    "glossary.packs.already_loaded.text": "{language}パックの用語はすべて用語集にあります — 追加するものはありません。",
    "glossary.packs.count.terms": "用語{count}件",
    "glossary.packs.count.replacements": "置換{count}件",
    "glossary.packs.count.join": "と",
    "glossary.packs.confirm.title": "{pack}パックを読み込みますか?",
    "glossary.packs.confirm.adds": "用語集に{language}で{what}を追加します。",
    "glossary.packs.confirm.skipped": "既に存在する{count}件はスキップされます。",
    "glossary.packs.confirm.editable": "編集・削除できる通常の行として追加され、保存したときにのみディスクへ書き込まれます。",

    # One name + hint per pack. Chrome — follows the UI locale, unlike the terms
    # (whose language is the "Pack language" picker) and the note (jurisdiction,
    # written in the pack's own language).
    "glossary.packs.legal.name": "法務",
    "glossary.packs.legal.hint": "訴訟、契約、会社法の語彙。",
    "glossary.packs.medical.name": "医療",
    "glossary.packs.medical.hint": "診療記録、診断名、一般的な略語。",
    "glossary.packs.it.name": "IT・ソフトウェア",
    "glossary.packs.it.hint": "開発、DevOps、コードレビューの語彙。",
    "glossary.packs.finance.name": "金融・会計",
    "glossary.packs.finance.hint": "報告、評価、取引の語彙。",
    "glossary.packs.sales.name": "営業・CRM",
    "glossary.packs.sales.hint": "パイプライン、アプローチ、顧客管理の語彙。",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "レイヤー",
    "glossary.layers.hint": "各レイヤーは同じ用語を使います。レイヤーごとに個別にオン・オフできます。",
    "glossary.layers.asr": "ASRバイアス",
    "glossary.layers.asr.hint": "音声認識をあなたの用語に寄せます(クラウドはprompt / ローカルはhotwords)。",
    "glossary.layers.correction": "LLM補正(文字起こし)",
    "glossary.layers.correction.hint": "既定の文字起こしアクションで、文法補正のプロンプトに用語を追加します。",
    "glossary.layers.rewrite": "翻訳・書き換えでのLLM",
    "glossary.layers.rewrite.hint": "翻訳・書き換えのプロンプトに用語を追加します(手動ボタン + ショートカットキーのアクション)。",
    "glossary.layers.fuzzy": "あいまい置換(文字起こし)",
    "glossary.layers.fuzzy.hint": "近い単語を定型の用語に確定的にそろえます。文字起こしのみ。",
    "glossary.layers.threshold": "あいまい一致のしきい値",
    "glossary.layers.threshold.hint": "あいまい置換が働くために単語が用語にどれだけ近い必要があるか(70〜100、大きいほど厳格)。",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "用語",
    "glossary.terms.hint": "会社固有の単語をグループ分けして。1行につき1件。",
    "glossary.terms.tab.names": "名前・用語",
    "glossary.terms.tab.replacements": "置換",
    "glossary.terms.names": "名前",
    "glossary.terms.names.hint": "会社、製品、顧客、パートナー、取引先。",
    # Invented company names — proper nouns, Latin in every locale.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "サービス・用語",
    "glossary.terms.services.hint": "サービス名、プラン、分野固有の用語。",
    # Latin brand kept, Japanese example on the second line.
    "glossary.terms.services.placeholder": "TurboDrive\nオービットプラン",
    # {sep} is the `=>` separator (_REPL_SEP). Illustrates the CJK case: a term
    # *said* in Japanese but *written* in Latin, which layer C's fuzzy pass
    # cannot cross scripts to fix.
    "glossary.terms.replacements.placeholder": "ターボドライブ {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "明示的で常時オンの修正 — 1行につき「聞こえた形 {sep} 定型」の形で。"
        "そのまま適用されるため(あいまいルールなし)、認識エンジンが確実に"
        "聞き間違える単語に使ってください。"
    ),
    "glossary.terms.counter.unlimited": "用語{total}件 — すべて有効。",
    "glossary.terms.counter.used": "{cap}件中{total}件の用語を使用中 · あと{remaining}件追加できます。",
    "glossary.terms.counter.over_free": (
        "{total}件中{cap}件の用語が有効 — 残りは保存されていますが無効です。"
        "Proならすべて有効になります(最大{pro_cap}件)。"
    ),
    "glossary.terms.counter.over_ceiling": (
        "{total}件中{cap}件の用語が有効 — 最初の{cap}件のみ使われます"
        "(それ以上は認識精度が低下します)。"
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "{line}行目: 区切り「{sep}」がありません — 「聞こえた形 {sep} 定型」の形で入力してください",
    "glossary.replacements.error.empty_side": "{line}行目: 「{sep}」の両側を空にはできません",
    "glossary.replacements.error.more": "(他{count}件)",
    "glossary.replacements.error.prefix": "置換: {details}",

    # ---------- settings: Custom style page ----------
    "page.customstyle.title": "カスタムスタイル",
    "page.customstyle.hint": (
        "「カスタム」書き換えボタンで使われます。下の指示はソーステキストとともに"
        "そのままモデルへ渡されます。"
    ),
    "customstyle.preset.title": "プリセット",
    "customstyle.name": "スタイル名",
    "customstyle.name.hint": "「カスタム」ボタンのツールチップとして表示されます。",
    "customstyle.name.placeholder": "任意 — 例: Academic",
    "customstyle.prompt": "指示",
    "customstyle.prompt.hint": "モデルはこれをシステムレベルの指示として扱います。",
    "customstyle.prompt.placeholder": (
        "例: 学術的な文体で書き換え、受動態を使い、"
        "出典を丁寧に示し、用語を正確に保つ。"
    ),
    "customstyle.pro_hint": (
        "✦ 指示の編集はPro機能です。Freeでは、下の職業テンプレートを選び"
        "そのまま使ってください。"
    ),
    "customstyle.templates.title": "テンプレートから始める",
    "customstyle.templates.hint": "職業をクリックすると上のフィールドが埋まります。指示は必要に応じて調整できます。",
    "customstyle.templates.tooltip": "上のフィールドを{name}テンプレートで埋める",
    "customstyle.templates.replace.title": "現在の指示を置き換えますか?",
    "customstyle.templates.replace.text": "「スタイル名」と「指示」フィールドが{name}テンプレートで上書きされます。",

    # One .name per template, in button order. A click copies the resolved name
    # into CUSTOM_STYLE_NAME, so these are what a user ends up with as the name.
    "customstyle.templates.lawyer.name": "弁護士",
    "customstyle.templates.doctor.name": "医師",
    "customstyle.templates.psychotherapist.name": "心理療法士",
    "customstyle.templates.financial_advisor.name": "ファイナンシャルアドバイザー",
    "customstyle.templates.recruiter.name": "採用担当",
    "customstyle.templates.salesperson.name": "営業担当",
    "customstyle.templates.support.name": "サポート",
    "customstyle.templates.insurance_agent.name": "保険代理人",
    "customstyle.templates.professional.name": "ビジネス",
    "customstyle.templates.programmer.name": "プログラマー・技術",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "カスタム書き換えスタイル",
    "customstyledialog.hint": "「カスタム」ボタンは、下の指示に従ってソーステキストを書き換えます。",
    "customstyledialog.name": "スタイル名(任意)",
    "customstyledialog.name.placeholder": "例: Academic、Toxic、Marketing copy",
    "customstyledialog.prompt": "スタイル指示",
    "customstyledialog.prompt.placeholder": (
        "例: 学術的な文体で書き換え、受動態を使い、"
        "出典を丁寧に示し、用語を正確に保つ。"
    ),
    "customstyledialog.preset_limit": "カスタムスタイルを無制限に保存できるのはPro機能です。",

    # ---------- settings window chrome ----------
    "settingswindow.title.setup": "Omni Verte — 初期設定",
    "settingswindow.title.settings": "Omni Verte — 設定",
    "settingswindow.nav.general": "一般",
    "settingswindow.nav.transcription": "文字起こし",
    "settingswindow.nav.languages": "言語",
    "settingswindow.nav.custom_style": "カスタムスタイル",
    "settingswindow.nav.glossary": "用語集",
    "settingswindow.nav.license": "ライセンス",
    "settingswindow.nav.about": "情報",
    "settingswindow.local_only": "ローカルのみ使用",
    # No "&&" in Japanese — natural wording instead of the Qt ampersand mnemonic.
    "settingswindow.save_start": "保存して開始",
    "settingswindow.save_apply": "保存して適用",
    "settingswindow.error.title": "保存できません",
    "settingswindow.error.apply_failed": "「{page}」の保存に失敗しました: {error}",

    # ---------- settings: License page ----------
    "page.license.title": "ライセンス",
    "page.license.hint": "Omni Verteは無料で使えます。Proライセンスでさらに多くの機能が使えます — 以下をご覧ください。",

    "license.status.title": "ステータス",
    "license.status.hint": "このマシンが現在動作しているレベルです。",
    "license.status.level": "現在のレベル: {tier}",
    "license.status.key": "(キー {key})",

    "license.benefit.glossary": "用語集 — 最大200件の用語(Free: 5件)と既製の職業別パック",
    "license.benefit.custom_styles": "カスタムスタイル — 独自の書き換えスタイルを作成・編集(Free: テンプレートのみ)",
    "license.benefit.presets": "スタイルプリセット — 好きなだけ保存(Free: 1枠)",
    "license.benefit.history": "履歴 — 無制限で検索可能(Free: 直近10件)",
    "license.benefit.builds": "署名付きの自動更新ビルドと優先サポート",

    "license.waitlist.title": "Proは近日公開",
    "license.waitlist.hint": "Proはまだ販売していません。ウェイトリストに登録すると、公開時にいち早くお知らせします — 支払いも義務もありません。",
    "license.waitlist.unlocks": "Proで使える機能:",
    "license.waitlist.button": "Proのウェイトリストに登録",

    "license.benefits.unlocks": "Proで使える機能:",
    "license.benefits.included": "あなたのProライセンスに含まれるもの:",

    "license.key.title": "ライセンスキー",
    "license.hint.enter": "受け取ったライセンスキーを入力し、「有効化」をクリックしてください。",
    "license.hint.activated": "このマシンでProが有効です。キーは安全に保存されており、再入力は不要です。",
    "license.hint.editing": "新しいライセンスキーを入力してください。新しいキーが承認されるまで、現在のキーは有効なままです。",
    "license.button.buy": "ライセンスを取得",
    "license.button.change_key": "別のキーを使う",
    "license.button.deactivate": "無効化",
    "license.button.activate": "有効化",
    "license.toast.activated": "Proを有効化しました",
    "license.toast.cleared": "ライセンスを解除しました — Freeに戻ります",

    "license.error.network": "ライセンスサーバーに接続できませんでした。接続を確認してもう一度お試しください — 現在のステータスは変わりません。",
    "license.error.empty_key": "まずライセンスキーを入力してください。",
    "license.error.no_fingerprint": "このマシンのIDを読み取れませんでした。有効化にはWindowsが必要です。",
    "license.error.local": "このマシンで有効化できませんでした。",
    "license.error.invalid_key": "そのライセンスキーは見つかりませんでした。確認してもう一度お試しください。",
    "license.error.seat_limit": "このキーのデバイスがすべて使用中です。いずれかのデバイスを解放し(そちらで無効化)、ここで再度有効化してください。",
    "license.error.rate_limit": "最近の有効化が多すぎます。しばらくしてからお試しください。",
    "license.error.inactive": "このライセンスは有効ではありません(取り消し・返金・期限切れ)。",
    "license.error.refused": "ライセンスサーバーがリクエストを拒否しました。キーの問題ではありません — もう一度お試しいただくか、続く場合はサポートにお問い合わせください。",
    "license.error.unverified": "有効化されましたが、このマシンでライセンスを検証できませんでした。サポートにお問い合わせください。",
    "license.error.generic": "有効化できませんでした。もう一度お試しください。",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "キーを取得",
    "hotkeycapture.listening": "キーを押してください…",
    "hotkeycapture.tooltip": "クリックしてから使いたいキーを押すと、このフィールドに入ります。",

    # ---------- history kinds (Activity Feed) ----------
    "history.kind.transcription": "文字起こし",
    "history.kind.translation": "翻訳",
    "history.kind.fix": "文法補正",
    "history.kind.casual": "カジュアルな書き換え",
    "history.kind.professional": "ビジネス調の書き換え",
    "history.kind.custom": "カスタム書き換え",

    # ---------- main window ----------
    "main.status.ready": "準備完了",
    "main.status.recording": "聞き取り中…",
    "main.status.processing": "文字起こし中…",
    "main.status.error": "エラー",
    "main.status.loading": "モデルを読み込み中…",
    "main.status.failed": "モデルの読み込みに失敗 — ネットワークを確認し、設定で選び直してください",

    # フローティング録音インジケーター (ui/rec_indicator.py) — 短いピル表示。
    "indicator.recording": "認識中",
    "indicator.processing": "文字起こし",
    "indicator.loading": "読み込み中",
    "indicator.nosignal": "音声なし",

    "main.card.original.title": "最新の文字起こし",
    "main.card.result.title": "AI結果",
    "main.card.result.placeholder": "翻訳または書き換えたテキストがここに表示されます。",
    "main.card.badge.generated": "生成済み",
    "main.card.result.working": "処理中…({label})",

    "main.button.copy": "コピー",
    "main.button.clear": "クリア",
    "main.button.fix_grammar": "文法を補正",
    "main.button.casual": "カジュアル",
    "main.button.professional": "ビジネス",
    "main.button.custom": "カスタム",

    # {primary}/{secondary} are 2-letter config codes (EN, RU) — Latin in every
    # locale. "auto" is not spelled out (the ↔ carries it, the tooltip states it).
    "main.pill.translate": "翻訳({primary} ↔ {secondary})",
    "main.pill.translate.tooltip": "{primary}と{secondary}の間を翻訳し、向きを自動判別します。右クリックで言語を変更できます。",
    "main.menu.pair": "{primary} ↔ {secondary}  (自動)",
    "main.menu.change_settings": "設定で変更",

    "main.feed.title": "履歴",

    "main.tooltip.theme.dark": "ダークテーマに切り替え",
    "main.tooltip.theme.light": "ライトテーマに切り替え",
    "main.tooltip.settings": "設定を開く",
    "main.tooltip.license": "ライセンスを管理",
    "main.tooltip.no_key": "OpenAIキーが必要です — トレイ → 設定 で設定してください。",
    # {name} is the user's own style name — data, never translated.
    "main.tooltip.custom.named": "使用するスタイル: {name}",
    "main.tooltip.custom.generic": "カスタムスタイルで書き換え",
    "main.tooltip.custom.unset": "未設定 — クリックしてカスタムスタイルを設定",

    # Empty-state onboarding. {key} is a live hotkey name (F9/F10/F11), Latin.
    "main.hint.keyboard.transcribe": "{key}を押して口述・文字起こし。",
    "main.hint.keyboard.translate": "{key}を押して口述・文字起こし・翻訳。",
    "main.hint.keyboard.custom": "{key}を押して口述・文字起こしし、{style}スタイルで返します。",
    # {style} above: the two built-in styles or the user's own name, verbatim.
    "main.hint.style.casual": "カジュアル",
    "main.hint.style.professional": "ビジネス",
    "main.hint.style.custom": "カスタム",
    "main.hint.mouse.dictate": "マウスの{button}を押して口述・文字起こし。",
    "main.hint.mouse.hotkeys": "設定でキーボードショートカットを割り当てると、翻訳やスタイルでの書き換えができます。",
    # {button} above. Same three buttons as general.mouse.*.
    "main.mouse.middle": "中ボタン",
    "main.mouse.left": "左ボタン",
    "main.mouse.right": "右ボタン",

    "main.dialog.operation_failed": "操作に失敗しました",
    "main.toast.custom_style_pro": (
        "カスタムスタイルの編集はPro機能です。設定 → カスタムスタイル で"
        "テンプレートを選んでください。"
    ),
}
