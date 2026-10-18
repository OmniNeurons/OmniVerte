# file: ui/settings_pages/glossary_packs/_es.py

"""Spanish pack content. See the package docstring for the rules this data obeys.

Legal follows Spain's practice (LEC / Código Civil / Registro Mercantil) — the
majority jurisdiction for the language, named in the pack's note so a Mexican or
Argentine user is told rather than surprised. The other packs are effectively
jurisdiction-free.

Replacements are case normalization of abbreviations Spanish speakers spell out
loud (IVA, EBITDA, CRM) plus form normalization ("postgres" -> "PostgreSQL").
No entry translates: a Spanish accountant says and writes "flujo de caja".
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "es"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Procedimiento
            "reconvención", "recurso de casación", "procedimiento monitorio",
            "litispendencia", "cosa juzgada", "prueba testifical",
            "laudo arbitral",
            # Contratos
            "cláusula penal", "arras", "cesión de créditos", "novación",
            "subrogación", "caso fortuito", "lucro cesante", "daño emergente",
            # Societario
            "Registro Mercantil", "diligencia debida", "CIF", "LEC",
        ],
        replacements=[
            ("cif", "CIF"),
            ("lec", "LEC"),
        ],
        note="Terminología de España (LEC, Código Civil, Registro Mercantil).",
    ),
    "medical": PackContent(
        terms=[
            # Anamnesis / exploración
            "anamnesis", "auscultación", "comorbilidad", "etiología", "patogenia",
            # Síntomas / hallazgos
            "disnea", "taquicardia", "bradicardia", "arritmia", "cianosis",
            "eritema", "hematuria", "hemoptisis", "mialgia", "síncope",
            "ictericia", "hipoxia", "febrícula", "afebril",
            # Pruebas
            "ECG", "EEG", "RMN", "TAC", "hemograma", "ecocardiograma",
            # Plan
            "profilaxis",
        ],
        replacements=[
            ("ecg", "ECG"),
            ("eeg", "EEG"),
            ("rmn", "RMN"),
            ("tac", "TAC"),
        ],
    ),
    "it": PackContent(
        # Spanish developers speak Spanish and write tool and process names in
        # Latin — the same split as the Russian IT pack.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # Jerga que el reconocimiento de voz suele fallar
            "microservicio", "idempotente",
            # Herramientas y procesos que se escriben en inglés
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
            # Contabilidad
            "devengo", "libro mayor",
            # Métricas
            "fondo de maniobra", "umbral de rentabilidad", "apalancamiento",
            "valor actual neto", "tasa interna de retorno",
            "EBITDA", "CAPEX", "OPEX", "ROI",
            # Operaciones / capital
            "pacto de socios", "due diligence",
            # Fiscal / regulatorio
            "IVA", "IRPF", "NIIF", "plan general contable",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("capex", "CAPEX"),
            ("opex", "OPEX"),
            ("roi", "ROI"),
            ("iva", "IVA"),
            ("irpf", "IRPF"),
            ("niif", "NIIF"),
        ],
        note="Fiscalidad española: IVA, IRPF, NIIF, plan general contable.",
    ),
    "sales": PackContent(
        terms=[
            # Embudo
            "embudo de ventas", "llamada en frío", "prueba de concepto",
            "ratio de conversión", "ticket medio",
            # Relación con el cliente
            "gestión de objeciones", "punto de dolor", "propuesta de valor",
            "venta adicional", "venta cruzada", "tasa de abandono",
            "punto de contacto",
            # Términos
            "CRM", "KPI", "NPS",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
