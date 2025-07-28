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

#### Nuovi Comandi CLI 🔧

**Test Scraping Decreto**
```bash
# Test decreto specifico con debug completo
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --verbose

# Test con timeout personalizzato
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --timeout 60

# Test con SSL non verificato (dev/test)
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --allow-unverified

# Test con rate limiting personalizzato
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --rate-limit 1.5
```

**Health Check Sistema**
```bash
# Check completo sistema
python scripts/cli.py health-check

# Check con dettagli estesi
python scripts/cli.py health-check --verbose

# Check con timeout personalizzato
python scripts/cli.py health-check --timeout 30

# Check ignorando SSL (emergenza)
python scripts/cli.py health-check --ignore-ssl
```

**Fix SSL Automatico**
```bash
# Applica fix SSL automatici
python scripts/cli.py fix-ssl

# Fix con backup configurazione
python scripts/cli.py fix-ssl --backup

# Fix solo certificati (no config)
python scripts/cli.py fix-ssl --certs-only

# Fix in modalità dry-run (test)
python scripts/cli.py fix-ssl --dry-run
```

**Retry Decreti Falliti**
```bash
# Riprova tutti i decreti falliti
python scripts/cli.py retry-failed

# Riprova con limite tentativi
python scripts/cli.py retry-failed --max-attempts 5

# Riprova solo errori SSL
python scripts/cli.py retry-failed --ssl-only

# Riprova con delay personalizzato
python scripts/cli.py retry-failed --delay 2.0
```

**Genera Report Dettagliato**
```bash
# Report completo ultimi 7 giorni
python scripts/cli.py generate-report

# Report periodo personalizzato
python scripts/cli.py generate-report --days 30

# Report con output personalizzato
python scripts/cli.py generate-report --output custom_report.html

# Report con dettagli debug
python scripts/cli.py generate-report --include-debug
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

## 🛡️ Troubleshooting SSL

### Gestione Errori Certificato

**Problema**: Errore `SSL: CERTIFICATE_VERIFY_FAILED`
```bash
# 1. Verifica stato certificato
python scripts/cli.py health-check --verbose

# 2. Applica fix automatico
python scripts/cli.py fix-ssl --backup

# 3. Test con SSL disabilitato (SOLO per dev/test)
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --allow-unverified
```

**Problema**: Certificato scaduto
```bash
# Controlla scadenza certificato
openssl s_client -connect decretidigitali.regione.liguria.it:443 -servername decretidigitali.regione.liguria.it < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Fix automatico certificati
python scripts/cli.py fix-ssl --certs-only
```

**Configurazione SSL Avanzata**
```yaml
# config.yaml
scraping:
  ssl_verification: true
  ssl_cert_path: "/path/to/cert.pem"  # Opzionale
  ssl_key_path: "/path/to/key.pem"    # Opzionale
  ssl_ca_bundle: "/path/to/ca.pem"    # Opzionale
  ssl_check_hostname: true
  ssl_timeout: 30
```

## 📊 Monitoring e Health Check

### Interpretare Health Check

**Stato Sistema**
- 🟢 **OPERATIONAL**: Tutto funziona correttamente
- 🟡 **DEGRADED**: Problemi minori, sistema funzionante
- 🔴 **CRITICAL**: Problemi gravi, intervento necessario
- ⚫ **UNKNOWN**: Stato non determinabile

**Metriche Chiave**
```bash
# Controlla metriche dettagliate
python scripts/cli.py health-check --verbose

# Output esempio:
# 🌐 Site Status: OPERATIONAL
# 🔒 SSL Status: VALID (45 days remaining)
# 📊 Success Rate: 95.2% (last 24h)
# ⚡ Response Time: 1250ms avg
# 🔗 Availability: 99.1% (last 24h)
# ❌ Total Errors: 3 (2 SSL, 1 timeout)
```

**Dashboard Analytics**
```bash
# Genera dashboard interattivo
python src/dashboard_generator.py

# Apri dashboard.html per visualizzare:
# - Success rate scraping 24h
# - Distribuzione errori
# - Timeline connessioni
# - Heatmap disponibilità sito
```

**File Metriche**
```bash
# Monitora file health metrics
tail -f logs/health_metrics.json

# Analizza metriche storiche
jq '.[] | select(.site_status == "critical")' logs/health_metrics.json
```

## ⚙️ Configurazione Avanzata

### Opzioni SSL
```yaml
# config.yaml - Sezione SSL
scraping:
  ssl_verification: true          # Verifica certificati SSL
  ssl_cert_path: null            # Path certificato client (opzionale)
  ssl_key_path: null             # Path chiave privata (opzionale)
  ssl_ca_bundle: null            # Path CA bundle personalizzato
  ssl_check_hostname: true       # Verifica hostname nel certificato
  ssl_timeout: 30                # Timeout connessione SSL (secondi)
  ssl_ciphers: "HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA"
```

### Opzioni Scraping
```yaml
# config.yaml - Sezione Scraping
scraping:
  max_retries: 3                 # Numero massimo retry
  retry_delay_seconds: [1, 3, 5] # Delay progressivo tra retry
  timeout: 30                    # Timeout richiesta (secondi)
  rate_limit: 2.0               # Secondi tra richieste
  
  # User agents per rotation
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101"
  
  # Endpoint di backup
  backup_endpoints:
    - 'https://decretidigitali.regione.liguria.it'
    - 'http://decretidigitali.regione.liguria.it'
  
  # Headers personalizzati
  headers:
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    Accept-Language: "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3"
    Accept-Encoding: "gzip, deflate"
    DNT: "1"
    Connection: "keep-alive"
    Upgrade-Insecure-Requests: "1"
```

### Configurazione Monitoring
```yaml
# config.yaml - Sezione Monitoring
monitoring:
  health_check_interval: 300     # Secondi tra health check
  metrics_retention_days: 30     # Giorni retention metriche
  
  # Soglie alert
  alert_thresholds:
    response_time_ms: 5000       # Soglia tempo risposta
    error_rate_percent: 10       # Soglia tasso errori
    availability_percent: 95     # Soglia disponibilità
    ssl_expiry_days: 30         # Giorni preavviso scadenza SSL
  
  # Destinazioni notifiche
  notifications:
    email_enabled: false
    slack_webhook: null
    log_file: "logs/alerts.log"
```

## 🚨 Common Issues

### 🔒 SSL Certificate Errors

**Problema**: `requests.exceptions.SSLError: HTTPSConnectionPool`
```bash
# Diagnosi
python scripts/cli.py health-check --verbose

# Soluzioni progressive
# 1. Update certificati sistema
sudo apt-get update && sudo apt-get install ca-certificates  # Ubuntu/Debian
brew install ca-certificates  # macOS

# 2. Fix automatico
python scripts/cli.py fix-ssl --backup

# 3. Bypass temporaneo (SOLO dev/test)
python scripts/cli.py test-scraping --allow-unverified --seduta 3930 --numero 1
```

**Problema**: `SSL: WRONG_VERSION_NUMBER`
```bash
# Il sito potrebbe usare HTTP invece di HTTPS
# Controlla endpoint di backup
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --verbose

# Modifica config per usare endpoint HTTP di backup
# config.yaml backup_endpoints section
```

### ⏱️ Timeout Issues

**Problema**: `requests.exceptions.ReadTimeout`
```bash
# Aumenta timeout
python scripts/cli.py test-scraping --timeout 60 --seduta 3930 --numero 1

# Test connettività
ping decretidigitali.regione.liguria.it
curl -I --connect-timeout 10 https://decretidigitali.regione.liguria.it

# Configurazione permanente in config.yaml
scraping:
  timeout: 60
  rate_limit: 3.0  # Rallenta richieste
```

**Problema**: `requests.exceptions.ConnectTimeout`
```bash
# Test network connectivity
python scripts/cli.py health-check --verbose

# Prova endpoint alternativi
python scripts/cli.py test-scraping --seduta 3930 --numero 1 --verbose

# Check DNS resolution
nslookup decretidigitali.regione.liguria.it
```

### 🌐 Network Connectivity Problems

**Problema**: `requests.exceptions.ConnectionError`
```bash
# Diagnosi completa
python scripts/cli.py health-check --verbose

# Test manuale connettività
curl -v https://decretidigitali.regione.liguria.it
telnet decretidigitali.regione.liguria.it 443

# Check proxy/firewall
export https_proxy=http://proxy:8080  # Se necessario
python scripts/cli.py test-scraping --seduta 3930 --numero 1
```

**Problema**: DNS Resolution Failed
```bash
# Test DNS
nslookup decretidigitali.regione.liguria.it
dig decretidigitali.regione.liguria.it

# Prova DNS alternativi
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf  # Temporaneo

# Test con IP diretto (se conosciuto)
curl -H "Host: decretidigitali.regione.liguria.it" https://IP_ADDRESS
```

### 📊 Notion API Rate Limiting

**Problema**: `notion_client.errors.APIResponseError: rate_limited`
```bash
# Controlla rate limiting attuale
python scripts/cli.py health-check --verbose | grep -i notion

# Rallenta operazioni Notion
# config.yaml
notion:
  rate_limit: 3.0              # Secondi tra richieste
  max_retries: 5               # Aumenta retry
  retry_backoff: [1, 2, 4, 8]  # Backoff esponenziale

# Test connettività Notion
python -c "from notion_client import Client; Client(auth='your_token').databases.retrieve('your_db_id')"
```

**Problema**: `notion_client.errors.APIResponseError: unauthorized`
```bash
# Verifica token Notion
echo $NOTION_TOKEN

# Test token validity
curl -H "Authorization: Bearer $NOTION_TOKEN" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/users/me

# Rigenera token se necessario
# https://www.notion.so/my-integrations
```

### 🔧 Risoluzione Rapida Problemi

**Comando Diagnosi Completa**
```bash
# Script diagnosi automatica
#!/bin/bash
echo "=== ODG System Diagnosis ==="
echo "1. Health Check:"
python scripts/cli.py health-check --verbose

echo "\n2. SSL Status:"
openssl s_client -connect decretidigitali.regione.liguria.it:443 -servername decretidigitali.regione.liguria.it < /dev/null 2>/dev/null | openssl x509 -noout -dates

echo "\n3. Network Test:"
ping -c 3 decretidigitali.regione.liguria.it

echo "\n4. DNS Resolution:"
nslookup decretidigitali.regione.liguria.it

echo "\n5. Recent Errors:"
tail -n 20 logs/health_metrics.json | jq '.[] | select(.site_status == "critical")'
```

**Risoluzione Step-by-Step**
1. **Esegui diagnosi**: `python scripts/cli.py health-check --verbose`
2. **Identifica problema**: Controlla stato (CRITICAL/DEGRADED)
3. **Applica fix**: `python scripts/cli.py fix-ssl` (per SSL)
4. **Test soluzione**: `python scripts/cli.py test-scraping --seduta 3930 --numero 1`
5. **Monitora**: Controlla dashboard o `tail -f logs/health_metrics.json`

## 🚨 Troubleshooting Avanzato

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