"""
Selenium Decreto Scraper - Automazione Browser Reale
Sistema di scraping avanzato usando Selenium WebDriver per siti con JavaScript pesante.

Caratteristiche principali:
- Simulazione interazioni umane reali
- Gestione JavaScript e validazioni client-side
- Auto-download Chrome driver
- Screenshot automatici per debugging
- Selezione intelligente dropdown
- Gestione timeout e attese dinamiche
- Fallback robusto per form complessi
"""

import logging
import time
import os
import json
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import difflib
import re
from pathlib import Path

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementNotInteractableException,
    StaleElementReferenceException
)

# WebDriver Manager for auto-download
from webdriver_manager.chrome import ChromeDriverManager


class SeleniumScraperError(Exception):
    """Base exception for Selenium scraper errors."""
    pass


class DriverSetupError(SeleniumScraperError):
    """Raised when WebDriver setup fails."""
    pass


class NavigationError(SeleniumScraperError):
    """Raised when page navigation fails."""
    pass


class FormInteractionError(SeleniumScraperError):
    """Raised when form interaction fails."""
    pass


class ResultExtractionError(SeleniumScraperError):
    """Raised when result extraction fails."""
    pass


class LogLevel(Enum):
    """Logging levels for selenium scraper."""
    SILENT = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


@dataclass
class SearchParameters:
    """Parametri per la ricerca Selenium."""
    seduta: str
    numero: str
    oggetto: str
    anno: Optional[str] = None
    data_sottoscrizione: Optional[str] = None
    tipo_atto: Optional[str] = None
    area_tematica: Optional[str] = None


@dataclass
class SeleniumResult:
    """Risultato estratto tramite Selenium."""
    title: str
    url: str
    date: Optional[str] = None
    document_type: Optional[str] = None
    number: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 0.0
    screenshot_path: Optional[str] = None


@dataclass 
class DropdownOption:
    """Opzione dropdown con metadati."""
    value: str
    text: str
    index: int
    selected: bool = False


class SeleniumDecretoScraper:
    """
    Scraper Selenium per decreto digitali con automazione browser reale.
    
    Caratteristiche:
    - Simulazione interazioni umane
    - Gestione JavaScript e AJAX
    - Auto-download Chrome driver
    - Screenshot debugging
    - Selezione intelligente form
    """

    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        headless: bool = True,
        implicit_wait: int = 10,
        page_load_timeout: int = 30,
        script_timeout: int = 30,
        debug_mode: bool = False,
        log_level: LogLevel = LogLevel.INFO,
        screenshot_dir: str = "logs/selenium_screenshots",
        user_agent: Optional[str] = None,
        window_size: Tuple[int, int] = (1920, 1080)
    ):
        """
        Inizializza Selenium decreto scraper.
        
        Args:
            base_url: URL base del sito decreto
            headless: Esegui browser in modalità headless
            implicit_wait: Timeout implicito per elementi (secondi)
            page_load_timeout: Timeout caricamento pagina (secondi)
            script_timeout: Timeout esecuzione script (secondi)
            debug_mode: Modalità debug con screenshot
            log_level: Livello logging
            screenshot_dir: Directory per screenshot
            user_agent: User agent personalizzato
            window_size: Dimensioni finestra browser
        """
        self.base_url = base_url.rstrip('/')
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.script_timeout = script_timeout
        self.debug_mode = debug_mode
        self.log_level = log_level
        self.screenshot_dir = Path(screenshot_dir)
        self.user_agent = user_agent
        self.window_size = window_size
        
        # Setup logging
        self._setup_logging()
        
        # WebDriver instance
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        
        # Performance metrics
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        
        # Screenshot counter for unique filenames
        self.screenshot_counter = 0
        
        # Ensure screenshot directory exists
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"SeleniumDecretoScraper initialized - Base URL: {self.base_url}")

    def _setup_logging(self):
        """Setup sistema di logging."""
        self.logger = logging.getLogger(f"{__name__}.SeleniumDecretoScraper")
        
        if self.log_level == LogLevel.SILENT:
            self.logger.setLevel(logging.CRITICAL + 1000)
        elif self.log_level == LogLevel.ERROR:
            self.logger.setLevel(logging.ERROR)
        elif self.log_level == LogLevel.WARN:
            self.logger.setLevel(logging.WARNING)
        elif self.log_level == LogLevel.INFO:
            self.logger.setLevel(logging.INFO)
        elif self.log_level == LogLevel.DEBUG:
            self.logger.setLevel(logging.DEBUG)
        elif self.log_level == LogLevel.TRACE:
            self.logger.setLevel(5)  # Custom trace level
            
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def setup_driver(self) -> webdriver.Chrome:
        """
        Configura Chrome WebDriver con opzioni ottimizzate.
        
        Returns:
            Istanza WebDriver configurata
            
        Raises:
            DriverSetupError: Se setup driver fallisce
        """
        try:
            self.logger.info("Setting up Chrome WebDriver...")
            
            # Chrome options
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
            
            # Security and performance options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            # User agent
            if self.user_agent:
                chrome_options.add_argument(f'--user-agent={self.user_agent}')
            else:
                # Default realistic user agent
                chrome_options.add_argument(
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            
            # Window size
            chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
            
            # Disable notifications and popups
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "popups": 2,
                    "media_stream": 2,
                    "plugins": 2,
                    "images": 2 if not self.debug_mode else 1,  # Disable images for speed unless debugging
                    "javascript": 1,  # Keep JavaScript enabled
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Disable logging to reduce noise
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Auto-download Chrome driver
            service = Service(ChromeDriverManager().install())
            
            # Create driver instance
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure timeouts
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.set_script_timeout(self.script_timeout)
            
            # Create WebDriverWait instance
            self.wait = WebDriverWait(self.driver, self.implicit_wait)
            
            # Execute script to hide automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Chrome WebDriver setup completed successfully")
            return self.driver
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to setup Chrome WebDriver: {e}")
            raise DriverSetupError(f"WebDriver setup failed: {e}")

    def take_screenshot(self, name: str = None) -> str:
        """
        Prende screenshot per debugging.
        
        Args:
            name: Nome custom per screenshot
            
        Returns:
            Path del screenshot salvato
        """
        if not self.driver:
            return ""
        
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now().strftime("%H%M%S")
            
            if name:
                filename = f"{self.screenshot_counter:02d}_{timestamp}_{name}.png"
            else:
                filename = f"{self.screenshot_counter:02d}_{timestamp}_screenshot.png"
            
            screenshot_path = self.screenshot_dir / filename
            
            if self.driver.save_screenshot(str(screenshot_path)):
                self.logger.debug(f"Screenshot saved: {screenshot_path}")
                return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
        
        return ""

    def navigate_to_search(self) -> bool:
        """
        Naviga alla pagina di ricerca decreto.
        
        Returns:
            True se navigazione riuscita
            
        Raises:
            NavigationError: Se navigazione fallisce
        """
        if not self.driver:
            raise NavigationError("WebDriver not initialized")
        
        try:
            self.logger.info(f"Navigating to: {self.base_url}")
            
            start_time = time.time()
            self.driver.get(self.base_url)
            
            # Wait for page to load completely
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            load_time = time.time() - start_time
            self.logger.info(f"Page loaded in {load_time:.2f}s")
            
            if self.debug_mode:
                self.take_screenshot("page_loaded")
            
            # Check if we're on the right page
            current_url = self.driver.current_url
            if self.base_url not in current_url:
                self.logger.warning(f"Unexpected URL after navigation: {current_url}")
            
            # Look for search form indicators
            form_found = self._find_search_form()
            if not form_found:
                self.logger.warning("Search form not immediately visible, but continuing...")
            
            self.success_count += 1
            return True
            
        except TimeoutException as e:
            self.error_count += 1
            if self.debug_mode:
                self.take_screenshot("navigation_timeout")
            self.logger.error(f"Navigation timeout: {e}")
            raise NavigationError(f"Page load timeout: {e}")
            
        except WebDriverException as e:
            self.error_count += 1
            if self.debug_mode:
                self.take_screenshot("navigation_error")
            self.logger.error(f"Navigation error: {e}")
            raise NavigationError(f"Navigation failed: {e}")

    def _find_search_form(self) -> bool:
        """
        Trova il form di ricerca nella pagina.
        
        Returns:
            True se form trovato
        """
        try:
            # Strategie multiple per trovare il form
            form_selectors = [
                'form[action*="ricerca"]',
                'form[action*="search"]',
                'form#searchForm',
                'form.search-form',
                'form:has(input[type="search"])',
                'form:has(select)',
                'form'  # Fallback: primo form
            ]
            
            for selector in form_selectors:
                try:
                    form = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if form.is_displayed():
                        self.logger.debug(f"Found search form with selector: {selector}")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error finding search form: {e}")
            return False

    def extract_dropdown_options(self, select_element) -> List[DropdownOption]:
        """
        Estrae tutte le opzioni da un dropdown.
        
        Args:
            select_element: Elemento Select
            
        Returns:
            Lista di DropdownOption
        """
        options = []
        
        try:
            select = Select(select_element)
            
            for i, option in enumerate(select.options):
                value = option.get_attribute('value') or ''
                text = option.text.strip()
                selected = option.is_selected()
                
                # Skip opzioni vuote o di default
                if value and text and text.lower() not in ['seleziona', 'choose', 'select', '---', '']:
                    options.append(DropdownOption(
                        value=value,
                        text=text,
                        index=i,
                        selected=selected
                    ))
            
            self.logger.debug(f"Extracted {len(options)} options from dropdown")
            return options
            
        except Exception as e:
            self.logger.error(f"Failed to extract dropdown options: {e}")
            return []

    def smart_dropdown_selection(
        self, 
        select_element, 
        target_value: str, 
        field_type: str = "generic"
    ) -> bool:
        """
        Selezione intelligente di un valore in dropdown.
        
        Args:
            select_element: Elemento select
            target_value: Valore target da cercare
            field_type: Tipo campo per logica specifica
            
        Returns:
            True se selezione riuscita
        """
        try:
            select = Select(select_element)
            options = self.extract_dropdown_options(select_element)
            
            if not options:
                self.logger.warning("No options found in dropdown")
                return False
            
            target_lower = target_value.lower()
            
            # 1. Exact match per value
            for option in options:
                if option.value.lower() == target_lower:
                    select.select_by_value(option.value)
                    self.logger.debug(f"Exact value match: {target_value} -> {option.value}")
                    return True
            
            # 2. Exact match per text
            for option in options:
                if option.text.lower() == target_lower:
                    select.select_by_visible_text(option.text)
                    self.logger.debug(f"Exact text match: {target_value} -> {option.text}")
                    return True
            
            # 3. Substring match
            for option in options:
                if target_lower in option.text.lower() or option.text.lower() in target_lower:
                    select.select_by_visible_text(option.text)
                    self.logger.debug(f"Substring match: {target_value} -> {option.text}")
                    return True
            
            # 4. Logica specifica per tipo campo
            if field_type == "anno" and target_value.isdigit():
                # Per anno, cerca anno corrente o successivo
                year = int(target_value)
                for option in options:
                    if option.value.isdigit() and int(option.value) >= year:
                        select.select_by_value(option.value)
                        self.logger.debug(f"Year match: {target_value} -> {option.value}")
                        return True
            
            elif field_type == "tipo_atto":
                # Per tipo atto, cerca deliberazione/delibera
                keywords = ['deliberazione', 'delibera', 'decreto', 'dgr']
                for keyword in keywords:
                    for option in options:
                        if keyword in option.text.lower():
                            select.select_by_visible_text(option.text)
                            self.logger.debug(f"Type match: {keyword} -> {option.text}")
                            return True
            
            # 5. Fuzzy matching
            best_ratio = 0.0
            best_option = None
            
            for option in options:
                # Match con text
                ratio = difflib.SequenceMatcher(None, target_lower, option.text.lower()).ratio()
                if ratio > best_ratio and ratio > 0.6:  # Soglia 60%
                    best_ratio = ratio
                    best_option = option
                
                # Match con value
                ratio = difflib.SequenceMatcher(None, target_lower, option.value.lower()).ratio()
                if ratio > best_ratio and ratio > 0.6:
                    best_ratio = ratio
                    best_option = option
            
            if best_option:
                select.select_by_visible_text(best_option.text)
                self.logger.debug(f"Fuzzy match: {target_value} -> {best_option.text} (ratio: {best_ratio:.2f})")
                return True
            
            # 6. Fallback: prima opzione valida
            if options:
                first_option = options[0]
                select.select_by_visible_text(first_option.text)
                self.logger.debug(f"Fallback selection: {first_option.text}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Smart dropdown selection failed: {e}")
            return False

    def fill_search_form(self, search_params: SearchParameters) -> bool:
        """
        Compila il form di ricerca automaticamente.
        
        Args:
            search_params: Parametri di ricerca
            
        Returns:
            True se compilazione riuscita
            
        Raises:
            FormInteractionError: Se compilazione fallisce
        """
        if not self.driver:
            raise FormInteractionError("WebDriver not initialized")
        
        try:
            self.logger.info("Filling search form...")
            
            if self.debug_mode:
                self.take_screenshot("before_form_fill")
            
            form_filled = False
            
            # 1. Campo parole chiave / oggetto
            keyword_selectors = [
                'input[name*="parola"]',
                'input[name*="keyword"]',
                'input[name*="oggetto"]',
                'input[name*="subject"]',
                'input[name*="title"]',
                'input[type="search"]',
                'input[name*="q"]'
            ]
            
            for selector in keyword_selectors:
                try:
                    keyword_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if keyword_field.is_displayed() and keyword_field.is_enabled():
                        keyword_field.clear()
                        keyword_field.send_keys(search_params.oggetto)
                        self.logger.debug(f"Filled keyword field: {search_params.oggetto}")
                        form_filled = True
                        break
                except NoSuchElementException:
                    continue
            
            # 2. Dropdown Anno
            if search_params.anno:
                anno_selectors = [
                    'select[name*="anno"]',
                    'select[name*="year"]',
                    'select[id*="anno"]'
                ]
                
                for selector in anno_selectors:
                    try:
                        anno_select = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if anno_select.is_displayed():
                            if self.smart_dropdown_selection(anno_select, search_params.anno, "anno"):
                                self.logger.debug(f"Selected anno: {search_params.anno}")
                                form_filled = True
                            break
                    except NoSuchElementException:
                        continue
            
            # 3. Dropdown Tipo Atto
            tipo_atto = search_params.tipo_atto or "Deliberazione"
            tipo_selectors = [
                'select[name*="tipo"]',
                'select[name*="atto"]',
                'select[name*="type"]',
                'select[id*="tipo"]'
            ]
            
            for selector in tipo_selectors:
                try:
                    tipo_select = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if tipo_select.is_displayed():
                        if self.smart_dropdown_selection(tipo_select, tipo_atto, "tipo_atto"):
                            self.logger.debug(f"Selected tipo atto: {tipo_atto}")
                            form_filled = True
                        break
                except NoSuchElementException:
                    continue
            
            # 4. Campo Numero
            if search_params.numero:
                numero_selectors = [
                    'input[name*="numero"]',
                    'input[name*="number"]',
                    'input[id*="numero"]'
                ]
                
                for selector in numero_selectors:
                    try:
                        numero_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if numero_field.is_displayed() and numero_field.is_enabled():
                            numero_field.clear()
                            numero_field.send_keys(search_params.numero)
                            self.logger.debug(f"Filled numero field: {search_params.numero}")
                            form_filled = True
                            break
                    except NoSuchElementException:
                        continue
            
            # 5. Campo Data
            if search_params.data_sottoscrizione:
                data_selectors = [
                    'input[name*="data"]',
                    'input[name*="date"]',
                    'input[type="date"]',
                    'input[id*="data"]'
                ]
                
                for selector in data_selectors:
                    try:
                        data_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if data_field.is_displayed() and data_field.is_enabled():
                            data_field.clear()
                            # Formato data appropriato
                            data_formatted = self._format_date(search_params.data_sottoscrizione)
                            data_field.send_keys(data_formatted)
                            self.logger.debug(f"Filled data field: {data_formatted}")
                            form_filled = True
                            break
                    except NoSuchElementException:
                        continue
            
            # 6. Altri dropdown generici
            try:
                all_selects = self.driver.find_elements(By.TAG_NAME, 'select')
                for select_elem in all_selects:
                    if select_elem.is_displayed():
                        options = self.extract_dropdown_options(select_elem)
                        if len(options) > 1:  # Ha opzioni multiple
                            name = select_elem.get_attribute('name') or select_elem.get_attribute('id') or ''
                            
                            # Area tematica/materia
                            if any(keyword in name.lower() for keyword in ['area', 'materia', 'category', 'subject']):
                                # Usa parole dall'oggetto
                                oggetto_words = search_params.oggetto.lower().split()
                                for word in oggetto_words:
                                    if len(word) > 3:
                                        if self.smart_dropdown_selection(select_elem, word):
                                            self.logger.debug(f"Selected {name}: {word}")
                                            break
            except Exception as e:
                self.logger.debug(f"Error handling generic dropdowns: {e}")
            
            if self.debug_mode:
                self.take_screenshot("after_form_fill")
            
            if not form_filled:
                self.logger.warning("No form fields were successfully filled")
                return False
            
            self.logger.info("Search form filled successfully")
            return True
            
        except Exception as e:
            self.error_count += 1
            if self.debug_mode:
                self.take_screenshot("form_fill_error")
            self.logger.error(f"Form filling failed: {e}")
            raise FormInteractionError(f"Failed to fill search form: {e}")

    def _format_date(self, date_string: str) -> str:
        """
        Formatta data per input field.
        
        Args:
            date_string: Data in formato stringa
            
        Returns:
            Data formattata
        """
        # Prova vari formati di input
        formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime('%d/%m/%Y')  # Formato italiano standard
            except ValueError:
                continue
        
        # Se nessun formato riconosciuto, restituisci originale
        return date_string

    def submit_and_wait_results(self, timeout: int = 30) -> bool:
        """
        Invia il form di ricerca e aspetta i risultati.
        
        Args:
            timeout: Timeout attesa risultati
            
        Returns:
            True se submission riuscita
        """
        if not self.driver:
            return False
        
        try:
            self.logger.info("Submitting search form...")
            
            if self.debug_mode:
                self.take_screenshot("before_submit")
            
            # Trova bottone submit
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:contains("Cerca")',
                'button:contains("Search")',
                'input[value*="Cerca"]',
                'input[value*="Search"]',
                '.btn-search',
                '#search-btn'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if ':contains(' in selector:
                        # XPath per testo
                        xpath = f"//button[contains(text(), '{selector.split(':contains("')[1].split('")')[0]}')]"
                        submit_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                # Fallback: premi Enter nel primo campo input
                try:
                    first_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="text"], input[type="search"]')
                    first_input.send_keys(Keys.RETURN)
                    self.logger.debug("Submitted form using Enter key")
                except NoSuchElementException:
                    self.logger.error("No submit button or input field found")
                    return False
            else:
                # Click submit button
                self.driver.execute_script("arguments[0].scrollIntoView();", submit_button)
                time.sleep(0.5)
                submit_button.click()
                self.logger.debug("Clicked submit button")
            
            # Aspetta che la pagina cambi o si aggiorni
            self._wait_for_results(timeout)
            
            if self.debug_mode:
                self.take_screenshot("results_loaded")
            
            self.logger.info("Form submitted and results loaded")
            return True
            
        except Exception as e:
            self.error_count += 1
            if self.debug_mode:
                self.take_screenshot("submit_error")
            self.logger.error(f"Form submission failed: {e}")
            return False

    def _wait_for_results(self, timeout: int = 30):
        """
        Aspetta che i risultati si carichino.
        
        Args:
            timeout: Timeout in secondi
        """
        try:
            # Aspetta elementi che indicano risultati
            result_indicators = [
                '.result',
                '.search-result',
                'table tbody tr',
                '.list-item',
                '#results',
                '.results-container'
            ]
            
            wait = WebDriverWait(self.driver, timeout)
            
            for indicator in result_indicators:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, indicator)))
                    self.logger.debug(f"Results found with indicator: {indicator}")
                    return
                except TimeoutException:
                    continue
            
            # Fallback: aspetta che la pagina sia completamente caricata
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Aspetta extra per JavaScript asincrono
            time.sleep(2)
            
        except TimeoutException:
            self.logger.warning(f"Timeout waiting for results after {timeout}s")

    def extract_results(self, search_params: SearchParameters) -> List[SeleniumResult]:
        """
        Estrae i risultati dalla pagina dei risultati.
        
        Args:
            search_params: Parametri ricerca per confidence scoring
            
        Returns:
            Lista di SeleniumResult
        """
        if not self.driver:
            return []
        
        try:
            self.logger.info("Extracting search results...")
            
            if self.debug_mode:
                self.take_screenshot("extract_results")
            
            results = []
            
            # Strategie multiple per trovare risultati
            result_selectors = [
                '.result',
                '.search-result',
                'table tbody tr',
                '.list-item',
                '.record',
                'li:has(a[href])',
                'div:has(h3) a[href]'
            ]
            
            result_elements = []
            for selector in result_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        result_elements = elements
                        self.logger.debug(f"Found {len(elements)} results with selector: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            if not result_elements:
                self.logger.warning("No result elements found")
                return []
            
            # Processa ogni risultato
            for i, element in enumerate(result_elements[:20]):  # Limita a primi 20 risultati
                try:
                    result = self._extract_single_result(element, search_params, i)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.debug(f"Failed to extract result {i}: {e}")
                    continue
            
            # Ordina per confidence score
            results.sort(key=lambda x: x.confidence_score, reverse=True)
            
            self.logger.info(f"Extracted {len(results)} search results")
            return results
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Result extraction failed: {e}")
            raise ResultExtractionError(f"Failed to extract results: {e}")

    def _extract_single_result(
        self, 
        element, 
        search_params: SearchParameters, 
        index: int
    ) -> Optional[SeleniumResult]:
        """
        Estrae un singolo risultato.
        
        Args:
            element: Elemento DOM del risultato
            search_params: Parametri ricerca
            index: Indice risultato
            
        Returns:
            SeleniumResult o None
        """
        try:
            # Estrai titolo
            title = self._extract_title_from_element(element)
            if not title:
                return None
            
            # Estrai URL
            url = self._extract_url_from_element(element)
            
            # Estrai altri campi
            date = self._extract_date_from_element(element)
            document_type = self._extract_document_type_from_element(element)
            number = self._extract_number_from_element(element)
            description = self._extract_description_from_element(element)
            
            # Calcola confidence score
            confidence_score = self._calculate_confidence_score(
                title, search_params, date, document_type, number, description
            )
            
            result = SeleniumResult(
                title=title,
                url=url or '',
                date=date,
                document_type=document_type,
                number=number,
                description=description,
                confidence_score=confidence_score
            )
            
            self.logger.debug(f"Extracted result {index}: {title[:50]}... (confidence: {confidence_score:.2f})")
            return result
            
        except Exception as e:
            self.logger.debug(f"Failed to extract single result: {e}")
            return None

    def _extract_title_from_element(self, element) -> Optional[str]:
        """Estrae titolo dall'elemento."""
        title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'a', 'strong', '.title', '.subject']
        
        for selector in title_selectors:
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.text.strip()
                if title and len(title) > 10:
                    return title
            except NoSuchElementException:
                continue
        
        # Fallback: tutto il testo dell'elemento
        text = element.text.strip()
        if text and len(text) > 10:
            return text[:200] + ('...' if len(text) > 200 else '')
        
        return None

    def _extract_url_from_element(self, element) -> Optional[str]:
        """Estrae URL dall'elemento."""
        try:
            # Cerca link nell'elemento
            link = element.find_element(By.TAG_NAME, 'a')
            href = link.get_attribute('href')
            if href and href.startswith('http'):
                return href
            elif href:
                return f"{self.base_url}{href}" if not href.startswith('/') else f"{self.base_url}{href}"
        except NoSuchElementException:
            pass
        
        return None

    def _extract_date_from_element(self, element) -> Optional[str]:
        """Estrae data dall'elemento."""
        text = element.text
        
        # Pattern per date italiane
        date_patterns = [
            r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b',  # dd/mm/yyyy
            r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b',  # yyyy/mm/dd
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None

    def _extract_document_type_from_element(self, element) -> Optional[str]:
        """Estrae tipo documento dall'elemento."""
        text = element.text.lower()
        
        types = ['deliberazione', 'delibera', 'decreto', 'ordinanza', 'determina', 'dgr']
        for doc_type in types:
            if doc_type in text:
                return doc_type.title()
        
        return None

    def _extract_number_from_element(self, element) -> Optional[str]:
        """Estrae numero dall'elemento."""
        text = element.text
        
        # Pattern per numeri
        patterns = [
            r'\bn[\.\s]*(\d+)',  # n. 123
            r'\bnum[\.\s]*(\d+)',  # num 123
            r'\b(\d+)[\/\-](\d{4})',  # 123/2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if len(match.groups()) == 1 else match.group(0)
        
        return None

    def _extract_description_from_element(self, element) -> Optional[str]:
        """Estrae descrizione dall'elemento."""
        text = element.text.strip()
        if text:
            return text[:500] + ('...' if len(text) > 500 else '')
        return None

    def _calculate_confidence_score(
        self,
        title: str,
        search_params: SearchParameters,
        date: Optional[str] = None,
        document_type: Optional[str] = None,
        number: Optional[str] = None,
        description: Optional[str] = None
    ) -> float:
        """
        Calcola confidence score per un risultato.
        
        Returns:
            Confidence score 0.0-1.0
        """
        score = 0.0
        max_score = 0.0
        
        title_lower = title.lower()
        oggetto_lower = search_params.oggetto.lower()
        
        # Match oggetto (peso maggiore)
        oggetto_words = set(w for w in oggetto_lower.split() if len(w) > 3)
        title_words = set(w for w in title_lower.split() if len(w) > 3)
        
        if oggetto_words and title_words:
            word_match_ratio = len(oggetto_words & title_words) / len(oggetto_words | title_words)
            score += word_match_ratio * 0.4
        max_score += 0.4
        
        # Match numero
        if number and search_params.numero in number:
            score += 0.3
        max_score += 0.3
        
        # Match tipo documento
        if document_type and 'delibera' in document_type.lower():
            score += 0.1
        max_score += 0.1
        
        # Match anno
        if date and search_params.anno and search_params.anno in date:
            score += 0.1
        max_score += 0.1
        
        # Fuzzy match complessivo
        fuzzy_ratio = difflib.SequenceMatcher(None, title_lower, oggetto_lower).ratio()
        score += fuzzy_ratio * 0.1
        max_score += 0.1
        
        # Normalizza score
        final_score = score / max_score if max_score > 0 else 0.0
        
        return min(1.0, final_score)

    def search_decreto_selenium(
        self,
        seduta: str,
        numero: str,
        oggetto: str,
        anno: Optional[str] = None,
        data_sottoscrizione: Optional[str] = None,
        tipo_atto: Optional[str] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Metodo principale per ricerca decreto con Selenium.
        
        Args:
            seduta: Numero seduta
            numero: Numero deliberazione
            oggetto: Oggetto deliberazione
            anno: Anno (opzionale)
            data_sottoscrizione: Data sottoscrizione (opzionale)
            tipo_atto: Tipo atto (opzionale)
            
        Returns:
            Tuple (trovato: bool, url: str, confidence: float)
        """
        self.logger.info(f"Starting Selenium decreto search - Seduta: {seduta}, Numero: {numero}")
        
        start_time = time.time()
        self.operation_count += 1
        
        try:
            # 1. Setup driver
            if not self.driver:
                self.setup_driver()
            
            # 2. Navigate to search page
            if not self.navigate_to_search():
                return False, None, 0.0
            
            # 3. Prepare search parameters
            search_params = SearchParameters(
                seduta=seduta,
                numero=numero,
                oggetto=oggetto,
                anno=anno or "2025",
                data_sottoscrizione=data_sottoscrizione,
                tipo_atto=tipo_atto or "Deliberazione"
            )
            
            # 4. Fill search form
            if not self.fill_search_form(search_params):
                return False, None, 0.0
            
            # 5. Submit and wait for results
            if not self.submit_and_wait_results():
                return False, None, 0.0
            
            # 6. Extract results
            results = self.extract_results(search_params)
            
            # 7. Return best match
            if results:
                best_result = results[0]
                self.success_count += 1
                
                execution_time = time.time() - start_time
                self.total_execution_time += execution_time
                
                self.logger.info(
                    f"Selenium search completed successfully in {execution_time:.2f}s - "
                    f"Best match: {best_result.title[:50]}... (confidence: {best_result.confidence_score:.2f})"
                )
                
                return True, best_result.url, best_result.confidence_score
            else:
                self.logger.info("No matching results found")
                return False, None, 0.0
                
        except Exception as e:
            self.error_count += 1
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            self.logger.error(f"Selenium decreto search failed after {execution_time:.2f}s: {e}")
            
            if self.debug_mode:
                self.take_screenshot("search_error")
            
            return False, None, 0.0

    def get_performance_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche performance."""
        avg_execution_time = (
            self.total_execution_time / self.operation_count if self.operation_count > 0 else 0.0
        )
        
        return {
            'total_operations': self.operation_count,
            'successful_operations': self.success_count,
            'failed_operations': self.error_count,
            'success_rate': self.success_count / max(1, self.operation_count),
            'average_execution_time': avg_execution_time,
            'total_execution_time': self.total_execution_time,
            'screenshots_taken': self.screenshot_counter,
            'driver_active': self.driver is not None,
            'headless_mode': self.headless,
            'debug_mode': self.debug_mode
        }

    def close(self):
        """Cleanup resources e chiude WebDriver."""
        if self.driver:
            try:
                self.logger.info("Closing WebDriver...")
                self.driver.quit()
                self.driver = None
                self.wait = None
                self.logger.info("WebDriver closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
        if exc_type:
            self.logger.error(f"Session ended with error: {exc_type.__name__}: {exc_val}")
        else:
            stats = self.get_performance_stats()
            self.logger.info(f"Selenium session completed - Stats: {stats}")


if __name__ == "__main__":
    # Test example
    with SeleniumDecretoScraper(headless=False, debug_mode=True, log_level=LogLevel.DEBUG) as scraper:
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929",
            numero="17",
            oggetto="Approvazione piano triennale lavori pubblici",
            anno="2025"
        )
        
        print(f"Found: {found}")
        print(f"URL: {url}")
        print(f"Confidence: {confidence:.2f}")
        
        stats = scraper.get_performance_stats()
        print(f"Stats: {stats}")