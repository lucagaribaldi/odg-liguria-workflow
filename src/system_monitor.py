"""
System Monitor for ODG Liguria Workflow.
Provides proactive monitoring of decree scraping infrastructure and health checks.
"""
import logging
import json
import ssl
import socket
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
from urllib.parse import urlparse
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decreto_scraper import DecretoScraper, LogLevel
@dataclass
class HealthMetrics:
    """Health metrics data structure."""
    timestamp: str
    site_status: str
    response_time_ms: float
    ssl_valid: bool
    ssl_expires_days: Optional[int]
    scraping_success_rate: float
    total_checks: int
    successful_connections: int
    failed_connections: int
    ssl_errors: int
    http_errors: int
    timeout_errors: int
    avg_response_time: float
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
@dataclass
class AlertThresholds:
    """Alert threshold configuration."""
    min_success_rate: float = 80.0  # Minimum success rate percentage
    max_response_time_ms: float = 10000.0  # Maximum acceptable response time
    ssl_expiry_warning_days: int = 30  # Days before SSL expiry to warn
    consecutive_failures_threshold: int = 3  # Consecutive failures before alert
    monitoring_interval_minutes: int = 15  # Minutes between health checks
class SystemMonitor:
    """Proactive system monitor for ODG workflow infrastructure."""
    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        metrics_file: str = "logs/health_metrics.json",
        alert_thresholds: Optional[AlertThresholds] = None,
        enable_email_alerts: bool = False,
        smtp_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the system monitor.
        Args:
            base_url: Base URL to monitor
            metrics_file: Path to store health metrics
            alert_thresholds: Alert threshold configuration
            enable_email_alerts: Whether to send email alerts
            smtp_config: SMTP configuration for email alerts
        """
        self.base_url = base_url
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.alert_thresholds = alert_thresholds or AlertThresholds()
        self.enable_email_alerts = enable_email_alerts
        self.smtp_config = smtp_config
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        # Initialize tracking data
        self.consecutive_failures = 0
        self.last_alert_time = None
        self.metrics_history = []
        # Load existing metrics
        self._load_metrics_history()
        self.logger.info(f"SystemMonitor initialized for {base_url}")
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    def check_decreto_site_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the decreto site.
        Returns:
            Dictionary with health status and metrics
        """
        self.logger.info("Starting comprehensive health check")
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "site_url": self.base_url,
            "overall_status": "unknown",
            "response_time_ms": None,
            "http_status": None,
            "ssl_status": {},
            "connectivity": {},
            "scraping_test": {},
            "recommendations": []
        }
        try:
            # 1. Basic connectivity test
            connectivity_result = self._test_basic_connectivity()
            health_status["connectivity"] = connectivity_result
            # 2. HTTP response test
            http_result = self._test_http_response()
            health_status.update({
                "response_time_ms": http_result.get("response_time_ms") or 0,
                "http_status": http_result.get("status"),
                "http_headers": http_result.get("headers", {})
            })
            # 3. SSL certificate check
            ssl_result = self.monitor_ssl_certificate()
            health_status["ssl_status"] = ssl_result
            # 4. Scraping functionality test
            scraping_result = self._test_scraping_functionality()
            health_status["scraping_test"] = scraping_result
            # 5. Determine overall status
            overall_status = self._determine_overall_status(
                connectivity_result, http_result, ssl_result, scraping_result
            )
            health_status["overall_status"] = overall_status
            # 6. Generate recommendations
            recommendations = self._generate_recommendations(health_status)
            health_status["recommendations"] = recommendations
            # 7. Update metrics
            self._update_health_metrics(health_status)
            # 8. Check for alerts
            self._check_and_send_alerts(health_status)
            self.logger.info(f"Health check completed: {overall_status}")
            return health_status
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            self.logger.error(error_msg)
            health_status.update({
                "overall_status": "error",
                "error": error_msg
            })
            return health_status
    def monitor_ssl_certificate(self) -> Dict[str, Any]:
        """
        Monitor SSL certificate validity and expiration.
        Returns:
            Dictionary with SSL certificate status
        """
        ssl_status = {
            "valid": False,
            "expires_in_days": None,
            "issuer": None,
            "subject": None,
            "expires_date": None,
            "error": None,
            "warnings": []
        }
        try:
            # Parse hostname from URL
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            self.logger.debug(f"Checking SSL certificate for {hostname}:{port}")
            # Create SSL context
            context = ssl.create_default_context()
            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    # Extract certificate information
                    ssl_status["valid"] = True
                    ssl_status["issuer"] = dict(x[0] for x in cert.get("issuer", []))
                    ssl_status["subject"] = dict(x[0] for x in cert.get("subject", []))
                    # Parse expiration date
                    not_after = cert.get("notAfter")
                    if not_after:
                        expires_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        ssl_status["expires_date"] = expires_date.isoformat()
                        # Calculate days until expiration
                        days_until_expiry = (expires_date - datetime.now()).days
                        ssl_status["expires_in_days"] = days_until_expiry
                        # Add warnings if certificate is expiring soon
                        if days_until_expiry <= self.alert_thresholds.ssl_expiry_warning_days:
                            warning = f"SSL certificate expires in {days_until_expiry} days"
                            ssl_status["warnings"].append(warning)
                            self.logger.warning(warning)
                        if days_until_expiry <= 0:
                            ssl_status["valid"] = False
                            ssl_status["error"] = "SSL certificate has expired"
            self.logger.debug("SSL certificate check completed successfully")
        except ssl.SSLError as e:
            ssl_status["error"] = f"SSL Error: {str(e)}"
            self.logger.error(f"SSL certificate check failed: {e}")
        except socket.timeout as e:
            ssl_status["error"] = f"Connection timeout: {str(e)}"
            self.logger.error(f"SSL certificate check timeout: {e}")
        except Exception as e:
            ssl_status["error"] = f"Unexpected error: {str(e)}"
            self.logger.error(f"SSL certificate check failed: {e}")
        return ssl_status
    def track_scraping_metrics(self, scraping_result: Dict[str, Any]) -> None:
        """
        Track scraping performance metrics.
        Args:
            scraping_result: Result from decreto scraping operation
        """
        try:
            timestamp = datetime.now().isoformat()
            # Extract metrics from scraping result
            metrics = {
                "timestamp": timestamp,
                "found": scraping_result.get("found", False),
                "response_time": scraping_result.get("debug_info", {}).get("performance_metrics", {}).get("total_duration", 0),
                "ssl_fallback_used": scraping_result.get("ssl_info", {}).get("fallback_used", False),
                "ssl_failed_attempts": scraping_result.get("ssl_info", {}).get("failed_attempts", 0),
                "strategies_attempted": len(scraping_result.get("debug_info", {}).get("strategies_attempted", [])),
                "validation_applied": scraping_result.get("validation_applied", {}),
                "error": scraping_result.get("error")
            }
            # Save to metrics file
            self._save_scraping_metrics(metrics)
            # Update internal tracking
            self._update_success_tracking(metrics)
            self.logger.debug(
                f"Scraping metrics tracked: success={metrics['found']}, time={metrics['response_time']}s")
        except Exception as e:
            self.logger.error(f"Failed to track scraping metrics: {e}")
    def generate_health_report(self, days_back: int = 7) -> str:
        """
        Generate comprehensive HTML health report.
        Args:
            days_back: Number of days to include in report
        Returns:
            HTML report string
        """
        try:
            # Get recent metrics
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_metrics = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
            ]
            # Calculate statistics
            stats = self._calculate_health_statistics(recent_metrics)
            # Generate HTML report
            html_report = self._generate_html_report(stats, days_back)
            # Save report to file
            report_path = self.metrics_file.parent / \
                f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            self.logger.info(f"Health report generated: {report_path}")
            return html_report
        except Exception as e:
            error_msg = f"Failed to generate health report: {e}"
            self.logger.error(error_msg)
            return f"<html><body><h1>Error</h1><p>{error_msg}</p></body></html>"
    def start_continuous_monitoring(self, interval_minutes: Optional[int] = None) -> None:
        """
        Start continuous monitoring in background thread.
        Args:
            interval_minutes: Minutes between checks (defaults to threshold setting)
        """
        interval = interval_minutes or self.alert_thresholds.monitoring_interval_minutes
        def monitor_loop():
            self.logger.info(f"Starting continuous monitoring (interval: {interval} minutes)")
            while True:
                try:
                    # Perform health check
                    health_status = self.check_decreto_site_health()
                    # Log status
                    status = health_status.get("overall_status", "unknown")
                    response_time = health_status.get("response_time_ms", 0)
                    self.logger.info(
                        f"Monitoring check: {status} (response: {response_time:.0f}ms)")
                    # Sleep until next check
                    time.sleep(interval * 60)
                except Exception as e:
                    self.logger.error(f"Monitoring loop error: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        self.logger.info("Continuous monitoring started in background thread")
    def get_current_metrics_summary(self) -> Dict[str, Any]:
        """
        Get current metrics summary for quick status check.
        Returns:
            Dictionary with current system metrics
        """
        try:
            # Get recent metrics (last 24 hours)
            cutoff_date = datetime.now() - timedelta(hours=24)
            recent_metrics = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
            ]
            if not recent_metrics:
                return {
                    "status": "no_data",
                    "message": "No recent metrics available",
                    "timestamp": datetime.now().isoformat()
                }
            # Calculate summary statistics
            total_checks = len(recent_metrics)
            successful_checks = sum(1 for m in recent_metrics if m.get("site_status") == "healthy")
            success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
            response_times = [m.get("response_time_ms", 0)
                              for m in recent_metrics if m.get("response_time_ms")]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            ssl_errors = sum(1 for m in recent_metrics if not m.get("ssl_valid", True))
            # Get latest SSL status
            latest_metric = recent_metrics[-1] if recent_metrics else {}
            ssl_expires_days = latest_metric.get("ssl_expires_days")
            summary = {
                "timestamp": datetime.now().isoformat(),
                "period_hours": 24,
                "total_checks": total_checks,
                "success_rate": round(success_rate, 1),
                "avg_response_time_ms": round(avg_response_time, 1),
                "ssl_valid": latest_metric.get("ssl_valid", False),
                "ssl_expires_in_days": ssl_expires_days,
                "ssl_errors_24h": ssl_errors,
                "consecutive_failures": self.consecutive_failures,
                "status": "healthy" if success_rate >= self.alert_thresholds.min_success_rate else "degraded"
            }
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    # Private helper methods
    def _test_basic_connectivity(self) -> Dict[str, Any]:
        """Test basic network connectivity."""
        try:
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            start_time = time.time()
            with socket.create_connection((hostname, port), timeout=10):
                connection_time = (time.time() - start_time) * 1000
            return {
                "status": "success",
                "connection_time_ms": round(connection_time, 2),
                "hostname": hostname,
                "port": port
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "hostname": parsed_url.hostname if parsed_url.hostname else "unknown",
                "port": parsed_url.port or 443
            }
    def _test_http_response(self) -> Dict[str, Any]:
        """Test HTTP response."""
        try:
            start_time = time.time()
            response = requests.head(self.base_url, timeout=30, allow_redirects=True)
            response_time = (time.time() - start_time) * 1000
            return {
                "status": response.status_code,
                "response_time_ms": round(response_time, 2),
                "headers": dict(response.headers),
                "success": response.status_code < 400
            }
        except requests.exceptions.SSLError as e:
            return {
                "status": "ssl_error",
                "error": str(e),
                "success": False
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "success": False
            }
    def _test_scraping_functionality(self) -> Dict[str, Any]:
        """Test basic scraping functionality."""
        try:
            # Create a test scraper
            test_scraper = DecretoScraper(
                debug_mode=False,
                log_level=LogLevel.ERROR,
                verify_ssl=False,  # Use fallback mode for testing
                timeout=30
            )
            # Test basic connectivity
            start_time = time.time()
            test_result = test_scraper._test_site_connectivity()
            test_time = (time.time() - start_time) * 1000
            return {
                "connectivity_test": test_result,
                "test_time_ms": round(test_time, 2),
                "ssl_fallback_available": hasattr(test_scraper, 'allow_unverified_ssl') and test_scraper.allow_unverified_ssl,
                "scraper_initialized": True
            }
        except Exception as e:
            return {
                "connectivity_test": False,
                "error": str(e),
                "scraper_initialized": False
            }
    def _determine_overall_status(
        self, connectivity: Dict, http: Dict, ssl: Dict, scraping: Dict
    ) -> str:
        """Determine overall system status."""
        # Critical failures
        if not connectivity.get("status") == "success":
            return "critical"
        if not http.get("success", False):
            return "critical"
        # Major issues
        if not ssl.get("valid", False):
            return "degraded"
        if not scraping.get("connectivity_test", False):
            return "degraded"
        # Performance issues
        response_time = http.get("response_time_ms") or 0
        if response_time > self.alert_thresholds.max_response_time_ms:
            return "degraded"
        # SSL expiry warning
        ssl_expires_days = ssl.get("expires_in_days")
        if ssl_expires_days and ssl_expires_days <= self.alert_thresholds.ssl_expiry_warning_days:
            return "warning"
        return "healthy"
    def _generate_recommendations(self, health_status: Dict) -> List[str]:
        """Generate recommendations based on health status."""
        recommendations = []
        # Connectivity recommendations
        if health_status["connectivity"].get("status") != "success":
            recommendations.append("Check network connectivity to decreto website")
        # HTTP recommendations
        if not health_status.get("http_status"):
            recommendations.append("Investigate HTTP response issues")
        elif (health_status.get("response_time_ms") or 0) > self.alert_thresholds.max_response_time_ms:
            recommendations.append("Consider performance optimization - response time is high")
        # SSL recommendations
        ssl_status = health_status.get("ssl_status", {})
        if not ssl_status.get("valid"):
            recommendations.append("SSL certificate validation failed - check certificate status")
        ssl_expires_days = ssl_status.get("expires_in_days")
        if ssl_expires_days and ssl_expires_days <= self.alert_thresholds.ssl_expiry_warning_days:
            recommendations.append(
                f"SSL certificate expires in {ssl_expires_days} days - renewal required")
        # Scraping recommendations
        scraping_status = health_status.get("scraping_test", {})
        if not scraping_status.get("connectivity_test"):
            recommendations.append(
                "Scraping functionality test failed - verify decreto scraper configuration")
        if not recommendations:
            recommendations.append("System is operating normally")
        return recommendations
    def _update_health_metrics(self, health_status: Dict) -> None:
        """Update health metrics tracking."""
        try:
            # Create metrics entry
            metrics = HealthMetrics(
                timestamp=health_status["timestamp"],
                site_status=health_status["overall_status"],
                response_time_ms=health_status.get("response_time_ms") or 0,
                ssl_valid=health_status.get("ssl_status", {}).get("valid", False),
                ssl_expires_days=health_status.get("ssl_status", {}).get("expires_in_days"),
                scraping_success_rate=self._calculate_recent_success_rate(),
                total_checks=len(self.metrics_history) + 1,
                successful_connections=1 if health_status["connectivity"].get(
                    "status") == "success" else 0,
                failed_connections=1 if health_status["connectivity"].get(
                    "status") != "success" else 0,
                ssl_errors=1 if not health_status.get("ssl_status", {}).get("valid", True) else 0,
                http_errors=1 if not health_status.get("http_status") else 0,
                timeout_errors=0,  # Would need to track this separately
                avg_response_time=health_status.get("response_time_ms") or 0
            )
            # Add to history
            self.metrics_history.append(metrics.to_dict())
            # Keep only recent metrics (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            self.metrics_history = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
            ]
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_history, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to update health metrics: {e}")
    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate from recent metrics."""
        if not self.metrics_history:
            return 0.0
        # Get last 24 hours of data
        cutoff_date = datetime.now() - timedelta(hours=24)
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
        ]
        if not recent_metrics:
            return 0.0
        successful = sum(1 for m in recent_metrics if m.get("site_status") == "healthy")
        return (successful / len(recent_metrics)) * 100
    def _check_and_send_alerts(self, health_status: Dict) -> None:
        """Check if alerts should be sent."""
        overall_status = health_status.get("overall_status")
        # Track consecutive failures
        if overall_status in ["critical", "degraded"]:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
        # Check if alert should be sent
        should_alert = (
            self.consecutive_failures >= self.alert_thresholds.consecutive_failures_threshold
            and self.enable_email_alerts
            and self.smtp_config
        )
        # Rate limit alerts (don't send more than once per hour)
        if should_alert and self.last_alert_time:
            time_since_last_alert = datetime.now() - self.last_alert_time
            if time_since_last_alert < timedelta(hours=1):
                should_alert = False
        if should_alert:
            self._send_alert_email(health_status)
            self.last_alert_time = datetime.now()
            self.logger.warning(f"Alert sent for {self.consecutive_failures} consecutive failures")
    def _send_alert_email(self, health_status: Dict) -> None:
        """Send alert email."""
        try:
            if not self.smtp_config:
                return
            # Create email content
            subject = f"ODG System Alert: {health_status.get('overall_status', 'unknown').upper()}"
            body = f"""
            ODG System Health Alert
            
            Status: {health_status.get('overall_status', 'unknown')}
            Timestamp: {health_status.get('timestamp', 'unknown')}
            Consecutive Failures: {self.consecutive_failures}
            
            Details:
            - Response Time: {health_status.get('response_time_ms', 0):.0f}ms
            - SSL Valid: {health_status.get('ssl_status', {}).get('valid', False)}
            - Connectivity: {health_status.get('connectivity', {}).get('status', 'unknown')}
            
            Recommendations:
            {'\n'.join(f"- {rec}" for rec in health_status.get('recommendations', []))}
            
            This is an automated alert from ODG System Monitor.
            """
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = self.smtp_config['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            # Send email
            with smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port']) as server:
                if self.smtp_config.get('use_tls'):
                    server.starttls()
                if self.smtp_config.get('username'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            self.logger.info("Alert email sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
    def _load_metrics_history(self) -> None:
        """Load existing metrics history."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    self.metrics_history = json.load(f)
                self.logger.info(f"Loaded {len(self.metrics_history)} historical metrics")
            else:
                self.metrics_history = []
        except Exception as e:
            self.logger.error(f"Failed to load metrics history: {e}")
            self.metrics_history = []
    def _save_scraping_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save scraping metrics to separate file."""
        try:
            scraping_metrics_file = self.metrics_file.parent / "scraping_metrics.json"
            # Load existing metrics
            scraping_history = []
            if scraping_metrics_file.exists():
                with open(scraping_metrics_file, 'r') as f:
                    scraping_history = json.load(f)
            # Add new metrics
            scraping_history.append(metrics)
            # Keep only recent data (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            scraping_history = [
                m for m in scraping_history
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
            ]
            # Save updated metrics
            with open(scraping_metrics_file, 'w') as f:
                json.dump(scraping_history, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save scraping metrics: {e}")
    def _update_success_tracking(self, metrics: Dict[str, Any]) -> None:
        """Update internal success tracking."""
        # This could be expanded to maintain more detailed internal state
        pass
    def _calculate_health_statistics(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics from health metrics."""
        if not metrics:
            return {"error": "No metrics available"}
        # Basic counts
        total_checks = len(metrics)
        healthy_checks = sum(1 for m in metrics if m.get("site_status") == "healthy")
        ssl_valid_checks = sum(1 for m in metrics if m.get("ssl_valid", False))
        # Response time statistics
        response_times = [m.get("response_time_ms", 0)
                          for m in metrics if m.get("response_time_ms")]
        stats = {
            "period": {
                "total_checks": total_checks,
                "first_check": metrics[0]["timestamp"] if metrics else None,
                "last_check": metrics[-1]["timestamp"] if metrics else None
            },
            "health": {
                "success_rate": (healthy_checks / total_checks) * 100 if total_checks > 0 else 0,
                "healthy_checks": healthy_checks,
                "unhealthy_checks": total_checks - healthy_checks
            },
            "ssl": {
                "valid_rate": (ssl_valid_checks / total_checks) * 100 if total_checks > 0 else 0,
                "valid_checks": ssl_valid_checks,
                "invalid_checks": total_checks - ssl_valid_checks
            },
            "performance": {
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "median_response_time": statistics.median(response_times) if response_times else 0
            }
        }
        return stats
    def _generate_html_report(self, stats: Dict[str, Any], days_back: int) -> str:
        """Generate HTML report from statistics."""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ODG System Health Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric-card {{ 
                    border: 1px solid #ddd; margin: 10px 0; padding: 15px; 
                    border-radius: 5px; background-color: #fafafa; 
                }}
                .healthy {{ border-left: 5px solid #28a745; }}
                .warning {{ border-left: 5px solid #ffc107; }}
                .critical {{ border-left: 5px solid #dc3545; }}
                .metric-value {{ font-size: 24px; font-weight: bold; }}
                .metric-label {{ color: #666; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ODG System Health Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Period: Last {days_back} days</p>
            </div>
            
            <div class="metric-card healthy">
                <h3>Overall Health</h3>
                <div class="metric-value">{stats.get('health', {}).get('success_rate', 0):.1f}%</div>
                <div class="metric-label">Success Rate</div>
                <p>Healthy checks: {stats.get('health', {}).get('healthy_checks', 0)} / {stats.get('period', {}).get('total_checks', 0)}</p>
            </div>
            
            <div class="metric-card">
                <h3>SSL Certificate Status</h3>
                <div class="metric-value">{stats.get('ssl', {}).get('valid_rate', 0):.1f}%</div>
                <div class="metric-label">SSL Valid Rate</div>
                <p>Valid checks: {stats.get('ssl', {}).get('valid_checks', 0)} / {stats.get('period', {}).get('total_checks', 0)}</p>
            </div>
            
            <div class="metric-card">
                <h3>Performance Metrics</h3>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Average Response Time</td><td>{stats.get('performance', {}).get('avg_response_time', 0):.0f} ms</td></tr>
                    <tr><td>Minimum Response Time</td><td>{stats.get('performance', {}).get('min_response_time', 0):.0f} ms</td></tr>
                    <tr><td>Maximum Response Time</td><td>{stats.get('performance', {}).get('max_response_time', 0):.0f} ms</td></tr>
                    <tr><td>Median Response Time</td><td>{stats.get('performance', {}).get('median_response_time', 0):.0f} ms</td></tr>
                </table>
            </div>
            
            <div class="metric-card">
                <h3>Report Period</h3>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Checks</td><td>{stats.get('period', {}).get('total_checks', 0)}</td></tr>
                    <tr><td>First Check</td><td>{stats.get('period', {}).get('first_check', 'N/A')}</td></tr>
                    <tr><td>Last Check</td><td>{stats.get('period', {}).get('last_check', 'N/A')}</td></tr>
                </table>
            </div>
            
            <footer>
                <p><small>Generated by ODG System Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
            </footer>
        </body>
        </html>
        """
        return html_template
def main():
    """Example usage of SystemMonitor."""
    # Configure alert thresholds
    thresholds = AlertThresholds(
        min_success_rate=85.0,
        max_response_time_ms=5000.0,
        ssl_expiry_warning_days=30,
        consecutive_failures_threshold=3,
        monitoring_interval_minutes=15
    )
    # Configure email alerts (optional)
    smtp_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_tls': True,
        'username': 'your_email@gmail.com',
        'password': 'your_app_password',
        'from_email': 'your_email@gmail.com',
        'to_email': 'admin@yourcompany.com'
    }
    # Initialize monitor
    monitor = SystemMonitor(
        alert_thresholds=thresholds,
        enable_email_alerts=False,  # Set to True to enable email alerts
        smtp_config=smtp_config
    )
    print("ODG System Monitor")
    print("==================")
    # Perform health check
    print("Performing health check...")
    health_status = monitor.check_decreto_site_health()
    print(f"Overall Status: {health_status['overall_status']}")
    print(f"Response Time: {health_status.get('response_time_ms', 0):.0f}ms")
    print(f"SSL Valid: {health_status.get('ssl_status', {}).get('valid', False)}")
    # Get metrics summary
    print("\nCurrent Metrics Summary:")
    summary = monitor.get_current_metrics_summary()
    print(f"Success Rate (24h): {summary.get('success_rate', 0)}%")
    print(f"Avg Response Time: {summary.get('avg_response_time_ms', 0):.0f}ms")
    # Generate health report
    print("\nGenerating health report...")
    monitor.generate_health_report(days_back=7)
    print("Health report generated successfully")
    # Optional: Start continuous monitoring
    # monitor.start_continuous_monitoring(interval_minutes=15)
    # print("Continuous monitoring started")
if __name__ == "__main__":
    main()

