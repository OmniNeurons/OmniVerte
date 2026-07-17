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
            "訴状", "答弁書", "反訴", "準備書面", "控訴", "上告", "決定",
            "判決", "支払督促", "仮処分", "仮差押え", "訴訟費用", "管轄",
            "既判力", "消滅時効", "除斥期間", "鑑定", "原告", "被告",
            "補助参加人", "仲裁", "仲裁判断", "強制執行", "立証責任",
            "送達", "口頭弁論",
            # 契約
            "売買契約", "賃貸借契約", "請負契約", "業務委託契約",
            "申込み", "承諾", "違約金", "手付金", "保証", "債権譲渡",
            "債務引受", "更改", "解除", "解約", "債務不履行",
            "履行遅滞", "不可抗力", "損害賠償", "逸失利益", "委任状",
            "信義則", "契約不適合責任", "秘密保持契約",
            # 会社
            "定款", "株主総会", "取締役会", "代表取締役", "資本金",
            "株式", "株式会社", "合同会社", "商業登記",
            "デューデリジェンス", "民法", "会社法",
        ],
        replacements=[],
        note="日本法の用語（民法、民事訴訟法、会社法）。",
    ),
    "medical": PackContent(
        terms=[
            # 病歴 / 診察
            "主訴", "現病歴", "既往歴", "家族歴", "身体所見", "聴診",
            "触診", "打診", "鑑別診断", "併存疾患", "病因", "病態生理",
            "予後", "後遺症", "退院サマリー", "経過観察記録",
            # 症状 / 所見
            "呼吸困難", "頻脈", "徐脈", "不整脈", "チアノーゼ", "浮腫",
            "紅斑", "血尿", "喀血", "筋痛", "失神", "黄疸", "蒼白",
            "高血圧", "低血圧", "低酸素血症", "発熱", "微熱", "異常なし",
            # 検査
            "心電図", "脳波", "MRI", "CT", "超音波検査", "レントゲン",
            "血算", "生化学検査", "生検", "内視鏡検査", "心エコー",
            # 治療
            "禁忌", "予防投与", "絶食", "静脈内投与", "筋肉内投与",
            "皮下投与", "経口投与", "頓用", "緊急", "経過観察",
            # 解剖
            "近位", "遠位", "外側", "内側", "両側", "片側",
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
        terms=[
            # 開発プロセス
            "ブランチ", "コミット", "マージ", "ロールバック", "リリース",
            "ビルド", "デプロイ", "コードレビュー", "技術的負債",
            "リファクタリング", "デグレ", "障害", "検証環境", "本番環境",
            "カナリアリリース", "リリース候補",
            # アーキテクチャ
            "マイクロサービス", "モノリス", "負荷分散", "レイテンシ",
            "スループット", "メモリリーク", "競合状態", "冗長化",
            "スケーラビリティ", "後方互換性", "メッセージキュー",
            "キャッシュ", "エンドポイント", "冪等",
            # データ
            "データベース", "インデックス", "マイグレーション",
            "トランザクション", "ロック", "レプリケーション",
            "シャーディング",
            # 運用
            "監視", "ログ", "分散トレーシング", "メトリクス",
            "単体テスト", "結合テスト", "カバレッジ", "負荷試験",
            "アラート",
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
            "買掛金", "売掛金", "発生主義", "減価償却", "貸借対照表",
            "損益計算書", "キャッシュフロー計算書", "総勘定元帳",
            "売上総利益", "営業利益", "経常利益",
            "販売費及び一般管理費", "消込", "引当金", "決算",
            "請求書", "会計年度", "仕訳",
            # 指標
            "運転資本", "キャッシュフロー", "フリーキャッシュフロー",
            "収益性", "損益分岐点", "流動性", "支払能力", "レバレッジ",
            "割引率", "正味現在価値", "内部収益率", "EBITDA", "ROI",
            # 資本
            "資本金", "増資", "希薄化", "企業価値評価",
            "資金調達ラウンド", "株主間契約", "デューデリジェンス",
            "配当", "ヘッジ", "エスクロー",
            # 税務 / 規制
            "消費税", "法人税", "監査報告書", "IFRS", "会計基準",
            "確定申告", "源泉徴収",
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
            "見込み客", "リード", "商談", "営業パイプライン",
            "商談フェーズ", "初回接触", "新規開拓", "提案書", "見積書",
            "デモ", "概念実証", "パイロット導入", "交渉", "受注",
            "失注", "営業サイクル", "売上予測", "売上目標", "成約率",
            "平均単価",
            # 顧客対応
            "反論", "反論処理", "決裁者", "窓口担当者", "課題",
            "価値提案", "アップセル", "クロスセル", "契約更新",
            "顧客維持", "解約率", "顧客基盤", "タッチポイント",
            "フォローアップ", "導入支援",
            # 用語
            "CRM", "KPI", "NPS", "発注書", "基本契約",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
