# ODG Liguria Workflow - Documentazione Completa

## 🎯 Panoramica

Il **ODG Liguria Workflow** è un sistema completo per l'elaborazione automatica dei documenti ODG (Ordine del Giorno) della Regione Liguria. Il sistema gestisce l'intero ciclo di vita dall'elaborazione dei PDF fino alla sincronizzazione con Notion e la verifica della pubblicazione dei decreti.

## 🏗️ Architettura del Sistema

### Componenti Principali

1. **PDF Parser** (`src/pdf_parser.py`)
   - Estrae deliberazioni dai file PDF ODG
   - Identifica informazioni di sessione (numero, data)
   - Supporta il formato standardizzato ODG

2. **Notion Integrator** (`src/notion_integrator.py`)
   - Sincronizza i dati con il database Notion
   - Implementa logica anti-duplicati basata su `seduta+numero`
   - Gestisce il mapping dei campi e la categorizzazione

3. **Decreto Scraper** (`src/decreto_scraper.py`)
   - Verifica lo stato di pubblicazione dei decreti
   - Utilizza multiple strategie di ricerca
   - Gestisce SSL e rate limiting

4. **AI Synthesizer** (`src/ai_synthesizer.py`)
   - Genera riassunti intelligenti delle deliberazioni
   - Estrae informazioni strutturate (budget, stakeholder, urgenza)
   - Categorizza automaticamente le deliberazioni

## 🚀 Flusso di Lavoro

### Workflow Principale

```
📄 PDF Input → 🔍 Parsing → 🤖 AI Synthesis → 📊 Notion Sync → 🔍 Decreto Scraping → 💾 Backup
```

### Passaggi Dettagliati

1. **Parsing PDF**
   - Estrazione del testo dal PDF
   - Identificazione delle deliberazioni
   - Estrazione di metadati (seduta, data, numero)

2. **Sintesi AI**
   - Generazione di riassunti rapidi
   - Categorizzazione automatica
   - Estrazione di informazioni chiave

3. **Sincronizzazione Notion**
   - Controllo anti-duplicati
   - Creazione/aggiornamento record
   - Mapping dei campi

4. **Scraping Decreti**
   - Ricerca sui siti ufficiali
   - Verifica stato di pubblicazione
   - Estrazione di URL e metadati

5. **Backup**
   - Salvataggio automatico dei risultati
   - Storicizzazione delle operazioni

## 📋 Script Disponibili

### 1. Workflow Principale
```bash
python3 main_workflow.py [options]
```

**Opzioni:**
- `--pdf-file FILE`: Elabora un PDF specifico
- `--skip-scraping`: Salta la ricerca dei decreti
- `--dry-run`: Modalità test senza elaborazione
- `--debug`: Abilita logging dettagliato

**Esempi:**
```bash
# Elabora tutti i PDF
python3 main_workflow.py

# Elabora un PDF specifico
python3 main_workflow.py --pdf-file ODG_03072025.pdf

# Test senza elaborazione
python3 main_workflow.py --dry-run
```

### 2. Monitoraggio PDF
```bash
python3 monitor_pdfs.py [options]
```

**Opzioni:**
- `--daemon`: Esecuzione continua
- `--check-only`: Solo controllo, senza elaborazione
- `--interval N`: Intervallo di polling (secondi)

**Esempi:**
```bash
# Controllo one-time
python3 monitor_pdfs.py

# Modalità daemon
python3 monitor_pdfs.py --daemon --interval 300

# Solo controllo
python3 monitor_pdfs.py --check-only
```

### 3. Elaborazione Batch
```bash
python3 batch_process_pdfs.py
```

Elabora tutti i PDF nella cartella input con sistema anti-duplicati.

## 🗂️ Struttura Directory

```
odg-liguria-workflow/
├── src/                          # Codice sorgente
│   ├── pdf_parser.py            # Parser PDF
│   ├── notion_integrator.py     # Integrazione Notion
│   ├── decreto_scraper.py       # Scraper decreti
│   └── ai_synthesizer.py        # Sintesi AI
├── data/
│   ├── input/                   # PDF da elaborare
│   ├── output/                  # Risultati elaborazione
│   └── backups/                 # Backup automatici
├── logs/                        # File di log
├── main_workflow.py             # Workflow principale
├── monitor_pdfs.py              # Monitoraggio PDF
├── batch_process_pdfs.py        # Elaborazione batch
└── README.md                    # Documentazione
```

## ⚙️ Configurazione

### Variabili d'Ambiente

```bash
# Credenziali Notion (obbligatorie per sync)
export NOTION_TOKEN="your_notion_token"
export NOTION_DATABASE_ID="your_database_id"

# Configurazioni opzionali
export LOG_LEVEL="INFO"
export BACKUP_ENABLED="true"
```

### File di Configurazione

- `.env`: Variabili d'ambiente
- `config.yaml`: Configurazione dettagliata
- `requirements.txt`: Dipendenze Python

## 🛠️ Installazione

### Prerequisiti
- Python 3.8+
- pip
- Accesso al database Notion

### Installazione Dipendenze
```bash
pip install -r requirements.txt
```

### Setup Ambiente
```bash
# Copia file di configurazione
cp .env.example .env
cp config.yaml.example config.yaml

# Modifica con i tuoi dati
nano .env
```

## 📊 Database Notion

### Schema Campi

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `Seduta` | Number | Numero di seduta |
| `Numero` | Number | Numero deliberazione |
| `Titolo` | Rich Text | Tipo atto (es. Deliberazione) |
| `Oggetto` | Rich Text | Oggetto della deliberazione |
| `Proponente` | Rich Text | Proponente |
| `FS` | Checkbox | Flag Fuori Sacco |
| `Pubblicato` | Select | Stato pubblicazione (Non Controllato/Non Pubblicato/Pubblicato) |
| `Data_Seduta` | Date | Data della seduta |
| `URL_Decreto` | URL | Link al decreto pubblicato |
| `Sintesi_Rapida` | Rich Text | Riassunto generato da AI |

### Campi Auto-generati

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `Budget Alto` | Checkbox | Flag budget elevato |
| `Urgente` | Checkbox | Flag urgenza |
| `Governance` | Checkbox | Flag governance |
| `Sanità` | Checkbox | Flag sanità |
| `Ambiente` | Checkbox | Flag ambiente |
| `Sociale` | Checkbox | Flag sociale |
| `Personale` | Checkbox | Flag personale |

## 🔍 Sistema Anti-Duplicati

### Logica di Identificazione

Il sistema utilizza una chiave composta `seduta+numero` per identificare univocamente ogni deliberazione:

```python
# Esempio di controllo duplicati
def is_duplicate(deliberation, existing_pages):
    seduta = deliberation.get('seduta')
    numero = deliberation.get('numero')
    
    return any(
        page.seduta == seduta and page.numero == numero
        for page in existing_pages
    )
```

### Comportamento

- **Prima esecuzione**: Crea tutti i record
- **Esecuzioni successive**: Salta i duplicati esistenti
- **File modificati**: Rileva modifiche tramite hash MD5

## 🤖 AI Synthesis

### Funzionalità

1. **Riassunti Automatici**
   - Genera riassunti di 50 caratteri
   - Estrae parole chiave principali
   - Identifica il tipo di atto

2. **Categorizzazione**
   - Sanità, Bilanci, Governance
   - Ambiente, Sociale, Altro
   - Basata su pattern testuali

3. **Analisi Urgenza**
   - Analizza flag FS (Fuori Sacco)
   - Rileva termini di urgenza
   - Classifica: Alta/Normale/Bassa

### Configurazione

```python
# Abilita AI (quando disponibile)
synthesizer = AISynthesizer(use_ai=True)

# Modalità rule-based (predefinita)
synthesizer = AISynthesizer(use_ai=False)
```

## 🔍 Decreto Scraping

### Strategie di Ricerca

1. **Ricerca per Numero e Data**
2. **Ricerca per Oggetto e Data**
3. **Ricerca per Seduta e Numero**
4. **Ricerca per Solo Numero** (fallback)

### Configurazione

```python
scraper = DecretoScraper(
    base_url="https://decretidigitali.regione.liguria.it",
    rate_limit=1.0,  # Secondi tra richieste
    max_retries=3,
    verify_ssl=False  # Per problemi certificati
)
```

## 📈 Monitoraggio e Logging

### Livelli di Log

- **DEBUG**: Dettagli tecnici
- **INFO**: Operazioni principali
- **WARNING**: Situazioni anomale
- **ERROR**: Errori che richiedono attenzione

### File di Log

```
logs/
├── workflow_YYYYMMDD_HHMMSS.log    # Workflow principale
├── monitor_YYYYMMDD_HHMMSS.log     # Monitoraggio PDF
└── batch_process.log               # Elaborazione batch
```

### Metriche

Il sistema traccia diverse metriche:

```python
session_stats = {
    "files_processed": 0,
    "files_failed": 0,
    "total_deliberations": 0,
    "notion_created": 0,
    "notion_duplicates": 0,
    "decreti_found": 0,
    "scraping_errors": 0
}
```

## 🚨 Gestione Errori

### Errori Comuni

1. **SSL Certificate Error**
   - Causa: Problemi certificati sito ufficiale
   - Soluzione: Usare `verify_ssl=False`

2. **Rate Limiting**
   - Causa: Troppe richieste al sito
   - Soluzione: Aumentare `rate_limit`

3. **Notion Authentication**
   - Causa: Token non valido
   - Soluzione: Verificare `NOTION_TOKEN`

4. **PDF Parsing Error**
   - Causa: Formato PDF non supportato
   - Soluzione: Verificare struttura PDF

### Strategie di Recovery

1. **Retry con Backoff Esponenziale**
2. **Graceful Degradation**
3. **Backup Automatico**
4. **Logging Dettagliato**

## 🔄 Manutenzione

### Operazioni Periodiche

1. **Pulizia Log**
   ```bash
   find logs/ -name "*.log" -mtime +30 -delete
   ```

2. **Backup Database**
   ```bash
   # I backup sono automatici in data/backups/
   ```

3. **Aggiornamento Dipendenze**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

### Monitoraggio Salute Sistema

```bash
# Verifica stato componenti
python3 -c "
from src.pdf_parser import ODGPDFParser
from src.notion_integrator import NotionIntegrator
print('Sistema operativo')
"
```

## 📝 Esempi d'Uso

### Scenario 1: Elaborazione Nuovi PDF

```bash
# 1. Posiziona i PDF in data/input/
cp ODG_*.pdf data/input/

# 2. Esegui il workflow completo
python3 main_workflow.py

# 3. Verifica i risultati
ls data/backups/
```

### Scenario 2: Monitoraggio Continuo

```bash
# Avvia monitoraggio daemon
python3 monitor_pdfs.py --daemon --interval 300

# In un altro terminale, aggiungi PDF
cp new_odg.pdf data/input/

# Il sistema elaborerà automaticamente
```

### Scenario 3: Elaborazione Specifica

```bash
# Elabora solo un PDF specifico
python3 main_workflow.py --pdf-file ODG_03072025.pdf

# Salta lo scraping per velocità
python3 main_workflow.py --skip-scraping

# Test senza modifiche
python3 main_workflow.py --dry-run
```

## 🏁 Risoluzione Problemi

### Problemi Frequenti

1. **"No PDF files found"**
   - Verifica che i PDF siano in `data/input/`
   - Controlla i permessi di lettura

2. **"Notion credentials not found"**
   - Imposta `NOTION_TOKEN` e `NOTION_DATABASE_ID`
   - Verifica validità del token

3. **"SSL Certificate Error"**
   - Aggiungi `--skip-scraping` temporaneamente
   - Configura `verify_ssl=False`

4. **"Rate Limited"**
   - Aumenta `rate_limit` in configurazione
   - Riduci numero di richieste parallele

### Support e Contributi

Per problemi o suggerimenti:

1. Controlla i log in `logs/`
2. Verifica la configurazione
3. Esegui in modalità `--debug`
4. Consulta la documentazione API

---

**Versione**: 1.0.0  
**Ultima modifica**: 2025-07-18  
**Autore**: ODG Liguria Workflow Team