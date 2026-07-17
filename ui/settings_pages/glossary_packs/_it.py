# file: ui/settings_pages/glossary_packs/_it.py

"""Italian pack content. See the package docstring for the rules this data obeys.

Legal follows Italy's practice (Codice civile / Codice di procedura civile /
Registro delle imprese), named in the pack's note. Swiss Italian practice
diverges.

Replacements are case normalization of abbreviations spelled out loud (IVA,
EBITDA, CRM). No entry translates: an Italian doctor says and writes "dispnea".

Note the module name collides with nothing: this is the *Italian* locale, while
the IT & Software pack is keyed "it" inside PACKS. Unfortunate but real — "it"
is both the ISO code for Italian and the shorthand for information technology.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "it"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # Procedura
            "atto di citazione", "comparsa di risposta", "domanda riconvenzionale",
            "memoria difensiva", "appello", "ricorso per cassazione",
            "ordinanza", "sentenza", "decreto ingiuntivo", "provvedimento cautelare",
            "sequestro conservativo", "spese di lite", "competenza territoriale",
            "litispendenza", "giudicato", "prescrizione", "decadenza",
            "consulenza tecnica d'ufficio", "attore", "convenuto",
            "terzo chiamato", "arbitrato", "lodo arbitrale",
            "esecuzione forzata", "onere della prova", "notifica",
            # Contratti
            "contratto di compravendita", "contratto di locazione",
            "contratto d'appalto", "contratto di prestazione d'opera",
            "proposta", "accettazione", "consenso", "clausola penale",
            "caparra confirmatoria", "fideiussione", "garanzia",
            "cessione del credito", "accollo", "novazione", "recesso",
            "risoluzione del contratto", "inadempimento", "mora",
            "forza maggiore", "caso fortuito", "risarcimento del danno",
            "lucro cessante", "danno emergente", "procura", "buona fede",
            # Societario
            "atto costitutivo", "statuto", "assemblea dei soci",
            "consiglio di amministrazione", "amministratore unico",
            "capitale sociale", "quote sociali",
            "società a responsabilità limitata", "società per azioni",
            "Registro delle imprese", "diligenza dovuta", "partita IVA",
            # Declared because the replacement below produces it: a canonical the
            # term lists never name is unreachable for the ASR-bias and LLM
            # layers, which read the terms and nothing else.
            "Codice civile",
        ],
        replacements=[
            ("codice civile", "Codice civile"),
        ],
        note="Diritto italiano (Codice civile, c.p.c., Registro delle imprese).",
    ),
    "medical": PackContent(
        terms=[
            # Anamnesi / esame
            "anamnesi", "motivo della visita", "anamnesi patologica remota",
            "anamnesi familiare", "storia clinica", "esame obiettivo",
            "auscultazione", "palpazione", "percussione",
            "diagnosi differenziale", "comorbidità", "eziologia", "patogenesi",
            "prognosi", "esiti", "lettera di dimissione", "decorso clinico",
            # Sintomi / segni
            "dispnea", "tachicardia", "bradicardia", "aritmia", "cianosi",
            "edema", "eritema", "ematuria", "emottisi", "mialgia", "sincope",
            "ittero", "pallore", "ipertensione arteriosa", "ipotensione",
            "ipossia", "febbre", "febbricola", "apiretico", "nella norma",
            # Esami
            "ECG", "EEG", "RM", "TC", "ecografia", "radiografia", "emocromo",
            "esami ematochimici", "biopsia", "endoscopia", "ecocardiogramma",
            # Terapia
            "controindicazione", "profilassi", "a digiuno", "via endovenosa",
            "via intramuscolare", "via sottocutanea", "via orale",
            "al bisogno", "in urgenza", "follow-up clinico",
            # Anatomia
            "anteriore", "posteriore", "prossimale", "distale", "laterale",
            "mediale", "bilaterale", "monolaterale",
        ],
        replacements=[
            ("ecg", "ECG"),
            ("eeg", "EEG"),
        ],
    ),
    "it": PackContent(
        # Italian developers speak Italian and write tool and process names in
        # Latin — the same split as the other IT packs.
        terms=[
            # Processo
            "ramo", "unione", "rilascio", "revisione del codice",
            "debito tecnico", "refactoring", "regressione", "incidente",
            "ambiente di test", "messa in produzione", "candidato al rilascio",
            "compilazione",
            # Architettura
            "microservizio", "monolite", "bilanciatore di carico", "latenza",
            "throughput", "perdita di memoria", "corsa critica",
            "tolleranza ai guasti", "scalabilità", "retrocompatibilità",
            "coda di messaggi", "cache", "punto di ingresso", "idempotente",
            # Dati
            "base di dati", "indice", "migrazione", "transazione", "blocco",
            "replica", "partizionamento",
            # Esercizio
            "monitoraggio", "registrazione eventi", "tracciabilità",
            "metriche", "test unitario", "test di integrazione",
            "copertura dei test", "test di carico",
            # Strumenti e processi scritti in inglese
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
            # Contabilità
            "debiti verso fornitori", "crediti verso clienti", "ratei e risconti",
            "ammortamento", "stato patrimoniale", "conto economico",
            "rendiconto finanziario", "libro mastro", "margine lordo",
            "margine netto", "costi operativi", "riconciliazione bancaria",
            "accantonamento", "bilancio d'esercizio", "fattura",
            "esercizio fiscale", "prima nota",
            # Indicatori
            "capitale circolante", "flusso di cassa", "flusso di cassa libero",
            "redditività", "punto di pareggio", "liquidità", "solvibilità",
            "leva finanziaria", "tasso di attualizzazione",
            "valore attuale netto", "tasso interno di rendimento",
            "EBITDA", "CAPEX", "OPEX", "ROI",
            # Operazioni / capitale
            "capitale sociale", "aumento di capitale", "diluizione",
            "valutazione d'azienda", "round di finanziamento",
            "patto parasociale", "due diligence", "dividendi", "copertura",
            "deposito a garanzia",
            # Fiscale / regolamentare
            "IVA", "IRES", "IRAP", "revisione legale dei conti", "IFRS",
            "principi contabili", "dichiarazione dei redditi",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("capex", "CAPEX"),
            ("opex", "OPEX"),
            ("roi", "ROI"),
            ("iva", "IVA"),
            ("ires", "IRES"),
            ("irap", "IRAP"),
        ],
        note="Fiscalità italiana: IVA, IRES, IRAP.",
    ),
    "sales": PackContent(
        terms=[
            # Imbuto
            "potenziale cliente", "opportunità", "imbuto di vendita",
            "fase della trattativa", "primo contatto", "chiamata a freddo",
            "proposta commerciale", "preventivo", "dimostrazione",
            "prova di fattibilità", "progetto pilota", "trattativa",
            "chiusura", "ciclo di vendita", "previsione di vendita",
            "obiettivo di vendita", "tasso di conversione", "scontrino medio",
            # Relazione con il cliente
            "obiezione", "gestione delle obiezioni", "decisore",
            "referente", "punto critico", "proposta di valore",
            "vendita aggiuntiva", "vendita incrociata", "rinnovo",
            "fidelizzazione", "tasso di abbandono", "portafoglio clienti",
            "punto di contatto", "sollecito commerciale", "attivazione cliente",
            # Termini
            "CRM", "KPI", "NPS", "ordine d'acquisto", "contratto quadro",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
