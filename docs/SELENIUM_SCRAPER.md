# SeleniumDecretoScraper - Documentazione Completa

## 🚀 Introduzione

`SeleniumDecretoScraper` è un'implementazione avanzata di browser automation per il sito `decretidigitali.regione.liguria.it` che utilizza **Selenium WebDriver** per gestire siti JavaScript-heavy e form complessi con le seguenti caratteristiche:

- **Simulazione browser reale** con Chrome WebDriver
- **Auto-setup Chrome driver** con webdriver-manager
- **Selezione intelligente dropdown** con fuzzy matching
- **Screenshot debugging** per troubleshooting visuale
- **Form automation** con strategie multiple di interazione
- **Confidence scoring avanzato** per risultati
- **Performance monitoring** e metriche dettagliate

## 🏗️ Architettura

### Componenti Principali

```
SeleniumDecretoScraper
├── Driver Management
│   ├── setup_driver()
│   ├── _configure_chrome_options()
│   └── cleanup()
├── Navigation & Form Interaction
│   ├── navigate_to_search()
│   ├── fill_search_form()
│   ├── smart_dropdown_selection()
│   └── submit_and_wait_results()
├── Result Processing
│   ├── extract_results()
│   ├── _extract_single_result()
│   └── _calculate_confidence_score()
├── Debugging & Monitoring
│   ├── take_screenshot()
│   ├── get_performance_stats()
│   └── _log()
└── Main Workflow
    ├── search_decreto_selenium()
    └── search_decreto_with_params()
```

### Dataclasses

```python
@dataclass
class SearchParameters:
    seduta: str
    numero: str
    oggetto: str
    anno: Optional[str] = None
    data_sottoscrizione: Optional[str] = None
    tipo_atto: Optional[str] = None

@dataclass  
class DropdownOption:
    value: str
    text: str
    index: int
    selected: bool = False

@dataclass
class SeleniumResult:
    title: str
    url: str
    date: Optional[str] = None
    document_type: Optional[str] = None
    number: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 0.0
```

## 🔧 Utilizzo

### Installazione Dipendenze

```bash
# Installa dipendenze richieste
pip install selenium webdriver-manager beautifulsoup4

# Chrome browser deve essere installato nel sistema
```

### Inizializzazione Base

```python
from src.selenium_scraper import SeleniumDecretoScraper, LogLevel

# Configurazione base
scraper = SeleniumDecretoScraper(
    base_url="https://decretidigitali.regione.liguria.it",
    headless=True,          # Modalità headless (senza GUI)
    implicit_wait=10,       # Timeout implicito per elementi
    debug_mode=False,       # Debug disabilitato
    log_level=LogLevel.INFO
)
```

### Utilizzo con Context Manager (Raccomandato)

```python
# Configurazione headless per produzione
with SeleniumDecretoScraper(headless=True) as scraper:
    found, url, confidence = scraper.search_decreto_selenium(
        seduta="3929",
        numero="17", 
        oggetto="Approvazione piano triennale lavori pubblici"
    )
    
    print(f"Trovato: {found}")
    print(f"URL: {url}")  
    print(f"Confidence: {confidence:.2f}")
```

### Configurazione Visual Debug

```python
# Configurazione con browser visibile per debug
with SeleniumDecretoScraper(
    headless=False,        # Browser visibile
    debug_mode=True,       # Screenshot automatici
    implicit_wait=15       # Timeout più lungo
) as scraper:
    
    # Il browser si aprirà visualmente
    found, url, confidence = scraper.search_decreto_selenium(
        seduta="3929",
        numero="17",
        oggetto="Approvazione piano triennale lavori pubblici"
    )
    
    # Screenshot salvati automaticamente in debug/
```

## 🧠 Funzionalità Principali

### 1. Chrome Driver Auto-Setup

```python
def setup_driver(self):
    """
    Auto-download e configurazione Chrome WebDriver:
    - Download automatico driver compatibile
    - Configurazione opzioni Chrome ottimizzate
    - Gestione headless/visual mode
    - Configurazione timeout e window size
    """
    
    # WebDriver Manager scarica automaticamente ChromeDriver
    service = ChromeService(ChromeDriverManager().install())
    
    # Opzioni Chrome ottimizzate
    options = self._configure_chrome_options()
    
    self.driver = webdriver.Chrome(service=service, options=options)
```

### 2. Selezione Intelligente Dropdown

```python
# Estrazione automatica opzioni dropdown
options = scraper.extract_dropdown_options(select_element)

# Selezione intelligente con multiple strategie
success = scraper.smart_dropdown_selection(
    select_element, 
    target_value="2025",
    field_type="anno"
)

# Strategie di matching:
# 1. Exact match per value
# 2. Exact match per text 
# 3. Substring match
# 4. Fuzzy matching (soglia 70%)
```

### 3. Form Automation Avanzata

```python
def fill_search_form(self, search_params: SearchParameters) -> bool:
    """
    Compilazione automatica form con strategie multiple:
    
    1. Rilevamento automatico campi per nome/ID/placeholder
    2. Mapping intelligente parametri → campi form
    3. Selezione dropdown con fuzzy matching
    4. Compilazione campi text/textarea
    5. Gestione campi required vs optional
    """
```

### 4. Screenshot Debugging

```python
# Screenshot automatici in debug mode
if self.debug_mode:
    screenshot_path = scraper.take_screenshot("form_filled")
    print(f"Screenshot salvato: {screenshot_path}")

# Screenshot manuali
screenshot_path = scraper.take_screenshot("custom_debug")
```

### 5. Confidence Scoring Selenium

```python
confidence = scraper._calculate_confidence_score(
    title="Deliberazione n. 17 - Approvazione piano triennale lavori pubblici",
    search_params=search_params,
    date="01/07/2025",
    document_type="Deliberazione",
    number="17"
)

# Algoritmo scoring:
# - Match oggetto: 40%
# - Match numero: 30% 
# - Match tipo documento: 10%
# - Match anno: 10%
# - Fuzzy match complessivo: 10%
```

## 🔍 Workflow Completo

### 1. Setup e Navigazione

```python
def search_decreto_selenium(self, seduta: str, numero: str, oggetto: str, 
                           anno: str = None) -> Tuple[bool, str, float]:
    """
    Workflow completo:
    
    1. Setup Chrome WebDriver con opzioni ottimizzate
    2. Navigazione a pagina di ricerca
    3. Attesa caricamento form
    4. Compilazione automatica campi
    5. Submit form e attesa risultati
    6. Estrazione e parsing risultati
    7. Calcolo confidence score
    8. Cleanup risorse
    """
```

### 2. Gestione Errori Robusta

```python
# Exception hierarchy personalizzata
SeleniumScraperError (base)
├── DriverSetupError        # Errori setup WebDriver
├── NavigationError         # Errori navigazione pagina
├── FormInteractionError    # Errori interazione form
└── ResultExtractionError   # Errori estrazione risultati

# Retry automatico con backoff
for attempt in range(self.max_retries):
    try:
        # Operazione Selenium
        break
    except WebDriverException as e:
        if attempt < self.max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        raise FormInteractionError(f"Failed after {self.max_retries} attempts")
```

### 3. Performance Monitoring

```python
# Metriche automatiche
stats = scraper.get_performance_stats()

print(f"Operazioni totali: {stats['total_operations']}")
print(f"Operazioni riuscite: {stats['successful_operations']}")  
print(f"Operazioni fallite: {stats['failed_operations']}")
print(f"Tasso successo: {stats['success_rate']:.1%}")
print(f"Tempo esecuzione medio: {stats['average_execution_time']:.2f}s")
print(f"Driver attivo: {stats['driver_active']}")
print(f"Modalità headless: {stats['headless_mode']}")
```

## 📋 Esempi di Utilizzo

### Esempio 1: Ricerca Base

```python
#!/usr/bin/env python3

from src.selenium_scraper import SeleniumDecretoScraper

def ricerca_decreto_base():
    """Esempio ricerca decreto base."""
    
    with SeleniumDecretoScraper(headless=True, debug_mode=False) as scraper:
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929",
            numero="17",
            oggetto="Approvazione piano triennale lavori pubblici"
        )
        
        if found:
            print(f"✅ Decreto trovato!")
            print(f"URL: {url}")
            print(f"Confidence: {confidence:.2f}")
        else:
            print("❌ Decreto non trovato")

if __name__ == "__main__":
    ricerca_decreto_base()
```

### Esempio 2: Debug Visuale

```python
def debug_ricerca_decreto():
    """Esempio con debug visuale."""
    
    # Browser visibile + screenshot automatici
    with SeleniumDecretoScraper(
        headless=False,           # Browser visibile
        debug_mode=True,          # Screenshot automatici
        implicit_wait=15,         # Timeout generoso
        log_level=LogLevel.DEBUG  # Log dettagliato
    ) as scraper:
        
        print("🔍 Avvio ricerca con debug visuale...")
        
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929", 
            numero="17",
            oggetto="Approvazione piano triennale lavori pubblici"
        )
        
        print(f"Risultato: Found={found}, Confidence={confidence:.2f}")
        
        # Screenshot manuali aggiuntivi
        scraper.take_screenshot("risultato_finale")
        
        # Statistiche dettagliate
        stats = scraper.get_performance_stats()
        print(f"Stats: {stats}")

if __name__ == "__main__":
    debug_ricerca_decreto()
```

### Esempio 3: Ricerche Multiple

```python
def ricerche_multiple():
    """Esempio ricerche multiple con stesso scraper."""
    
    test_cases = [
        {
            "seduta": "3929",
            "numero": "17", 
            "oggetto": "Approvazione piano triennale lavori pubblici"
        },
        {
            "seduta": "3930",
            "numero": "5",
            "oggetto": "Regolamento comunale parcheggi"
        },
        {
            "seduta": "3931", 
            "numero": "12",
            "oggetto": "Autorizzazione spesa manutenzione strade"
        }
    ]
    
    with SeleniumDecretoScraper(headless=True) as scraper:
        risultati = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {case['oggetto'][:40]}...")
            
            found, url, confidence = scraper.search_decreto_selenium(**case)
            
            risultati.append({
                'case': case,
                'found': found,
                'url': url, 
                'confidence': confidence
            })
            
            print(f"  Risultato: {found} (confidence: {confidence:.2f})")
        
        # Statistiche finali
        stats = scraper.get_performance_stats()
        print(f"\n📊 Statistiche finali:")
        print(f"  Operazioni: {stats['total_operations']}")
        print(f"  Successi: {stats['successful_operations']}")
        print(f"  Tasso successo: {stats['success_rate']:.1%}")

if __name__ == "__main__":
    ricerche_multiple()
```

### Esempio 4: Configurazione Produzione

```python
def setup_produzione():
    """Configurazione ottimizzata per produzione."""
    
    scraper = SeleniumDecretoScraper(
        base_url="https://decretidigitali.regione.liguria.it",
        headless=True,              # Sempre headless in produzione
        implicit_wait=10,           # Timeout ragionevole
        debug_mode=False,           # Debug disabilitato per performance
        log_level=LogLevel.WARN,    # Solo warning ed errori
        max_retries=3               # Retry moderati
    )
    
    return scraper

def produzione_workflow():
    """Workflow di produzione con error handling."""
    
    with setup_produzione() as scraper:
        try:
            found, url, confidence = scraper.search_decreto_selenium(
                seduta="3929",
                numero="17", 
                oggetto="Approvazione piano triennale lavori pubblici"
            )
            
            # Verifica confidence threshold
            if confidence < 0.7:
                print(f"⚠️ Low confidence: {confidence:.2f}")
            
            return found, url, confidence
            
        except Exception as e:
            print(f"❌ Errore produzione: {e}")
            return False, None, 0.0

if __name__ == "__main__":
    found, url, confidence = produzione_workflow()
    print(f"Produzione result: {found}, {confidence:.2f}")
```

## ⚙️ Configurazione Chrome

### Opzioni Chrome Ottimizzate

```python
def _configure_chrome_options(self) -> ChromeOptions:
    """Configurazione Chrome ottimizzata per scraping."""
    
    options = ChromeOptions()
    
    # Modalità headless
    if self.headless:
        options.add_argument("--headless")
    
    # Opzioni performance
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    
    # Opzioni stealth
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User agent personalizzato
    options.add_argument(f"--user-agent={self._get_random_user_agent()}")
    
    # Window size per rendering corretto
    options.add_argument("--window-size=1920,1080")
    
    return options
```

### Configurazioni per Ambienti Diversi

```python
# Sviluppo - Browser visibile
scraper_dev = SeleniumDecretoScraper(
    headless=False,
    debug_mode=True,
    log_level=LogLevel.DEBUG
)

# Test - Headless con logging
scraper_test = SeleniumDecretoScraper(
    headless=True,
    debug_mode=True,
    log_level=LogLevel.INFO
)

# Produzione - Ottimizzato per performance
scraper_prod = SeleniumDecretoScraper(
    headless=True,
    debug_mode=False,
    log_level=LogLevel.WARN,
    implicit_wait=5  # Timeout più aggressivo
)
```

## 🔧 Troubleshooting

### Problemi Comuni

#### 1. Chrome Driver Issues

```python
# Errore: ChromeDriver non trovato
# Soluzione: webdriver-manager gestisce automaticamente
from webdriver_manager.chrome import ChromeDriverManager

# Verifica versione Chrome installata
chrome_version = ChromeDriverManager().get_compatible_driver()
```

#### 2. Element Not Found

```python
# Aumenta implicit_wait per elementi lenti
scraper = SeleniumDecretoScraper(implicit_wait=20)

# Usa wait espliciti per elementi specifici
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "search-form"))
)
```

#### 3. JavaScript Not Loaded

```python
# Attesa extra per JavaScript
time.sleep(2)

# Verifica document.readyState
self.driver.execute_script("return document.readyState") == "complete"
```

#### 4. Form Submit Failed

```python
# Strategie multiple per submit
try:
    submit_button.click()
except:
    # Fallback: submit via JavaScript
    self.driver.execute_script("arguments[0].click();", submit_button)
```

### Debug Mode Features

```python
# Abilita debug mode per troubleshooting
with SeleniumDecretoScraper(debug_mode=True) as scraper:
    # Screenshot automatici ad ogni step
    # - navigate_to_search_start.png
    # - form_filled.png  
    # - results_extracted.png
    
    # Log dettagliato di ogni operazione
    # - Element selectors utilizzati
    # - Valori dropdown trovati
    # - Form data compilato
    # - Risultati estratti
```

## 📊 Performance e Ottimizzazioni

### Caratteristiche Performance

- **Chrome Options Ottimizzate**: Disabilita GPU, plugins, extensions
- **Element Caching**: Cache selettori elementi frequenti
- **Smart Waits**: Timeout adattivi basati su tipo operazione
- **Resource Management**: Cleanup automatico driver e finestre
- **Error Recovery**: Retry con backoff esponenziale

### Metriche Tipiche

- **Setup driver**: ~2-5s (prima volta), ~1s (cache)
- **Navigazione pagina**: ~2-4s
- **Form filling**: ~1-3s
- **Results extraction**: ~1-2s
- **Screenshot**: ~200-500ms

### Ottimizzazioni Produzione

```python
# Configurazione ottimizzata per throughput
scraper = SeleniumDecretoScraper(
    headless=True,           # Essenziale per performance
    debug_mode=False,        # Disabilita screenshot
    implicit_wait=5,         # Timeout aggressivo
    log_level=LogLevel.ERROR # Logging minimale
)

# Riutilizza stesso scraper per ricerche multiple
with scraper:
    for decreto_info in decreti_lista:
        found, url, conf = scraper.search_decreto_selenium(**decreto_info)
        # Processa risultato...
```

## 🚀 Best Practices

### 1. Context Manager Usage

```python
# ✅ Raccomandato - Cleanup automatico
with SeleniumDecretoScraper() as scraper:
    result = scraper.search_decreto_selenium(...)

# ❌ Sconsigliato - Possibili memory leak
scraper = SeleniumDecretoScraper()
result = scraper.search_decreto_selenium(...)
# scraper.cleanup() deve essere chiamato manualmente
```

### 2. Error Handling

```python
def safe_selenium_search(seduta, numero, oggetto):
    """Ricerca sicura con error handling completo."""
    
    try:
        with SeleniumDecretoScraper() as scraper:
            return scraper.search_decreto_selenium(seduta, numero, oggetto)
            
    except DriverSetupError:
        # Chrome/ChromeDriver non disponibile
        logger.error("Driver setup failed")
        return False, None, 0.0
        
    except NavigationError:
        # Sito non raggiungibile
        logger.error("Navigation failed")
        return False, None, 0.0
        
    except FormInteractionError:
        # Form non trovato o non interagibile
        logger.error("Form interaction failed") 
        return False, None, 0.0
        
    except Exception as e:
        # Errore generico
        logger.error(f"Unexpected error: {e}")
        return False, None, 0.0
```

### 3. Production Configuration

```python
# Setup produzione con configurazione robusta
def create_production_scraper():
    return SeleniumDecretoScraper(
        headless=True,              # Performance
        debug_mode=False,           # No screenshot overhead
        implicit_wait=8,            # Bilanciato timeout
        log_level=LogLevel.WARN,    # Log essenziali
        max_retries=2               # Retry limitati
    )

# Monitoring in produzione  
def monitor_scraper_performance(scraper):
    stats = scraper.get_performance_stats()
    
    if stats['success_rate'] < 0.8:
        alert_low_success_rate(stats)
        
    if stats['average_execution_time'] > 30:
        alert_slow_performance(stats)
```

### 4. Resource Management

```python
# Gestione memoria per operazioni long-running
scraper_pool = []

try:
    for batch in decreto_batches:
        scraper = SeleniumDecretoScraper()
        scraper_pool.append(scraper)
        
        # Processa batch...
        
finally:
    # Cleanup di tutti gli scraper
    for scraper in scraper_pool:
        scraper.cleanup()
```

## 🔄 Integrazione con DecretoScraperAdvanced

### Fallback Strategy

```python
def decreto_search_with_fallback(seduta, numero, oggetto):
    """Ricerca con fallback da Selenium a requests."""
    
    # Tentativo 1: SeleniumDecretoScraper (per JS-heavy sites)
    try:
        with SeleniumDecretoScraper() as selenium_scraper:
            found, url, confidence = selenium_scraper.search_decreto_selenium(
                seduta, numero, oggetto
            )
            
            if found and confidence > 0.7:
                return found, url, confidence, "selenium"
                
    except Exception as e:
        logger.warning(f"Selenium failed: {e}")
    
    # Fallback: DecretoScraperAdvanced (più veloce)
    try:
        with DecretoScraperAdvanced() as requests_scraper:
            found, url, confidence = requests_scraper.verify_decreto_publication(
                seduta, numero, oggetto
            )
            
            return found, url, confidence, "requests"
            
    except Exception as e:
        logger.error(f"Both scrapers failed: {e}")
        return False, None, 0.0, "failed"
```

### Adaptive Strategy

```python
def smart_decreto_search(seduta, numero, oggetto, prefer_selenium=False):
    """Scelta intelligente tra Selenium e requests."""
    
    # Fattori decisione
    use_selenium = (
        prefer_selenium or
        oggetto_requires_javascript(oggetto) or
        is_complex_search(seduta, numero)
    )
    
    if use_selenium:
        return selenium_search(seduta, numero, oggetto)
    else:
        return requests_search(seduta, numero, oggetto)
```

## 📈 Roadmap e Miglioramenti Futuri

### Possibili Enhancement

1. **Parallel Processing**: Selenium Grid per ricerche multiple
2. **Smart Caching**: Cache risultati con TTL
3. **ML-based Element Detection**: Riconoscimento automatico form con ML
4. **Mobile Simulation**: User agent mobile per test
5. **Proxy Support**: Rotazione proxy per rate limiting
6. **Headless Browser Alternatives**: Support per Firefox, Edge

---

**Versione**: 1.0.0  
**Ultima modifica**: 2025-07-29  
**Status**: ✅ Production Ready

**Powered by**: Selenium WebDriver + Chrome Automation + Smart Form Interaction