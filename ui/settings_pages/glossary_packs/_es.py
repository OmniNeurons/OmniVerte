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
            "demanda", "contestación a la demanda", "reconvención",
            "escrito de alegaciones", "recurso de apelación", "recurso de casación",
            "auto", "sentencia", "providencia", "juicio ordinario", "juicio verbal",
            "procedimiento monitorio", "medidas cautelares", "costas procesales",
            "competencia territorial", "litispendencia", "cosa juzgada",
            "prueba documental", "prueba pericial", "prueba testifical",
            "interrogatorio de partes", "demandante", "demandado",
            "prescripción", "caducidad", "arbitraje", "laudo arbitral",
            "ejecución de sentencia",
            # Contratos
            "contrato de compraventa", "contrato de arrendamiento",
            "contrato de obra", "contrato de prestación de servicios",
            "oferta", "aceptación", "consentimiento", "cláusula penal", "arras",
            "fianza", "aval", "cesión de créditos", "novación", "subrogación",
            "resolución del contrato", "desistimiento", "incumplimiento", "mora",
            "fuerza mayor", "caso fortuito", "daños y perjuicios",
            "lucro cesante", "daño emergente", "poder notarial", "buena fe",
            # Societario
            "escritura de constitución", "estatutos sociales", "junta general",
            "consejo de administración", "administrador único", "capital social",
            "participaciones sociales", "sociedad limitada", "sociedad anónima",
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
            "anamnesis", "motivo de consulta", "antecedentes personales",
            "antecedentes familiares", "enfermedad actual", "exploración física",
            "auscultación", "palpación", "percusión", "diagnóstico diferencial",
            "comorbilidad", "etiología", "patogenia", "pronóstico", "secuelas",
            "informe de alta", "evolución clínica",
            # Síntomas / hallazgos
            "disnea", "taquicardia", "bradicardia", "arritmia", "cianosis",
            "edema", "eritema", "hematuria", "hemoptisis", "mialgia", "síncope",
            "ictericia", "palidez", "hipertensión arterial", "hipotensión",
            "hipoxia", "fiebre", "febrícula", "afebril", "sin hallazgos",
            # Pruebas
            "ECG", "EEG", "RMN", "TAC", "ecografía", "radiografía", "hemograma",
            "analítica", "bioquímica", "biopsia", "endoscopia", "ecocardiograma",
            # Plan
            "contraindicación", "profilaxis", "en ayunas", "vía intravenosa",
            "vía intramuscular", "vía subcutánea", "vía oral", "a demanda",
            "urgente", "seguimiento",
            # Anatomía
            "anterior", "posterior", "proximal", "distal", "lateral",
            "medial", "bilateral", "unilateral",
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
        terms=[
            # Proceso
            "rama", "fusión", "despliegue", "revisión de código", "deuda técnica",
            "refactorización", "regresión", "incidencia", "entorno de pruebas",
            "puesta en producción", "versión candidata", "compilación",
            # Arquitectura
            "microservicio", "monolito", "balanceador de carga", "latencia",
            "rendimiento", "fuga de memoria", "condición de carrera",
            "tolerancia a fallos", "escalabilidad", "retrocompatibilidad",
            "cola de mensajes", "caché", "punto de entrada", "idempotente",
            # Datos
            "base de datos", "índice", "migración", "transacción", "bloqueo",
            "replicación", "particionado",
            # Operación
            "monitorización", "registro de eventos", "trazabilidad", "métricas",
            "prueba unitaria", "prueba de integración", "cobertura de pruebas",
            "pruebas de carga",
            # Herramientas y procesos que se escriben en inglés
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
            # Contabilidad
            "cuentas a pagar", "cuentas a cobrar", "devengo", "amortización",
            "balance de situación", "cuenta de pérdidas y ganancias",
            "estado de flujos de efectivo", "libro mayor", "margen bruto",
            "margen neto", "gastos operativos", "conciliación bancaria",
            "provisión", "cierre contable", "factura", "ejercicio fiscal",
            # Métricas
            "fondo de maniobra", "flujo de caja", "flujo de caja libre",
            "rentabilidad", "umbral de rentabilidad", "liquidez", "solvencia",
            "apalancamiento", "tasa de descuento", "valor actual neto",
            "tasa interna de retorno", "EBITDA", "CAPEX", "OPEX", "ROI",
            # Operaciones / capital
            "capital social", "ampliación de capital", "dilución", "valoración",
            "ronda de financiación", "pacto de socios", "due diligence",
            "participaciones", "dividendos", "cobertura", "garantía",
            # Fiscal / regulatorio
            "IVA", "impuesto de sociedades", "IRPF", "auditoría de cuentas",
            "NIIF", "plan general contable",
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
            "cliente potencial", "oportunidad", "embudo de ventas",
            "etapa de la oportunidad", "primer contacto", "llamada en frío",
            "propuesta comercial", "presupuesto", "demostración",
            "prueba de concepto", "piloto", "negociación", "cierre",
            "ciclo de venta", "previsión de ventas", "objetivo de ventas",
            "ratio de conversión", "ticket medio",
            # Relación con el cliente
            "objeción", "gestión de objeciones", "responsable de decisión",
            "interlocutor", "punto de dolor", "propuesta de valor",
            "venta adicional", "venta cruzada", "renovación", "fidelización",
            "tasa de abandono", "cartera de clientes", "punto de contacto",
            "seguimiento comercial", "alta de cliente",
            # Términos
            "CRM", "KPI", "NPS", "pedido de compra", "contrato marco",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
