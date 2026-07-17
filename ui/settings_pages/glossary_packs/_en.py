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
            # Procedure
            "affidavit", "amicus curiae", "arbitration", "cause of action",
            "cease and desist", "class action", "counterclaim", "deposition",
            "discovery", "due diligence", "injunction", "interrogatories",
            "judgment", "jurisdiction", "litigation", "motion to dismiss",
            "plaintiff", "pleading", "res judicata", "settlement", "subpoena",
            "summary judgment", "tort", "venue", "voir dire", "writ",
            # Contract / corporate
            "arm's length", "assignment", "breach of contract", "consideration",
            "covenant", "estoppel", "force majeure", "good faith",
            "indemnity", "indemnification", "injunctive relief", "lien",
            "liquidated damages", "material adverse change", "novation",
            "power of attorney", "severability", "statute of limitations",
            "termination for convenience", "warranty",
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
            # History / exam
            "anamnesis", "auscultation", "chief complaint", "comorbidity",
            "differential diagnosis", "etiology", "history of present illness",
            "palpation", "past medical history", "percussion", "prognosis",
            "review of systems", "sequelae",
            # Findings / symptoms
            "afebrile", "arrhythmia", "bradycardia", "cyanosis", "dyspnea",
            "edema", "erythema", "hematuria", "hemoptysis", "hypertension",
            "hypotension", "hypoxia", "jaundice", "myalgia", "pallor",
            "syncope", "tachycardia",
            # Studies / orders
            "auscultatory", "biopsy", "CBC", "CT", "ECG", "EEG", "MRI",
            "ultrasound", "X-ray",
            # Plan
            "contraindication", "NPO", "prophylaxis", "stat",
            "titrate", "PRN", "BID", "TID", "QID",
            # Anatomy / direction
            "anterior", "posterior", "proximal", "distal", "lateral",
            "medial", "bilateral", "unilateral",
        ],
        replacements=[],
    ),
    "it": PackContent(
        terms=[
            # Version control / process
            "merge request", "pull request", "rebase", "cherry-pick", "squash",
            "commit", "branch", "changelog", "code review", "hotfix",
            "regression", "rollback", "release candidate", "retrospective",
            "sprint", "backlog", "standup", "tech debt",
            # Architecture / concepts
            "API", "backend", "frontend", "cache", "endpoint", "idempotent",
            "latency", "load balancer", "microservice", "middleware",
            "migration", "monolith", "throughput", "webhook", "race condition",
            "memory leak", "feature flag", "canary release",
            "blue-green deployment",
            # Infra / tooling
            "Kubernetes", "Docker", "container", "CI/CD", "pipeline",
            "Terraform", "nginx", "PostgreSQL", "Redis", "Kafka", "gRPC",
            "GitHub", "GitLab", "observability", "telemetry",
            # Quality
            "unit test", "integration test", "end-to-end test", "coverage",
            "linter", "staging", "production", "stack trace",
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
            # Reporting
            "accounts payable", "accounts receivable", "accrual",
            "amortization", "balance sheet", "cash flow statement",
            "depreciation", "general ledger", "gross margin",
            "income statement", "net margin", "operating expenses", "P&L",
            "reconciliation", "write-off", "CAPEX", "OPEX",
            # Metrics
            "ARR", "MRR", "CAC", "LTV", "churn", "burn rate", "runway",
            "EBITDA", "EBIT", "CAGR", "ROI", "IRR", "NPV", "WACC",
            "working capital", "cash flow", "free cash flow",
            # Deals / capital
            "cap table", "convertible note", "due diligence", "equity",
            "liquidity", "valuation", "term sheet", "dilution",
            "vesting", "cliff", "escrow", "hedge", "leverage",
            # Compliance
            "audit trail", "IFRS", "GAAP", "VAT", "invoice", "fiscal year",
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
            # Pipeline
            "lead", "prospect", "qualified lead", "opportunity", "pipeline",
            "deal stage", "discovery call", "demo", "proof of concept",
            "pilot", "proposal", "quote", "negotiation", "closed won",
            "closed lost", "win rate", "sales cycle", "forecast", "quota",
            # Method / motion
            "cold outreach", "follow-up", "touchpoint", "objection handling",
            "decision maker", "champion", "gatekeeper", "stakeholder",
            "pain point", "value proposition", "upsell", "cross-sell",
            "renewal", "onboarding", "account review",
            # Metrics / terms
            # ("SQL" as sales-qualified lead is left out on purpose — it would
            # collide with the database language for anyone who says both.)
            "conversion rate", "MQL", "ICP", "TAM", "NPS",
            "retention", "churn", "SLA", "purchase order",
        ],
        replacements=[],
    ),
}
