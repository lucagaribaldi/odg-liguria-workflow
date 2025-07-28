"""
Decreto Scraper for checking publication status on decretidigitali.regione.liguria.it
Verifies if decreti from ODG are published on the official website.

Enhanced with:
- Input validation and sanitization
- Custom exception handling
- Context manager support
- Detailed request tracing
- Security improvements
"""

import logging
import requests
import time
from typing import Tuple, Optional, Dict, Any, Union, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import random
import json
from contextlib import contextmanager
import urllib3
import traceback
import sys
import os
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Custom Exceptions for specific error handling
class DecretoScraperError(Exception):
    """Base exception for decreto scraper errors."""
    pass


class DecretoValidationError(DecretoScraperError):
    """Raised when input validation fails."""
    pass


class DecretoConnectionError(DecretoScraperError):
    """Raised when connection to decreto website fails."""
    pass


class DecretoSSLError(DecretoScraperError):
    """Raised when SSL verification fails."""
    pass


class DecretoNotFoundError(DecretoScraperError):
    """Raised when decreto is not found on website."""
    pass


class DecretoParsingError(DecretoScraperError):
    """Raised when parsing response fails."""
    pass


class DecretoRateLimitError(DecretoScraperError):
    """Raised when rate limiting fails."""
    pass


class LogLevel(Enum):
    """Enhanced logging levels for decreto scraper."""
    SILENT = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


@dataclass
class ErrorReport:
    """Comprehensive error report structure."""
    timestamp: str
    error_type: str
    error_message: str
    operation: str
    input_data: Dict[str, Any]
    stack_trace: str
    request_details: Optional[Dict[str, Any]] = None
    response_details: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)
    severity: str = "medium"
    error_code: str = ""


@dataclass
class DebugContext:
    """Debug context for enhanced error reporting."""
    operation_id: str
    start_time: float
    operation_name: str
    input_parameters: Dict[str, Any]
    intermediate_results: List[Dict[str, Any]] = field(default_factory=list)
    debug_messages: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def add_debug_message(self, message: str):
        """Add a debug message with timestamp."""
        timestamp = datetime.now().isoformat()
        self.debug_messages.append(f"[{timestamp}] {message}")
    
    def add_intermediate_result(self, step: str, result: Any):
        """Add intermediate result for debugging."""
        self.intermediate_results.append({
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'result': str(result)[:500]  # Limit length for safety
        })
    
    def add_performance_metric(self, metric_name: str, value: float):
        """Add performance metric."""
        self.performance_metrics[metric_name] = value


class DecretoScraper:
    """Scraper for checking decreto publication status on Regione Liguria website.
    
    Enhanced with security features:
    - Input validation and sanitization
    - Regex escaping for user inputs
    - Context manager support for resource cleanup
    - Detailed request tracing and debugging
    - Custom exception handling
    - Advanced error reporting and logging
    - Comprehensive debug mode
    """
    
    # Input validation constants
    MAX_INPUT_LENGTH = 500
    MAX_URL_LENGTH = 2048
    ALLOWED_URL_SCHEMES = {'http', 'https'}
    
    # Debug and logging configuration
    _trace_requests = False
    _captured_responses = []
    _debug_mode = False
    _log_level = LogLevel.INFO
    _error_reports = []
    _debug_contexts = {}
    _performance_stats = {}
    
    # Enhanced logging configuration
    LOG_FORMAT_DETAILED = (
        "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - [%(thread)d] - %(message)s"
    )
    
    LOG_FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"

    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        rate_limit: float = 1.0,
        max_retries: int = 3,
        timeout: int = 30,
        verify_ssl: bool = True,
        allow_unverified_ssl: bool = True,
        debug_mode: bool = False,
        log_level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        enable_performance_tracking: bool = False,
    ):
        """
        Initialize the decreto scraper with enhanced debugging and logging.

        Args:
            base_url: Base URL for the decreto website
            rate_limit: Minimum seconds between requests
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates (primary attempt)
            allow_unverified_ssl: Allow fallback to unverified SSL connections
            debug_mode: Enable comprehensive debug mode
            log_level: Logging detail level
            log_file: Optional log file path
            enable_performance_tracking: Track performance metrics
        """
        # Validate initialization parameters
        self.base_url = self._validate_url(base_url, "base_url")
        self.rate_limit = self._validate_numeric(rate_limit, "rate_limit", min_val=0.1, max_val=60.0)
        self.max_retries = self._validate_numeric(max_retries, "max_retries", min_val=1, max_val=10)
        self.timeout = self._validate_numeric(timeout, "timeout", min_val=5, max_val=300)
        self.verify_ssl = verify_ssl
        self.allow_unverified_ssl = allow_unverified_ssl
        self.last_request_time = 0
        
        # SSL configuration tracking
        self.ssl_failed_attempts = 0
        self.ssl_fallback_active = False
        
        # Enhanced debug and logging configuration
        self.debug_mode = debug_mode
        self.log_level = log_level
        self.log_file = log_file
        self.enable_performance_tracking = enable_performance_tracking
        
        # Initialize debug tracking
        self.current_debug_context = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Setup enhanced logging
        self.logger = logging.getLogger(f"{__name__}_{self.session_id}")
        self.setup_enhanced_logging()
        
        # Initialize performance tracking
        if self.enable_performance_tracking:
            self.performance_start_time = time.time()
            self._log_debug("Performance tracking enabled")
        
        # Set debug mode if requested
        if self.debug_mode:
            self.enable_debug_mode(True)
            self._log_debug("Debug mode enabled - comprehensive logging activated")

        # Browser-like headers to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        # Common search patterns for decreto identification
        self.decreto_patterns = {
            "dgr": r"(?:DGR|D\.G\.R\.)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "dcr": r"(?:DCR|D\.C\.R\.)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "decreto": r"(?:DECRETO|Decreto)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "deliberazione": r"(?:Deliberazione|DELIBERAZIONE)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
        }

        # Initialize session with SSL configurations
        self._setup_session()
        
        # User agent rotation for better resilience
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        self.current_user_agent_index = 0

        # Final initialization log
        self._log_info(f"DecretoScraper initialized with session_id: {self.session_id}")
        if self.debug_mode:
            self._log_debug(f"Debug mode active - base_url: {self._sanitize_for_log(self.base_url)}")
            self._log_debug(f"SSL settings - verify_ssl: {self.verify_ssl}, allow_unverified_ssl: {self.allow_unverified_ssl}")
        
        # Test connectivity on initialization
        if self.debug_mode:
            self._test_site_connectivity()

    def _setup_session(self) -> None:
        """Setup requests session with SSL configuration and fallback strategies."""
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure SSL verification
        if not self.verify_ssl:
            self.session.verify = False
            # Disable SSL warnings when verification is disabled
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self._log_warning("SSL verification disabled - connections are not secure")
    
    def _create_unverified_session(self) -> requests.Session:
        """Create a new session with SSL verification disabled as fallback."""
        try:
            self._log_warning("Creating unverified SSL session as fallback")
            
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            session = requests.Session()
            session.verify = False
            session.headers.update(self.headers)
            
            # Rotate user agent
            self._rotate_user_agent()
            session.headers.update({"User-Agent": self.user_agents[self.current_user_agent_index]})
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            self._log_info("Unverified SSL session created successfully")
            return session
            
        except Exception as e:
            self._log_error(f"Failed to create unverified SSL session: {e}")
            raise DecretoSSLError(f"Cannot create unverified SSL session: {e}")
    
    def _rotate_user_agent(self) -> None:
        """Rotate to next user agent for better request resilience."""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        self._log_debug(f"Rotated to user agent index: {self.current_user_agent_index}")
    
    def _test_site_connectivity(self) -> bool:
        """Test connectivity to the decreto website."""
        try:
            self._log_debug("Testing site connectivity...")
            
            # First try with SSL verification
            test_url = self.base_url
            response = self.session.head(test_url, timeout=10)
            
            if response.status_code == 200:
                self._log_info("Site connectivity test passed with SSL verification")
                return True
            else:
                self._log_warning(f"Site returned status {response.status_code}")
                return False
                
        except requests.exceptions.SSLError as e:
            self._log_warning(f"SSL connectivity test failed: {e}")
            if self.allow_unverified_ssl:
                return self._test_unverified_connectivity()
            return False
            
        except Exception as e:
            self._log_error(f"Connectivity test failed: {e}")
            return False
    
    def _test_unverified_connectivity(self) -> bool:
        """Test connectivity with unverified SSL as fallback."""
        try:
            self._log_debug("Testing unverified SSL connectivity...")
            
            unverified_session = self._create_unverified_session()
            test_url = self.base_url
            response = unverified_session.head(test_url, timeout=10)
            
            if response.status_code == 200:
                self._log_info("Site connectivity test passed with unverified SSL")
                self.ssl_fallback_active = True
                return True
            else:
                self._log_warning(f"Unverified SSL test returned status {response.status_code}")
                return False
                
        except Exception as e:
            self._log_error(f"Unverified SSL connectivity test failed: {e}")
            return False

    def setup_enhanced_logging(self) -> None:
        """Setup enhanced logging configuration with multiple handlers and formats."""
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set logging level based on configuration
        log_levels = {
            LogLevel.SILENT: logging.CRITICAL + 1,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.WARN: logging.WARNING,
            LogLevel.INFO: logging.INFO,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.TRACE: logging.DEBUG - 5
        }
        self.logger.setLevel(log_levels.get(self.log_level, logging.INFO))
        
        # Console handler with appropriate format
        console_handler = logging.StreamHandler(sys.stdout)
        if self.debug_mode or self.log_level in [LogLevel.DEBUG, LogLevel.TRACE]:
            console_formatter = logging.Formatter(
                self.LOG_FORMAT_DETAILED,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            console_formatter = logging.Formatter(
                self.LOG_FORMAT_SIMPLE,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if self.log_file:
            try:
                # Ensure log directory exists
                log_path = Path(self.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
                file_formatter = logging.Formatter(
                    self.LOG_FORMAT_DETAILED,
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
                self._log_info(f"File logging enabled: {self.log_file}")
            except Exception as e:
                self._log_error(f"Failed to setup file logging: {e}")
        
        # Set up trace level if needed
        if self.log_level == LogLevel.TRACE:
            logging.addLevelName(logging.DEBUG - 5, 'TRACE')
    
    # ============================================================================
    # ENHANCED LOGGING METHODS
    # ============================================================================
    
    def _log_trace(self, message: str, **kwargs):
        """Log at TRACE level (most detailed)."""
        if self.log_level == LogLevel.TRACE:
            self.logger.log(logging.DEBUG - 5, message, **kwargs)
    
    def _log_debug(self, message: str, **kwargs):
        """Log at DEBUG level."""
        if self.log_level.value >= LogLevel.DEBUG.value:
            self.logger.debug(message, **kwargs)
    
    def _log_info(self, message: str, **kwargs):
        """Log at INFO level."""
        if self.log_level.value >= LogLevel.INFO.value:
            self.logger.info(message, **kwargs)
    
    def _log_warning(self, message: str, **kwargs):
        """Log at WARNING level."""
        if self.log_level.value >= LogLevel.WARN.value:
            self.logger.warning(message, **kwargs)
    
    def _log_error(self, message: str, **kwargs):
        """Log at ERROR level."""
        if self.log_level.value >= LogLevel.ERROR.value:
            self.logger.error(message, **kwargs)
    
    def _log_critical(self, message: str, **kwargs):
        """Log at CRITICAL level."""
        self.logger.critical(message, **kwargs)
    
    # ============================================================================
    # DEBUG MODE AND ERROR REPORTING
    # ============================================================================
    
    @classmethod
    def enable_debug_mode(cls, enable: bool = True):
        """Enable or disable comprehensive debug mode."""
        cls._debug_mode = enable
        if enable:
            cls._trace_requests = True
            cls._log_level = LogLevel.DEBUG
        
    def create_debug_context(self, operation_name: str, **input_params) -> DebugContext:
        """Create a new debug context for operation tracking."""
        operation_id = f"{operation_name}_{datetime.now().strftime('%H%M%S_%f')}"
        context = DebugContext(
            operation_id=operation_id,
            start_time=time.time(),
            operation_name=operation_name,
            input_parameters=input_params
        )
        
        if self.debug_mode:
            self._debug_contexts[operation_id] = context
            self._log_debug(f"Debug context created: {operation_id}")
        
        return context
    
    def finalize_debug_context(self, context: DebugContext):
        """Finalize debug context and log performance metrics."""
        if not context:
            return
            
        elapsed_time = time.time() - context.start_time
        context.add_performance_metric("total_duration", elapsed_time)
        
        if self.debug_mode:
            self._log_debug(f"Operation {context.operation_name} completed in {elapsed_time:.3f}s")
            if context.debug_messages:
                self._log_debug(f"Debug messages: {len(context.debug_messages)}")
                for msg in context.debug_messages[-5:]:  # Show last 5 messages
                    self._log_trace(f"  {msg}")
        
        # Store for later analysis
        self._performance_stats[context.operation_id] = context.performance_metrics
    
    def create_error_report(self, error: Exception, operation: str, input_data: Dict[str, Any], 
                          request_details: Optional[Dict] = None, 
                          response_details: Optional[Dict] = None) -> ErrorReport:
        """Create comprehensive error report."""
        
        # Determine error severity and suggestions
        severity = "low"
        suggestions = []
        error_code = ""
        
        if isinstance(error, DecretoValidationError):
            severity = "medium"
            error_code = "VALIDATION_ERROR"
            suggestions = [
                "Check input parameters for correct format and length",
                "Ensure all required fields are provided",
                "Verify date format is YYYY-MM-DD"
            ]
        elif isinstance(error, DecretoConnectionError):
            severity = "high"
            error_code = "CONNECTION_ERROR"
            suggestions = [
                "Check internet connectivity",
                "Verify decreto website is accessible",
                "Consider increasing timeout values",
                "Check if SSL verification should be disabled"
            ]
        elif isinstance(error, DecretoNotFoundError):
            severity = "low"
            error_code = "NOT_FOUND"
            suggestions = [
                "Verify decreto number and session are correct",
                "Check if decreto might not be published yet",
                "Try alternative search terms"
            ]
        elif isinstance(error, DecretoParsingError):
            severity = "medium"
            error_code = "PARSING_ERROR"
            suggestions = [
                "Website structure may have changed",
                "Check if response contains expected content",
                "Consider updating parsing logic"
            ]
        
        report = ErrorReport(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
            operation=operation,
            input_data=input_data,
            stack_trace=traceback.format_exc(),
            request_details=request_details,
            response_details=response_details,
            suggestions=suggestions,
            severity=severity,
            error_code=error_code
        )
        
        # Store error report
        self._error_reports.append(report)
        
        # Log error with appropriate detail level
        if self.debug_mode:
            self._log_error(f"Error Report Created: {error_code}")
            self._log_debug(f"Operation: {operation}")
            self._log_debug(f"Error: {error}")
            self._log_trace(f"Stack trace: {report.stack_trace}")
            if suggestions:
                self._log_info(f"Suggestions: {'; '.join(suggestions)}")
        else:
            self._log_error(f"{error_code}: {error}")
        
        return report
    
    def get_error_reports(self, operation: Optional[str] = None, 
                         severity: Optional[str] = None) -> List[ErrorReport]:
        """Get error reports filtered by operation or severity."""
        reports = self._error_reports
        
        if operation:
            reports = [r for r in reports if r.operation == operation]
        
        if severity:
            reports = [r for r in reports if r.severity == severity]
        
        return reports
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_operations = len(self._performance_stats)
        if total_operations == 0:
            return {"message": "No performance data available"}
        
        # Calculate aggregate statistics
        total_durations = [stats.get("total_duration", 0) for stats in self._performance_stats.values()]
        
        stats = {
            "session_id": self.session_id,
            "total_operations": total_operations,
            "average_duration": sum(total_durations) / len(total_durations) if total_durations else 0,
            "min_duration": min(total_durations) if total_durations else 0,
            "max_duration": max(total_durations) if total_durations else 0,
            "total_time": sum(total_durations),
            "operations": self._performance_stats
        }
        
        if self.enable_performance_tracking and hasattr(self, 'performance_start_time'):
            stats["session_duration"] = time.time() - self.performance_start_time
        
        return stats
    
    def save_debug_report(self, filename: Optional[str] = None) -> str:
        """Save comprehensive debug report to file."""
        if not filename:
            filename = f"decreto_debug_report_{self.session_id}.json"
        
        debug_data = {
            "session_info": {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "debug_mode": self.debug_mode,
                "log_level": self.log_level.name,
                "base_url": self.base_url
            },
            "error_reports": [
                {
                    "timestamp": report.timestamp,
                    "error_type": report.error_type,
                    "error_message": report.error_message,
                    "operation": report.operation,
                    "severity": report.severity,
                    "error_code": report.error_code,
                    "suggestions": report.suggestions
                }
                for report in self._error_reports
            ],
            "performance_stats": self.get_performance_stats(),
            "captured_responses": self._captured_responses,
            "debug_contexts": {
                ctx_id: {
                    "operation_name": ctx.operation_name,
                    "input_parameters": ctx.input_parameters,
                    "debug_messages": ctx.debug_messages,
                    "performance_metrics": ctx.performance_metrics
                }
                for ctx_id, ctx in self._debug_contexts.items()
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self._log_info(f"Debug report saved: {filename}")
            return filename
            
        except Exception as e:
            self._log_error(f"Failed to save debug report: {e}")
            raise DecretoScraperError(f"Could not save debug report: {e}")
    
    # ============================================================================
    # INPUT VALIDATION AND SECURITY METHODS
    # ============================================================================
    
    def _validate_string_input(self, value: Any, field_name: str, 
                              max_length: int = None, allow_empty: bool = False) -> str:
        """Validate and sanitize string input.
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            max_length: Maximum allowed length
            allow_empty: Whether empty strings are allowed
            
        Returns:
            Sanitized string
            
        Raises:
            DecretoValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise DecretoValidationError(f"{field_name} must be a string, got {type(value)}")
        
        if not allow_empty and not value.strip():
            raise DecretoValidationError(f"{field_name} cannot be empty")
        
        # Use default max length if not specified
        max_len = max_length or self.MAX_INPUT_LENGTH
        if len(value) > max_len:
            raise DecretoValidationError(f"{field_name} too long (max {max_len} chars)")
        
        # Sanitize: remove control characters and normalize whitespace
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\\t\\n\\r')
        sanitized = ' '.join(sanitized.split())
        
        return sanitized
    
    def _validate_url(self, url: str, field_name: str) -> str:
        """Validate URL format and scheme.
        
        Args:
            url: URL to validate
            field_name: Field name for error messages
            
        Returns:
            Validated URL
            
        Raises:
            DecretoValidationError: If URL is invalid
        """
        if not isinstance(url, str):
            raise DecretoValidationError(f"{field_name} must be a string")
        
        if len(url) > self.MAX_URL_LENGTH:
            raise DecretoValidationError(f"{field_name} too long")
        
        try:
            parsed = urlparse(url)
            if parsed.scheme not in self.ALLOWED_URL_SCHEMES:
                raise DecretoValidationError(f"{field_name} must use http or https")
            if not parsed.netloc:
                raise DecretoValidationError(f"{field_name} must have a valid domain")
        except Exception as e:
            raise DecretoValidationError(f"Invalid {field_name}: {e}")
        
        return url
    
    def _validate_numeric(self, value: Union[int, float], field_name: str,
                         min_val: Union[int, float] = None, 
                         max_val: Union[int, float] = None) -> Union[int, float]:
        """Validate numeric input.
        
        Args:
            value: Numeric value to validate
            field_name: Field name for error messages
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Validated numeric value
            
        Raises:
            DecretoValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise DecretoValidationError(f"{field_name} must be numeric")
        
        if min_val is not None and value < min_val:
            raise DecretoValidationError(f"{field_name} must be >= {min_val}")
        
        if max_val is not None and value > max_val:
            raise DecretoValidationError(f"{field_name} must be <= {max_val}")
        
        return value
    
    def _escape_regex_pattern(self, pattern: str) -> str:
        """Escape user input for safe use in regex patterns.
        
        Args:
            pattern: Pattern to escape
            
        Returns:
            Escaped pattern safe for regex use
        """
        return re.escape(pattern)
    
    def _sanitize_for_log(self, value: str, max_length: int = 100) -> str:
        """Sanitize string for safe logging.
        
        Args:
            value: String to sanitize
            max_length: Maximum length to log
            
        Returns:
            Sanitized string safe for logging
        """
        if not isinstance(value, str):
            return str(value)[:max_length]
        
        # Remove control characters and limit length
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\\t\\n\\r')
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length-3] + "..."
        
        return sanitized
    
    def _validate_date_format(self, date_str: str) -> str:
        """Validate date string format (YYYY-MM-DD).
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Validated date string
            
        Raises:
            DecretoValidationError: If date format is invalid
        """
        if not isinstance(date_str, str):
            raise DecretoValidationError("Date must be a string")
        
        try:
            # Parse to validate format
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError as e:
            raise DecretoValidationError(f"Invalid date format (expected YYYY-MM-DD): {e}")
    
    def validate_and_sanitize_input(self, input_value: str, field_name: str, 
                                   for_regex: bool = True, 
                                   max_length: int = 200,
                                   allow_empty: bool = False) -> str:
        """Validate and sanitize input specifically for safe regex usage.
        
        This method combines validation and sanitization to ensure input is safe
        for use in regex patterns and search operations.
        
        Args:
            input_value: The input string to validate and sanitize
            field_name: Field name for error messages
            for_regex: Whether to escape for regex usage (default: True)
            max_length: Maximum allowed length (default: 200)
            allow_empty: Whether empty strings are allowed (default: False)
            
        Returns:
            Validated and sanitized string safe for regex usage
            
        Raises:
            DecretoValidationError: If validation fails
        """
        # First, validate using existing string validation
        validated_input = self._validate_string_input(
            input_value, field_name, max_length, allow_empty
        )
        
        # Additional sanitization for regex usage
        if for_regex:
            # Remove potentially dangerous regex metacharacters if not escaped
            dangerous_chars = ['$', '^', '[', ']', '{', '}', '(', ')', '|', '*', '+', '?', '.', '\\']
            
            # Check for unescaped dangerous characters
            for char in dangerous_chars:
                if char in validated_input and f"\\{char}" not in validated_input:
                    # Log warning about dangerous characters
                    self._log_warning(f"Found unescaped regex metacharacter '{char}' in {field_name}")
            
            # Escape for safe regex usage
            sanitized_input = self._escape_regex_pattern(validated_input)
            
            # Log the sanitization for debugging
            if self.debug_mode and sanitized_input != validated_input:
                self._log_debug(f"Sanitized {field_name} for regex: '{validated_input}' -> '{sanitized_input}'")
        else:
            # Just remove control characters for non-regex usage
            sanitized_input = ''.join(
                char for char in validated_input 
                if ord(char) >= 32 or char in '\t\n\r'
            )
        
        # Additional validation for sanitized result
        if not sanitized_input and not allow_empty:
            raise DecretoValidationError(f"{field_name} cannot be empty after sanitization")
        
        # Final length check after sanitization
        if len(sanitized_input) > max_length:
            raise DecretoValidationError(
                f"{field_name} too long after sanitization (max {max_length} chars)"
            )
        
        # Log successful validation in debug mode
        if self.debug_mode:
            self._log_trace(f"Successfully validated and sanitized {field_name}: "
                          f"length={len(sanitized_input)}, for_regex={for_regex}")
        
        return sanitized_input
    
    # ============================================================================
    # CONTEXT MANAGER SUPPORT
    # ============================================================================
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with resource cleanup."""
        self.close()
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
            self.logger.debug("Session closed and resources cleaned up")
    
    # ============================================================================
    # REQUEST TRACING AND DEBUGGING
    # ============================================================================
    
    @classmethod
    def enable_request_tracing(cls, enable: bool = True):
        """Enable/disable detailed request tracing."""
        cls._trace_requests = enable
        cls._captured_responses = []
    
    @classmethod
    def get_captured_responses(cls) -> list:
        """Get list of captured responses for debugging."""
        return cls._captured_responses.copy()
    
    def _trace_request(self, method: str, url: str, **kwargs):
        """Trace request details for debugging."""
        if self._trace_requests:
            trace_info = {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'url': self._sanitize_for_log(url),
                'params': {k: self._sanitize_for_log(str(v)) for k, v in kwargs.get('params', {}).items()},
                'headers': {k: self._sanitize_for_log(str(v)) for k, v in kwargs.get('headers', {}).items()}
            }
            self.logger.debug(f"REQUEST TRACE: {json.dumps(trace_info, indent=2)}")
    
    def _trace_response(self, response: requests.Response):
        """Trace response details for debugging."""
        if self._trace_requests and response:
            trace_info = {
                'timestamp': datetime.now().isoformat(),
                'status_code': response.status_code,
                'url': self._sanitize_for_log(response.url),
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'content_preview': self._sanitize_for_log(response.text[:500])
            }
            self.logger.debug(f"RESPONSE TRACE: {json.dumps(trace_info, indent=2)}")
            self._captured_responses.append(trace_info)

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests with proper error handling."""
        try:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time

            if time_since_last_request < self.rate_limit:
                sleep_time = self.rate_limit - time_since_last_request
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

            self.last_request_time = time.time()
        except Exception as e:
            self.logger.error(f"Rate limiting failed: {e}")
            raise DecretoRateLimitError(f"Rate limiting error: {e}")

    def _make_request(self, url: str, params: dict = None) -> Optional[requests.Response]:
        """
        Make HTTP request with enhanced validation, retry logic and rate limiting.

        Args:
            url: URL to request (will be validated)
            params: Optional query parameters (will be sanitized)

        Returns:
            Response object or None if all retries failed
            
        Raises:
            DecretoValidationError: If inputs are invalid
            DecretoConnectionError: If connection fails permanently
        """
        # Validate inputs
        validated_url = self._validate_url(url, "request_url")
        sanitized_params = {}
        
        if params:
            if not isinstance(params, dict):
                raise DecretoValidationError("params must be a dictionary")
            
            # Sanitize parameters
            for key, value in params.items():
                clean_key = self._validate_string_input(str(key), f"param_key_{key}", max_length=100)
                clean_value = self._validate_string_input(str(value), f"param_value_{key}", max_length=500, allow_empty=True)
                sanitized_params[clean_key] = clean_value

        # Apply rate limiting
        self._rate_limit()
        
        # Trace request if enabled
        self._trace_request("GET", validated_url, params=sanitized_params)

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(
                    f"Making request to {self._sanitize_for_log(validated_url)} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

                response = self.session.get(
                    validated_url, 
                    params=sanitized_params, 
                    timeout=self.timeout, 
                    allow_redirects=True
                )

                response.raise_for_status()
                
                # Trace response if enabled
                self._trace_response(response)
                
                self.logger.debug(f"Request successful: {response.status_code}")
                return response

            except requests.exceptions.SSLError as e:
                self.ssl_failed_attempts += 1
                self._log_warning(f"SSL error (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                # Try SSL fallback if allowed and not already active
                if self.allow_unverified_ssl and not self.ssl_fallback_active:
                    try:
                        self._log_info("Attempting SSL fallback with unverified connection")
                        fallback_response = self._make_request_with_fallback(validated_url, sanitized_params)
                        if fallback_response:
                            self.ssl_fallback_active = True
                            self._log_info("SSL fallback successful")
                            return fallback_response
                    except Exception as fallback_error:
                        self._log_error(f"SSL fallback failed: {fallback_error}")
                
                last_exception = DecretoSSLError(f"SSL verification failed: {e}")
                
            except requests.exceptions.ConnectionError as e:
                last_exception = DecretoConnectionError(f"Connection failed: {e}")
                self.logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.Timeout as e:
                last_exception = DecretoConnectionError(f"Request timeout: {e}")
                self.logger.warning(f"Timeout error (attempt {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.HTTPError as e:
                last_exception = DecretoConnectionError(f"HTTP error: {e}")
                self.logger.warning(f"HTTP error (attempt {attempt + 1}/{self.max_retries}): {e}")
                
            except requests.exceptions.RequestException as e:
                last_exception = DecretoConnectionError(f"Request failed: {e}")
                self.logger.warning(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}")

            # Retry logic with exponential backoff
            if attempt < self.max_retries - 1:
                backoff_time = (2**attempt) + random.uniform(0, 1)
                self.logger.debug(f"Backing off for {backoff_time:.2f} seconds")
                time.sleep(backoff_time)

        # All retries failed - try one final SSL fallback attempt
        if self.allow_unverified_ssl and not self.ssl_fallback_active and self.ssl_failed_attempts > 0:
            try:
                self._log_info("Final attempt with SSL fallback before giving up")
                fallback_response = self._make_request_with_fallback(validated_url, sanitized_params)
                if fallback_response:
                    self.ssl_fallback_active = True
                    self._log_info("Final SSL fallback successful")
                    return fallback_response
            except Exception as final_error:
                self._log_error(f"Final SSL fallback failed: {final_error}")
        
        # All retries failed
        error_msg = f"All {self.max_retries} retry attempts failed for {self._sanitize_for_log(validated_url)}"
        self.logger.error(error_msg)
        
        if last_exception:
            raise last_exception
        else:
            raise DecretoConnectionError(error_msg)
    
    def _make_request_with_fallback(self, url: str, params: dict = None) -> Optional[requests.Response]:
        """Make request using unverified SSL session as fallback."""
        try:
            # Create unverified session
            fallback_session = self._create_unverified_session()
            
            self._log_debug(f"Making fallback request to {self._sanitize_for_log(url)}")
            
            response = fallback_session.get(
                url,
                params=params,
                timeout=self.timeout * 2,  # Double timeout for fallback
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            # Trace response if enabled
            self._trace_response(response)
            
            self._log_info(f"Fallback request successful: {response.status_code}")
            return response
            
        except Exception as e:
            self._log_error(f"Fallback request failed: {e}")
            raise DecretoSSLError(f"SSL fallback request failed: {e}")

    def verify_decreto_publication(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify if a decreto is published on the official website with comprehensive debugging.

        Args:
            seduta: Session number (will be validated and sanitized)
            numero: Decreto number (will be validated and sanitized) 
            oggetto: Decreto subject/object (will be validated and sanitized)
            data_seduta: Session date in YYYY-MM-DD format (optional, will be validated)

        Returns:
            Dictionary with publication info: {
                'found': bool,
                'url': str|None,
                'data_pubblicazione': str|None,
                'dgr_numero': str|None,
                'dgr_anno': str|None,
                'debug_info': dict (if debug_mode enabled)
            }
            
        Raises:
            DecretoValidationError: If input validation fails
            DecretoConnectionError: If connection to decreto website fails
            DecretoParsingError: If response parsing fails
        """
        # Create debug context for comprehensive tracking
        debug_context = self.create_debug_context(
            "verify_decreto_publication",
            seduta=seduta,
            numero=numero, 
            oggetto=oggetto[:50] + "..." if len(oggetto) > 50 else oggetto,
            data_seduta=data_seduta
        )
        
        input_data = {
            'seduta': seduta,
            'numero': numero,
            'oggetto': oggetto,
            'data_seduta': data_seduta
        }
        
        try:
            # Step 1: Input validation with detailed debugging
            debug_context.add_debug_message("Starting input validation")
            start_validation = time.time()
            
            try:
                # Use enhanced validation and sanitization before regex usage
                validated_seduta = self.validate_and_sanitize_input(seduta, "seduta", for_regex=True, max_length=50)
                validated_numero = self.validate_and_sanitize_input(numero, "numero", for_regex=True, max_length=50)
                validated_oggetto = self.validate_and_sanitize_input(oggetto, "oggetto", for_regex=False, max_length=1000)
                
                validated_data_seduta = None
                if data_seduta:
                    validated_data_seduta = self._validate_date_format(data_seduta)
                    
                debug_context.add_performance_metric("validation_time", time.time() - start_validation)
                debug_context.add_debug_message("Input validation completed successfully")
                debug_context.add_intermediate_result("validation", "All inputs validated successfully")
                
            except DecretoValidationError as e:
                error_report = self.create_error_report(e, "input_validation", input_data)
                debug_context.add_debug_message(f"Validation failed: {e}")
                raise
            except Exception as e:
                validation_error = DecretoValidationError(f"Input validation error: {e}")
                error_report = self.create_error_report(validation_error, "input_validation", input_data)
                debug_context.add_debug_message(f"Unexpected validation error: {e}")
                raise validation_error
            
            # Enhanced logging with debug context
            self._log_info(
                f"[{debug_context.operation_id}] Verifying decreto {self._sanitize_for_log(validated_numero)} "
                f"from seduta {self._sanitize_for_log(validated_seduta)}"
            )
            
            if self.debug_mode:
                self._log_debug(f"[{debug_context.operation_id}] Input parameters validated:")
                self._log_debug(f"  Seduta: {validated_seduta}")
                self._log_debug(f"  Numero: {validated_numero}")
                self._log_debug(f"  Oggetto length: {len(validated_oggetto)} chars")
                self._log_debug(f"  Data seduta: {validated_data_seduta}")

            # Initialize result structure
            result = {
                "found": False,
                "url": None,
                "data_pubblicazione": None,
                "dgr_numero": None,
                "dgr_anno": None,
            }
            
            # Add debug info if in debug mode
            if self.debug_mode:
                result["debug_info"] = {
                    "operation_id": debug_context.operation_id,
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "strategies_attempted": [],
                    "performance_metrics": {}
                }

            # Step 2: Try working scraper first
            debug_context.add_debug_message("Attempting working scraper strategy")
            start_working = time.time()
            
            try:
                working_result = self._search_with_working_scraper(
                    validated_seduta, validated_numero, validated_oggetto, validated_data_seduta
                )
                
                working_time = time.time() - start_working
                debug_context.add_performance_metric("working_scraper_time", working_time)
                
                if working_result.get("found"):
                    debug_context.add_debug_message("Working scraper found result")
                    debug_context.add_intermediate_result("working_scraper", "SUCCESS - Decreto found")
                    
                    if self.debug_mode:
                        result["debug_info"]["strategies_attempted"].append({
                            "strategy": "working_scraper",
                            "result": "success",
                            "duration": working_time
                        })
                    
                    self._log_info(
                        f"[{debug_context.operation_id}] Decreto found with working scraper in {working_time:.3f}s"
                    )
                    
                    # Merge debug info if present
                    if self.debug_mode:
                        working_result.update(result)
                    
                    self.finalize_debug_context(debug_context)
                    return working_result
                else:
                    debug_context.add_debug_message("Working scraper returned no results")
                    debug_context.add_intermediate_result("working_scraper", "No results found")
                    
            except DecretoConnectionError as e:
                error_report = self.create_error_report(e, "working_scraper", input_data)
                debug_context.add_debug_message(f"Working scraper connection error: {e}")
                if self.debug_mode:
                    result["debug_info"]["strategies_attempted"].append({
                        "strategy": "working_scraper", 
                        "result": "connection_error",
                        "error": str(e)
                    })
                raise
            except Exception as e:
                error_report = self.create_error_report(e, "working_scraper", input_data)
                debug_context.add_debug_message(f"Working scraper failed: {e}")
                self._log_warning(f"[{debug_context.operation_id}] Working scraper failed: {str(e)}")
                if self.debug_mode:
                    result["debug_info"]["strategies_attempted"].append({
                        "strategy": "working_scraper",
                        "result": "error", 
                        "error": str(e)
                    })
            
            # Step 3: Try multiple search strategies
            debug_context.add_debug_message("Starting fallback search strategies")
            search_strategies = [
                self._search_by_numero_and_date,
                self._search_by_oggetto_and_date,
                self._search_by_seduta_and_numero,
                self._search_by_numero,  # Fallback
            ]

            for i, strategy in enumerate(search_strategies, 1):
                strategy_name = strategy.__name__
                debug_context.add_debug_message(f"Trying strategy {i}/{len(search_strategies)}: {strategy_name}")
                start_strategy = time.time()
                
                try:
                    strategy_result = strategy(
                        validated_seduta, validated_numero, validated_oggetto, validated_data_seduta
                    )
                    
                    strategy_time = time.time() - start_strategy
                    debug_context.add_performance_metric(f"{strategy_name}_time", strategy_time)
                    
                    if strategy_result.get("found"):
                        debug_context.add_debug_message(f"Strategy {strategy_name} found result")
                        debug_context.add_intermediate_result(strategy_name, "SUCCESS - Decreto found")
                        
                        result.update(strategy_result)
                        
                        if self.debug_mode:
                            result["debug_info"]["strategies_attempted"].append({
                                "strategy": strategy_name,
                                "result": "success",
                                "duration": strategy_time
                            })
                        
                        self._log_info(
                            f"[{debug_context.operation_id}] Decreto found using {strategy_name} in {strategy_time:.3f}s"
                        )
                        
                        self.finalize_debug_context(debug_context)
                        return result
                    else:
                        debug_context.add_debug_message(f"Strategy {strategy_name} returned no results")
                        debug_context.add_intermediate_result(strategy_name, "No results found")
                        
                        if self.debug_mode:
                            result["debug_info"]["strategies_attempted"].append({
                                "strategy": strategy_name,
                                "result": "no_results",
                                "duration": strategy_time
                            })
                        
                except DecretoConnectionError as e:
                    error_report = self.create_error_report(e, strategy_name, input_data)
                    debug_context.add_debug_message(f"Strategy {strategy_name} connection error: {e}")
                    if self.debug_mode:
                        result["debug_info"]["strategies_attempted"].append({
                            "strategy": strategy_name,
                            "result": "connection_error", 
                            "error": str(e)
                        })
                    raise
                except DecretoParsingError as e:
                    error_report = self.create_error_report(e, strategy_name, input_data)
                    debug_context.add_debug_message(f"Strategy {strategy_name} parsing error: {e}")
                    if self.debug_mode:
                        result["debug_info"]["strategies_attempted"].append({
                            "strategy": strategy_name,
                            "result": "parsing_error",
                            "error": str(e)
                        })
                    raise
                except Exception as e:
                    error_report = self.create_error_report(e, strategy_name, input_data)
                    debug_context.add_debug_message(f"Strategy {strategy_name} failed: {e}")
                    self._log_warning(f"[{debug_context.operation_id}] Strategy {strategy_name} failed: {str(e)}")
                    if self.debug_mode:
                        result["debug_info"]["strategies_attempted"].append({
                            "strategy": strategy_name,
                            "result": "error",
                            "error": str(e)
                        })
                    continue

            # Step 4: All strategies exhausted - decreto not found
            debug_context.add_debug_message("All search strategies exhausted - decreto not found")
            debug_context.add_intermediate_result("final_result", "NOT_FOUND - All strategies failed")
            
            error_msg = (
                f"Decreto {validated_numero} from seduta {validated_seduta} not found "
                f"after trying {len(search_strategies)} search strategies"
            )
            
            not_found_error = DecretoNotFoundError(error_msg)
            error_report = self.create_error_report(not_found_error, "all_strategies", input_data)
            
            self._log_info(f"[{debug_context.operation_id}] {error_msg}")
            
            if self.debug_mode:
                result["debug_info"]["final_result"] = "not_found"
                result["debug_info"]["performance_metrics"] = debug_context.performance_metrics
                
                # Return result with debug info instead of raising exception
                self.finalize_debug_context(debug_context)
                return result
            else:
                self.finalize_debug_context(debug_context)
                raise not_found_error

        except (DecretoValidationError, DecretoConnectionError, DecretoParsingError, DecretoNotFoundError):
            # Specific errors - finalize context and re-raise
            self.finalize_debug_context(debug_context)
            raise
        except Exception as e:
            # Unexpected error - create error report and finalize context
            error_msg = f"Unexpected error verifying decreto {self._sanitize_for_log(numero)}: {str(e)}"
            unexpected_error = DecretoScraperError(error_msg)
            error_report = self.create_error_report(unexpected_error, "verify_decreto_publication", input_data)
            
            debug_context.add_debug_message(f"Unexpected error: {e}")
            self._log_error(f"[{debug_context.operation_id}] {error_msg}")
            
            self.finalize_debug_context(debug_context)
            raise unexpected_error

    def _search_by_numero_and_date(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by number and session date."""
        self.logger.debug(f"Searching by numero {numero} and date {data_seduta}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Build search params with date range
        params = {"numero": numero}
        if data_seduta:
            # Search in a date range around the session date
            params["data_da"] = data_seduta
            # Add 30 days for publication delay
            try:
                session_date = datetime.strptime(data_seduta, "%Y-%m-%d")
                end_date = session_date + timedelta(days=30)
                params["data_a"] = end_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        search_urls = [
            f"{self.base_url}/ricerca",
            f"{self.base_url}/search",
            f"{self.base_url}/decreti",
        ]

        for search_url in search_urls:
            try:
                response = self._make_request(search_url, params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result
            except Exception as e:
                self.logger.debug(f"Search by numero and date failed for {search_url}: {str(e)}")
                continue

        return result

    def _search_by_oggetto_and_date(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by object and session date."""
        self.logger.debug(f"Searching by oggetto and date {data_seduta}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Extract key terms from oggetto
        key_terms = self._extract_key_terms(oggetto)

        for term in key_terms:
            try:
                params = {"oggetto": term, "query": term}
                if data_seduta:
                    params["data_da"] = data_seduta
                    try:
                        session_date = datetime.strptime(data_seduta, "%Y-%m-%d")
                        end_date = session_date + timedelta(days=30)
                        params["data_a"] = end_date.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                response = self._make_request(f"{self.base_url}/ricerca", params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result
            except Exception as e:
                self.logger.debug(f"Search by oggetto and date failed for term '{term}': {str(e)}")
                continue

        return result

    def _search_by_numero(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by number."""
        self.logger.debug(f"Searching by numero: {numero}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Try different search endpoints
        search_urls = [
            f"{self.base_url}/ricerca",
            f"{self.base_url}/search",
            f"{self.base_url}/decreti",
        ]

        for search_url in search_urls:
            try:
                # Search parameters
                params = {"numero": numero, "query": numero, "search": numero}

                response = self._make_request(search_url, params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result

            except Exception as e:
                self.logger.debug(f"Search by numero failed for {search_url}: {str(e)}")
                continue

        return result

    def _search_by_oggetto(
        self, seduta: str, numero: str, oggetto: str
    ) -> Tuple[bool, Optional[str]]:
        """Search decreto by object/subject."""
        self.logger.debug(f"Searching by oggetto: {oggetto[:50]}...")

        # Extract key terms from oggetto
        key_terms = self._extract_key_terms(oggetto)

        for term in key_terms:
            try:
                params = {"oggetto": term, "query": term, "search": term}

                response = self._make_request(f"{self.base_url}/ricerca", params)
                if response:
                    found, url = self._parse_search_results(response, numero, oggetto)
                    if found:
                        return found, url

            except Exception as e:
                self.logger.debug(f"Search by oggetto failed for term '{term}': {str(e)}")
                continue

        return False, None

    def _search_by_seduta_and_numero(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by session and number combination."""
        self.logger.debug(f"Searching by seduta {seduta} and numero {numero}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            params = {
                "seduta": seduta,
                "numero": numero,
                "query": f"seduta {seduta} numero {numero}",
            }

            response = self._make_request(f"{self.base_url}/ricerca", params)
            if response:
                found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                if found_result.get("found"):
                    result.update(found_result)

        except Exception as e:
            self.logger.debug(f"Search by seduta and numero failed: {str(e)}")

        return result

    def _parse_search_results(
        self, response: requests.Response, numero: str, oggetto: str
    ) -> Tuple[bool, Optional[str]]:
        """Parse search results to find matching decreto."""
        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for decreto links or entries
            potential_matches = []

            # Common selectors for decreto listings
            selectors = [
                'a[href*="decreto"]',
                'a[href*="dgr"]',
                'a[href*="dcr"]',
                ".decreto-item a",
                ".result-item a",
                ".search-result a",
            ]

            for selector in selectors:
                links = soup.select(selector)
                potential_matches.extend(links)

            # If no specific selectors work, try all links
            if not potential_matches:
                potential_matches = soup.find_all("a", href=True)

            # Score and filter matches
            best_match = None
            best_score = 0

            for link in potential_matches:
                score = self._calculate_match_score(link, numero, oggetto)
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_score = score
                    best_match = link

            if best_match:
                href = best_match.get("href")
                if href:
                    if href.startswith("/"):
                        full_url = urljoin(self.base_url, href)
                    else:
                        full_url = href

                    self.logger.debug(f"Found match with score {best_score:.2f}: {full_url}")
                    return True, full_url

            return False, None

        except Exception as e:
            self.logger.warning(f"Error parsing search results: {str(e)}")
            return False, None

    def _calculate_match_score(self, link_element, numero: str, oggetto: str) -> float:
        """Calculate match score for a potential decreto link."""
        score = 0.0

        # Get link text and href
        link_text = link_element.get_text(strip=True).lower()
        link_href = link_element.get("href", "").lower()

        # Check for numero match
        if numero.lower() in link_text or numero.lower() in link_href:
            score += 0.5

        # Check for oggetto keywords
        oggetto_words = set(word.lower() for word in oggetto.split() if len(word) > 3)
        link_words = set(word.lower() for word in link_text.split())

        if oggetto_words and link_words:
            word_overlap = len(oggetto_words.intersection(link_words))
            score += (word_overlap / len(oggetto_words)) * 0.3

        # Check for decreto-related keywords
        decreto_keywords = ["decreto", "dgr", "dcr", "deliberazione"]
        for keyword in decreto_keywords:
            if keyword in link_text or keyword in link_href:
                score += 0.2
                break

        return score

    def _extract_key_terms(self, oggetto: str) -> list:
        """Extract key terms from oggetto for search."""
        # Remove common words and extract meaningful terms
        stop_words = {
            "di",
            "da",
            "in",
            "con",
            "su",
            "per",
            "tra",
            "fra",
            "a",
            "e",
            "il",
            "lo",
            "la",
            "i",
            "gli",
            "le",
            "un",
            "una",
            "uno",
            "del",
            "dello",
            "della",
            "dei",
            "degli",
            "delle",
            "al",
            "allo",
            "alla",
            "ai",
            "agli",
            "alle",
            "dal",
            "dallo",
            "dalla",
            "dai",
            "dagli",
            "dalle",
            "nel",
            "nello",
            "nella",
            "nei",
            "negli",
            "nelle",
            "sul",
            "sullo",
            "sulla",
            "sui",
            "sugli",
            "sulle",
        }

        words = re.findall(r"\b[a-zA-Zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{4,}\b", oggetto.lower())
        key_terms = [word for word in words if word not in stop_words]

        # Return top 5 most relevant terms
        return key_terms[:5]

    def _parse_search_results_enhanced(
        self, response: requests.Response, numero: str, oggetto: str
    ) -> Dict[str, Any]:
        """Parse search results with enhanced extraction of DGR info and dates."""
        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for decreto links or entries
            potential_matches = []

            # Common selectors for decreto listings
            selectors = [
                'a[href*="decreto"]',
                'a[href*="dgr"]',
                'a[href*="dcr"]',
                ".decreto-item",
                ".result-item",
                ".search-result",
                ".deliberazione-item",
            ]

            for selector in selectors:
                elements = soup.select(selector)
                potential_matches.extend(elements)

            # If no specific selectors work, try all links
            if not potential_matches:
                potential_matches = soup.find_all("a", href=True)

            # Score and filter matches
            best_match = None
            best_score = 0

            for element in potential_matches:
                match_info = self._extract_match_info_enhanced(element, numero, oggetto)

                if match_info["score"] > best_score and match_info["score"] > 0.3:
                    best_score = match_info["score"]
                    best_match = match_info

            if best_match:
                result["found"] = True
                result["url"] = best_match["url"]
                result["data_pubblicazione"] = best_match.get("data_pubblicazione")
                result["dgr_numero"] = best_match.get("dgr_numero")
                result["dgr_anno"] = best_match.get("dgr_anno")

                self.logger.debug(f"Found match with score {best_score:.2f}")

            return result

        except Exception as e:
            self.logger.warning(f"Error parsing enhanced search results: {str(e)}")
            return result

    def _extract_match_info_enhanced(self, element, numero: str, oggetto: str) -> Dict[str, Any]:
        """Extract enhanced match information including DGR number and dates."""
        info = {
            "score": 0.0,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            # Get element text and href
            element_text = element.get_text(strip=True).lower()
            element_href = element.get("href", "").lower()

            # Build full URL
            if element_href:
                if element_href.startswith("/"):
                    info["url"] = f"{self.base_url}{element_href}"
                elif element_href.startswith("http"):
                    info["url"] = element_href
                else:
                    info["url"] = f"{self.base_url}/{element_href}"

            # Score based on numero match
            if numero.lower() in element_text or numero.lower() in element_href:
                info["score"] += 0.5

            # Score based on oggetto keywords
            oggetto_words = set(word.lower() for word in oggetto.split() if len(word) > 3)
            element_words = set(word.lower() for word in element_text.split())

            if oggetto_words and element_words:
                word_overlap = len(oggetto_words.intersection(element_words))
                info["score"] += (word_overlap / len(oggetto_words)) * 0.3

            # Check for decreto-related keywords
            decreto_keywords = ["decreto", "dgr", "dcr", "deliberazione"]
            for keyword in decreto_keywords:
                if keyword in element_text or keyword in element_href:
                    info["score"] += 0.2
                    break

            # Extract DGR information from text
            dgr_info = self._extract_dgr_info(element_text)
            if dgr_info:
                info["dgr_numero"] = dgr_info.get("numero")
                info["dgr_anno"] = dgr_info.get("anno")
                info["score"] += 0.1

            # Extract publication date
            date_info = self._extract_date_info(element_text)
            if date_info:
                info["data_pubblicazione"] = date_info
                info["score"] += 0.1

            return info

        except Exception as e:
            self.logger.debug(f"Error extracting match info: {str(e)}")
            return info

    def _extract_dgr_info(self, text: str) -> Optional[Dict[str, str]]:
        """Extract DGR number and year from text."""
        dgr_patterns = [
            r"DGR\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"DGR\s+(\d+)\s*/\s*(\d{4})",
            r"Deliberazione\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"Delibera\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"n\.\s*(\d+)\s*/\s*(\d{4})",
            r"(\d+)\s*/\s*(\d{4})",
        ]

        for pattern in dgr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {"numero": match.group(1), "anno": match.group(2)}

        return None

    def _extract_date_info(self, text: str) -> Optional[str]:
        """Extract publication date from text."""
        date_patterns = [
            r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
            r"pubblicat[oa]\s+il\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"data\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"del\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalize date format
                normalized_date = self._normalize_date_string(date_str)
                if normalized_date:
                    return normalized_date

        return None

    def _normalize_date_string(self, date_str: str) -> Optional[str]:
        """Normalize date string to YYYY-MM-DD format."""
        try:
            # Handle different date formats
            date_patterns = [
                r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
                r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})",
            ]

            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    parts = match.groups()
                    if len(parts[2]) == 4:  # Year is last
                        day, month, year = parts
                    else:  # Year is first
                        year, month, day = parts

                    # Normalize to ISO format
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            return None

        except Exception as e:
            self.logger.debug(f"Error normalizing date '{date_str}': {str(e)}")
            return None

    def _search_with_working_scraper(self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None) -> Dict[str, Any]:
        """Search using the working scraper implementation."""
        self.logger.debug(f"Searching with working scraper for decreto {numero}")
        
        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }
        
        try:
            # Import the working scraper functionality
            from datetime import datetime
            
            # Extract year for search
            year = None
            if data_seduta:
                try:
                    date_obj = datetime.strptime(data_seduta, "%Y-%m-%d")
                    year = date_obj.year
                except:
                    year = 2025  # Default fallback
            else:
                year = 2025  # Default fallback
            
            # Search endpoint
            search_url = f"{self.base_url}/components/com_lddocs_iterg/getSearch.php"
            
            # Prepare search query
            search_terms = []
            if numero:
                search_terms.append(f"numero {numero}")
            if seduta:
                search_terms.append(f"seduta {seduta}")
            
            # Extract key terms from oggetto
            key_terms = self._extract_key_terms(oggetto)
            search_terms.extend(key_terms[:2])  # Add first 2 key terms
            
            query_text = " ".join(search_terms)
            
            # Elasticsearch query
            query_data = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["title", "content", "numero", "oggetto"],
                                    "type": "best_fields",
                                    "operator": "or"
                                }
                            },
                            {
                                "range": {
                                    "anno": {
                                        "gte": year - 1,
                                        "lte": year + 1
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "sort": [{"data_pubblicazione": {"order": "desc"}}]
            }
            
            # Make the search request
            response = self._make_enhanced_request(search_url, method="POST", json_data=query_data)
            
            if response and response.status_code == 200:
                # Parse the response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for decreto results
                decreto_links = soup.find_all('a', href=True)
                
                for link in decreto_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Check if this looks like a decreto
                    if any(keyword in text.lower() for keyword in ['decreto', 'deliberazione', 'dgr', 'dcr']):
                        # Extract information
                        if numero in text or seduta in text:
                            result["found"] = True
                            result["url"] = href if href.startswith('http') else f"{self.base_url}{href}"
                            
                            # Try to extract DGR number and date
                            dgr_match = re.search(r'(\d+)/(\d{4})', text)
                            if dgr_match:
                                result["dgr_numero"] = dgr_match.group(1)
                                result["dgr_anno"] = dgr_match.group(2)
                            
                            # Try to extract date
                            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
                            if date_match:
                                result["data_pubblicazione"] = self._normalize_date_string(date_match.group(1))
                            
                            break
            
            return result
            
        except Exception as e:
            self.logger.debug(f"Working scraper search failed: {str(e)}")
            return result

    def _make_enhanced_request(self, url: str, params: dict = None, method: str = "GET", json_data: dict = None) -> Optional[requests.Response]:
        """Enhanced request method supporting POST with JSON data."""
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries})")
                
                if method.upper() == "POST":
                    if json_data:
                        response = self.session.post(
                            url, 
                            json=json_data, 
                            timeout=self.timeout, 
                            allow_redirects=True
                        )
                    else:
                        response = self.session.post(
                            url, 
                            data=params, 
                            timeout=self.timeout, 
                            allow_redirects=True
                        )
                else:
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.timeout, 
                        allow_redirects=True
                    )

                response.raise_for_status()
                self.logger.debug(f"Request successful: {response.status_code}")
                return response

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    backoff_time = (2**attempt) + random.uniform(0, 1)
                    self.logger.debug(f"Backing off for {backoff_time:.2f} seconds")
                    time.sleep(backoff_time)
                else:
                    self.logger.error(f"All retry attempts failed for {url}")
                    return None

        return None
    
    def _make_enhanced_request_with_fallback(self, url: str, params: dict = None, method: str = "GET", json_data: dict = None) -> Optional[requests.Response]:
        """Make enhanced request using unverified SSL session as fallback."""
        try:
            # Create unverified session
            fallback_session = self._create_unverified_session()
            
            self._log_debug(f"Making enhanced fallback {method} request to {self._sanitize_for_log(url)}")
            
            if method.upper() == "POST":
                if json_data:
                    response = fallback_session.post(
                        url,
                        json=json_data,
                        timeout=self.timeout * 2,  # Double timeout for fallback
                        allow_redirects=True
                    )
                else:
                    response = fallback_session.post(
                        url,
                        data=params,
                        timeout=self.timeout * 2,
                        allow_redirects=True
                    )
            else:
                response = fallback_session.get(
                    url,
                    params=params,
                    timeout=self.timeout * 2,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            
            self._log_info(f"Enhanced fallback request successful: {response.status_code}")
            return response
            
        except Exception as e:
            self._log_error(f"Enhanced fallback request failed: {e}")
            raise DecretoSSLError(f"Enhanced SSL fallback request failed: {e}")

    def get_decreto_details(self, decreto_url: str) -> dict:
        """
        Get detailed information about a decreto from its URL.

        Args:
            decreto_url: URL of the decreto page

        Returns:
            Dictionary with decreto details
        """
        self.logger.info(f"Getting details for decreto: {decreto_url}")

        try:
            response = self._make_request(decreto_url)
            if not response:
                return {}

            soup = BeautifulSoup(response.text, "html.parser")

            details = {
                "url": decreto_url,
                "title": None,
                "numero": None,
                "data_pubblicazione": None,
                "oggetto": None,
                "status": None,
            }

            # Extract title
            title_element = soup.find("title") or soup.find("h1")
            if title_element:
                details["title"] = title_element.get_text(strip=True)

            # Try to extract structured data
            # This would need to be customized based on actual website structure

            return details

        except Exception as e:
            self.logger.error(f"Error getting decreto details: {str(e)}")
            return {}


def main():
    """Example usage of the DecretoScraper."""
    scraper = DecretoScraper()

    # Example verification
    try:
        found, url = scraper.verify_decreto_publication(
            seduta="3929",
            numero="1",
            oggetto="AZIENDA PUBBLICA DI SERVIZI ALLA PERSONA OPERE PIE RIUNITE DEVOTO MARINI SIVORI",
        )

        if found:
            print(f"Decreto found at: {url}")

            # Get additional details
            details = scraper.get_decreto_details(url)
            print(f"Details: {details}")
        else:
            print("Decreto not found")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
