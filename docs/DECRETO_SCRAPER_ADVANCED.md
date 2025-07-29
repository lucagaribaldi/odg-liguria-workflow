# DecretoScraperAdvanced - Documentazione Completa

## 🚀 Introduzione

`DecretoScraperAdvanced` è una riscrittura completa del sistema di scraping per il sito `decretidigitali.regione.liguria.it` che implementa **form scraping automatico** con le seguenti caratteristiche avanzate:

- **Analisi automatica della struttura dei form**
- **Estrazione dinamica delle opzioni dropdown**
- **Auto-fill intelligente dei campi**
- **Parsing avanzato dei risultati con confidence scoring**
- **Gestione errori robusta e retry automatici**
- **Sistema di performance monitoring**

## 🏗️ Architettura

### Componenti Principali

```
DecretoScraperAdvanced
├── Form Analysis Engine
│   ├── analyze_form_structure()
│   ├── extract_dropdown_options()
│   └── _find_search_form()
├── Smart Field Selection
│   ├── smart_field_selection()
│   ├── _find_best_match_in_options()
│   └── build_form_data()
├── Request Management
│   ├── _make_request()
│   ├── _rotate_user_agent()
│   └── submit_search_form()
├── Result Processing
│   ├── parse_search_results()
│   ├── _parse_single_result()
│   └── _calculate_confidence_score()
└── Performance & Monitoring
    ├── get_performance_stats()
    └── session_context()
```

### Dataclasses

```python
@dataclass
class FormField:
    name: str
    field_type: str  # select, input, textarea
    required: bool = False
    options: Dict[str, str] = field(default_factory=dict)
    default_value: Optional[str] = None
    placeholder: Optional[str] = None

@dataclass
class FormStructure:
    action_url: str
    method: str = "GET"
    fields: Dict[str, FormField] = field(default_factory=dict)
    hidden_fields: Dict[str, str] = field(default_factory=dict)
    csrf_token: Optional[str] = None

@dataclass
class SearchResult:
    title: str
    url: str
    date: Optional[str] = None
    document_type: Optional[str] = None
    number: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 0.0

@dataclass
class SearchParameters:
    seduta: str
    numero: str
    oggetto: str
    anno: Optional[str] = None
    data_sottoscrizione: Optional[str] = None
    tipo_atto: Optional[str] = None
```

## 🔧 Utilizzo

### Inizializzazione Base

```python
from src.decreto_scraper import DecretoScraperAdvanced, LogLevel

# Configurazione base
scraper = DecretoScraperAdvanced(
    base_url="https://decretidigitali.regione.liguria.it",
    rate_limit=2.0,
    max_retries=3,
    timeout=30,
    verify_ssl=True,
    debug_mode=False,
    log_level=LogLevel.INFO
)
```

### Utilizzo con Context Manager (Raccomandato)

```python
with DecretoScraperAdvanced(debug_mode=True) as scraper:
    found, url, confidence = scraper.verify_decreto_publication(
        seduta="3929",
        numero="17",
        oggetto="Approvazione piano triennale lavori pubblici",
        anno="2025"
    )
    
    print(f"Trovato: {found}")
    print(f"URL: {url}")
    print(f"Confidence: {confidence:.2f}")
```

### Configurazione Avanzata

```python
scraper = DecretoScraperAdvanced(
    base_url="https://decretidigitali.regione.liguria.it",
    search_endpoint="/",  # Endpoint ricerca personalizzato
    rate_limit=1.5,       # Rate limiting più conservativo
    max_retries=5,        # Più tentativi
    timeout=45,           # Timeout esteso
    verify_ssl=False,     # Solo per test/sviluppo
    debug_mode=True,      # Debug dettagliato
    log_level=LogLevel.DEBUG,
    user_agents=[         # User agents personalizzati
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    ]
)
```

## 🧠 Funzionalità Principali

### 1. Analisi Automatica Form Structure

```python
# Analizza automaticamente la struttura del form
form_structure = scraper.analyze_form_structure()

print(f"Action URL: {form_structure.action_url}")
print(f"Method: {form_structure.method}")
print(f"Campi: {len(form_structure.fields)}")

# Mostra campi dropdown
for name, field in form_structure.fields.items():
    if field.field_type == 'select':
        print(f"{name}: {len(field.options)} opzioni")
```

### 2. Estrazione Opzioni Dropdown

```python
# Estrazione automatica opzioni da HTML
html = '<select name="anno"><option value="2025">2025</option></select>'
soup = BeautifulSoup(html, 'html.parser')
select = soup.find('select')

options = scraper.extract_dropdown_options(select)
# Output: {'2025': '2025'}
```

### 3. Selezione Intelligente Campi

```python
search_params = SearchParameters(
    seduta="3929",
    numero="17", 
    oggetto="Approvazione piano triennale lavori pubblici",
    anno="2025"
)

# Selezione automatica basata su logica intelligente
selected_value = scraper.smart_field_selection(
    "anno", search_params, form_structure
)
# Seleziona automaticamente "2025" se disponibile
```

### 4. Confidence Scoring Avanzato

Il sistema calcola un punteggio di confidenza (0.0-1.0) per ogni risultato basato su:

- **Match parole chiave oggetto** (peso 40%)
- **Match numero deliberazione** (peso 30%)  
- **Match tipo documento** (peso 10%)
- **Match anno** (peso 10%)
- **Fuzzy matching complessivo** (peso 10%)

```python
confidence = scraper._calculate_confidence_score(
    title="Deliberazione n. 17 - Approvazione piano triennale lavori pubblici",
    search_params=search_params,
    date="2025-07-01",
    document_type="Deliberazione", 
    number="17"
)
# Output: ~0.9 (alta confidenza)
```

## 🔍 Workflow Completo

### 1. Analisi Form Structure

```python
def analyze_form_structure(self, force_refresh: bool = False) -> FormStructure:
    """
    1. GET della pagina principale
    2. Parse HTML con BeautifulSoup
    3. Trova form di ricerca con strategie multiple
    4. Estrae tutti i campi (select, input, textarea)
    5. Identifica campi hidden e CSRF token
    6. Cache risultato per 1 ora
    """
```

### 2. Smart Field Selection

```python
def smart_field_selection(self, field_name: str, search_params: SearchParameters, 
                         form_structure: FormStructure) -> Optional[str]:
    """
    Logica di selezione per tipo campo:
    
    - Anno: usa search_params.anno o "2025"
    - Tipo atto: cerca "deliberazione", "delibera", "decree"
    - Area tematica: usa parole chiave da oggetto
    - Numero: usa search_params.numero
    - Default: prima opzione non vuota
    
    Strategie matching:
    1. Exact match (value e label)
    2. Substring match
    3. Fuzzy matching (difflib, soglia 60%)
    """
```

### 3. Form Data Building

```python
def build_form_data(self, search_params: SearchParameters) -> Dict[str, str]:
    """
    1. Aggiunge campi hidden (incluso CSRF token)
    2. Mappa campi select con smart_field_selection
    3. Mappa campi text con pattern matching su nome campo
    4. Usa valori default se specifici non disponibili
    """
```

### 4. Result Parsing & Confidence Scoring

```python
def parse_search_results(self, html_response: str, 
                        search_params: SearchParameters) -> List[SearchResult]:
    """
    1. Parse HTML con strategie multiple per container risultati
    2. Estrae: titolo, URL, data, tipo documento, numero
    3. Calcola confidence score per ogni risultato
    4. Ordina per confidence score decrescente
    """
```

## 📊 Performance Monitoring

```python
# Statistiche automatiche
stats = scraper.get_performance_stats()

print(f"Richieste totali: {stats['total_requests']}")
print(f"Tasso successo: {stats['success_rate']:.1%}")
print(f"Tempo risposta medio: {stats['average_response_time']:.2f}s")
print(f"Form structure cached: {stats['form_structure_cached']}")
print(f"Cache age: {stats['cache_age_minutes']} minuti")
```

## 🛡️ Gestione Errori

### Exception Hierarchy

```python
DecretoScraperError (base)
├── DecretoFormAnalysisError    # Errori analisi form
├── DecretoFieldMappingError    # Errori mapping campi
├── DecretoSubmissionError      # Errori submission form
└── DecretoParsingError         # Errori parsing risultati
```

### Error Handling Strategy

```python
try:
    found, url, confidence = scraper.verify_decreto_publication(...)
except DecretoFormAnalysisError:
    # Form non trovato o non analizzabile
    pass
except DecretoSubmissionError:
    # Problemi invio form
    pass
except DecretoScraperError:
    # Altri errori generici
    pass
```

## ⚙️ Configurazione Avanzata

### SSL Configuration

```python
# Produzione - SSL sempre abilitato
scraper = DecretoScraperAdvanced(verify_ssl=True)

# Sviluppo/Test - SSL disabilitato per problemi certificati
scraper = DecretoScraperAdvanced(verify_ssl=False)
```

### Rate Limiting

```python
# Conservativo (good citizen)
scraper = DecretoScraperAdvanced(rate_limit=2.0)

# Aggressivo (solo per test)
scraper = DecretoScraperAdvanced(rate_limit=0.5)
```

### Logging Levels

```python
LogLevel.SILENT   # Nessun log
LogLevel.ERROR    # Solo errori
LogLevel.WARN     # Warning ed errori
LogLevel.INFO     # Informazioni generali (default)
LogLevel.DEBUG    # Debug dettagliato
LogLevel.TRACE    # Trace completo (molto verboso)
```

### User Agent Rotation

```python
custom_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
]

scraper = DecretoScraperAdvanced(user_agents=custom_agents)
```

## 🧪 Testing

### Unit Tests

```bash
# Test funzionalità base
python test_decreto_scraper_new.py

# Test connessione reale (opzionale)
python test_real_connection.py

# Esempi utilizzo
python examples/decreto_scraper_advanced_usage.py
```

### Mock Testing

```python
# Test con dati mock per sviluppo
scraper = DecretoScraperAdvanced(debug_mode=True, verify_ssl=False)

# Simula risultati con HTML mock
mock_html = '<div class="result"><h3>Test Result</h3></div>'
results = scraper.parse_search_results(mock_html, search_params)
```

## 🔄 Backward Compatibility

```python
# Alias per compatibilità con codice esistente
class DecretoScraper(DecretoScraperAdvanced):
    """Alias per backward compatibility."""
    pass

# Il codice esistente continua a funzionare
scraper = DecretoScraper()  # Usa DecretoScraperAdvanced
```

## 🚀 Best Practices

### 1. Uso Context Manager

```python
# ✅ Raccomandato
with DecretoScraperAdvanced() as scraper:
    result = scraper.verify_decreto_publication(...)

# ❌ Sconsigliato  
scraper = DecretoScraperAdvanced()
result = scraper.verify_decreto_publication(...)
```

### 2. Configurazione Ambiente

```python
# Produzione
scraper = DecretoScraperAdvanced(
    rate_limit=2.0,
    verify_ssl=True,
    debug_mode=False,
    log_level=LogLevel.WARN
)

# Sviluppo
scraper = DecretoScraperAdvanced(
    rate_limit=0.5,
    verify_ssl=False,
    debug_mode=True,
    log_level=LogLevel.DEBUG
)
```

### 3. Error Handling

```python
def safe_decreto_check(seduta, numero, oggetto):
    try:
        with DecretoScraperAdvanced() as scraper:
            return scraper.verify_decreto_publication(seduta, numero, oggetto)
    except DecretoScraperError as e:
        logger.error(f"Decreto check failed: {e}")
        return False, None, 0.0
```

### 4. Performance Monitoring

```python
with DecretoScraperAdvanced() as scraper:
    # Operazioni...
    
    stats = scraper.get_performance_stats()
    if stats['success_rate'] < 0.8:
        logger.warning(f"Low success rate: {stats['success_rate']:.1%}")
```

## 🔧 Troubleshooting

### Problemi Comuni

1. **SSL Certificate Errors**
   ```python
   # Soluzione temporanea per sviluppo
   scraper = DecretoScraperAdvanced(verify_ssl=False)
   ```

2. **Form Not Found**
   ```python
   # Usa endpoint personalizzato
   scraper = DecretoScraperAdvanced(search_endpoint="/search")
   ```

3. **Rate Limiting**
   ```python
   # Aumenta rate limit
   scraper = DecretoScraperAdvanced(rate_limit=3.0)
   ```

4. **Timeout Issues**
   ```python
   # Aumenta timeout
   scraper = DecretoScraperAdvanced(timeout=60)
   ```

### Debug Mode

```python
# Debug completo con log dettagliato
scraper = DecretoScraperAdvanced(
    debug_mode=True,
    log_level=LogLevel.TRACE
)

# Log mostrerà:
# - Analisi form structure
# - Opzioni dropdown estratte
# - Field selection logic
# - Form data costruito
# - Risultati parsing
# - Confidence scores
```

## 📈 Performance

### Caratteristiche Ottimizzate

- **Form Structure Caching**: Cache della struttura form per 1 ora
- **Connection Pooling**: Riutilizzo connessioni HTTP
- **Retry Strategy**: Retry intelligente con backoff
- **User Agent Rotation**: Evita detection automatica
- **Rate Limiting**: Rispetta limiti server

### Metriche Tipiche

- **Analisi form**: ~500ms (prima volta), ~0ms (cached)
- **Submission form**: ~1-2s
- **Parsing risultati**: ~100-500ms
- **Confidence scoring**: ~10-50ms per risultato

## 🎯 Roadmap Future

### Possibili Miglioramenti

1. **Machine Learning**: Confidence scoring con ML
2. **Parallel Processing**: Ricerche multiple in parallelo  
3. **Advanced Caching**: Cache risultati ricerche
4. **Selenium Integration**: Fallback per JS-heavy sites
5. **API Integration**: Supporto API REST se disponibili

---

**Versione**: 2.0.0 Advanced  
**Ultima modifica**: 2025-07-29  
**Status**: ✅ Production Ready  

**Powered by**: Form Scraping Automatico + Confidence Scoring + Performance Monitoring