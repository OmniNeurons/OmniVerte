# file: ui/settings_pages/glossary_packs/_en.py

"""English pack content. See the package docstring for the rules this data obeys.

The replacements here are the one apparent oddity: they are Russian on the heard
side. That is deliberate and is the *English* pack's job — a Russian developer
says "мёрж реквест" and wants the English "merge request" written. Layer C's
fuzzy matcher cannot cross scripts, so an explicit entry is the only route. An
English speaker just says "merge request" and the term list handles it.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "en"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Only what speech recognition genuinely gets wrong: rare terms of
            # art, homophones (tort, lien, writ), Latin. Everyday legal words
            # (contract, court, settlement) are left out — the recognizer
            # already knows them, and every term spends a slot of a capped bias
            # list (ElevenLabs: 50).
            # Procedure
            "affidavit", "amicus curiae", "interrogatories", "res judicata",
            "subpoena", "tort", "voir dire", "writ",
            # Contract / corporate
            "estoppel", "force majeure", "lien", "novation", "severability",
            # Latin / terms of art
            "bona fide", "de facto", "de jure", "ex parte", "inter alia",
            "prima facie", "pro bono", "pro rata", "quid pro quo", "ultra vires",
        ],
        # An English-dictating lawyer says "force majeure" outright; the term
        # list and layer C's fuzzy pass ("force major") cover it.
        replacements=[],
        note="Common-law vocabulary (US/UK practice).",
    ),
    "medical": PackContent(
        terms=[
            # Only specialist vocabulary and order abbreviations; everyday
            # words (blood pressure, fever, pain, MRI) are left out — the
            # recognizer already knows them, and the bias list is capped.
            # History / exam
            "anamnesis", "auscultation", "comorbidity", "etiology",
            "palpation", "sequelae",
            # Findings / symptoms
            "afebrile", "bradycardia", "cyanosis", "dyspnea", "edema",
            "erythema", "hematuria", "hemoptysis", "myalgia", "syncope",
            "tachycardia",
            # Studies / orders
            "CBC", "ECG", "EEG",
            # Plan
            "NPO", "prophylaxis", "titrate", "PRN", "BID", "TID", "QID",
        ],
        replacements=[],
    ),
    "it": PackContent(
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Version control / process
            "merge request", "pull request", "rebase", "cherry-pick", "changelog",
            "hotfix", "rollback",
            # Architecture / concepts
            "API", "endpoint", "idempotent", "middleware", "webhook", "microservice",
            "feature flag", "canary release", "blue-green deployment",
            # Infra / tooling
            "Kubernetes", "Docker", "CI/CD", "Terraform", "nginx", "PostgreSQL",
            "Redis", "Kafka", "gRPC", "GitHub", "GitLab", "linter", "stack trace",
        ],
        # The strongest case for replacements in any pack: Russian developers
        # pronounce these in Russian and write them in Latin without exception.
        # Variants the regex cannot equate (ё/е, one/two л) are listed
        # separately; space/hyphen it handles.
        replacements=[
            ("мёрж реквест", "merge request"),
            ("мерж реквест", "merge request"),
            ("пул реквест", "pull request"),
            ("пулл реквест", "pull request"),
            ("ребейз", "rebase"),
            ("роллбэк", "rollback"),
            ("роллбек", "rollback"),
            ("хотфикс", "hotfix"),
            ("кубернетес", "Kubernetes"),
            ("кубернетис", "Kubernetes"),
            ("докер", "Docker"),
            ("постгрес", "PostgreSQL"),
            ("редис", "Redis"),
            ("кафка", "Kafka"),
            ("си ай си ди", "CI/CD"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # Only acronyms and terms of art; everyday words (budget, invoice,
            # revenue, equity) are left out — the recognizer already knows
            # them, and the bias list is capped. "cash flow", "cap table",
            # "term sheet" and "due diligence" stay: the map below produces them.
            # Reporting
            "accrual", "P&L", "CAPEX", "OPEX",
            # Metrics
            "ARR", "MRR", "CAC", "LTV",
            "EBITDA", "EBIT", "CAGR", "ROI", "IRR", "NPV", "WACC",
            "cash flow",
            # Deals / capital
            "cap table", "due diligence", "term sheet", "escrow",
            # Compliance
            "IFRS", "GAAP", "VAT",
        ],
        # Only the borrowings a Russian speaker says in Russian but writes in
        # Latin.
        replacements=[
            ("эбитда", "EBITDA"),
            ("кэш флоу", "cash flow"),
            ("кэпэкс", "CAPEX"),
            ("опекс", "OPEX"),
            ("терм шит", "term sheet"),
            ("кэп тейбл", "cap table"),
            ("дью дилидженс", "due diligence"),
        ],
    ),
    "sales": PackContent(
        terms=[
            # Only acronyms and hyphenation-sensitive forms; everyday words
            # (customer, deal, discount, call, meeting) are left out — the
            # recognizer already knows them, and the bias list is capped.
            # Method / motion
            "follow-up", "touchpoint", "upsell", "cross-sell",
            # Metrics / terms
            # ("SQL" as sales-qualified lead is left out on purpose — it would
            # collide with the database language for anyone who says both.)
            "MQL", "ICP", "TAM", "NPS", "SLA",
        ],
        replacements=[],
    ),
}
