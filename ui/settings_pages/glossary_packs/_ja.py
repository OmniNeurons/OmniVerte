# file: ui/settings_pages/glossary_packs/_ja.py

"""Japanese pack content. See the package docstring for the rules this data
obeys, including the standing note that layer C's *fuzzy* pass is inert on CJK —
these terms reach the user through ASR bias, the LLM block and the explicit
replacement map.

Legal follows Japanese practice (民法 / 民事訴訟法 / 会社法), named in the
pack's note.

**No homophone replacements are shipped.** Japanese has more homophones than any
language here (鑑定/艦艇/干潮 all きかん-adjacent confusions exist), which makes
the map valuable *and* makes authoring it from outside the language reckless: a
wrong pair corrupts text that was correct. The map here is limited to Latin
abbreviations Japanese speakers embed in speech and write in Latin. A user who
knows the homophones their own dictation hits can add them by hand — since the
``_heard_regex`` fix, those now fire inside a sentence instead of silently doing
nothing.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "ja"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # 訴訟
            "訴状", "答弁書", "反訴", "準備書面", "上告", "支払督促",
            "仮処分", "仮差押え", "既判力", "消滅時効", "除斥期間",
            "補助参加人", "立証責任", "送達", "口頭弁論",
            # 契約
            "賃貸借契約", "請負契約", "手付金", "債権譲渡", "債務引受",
            "更改", "債務不履行", "履行遅滞", "逸失利益", "信義則",
            "契約不適合責任",
            # 会社
            "定款", "デューデリジェンス",
        ],
        replacements=[],
        note="日本法の用語（民法、民事訴訟法、会社法）。",
    ),
    "medical": PackContent(
        terms=[
            # 病歴 / 診察
            "主訴", "現病歴", "既往歴", "鑑別診断", "併存疾患", "病態生理",
            "予後",
            # 症状 / 所見
            "頻脈", "徐脈", "チアノーゼ", "浮腫", "喀血", "低酸素血症",
            # 検査
            "MRI", "CT", "血算", "生検", "心エコー",
            # 治療
            "頓用",
            # 解剖
            "近位", "遠位",
        ],
        # Latin abbreviations only — see the module docstring on homophones.
        replacements=[
            ("ct", "CT"),
            ("mri", "MRI"),
        ],
    ),
    "it": PackContent(
        # Japanese developers speak Japanese and write tool names in Latin,
        # while the process vocabulary is katakana — the same split as every
        # other IT pack, just with a third script involved.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # 音声認識が誤りやすい業界用語
            "デグレ", "冪等", "カナリアリリース", "シャーディング",
            # ラテン文字で書くツールとプロセス
            "merge request", "pull request", "Kubernetes", "Docker",
            "PostgreSQL", "Redis", "Kafka", "nginx", "Git", "GitLab",
            "CI/CD", "API",
        ],
        replacements=[
            ("k8s", "Kubernetes"),
            ("kubernetes", "Kubernetes"),
            ("postgres", "PostgreSQL"),
            ("ci cd", "CI/CD"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # 会計
            "買掛金", "売掛金", "発生主義", "総勘定元帳",
            "販売費及び一般管理費", "消込", "引当金", "仕訳",
            # 指標
            "運転資本", "割引率", "正味現在価値", "内部収益率", "EBITDA",
            "ROI",
            # 資本
            "希薄化", "株主間契約", "デューデリジェンス", "エスクロー",
            # 税務 / 規制
            "IFRS",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("roi", "ROI"),
            ("ifrs", "IFRS"),
        ],
        note="日本の税務・会計用語（消費税、法人税、確定申告）。",
    ),
    "sales": PackContent(
        terms=[
            # パイプライン
            "概念実証", "失注", "成約率",
            # 顧客対応
            "反論処理", "決裁者", "価値提案", "アップセル", "クロスセル",
            "タッチポイント",
            # 用語
            "CRM", "KPI", "NPS",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
