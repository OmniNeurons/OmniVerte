# file: ui/settings_pages/glossary_packs/_fr.py

"""French pack content. See the package docstring for the rules this data obeys.

Legal follows France's practice (Code civil / Code de procédure civile / RCS) —
the majority jurisdiction, named in the pack's note so a Belgian or Québécois
user is told rather than surprised.

Replacements are case normalization of abbreviations spelled out loud (TVA, RCS,
EBITDA) plus form normalization. No entry translates: a French doctor says and
writes "dyspnée".
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "fr"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Procédure
            "mémoire en défense", "demande reconventionnelle",
            "pourvoi en cassation", "référé", "mise en demeure",
            "mesures conservatoires", "dépens", "litispendance",
            "autorité de la chose jugée", "forclusion", "tiers intervenant",
            "sentence arbitrale", "voies de recours",
            # Contrats
            "clause pénale", "arrhes", "garantie autonome",
            "cession de créance", "novation", "subrogation", "force majeure",
            "obligation de moyens", "obligation de résultat",
            # Sociétés
            "société par actions simplifiée", "RCS", "SIRET",
            "diligence raisonnable",
        ],
        replacements=[
            ("rcs", "RCS"),
            ("siret", "SIRET"),
        ],
        note="Terminologie française (Code civil, CPC, RCS).",
    ),
    "medical": PackContent(
        terms=[
            # Anamnèse / examen
            "anamnèse", "comorbidité", "étiologie", "physiopathologie",
            # Symptômes / signes
            "dyspnée", "tachycardie", "bradycardie", "arythmie", "cyanose",
            "œdème", "érythème", "hématurie", "hémoptysie", "myalgie",
            "ictère", "hypoxie", "fébricule", "apyrétique",
            # Examens
            "ECG", "EEG", "IRM", "numération formule sanguine",
            "échocardiographie",
            # Prise en charge
            "contre-indication", "prophylaxie",
        ],
        replacements=[
            ("ecg", "ECG"),
            ("eeg", "EEG"),
            ("irm", "IRM"),
        ],
    ),
    "it": PackContent(
        # French developers speak French and write tool and process names in
        # Latin — the same split as the Russian and Spanish IT packs.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Jargon que la reconnaissance vocale rate facilement
            "microservice", "idempotent",
            # Outils et processus écrits en anglais
            "merge request", "pull request", "commit", "rollback", "hotfix",
            "backlog", "deploy", "Kubernetes", "Docker", "PostgreSQL", "Redis",
            "Kafka", "nginx", "Git", "GitLab", "CI/CD", "API",
        ],
        replacements=[
            ("kubernetes", "Kubernetes"),
            ("postgres", "PostgreSQL"),
            ("ci cd", "CI/CD"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # Comptabilité
            "charges à payer", "grand livre", "rapprochement bancaire",
            # Indicateurs
            "besoin en fonds de roulement", "taux d'actualisation",
            "valeur actuelle nette", "taux de rendement interne",
            "EBITDA", "CAPEX", "OPEX", "ROI",
            # Opérations / capital
            "tour de table", "pacte d'associés", "due diligence", "séquestre",
            # Fiscal / réglementaire
            "TVA", "URSSAF", "commissaire aux comptes", "IFRS",
            "plan comptable général", "liasse fiscale",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("capex", "CAPEX"),
            ("opex", "OPEX"),
            ("roi", "ROI"),
            ("tva", "TVA"),
            ("urssaf", "URSSAF"),
            ("ifrs", "IFRS"),
        ],
        note="Fiscalité française : TVA, URSSAF, plan comptable général.",
    ),
    "sales": PackContent(
        terms=[
            # Tunnel
            "tunnel de vente", "appel à froid", "preuve de concept",
            # Relation client
            "point de douleur", "proposition de valeur",
            "vente additionnelle", "vente croisée", "taux d'attrition",
            # Termes
            "CRM", "KPI", "NPS", "contrat-cadre",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
