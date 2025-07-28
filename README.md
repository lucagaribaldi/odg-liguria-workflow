# ODG Liguria Enhanced Workflow 🚀

Sistema completo ed avanzato per l'elaborazione automatica dei documenti ODG (Ordine del Giorno) della Regione Liguria con integrazione Notion, verifica pubblicazione decreti e funzionalità di sicurezza avanzate.

## ✨ Caratteristiche Principali

- 📄 **Parsing automatico PDF**: Estrazione intelligente delle deliberazioni
- 🛡️ **Sistema di validazione avanzato**: Protezione contro attacchi di injection
- 🔍 **Decreto Scraping Potenziato**: Verifica stato pubblicazione con retry automatico
- 📊 **Integrazione Notion**: Sincronizzazione con database Notion con anti-duplicati
- 🚫 **Sistema di sicurezza**: Validazione e sanitizzazione degli input
- 📈 **Monitoraggio performance**: Metriche dettagliate e reporting
- 🐛 **Debug avanzato**: Sistema di troubleshooting completo
- 💾 **Backup automatico**: Salvataggio sicuro dei risultati
- 🔧 **Configurabile**: Configurazione per ambiente (prod/dev/test)

## 🏗️ Architettura

```
📄 PDF → 🔍 Parsing → 🛡️ Validation → 📊 Notion → 🔍 Enhanced Scraping → 💾 Backup
```

### Componenti Potenziati

- **Enhanced PDF Parser**: Estrae deliberazioni da PDF ODG con validazione
- **Enhanced Decreto Scraper**: Verifica pubblicazione con sistema di retry e performance tracking
- **Notion Integrator**: Sincronizzazione con anti-duplicati e error recovery
- **Validation System**: Protezione contro regex injection e input malformi
- **Error Reporting**: Sistema completo di analisi e reportistica errori
- **Performance Tracker**: Monitoraggio dettagliato delle performance

## 🚀 Quick Start

### Installazione

```bash
# Clona repository
git clone [repo-url]
cd odg-liguria-workflow

# Installa dipendenze
pip install -r requirements.txt

# Configura ambiente
cp .env.example .env
# Modifica .env con i tuoi dati Notion
```

### Configurazione

#### Notion Setup
```bash
# Aggiungi al file .env
NOTION_TOKEN="your_notion_token"
NOTION_DATABASE_ID="your_database_id"
```

#### Configurazione Avanzata
```bash
# Usa la configurazione enhanced per produzione
cp config_enhanced.yaml config.yaml
# Modifica config.yaml per le tue esigenze
```

### Utilizzo

#### Workflow Principale (Enhanced)
```bash
# Elabora tutti i PDF con funzionalità avanzate
python3 main_workflow.py

# Elabora un PDF specifico
python3 main_workflow.py --pdf-file ODG_03072025.pdf

# Modalità debug avanzato
python3 main_workflow.py --debug

# Modalità test (no modifiche)
python3 main_workflow.py --dry-run
```

#### Test e Validazione
```bash
# Test integrazione completa
python3 tests/integration/test_enhanced_workflow.py

# Test solo validazione (veloce)
python3 tests/integration/test_validation_only.py

# Test con database Notion reale
python3 tests/integration/decreto_scraper/test_notion_final.py
```

## 🛡️ Caratteristiche di Sicurezza

### Sistema di Validazione
- **Input Sanitization**: Escape automatico di caratteri pericolosi per regex
- **Field Length Validation**: Controllo lunghezza massima dei campi
- **Empty Field Detection**: Rilevamento campi obbligatori vuoti
- **Character Filtering**: Rimozione caratteri di controllo

### Esempio di Validazione
```python
# Input potenzialmente pericoloso
seduta = "3929+malicious"
numero = "17*injection"

# Sistema automatico di sanitizzazione
validated_seduta = "3929\\+malicious"  # Carattere + escapato
validated_numero = "17\\*injection"    # Carattere * escapato
```

### Protezioni di Rete
- **SSL Verification**: Verifica certificati SSL in produzione
- **Rate Limiting**: Controllo velocità richieste (2 sec. tra richieste)
- **Request Timeout**: Timeout configurabile (30 sec. default)
- **Retry Logic**: Retry automatico con backoff

## 📊 Sistema di Monitoraggio

### Metriche Performance
```bash
# Il sistema traccia automaticamente:
- Tempo di elaborazione per operazione
- Tasso di successo/fallimento
- Numero di retry per richiesta
- Statistiche di validazione input
- Tempo di risposta rete
```

### Error Reporting
```python
# Accesso ai report di errore
scraper = DecretoScraper(debug_mode=True)
error_reports = scraper.get_error_reports()

for report in error_reports:
    print(f"Error: {report.error_type}")
    print(f"Message: {report.error_message}")
    print(f"Suggestions: {report.suggestions}")
```

### Debug Reports
Il sistema genera automaticamente report debug in formato JSON con:
- Informazioni sessione
- Statistiche performance
- Log completi delle operazioni
- Tracce di debugging dettagliate

## 🗂️ Struttura Ottimizzata

```
odg-liguria-workflow/
├── src/                              # 🎯 Codice sorgente
│   ├── decreto_scraper.py           # Enhanced decreto scraper
│   ├── notion_integrator.py         # Integrazione Notion
│   ├── pdf_parser.py                # PDF parsing
│   ├── workflow_orchestrator.py     # Orchestratore workflow
│   └── ai_synthesizer.py            # Sintesi AI
├── tests/                           # 🧪 Test organizzati
│   ├── unit/                        # Test unitari
│   ├── integration/                 # Test integrazione
│   └── examples/                    # Esempi e demo
├── docs/                            # 📚 Documentazione
│   ├── guides/                      # Guide utente
│   └── reports/                     # Report tecnici
├── data/
│   ├── input/                       # 📥 PDF da elaborare
│   └── backups/                     # 💾 Backup automatici
├── logs/                            # 📝 File di log
├── config_enhanced.yaml             # ⚙️ Configurazione produzione
├── main_workflow.py                 # 🚀 Workflow principale
└── process_pdf.py                   # 📄 Processing PDF
```

## 📈 Risultati Test Recenti

### Test Completati ✅

**Test Integrazione Enhanced (2025-07-24)**
- ✅ **Validation Tests**: 4 test cases - 3 successi, 1 errore catturato
- ✅ **Input Sanitization**: Funziona correttamente (+ e * escapati)
- ✅ **Error Detection**: Sistema rileva campi vuoti
- ✅ **Notion Integration**: 51 pagine elaborate, 15 deliberazioni testate
- ✅ **Performance Tracking**: Metriche operative raccolte
- ✅ **Debug Reports**: Generazione automatica report funzionante

**Statistiche Performance**
```
📊 Database Notion: 51 pagine totali
🎯 Deliberazioni testate: 15 (100% successo)
🛡️ Validazione applicata: 15/15 (100%)
🔧 Sanitizzazione applicata: 2/15 (quando necessario)
⚡ Tempo elaborazione: < 1 secondo per deliberazione
🚨 Errori catturati e gestiti: 0 (sistema robusto)
```

## 🔧 Configurazione Avanzata

### Environment Settings
```yaml
# config_enhanced.yaml
environments:
  production:
    decreto_scraper:
      debug_mode: false
      log_level: "WARN"
      verify_ssl: true
      rate_limit: 2.0
  
  development:
    decreto_scraper:
      debug_mode: true
      log_level: "DEBUG"
      verify_ssl: false
      rate_limit: 0.5
```

### Validation Settings
```yaml
decreto_scraper:
  validation:
    strict_mode: true
    sanitize_regex: true
    max_field_lengths:
      seduta: 50
      numero: 50
      oggetto: 1000
```

## 🚨 Troubleshooting

### Debug Mode
```bash
# Attiva debug completo
python3 main_workflow.py --debug

# I log dettagliati sono in:
# - logs/workflow_YYYYMMDD_HHMMSS.log
# - logs/decreto_scraper_YYYYMMDD_HHMMSS.log
```

### Validation Errors
Se ricevi errori di validazione:
1. Controlla la qualità dei dati di input
2. Verifica i limiti di lunghezza campi
3. Esamina il report di errore per suggerimenti
4. Usa il debug mode per analisi dettagliata

### Network Issues
```bash
# Test connettività
python3 -c "import requests; print(requests.get('https://decretidigitali.regione.liguria.it').status_code)"

# Se SSL problemi in dev:
# Imposta verify_ssl: false in config
```

## 📚 Documentazione Completa

- 📖 **[Guida Enhanced Features](docs/guides/ENHANCED_FEATURES_DOCUMENTATION.md)** - Documentazione completa funzionalità avanzate
- 📋 **[Workflow Documentation](docs/guides/WORKFLOW_DOCUMENTATION.md)** - Guida workflow completo
- 📊 **[Reports Tecnici](docs/reports/)** - Report implementazione e test
- 🧪 **[Test Examples](tests/examples/)** - Esempi di utilizzo

## 🎯 Stato Attuale

### ✅ Completato e Testato
- [x] **Enhanced Decreto Scraper** - Sistema completo con validazione e sicurezza
- [x] **Input Validation & Sanitization** - Protezione contro injection attacks
- [x] **Performance Tracking** - Monitoraggio dettagliato performance
- [x] **Error Reporting System** - Sistema completo gestione errori
- [x] **Debug Mode** - Troubleshooting avanzato con session tracking
- [x] **Notion Integration** - Integrazione testata con database reale
- [x] **Production Configuration** - Configurazione per ambienti diversi
- [x] **Comprehensive Testing** - Suite test completa con esempi reali

### 🔄 Caratteristiche Uniche
- **Context Managers**: Gestione automatica risorse con cleanup
- **Session Tracking**: Ogni operazione tracciata con ID univoco
- **Configurable Logging**: 6 livelli di log (SILENT → TRACE)
- **Multi-Strategy Search**: 4 strategie di ricerca per decreti
- **Automatic Retry**: Retry intelligente con backoff exponential
- **SSL Flexibility**: Supporto SSL configurabile per ambienti diversi

## 🔐 Best Practices Sicurezza

1. **Sempre usare validazione**: Non bypassare mai il sistema di validazione
2. **SSL in produzione**: Sempre `verify_ssl: true` in produzione
3. **Rate limiting**: Rispettare i limiti per essere "good citizens"
4. **Monitor error reports**: Controllare regolarmente i report di errore
5. **Debug mode solo in dev**: Non usare debug mode in produzione
6. **Configurazioni separate**: Mantenere config separate per ambienti

## 🤝 Versioning

**Versione**: 2.0.0 Enhanced  
**Ultima modifica**: 2025-07-24  
**Status**: ✅ Production Ready + Enhanced Security  

### Changelog v2.0.0
- ➕ Sistema validazione e sanitizzazione input
- ➕ Error reporting con suggerimenti automatici
- ➕ Performance tracking dettagliato
- ➕ Debug mode con session tracking
- ➕ Configurazione multi-ambiente
- ➕ Context manager support
- ➕ Custom exception hierarchy
- ➕ Enhanced logging system
- 🔧 Workflow integration completa
- 🔧 Test suite estesa con Notion reale
- 📚 Documentazione completa

---

**Powered by**: Enhanced Decreto Scraper v2.0 con funzionalità enterprise  
**Sicurezza**: Input validation + sanitization + SSL + rate limiting  
**Performance**: Tracking completo + retry logic + session management  
**Debug**: Comprehensive logging + error reporting + troubleshooting tools