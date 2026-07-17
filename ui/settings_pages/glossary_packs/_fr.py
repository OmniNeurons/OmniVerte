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
            "assignation", "requête", "conclusions", "mémoire en défense",
            "demande reconventionnelle", "appel", "pourvoi en cassation",
            "ordonnance", "jugement", "arrêt", "référé", "mise en demeure",
            "mesures conservatoires", "dépens", "compétence territoriale",
            "litispendance", "autorité de la chose jugée", "prescription",
            "forclusion", "expertise judiciaire", "demandeur", "défendeur",
            "tiers intervenant", "arbitrage", "sentence arbitrale",
            "exécution forcée", "voies de recours",
            # Contrats
            "contrat de vente", "contrat de bail", "contrat d'entreprise",
            "contrat de prestation de services", "offre", "acceptation",
            "consentement", "clause pénale", "arrhes", "caution",
            "garantie autonome", "cession de créance", "novation",
            "subrogation", "résiliation", "résolution du contrat",
            "inexécution", "mise en demeure préalable", "force majeure",
            "dommages et intérêts", "manque à gagner", "perte subie",
            "procuration", "bonne foi", "obligation de moyens",
            "obligation de résultat",
            # Sociétés
            "statuts", "assemblée générale", "conseil d'administration",
            "gérant", "capital social", "parts sociales", "actions",
            "société à responsabilité limitée", "société par actions simplifiée",
            "RCS", "SIRET", "diligence raisonnable",
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
            "anamnèse", "motif de consultation", "antécédents personnels",
            "antécédents familiaux", "histoire de la maladie",
            "examen clinique", "auscultation", "palpation", "percussion",
            "diagnostic différentiel", "comorbidité", "étiologie",
            "physiopathologie", "pronostic", "séquelles",
            "compte rendu d'hospitalisation", "évolution clinique",
            # Symptômes / signes
            "dyspnée", "tachycardie", "bradycardie", "arythmie", "cyanose",
            "œdème", "érythème", "hématurie", "hémoptysie", "myalgie",
            "syncope", "ictère", "pâleur", "hypertension artérielle",
            "hypotension", "hypoxie", "fièvre", "fébricule", "apyrétique",
            "sans particularité",
            # Examens
            "ECG", "EEG", "IRM", "scanner", "échographie", "radiographie",
            "numération formule sanguine", "bilan biologique", "biopsie",
            "endoscopie", "échocardiographie",
            # Prise en charge
            "contre-indication", "prophylaxie", "à jeun", "voie intraveineuse",
            "voie intramusculaire", "voie sous-cutanée", "voie orale",
            "à la demande", "en urgence", "surveillance",
            # Anatomie
            "antérieur", "postérieur", "proximal", "distal", "latéral",
            "médial", "bilatéral", "unilatéral",
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
        terms=[
            # Processus
            "branche", "fusion", "déploiement", "revue de code",
            "dette technique", "refactorisation", "régression", "incident",
            "environnement de test", "mise en production", "version candidate",
            "compilation",
            # Architecture
            "microservice", "monolithe", "répartiteur de charge", "latence",
            "débit", "fuite mémoire", "situation de compétition",
            "tolérance aux pannes", "montée en charge",
            "rétrocompatibilité", "file de messages", "cache",
            "point d'entrée", "idempotent",
            # Données
            "base de données", "index", "migration", "transaction", "verrou",
            "réplication", "partitionnement",
            # Exploitation
            "supervision", "journalisation", "traçabilité", "métriques",
            "test unitaire", "test d'intégration", "couverture de test",
            "test de charge",
            # Outils et processus écrits en anglais
            "merge request", "pull request", "commit", "rollback", "hotfix",
            "sprint", "backlog", "deploy", "Kubernetes", "Docker", "PostgreSQL",
            "Redis", "Kafka", "nginx", "Git", "GitLab", "CI/CD", "API",
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
            "dettes fournisseurs", "créances clients", "charges à payer",
            "amortissement", "bilan", "compte de résultat",
            "tableau des flux de trésorerie", "grand livre", "marge brute",
            "marge nette", "charges d'exploitation", "rapprochement bancaire",
            "provision", "clôture des comptes", "facture", "exercice comptable",
            # Indicateurs
            "besoin en fonds de roulement", "flux de trésorerie",
            "flux de trésorerie disponible", "rentabilité", "seuil de rentabilité",
            "liquidité", "solvabilité", "effet de levier", "taux d'actualisation",
            "valeur actuelle nette", "taux de rendement interne",
            "EBITDA", "CAPEX", "OPEX", "ROI",
            # Opérations / capital
            "capital social", "augmentation de capital", "dilution",
            "valorisation", "tour de table", "pacte d'associés",
            "due diligence", "dividendes", "couverture", "séquestre",
            # Fiscal / réglementaire
            "TVA", "impôt sur les sociétés", "URSSAF", "commissaire aux comptes",
            "IFRS", "plan comptable général", "liasse fiscale",
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
            "prospect", "opportunité", "tunnel de vente", "étape de vente",
            "premier contact", "appel à froid", "proposition commerciale",
            "devis", "démonstration", "preuve de concept", "pilote",
            "négociation", "signature", "cycle de vente", "prévision des ventes",
            "objectif de vente", "taux de conversion", "panier moyen",
            # Relation client
            "objection", "traitement des objections", "décideur",
            "interlocuteur", "point de douleur", "proposition de valeur",
            "vente additionnelle", "vente croisée", "renouvellement",
            "fidélisation", "taux d'attrition", "portefeuille clients",
            "point de contact", "relance commerciale", "mise en service",
            # Termes
            "CRM", "KPI", "NPS", "bon de commande", "contrat-cadre",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
