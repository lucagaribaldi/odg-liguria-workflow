#!/usr/bin/env python3
"""
ODG Liguria Workflow - Command Line Interface
Command line interface for all ODG workflow operations.
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import List, Optional, Dict

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class ODGCLIError(Exception):
    """Custom exception for CLI errors."""

    pass


class ODGCLI:
    """Command Line Interface for ODG Liguria Workflow."""

    def __init__(self):
        """Initialize CLI with environment variables."""
        self.load_environment()
        self.setup_colors()

    def load_environment(self):
        """Load environment variables."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            print(
                "⚠️  python-dotenv not installed. "
                "Environment variables from .env file won't be loaded."
            )

        self.notion_token = os.getenv("NOTION_TOKEN")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Validate required environment variables
        if not self.notion_token or not self.notion_database_id:
            print(
                "⚠️  Warning: NOTION_TOKEN and NOTION_DATABASE_ID not set. "
                "Some commands may fail."
            )

    def setup_colors(self):
        """Setup color codes for terminal output."""
        self.COLORS = {
            "RED": "\033[91m",
            "GREEN": "\033[92m",
            "YELLOW": "\033[93m",
            "BLUE": "\033[94m",
            "MAGENTA": "\033[95m",
            "CYAN": "\033[96m",
            "WHITE": "\033[97m",
            "BOLD": "\033[1m",
            "UNDERLINE": "\033[4m",
            "END": "\033[0m",
        }

    def print_colored(self, text: str, color: str = "WHITE", bold: bool = False):
        """Print colored text to terminal."""
        color_code = self.COLORS.get(color.upper(), self.COLORS["WHITE"])
        if bold:
            color_code = self.COLORS["BOLD"] + color_code
        print(f"{color_code}{text}{self.COLORS['END']}")

    def print_header(self, title: str):
        """Print formatted header."""
        self.print_colored("=" * 60, "CYAN")
        self.print_colored(f"🏛️  {title}", "CYAN", bold=True)
        self.print_colored("=" * 60, "CYAN")

    def print_error(self, message: str):
        """Print error message."""
        self.print_colored(f"❌ Error: {message}", "RED", bold=True)

    def print_success(self, message: str):
        """Print success message."""
        self.print_colored(f"✅ {message}", "GREEN", bold=True)

    def print_info(self, message: str):
        """Print info message."""
        self.print_colored(f"ℹ️  {message}", "BLUE")

    def print_warning(self, message: str):
        """Print warning message."""
        self.print_colored(f"⚠️  {message}", "YELLOW")

    def validate_file_exists(self, file_path: str) -> Path:
        """Validate that a file exists."""
        path = Path(file_path)
        if not path.exists():
            raise ODGCLIError(f"File not found: {file_path}")
        return path

    def validate_pdf_file(self, file_path: str) -> Path:
        """Validate that a PDF file exists."""
        path = self.validate_file_exists(file_path)
        if not path.suffix.lower() == ".pdf":
            raise ODGCLIError(f"File must be a PDF: {file_path}")
        return path

    def command_process(self, args):
        """Process ODG PDF through complete workflow."""
        try:
            from workflow_orchestrator import ODGWorkflowOrchestrator

            self.print_header("PROCESSING ODG PDF")

            # Validate PDF file
            pdf_path = self.validate_pdf_file(args.pdf)
            self.print_info(f"Processing: {pdf_path}")

            # Initialize orchestrator
            orchestrator = ODGWorkflowOrchestrator(
                notion_token=self.notion_token,
                notion_database_id=self.notion_database_id,
                anthropic_api_key=self.anthropic_api_key,
            )

            # Run workflow
            result = orchestrator.process_odg_pdf(
                str(pdf_path),
                enable_scraping=not args.no_scraping,
                enable_synthesis=not args.no_synthesis,
                enable_notion_sync=not args.no_notion,
                scraping_mode=args.scraping_mode,
            )

            # Print results
            if result.success:
                self.print_success("Workflow completed successfully!")
                self.print_info(f"Processed {result.metrics.total_deliberations} deliberations")
                self.print_info(f"Success rate: {result.metrics.success_rate:.1f}%")
                self.print_info(f"Duration: {result.metrics.duration.total_seconds():.1f}s")

                if result.backup_path:
                    self.print_info(f"Backup saved: {result.backup_path}")
            else:
                self.print_error("Workflow failed!")
                for error in result.errors:
                    self.print_error(f"  - {error}")

            # Print detailed metrics
            if args.verbose:
                self.print_colored("\n📊 Detailed Metrics:", "MAGENTA", bold=True)
                metrics = result.metrics
                print(f"  Parsed: {metrics.parsed_successfully}/{metrics.total_deliberations}")
                print(f"  Scraped: {metrics.scraped_successfully}/{metrics.parsed_successfully}")
                print(
                    f"  Synthesized: {metrics.synthesized_successfully}/"
                    f"{metrics.parsed_successfully}"
                )
                print(
                    f"  Synced to Notion: {metrics.synced_to_notion}/"
                    f"{metrics.synthesized_successfully}"
                )

        except ODGCLIError as e:
            self.print_error(str(e))
            return 1
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return 1

        return 0

    def command_verify(self, args):
        """Verify publication status of deliberations."""
        try:
            from workflow_orchestrator import ODGWorkflowOrchestrator

            self.print_header("VERIFYING PUBLICATION STATUS")

            # Initialize orchestrator for daily verification
            orchestrator = ODGWorkflowOrchestrator(
                notion_token=self.notion_token,
                notion_database_id=self.notion_database_id,
                anthropic_api_key=self.anthropic_api_key,
            )

            # Run daily verification
            result = orchestrator.run_daily_verification()

            if "error" in result:
                self.print_error(f"Verification failed: {result['error']}")
                return 1

            self.print_success("Daily verification completed!")
            self.print_info(f"Verified: {result.get('verified_count', 0)} deliberations")
            self.print_info(f"Newly published: {result.get('newly_published', 0)} deliberations")

            if result.get("errors", 0) > 0:
                self.print_warning(f"Errors encountered: {result['errors']}")

        except Exception as e:
            self.print_error(f"Verification error: {str(e)}")
            return 1

        return 0

    def command_dashboard(self, args):
        """Generate HTML dashboard."""
        try:
            from dashboard_generator import DashboardGenerator

            self.print_header("GENERATING DASHBOARD")

            # Initialize dashboard generator
            dashboard = DashboardGenerator(
                notion_token=self.notion_token,
                notion_database_id=self.notion_database_id,
                backup_dir=args.backup_dir,
            )

            # Generate dashboard
            output_path = dashboard.generate_dashboard_html(
                output_path=args.output, data_source=args.source
            )

            self.print_success(f"Dashboard generated: {output_path}")

            if args.open:
                import webbrowser

                webbrowser.open(f"file://{os.path.abspath(output_path)}")
                self.print_info("Dashboard opened in browser")

        except Exception as e:
            self.print_error(f"Dashboard generation error: {str(e)}")
            return 1

        return 0

    def command_synthesis(self, args):
        """Generate detailed synthesis for specific deliberations."""
        try:
            from ai_synthesizer import AISynthesizer, SynthesisType

            self.print_header("GENERATING SYNTHESIS")

            # Parse synthesis type
            synthesis_type_map = {
                "executive": SynthesisType.EXECUTIVE,
                "esecutiva": SynthesisType.EXECUTIVE,
                "operational": SynthesisType.OPERATIONAL,
                "operativa": SynthesisType.OPERATIONAL,
                "communicative": SynthesisType.COMMUNICATIVE,
                "comunicativa": SynthesisType.COMMUNICATIVE,
            }

            synthesis_type = synthesis_type_map.get(args.type.lower(), SynthesisType.EXECUTIVE)

            # Initialize synthesizer
            synthesizer = AISynthesizer(anthropic_api_key=self.anthropic_api_key)

            # Process each deliberation number
            for numero in args.numbers:
                self.print_info(f"Generating synthesis for deliberation {numero}")

                # For this example, we'll need to load deliberation data
                # This would typically come from Notion or backup files
                deliberation = {
                    "numero": numero,
                    "seduta": args.seduta,
                    "oggetto": f"Deliberazione {numero} from seduta {args.seduta}",
                    "proponente": "Example Proponent",
                    "tipo_atto": "Deliberazione",
                }

                try:
                    result = synthesizer.generate_detailed_synthesis(deliberation, synthesis_type)

                    self.print_colored(
                        f"\n📝 Synthesis for Deliberation {numero}:", "MAGENTA", bold=True
                    )
                    self.print_colored(f"Type: {result.synthesis_type.value}", "CYAN")
                    self.print_colored(f"Confidence: {result.confidence:.1f}", "CYAN")
                    self.print_colored(f"AI Generated: {result.generated_with_ai}", "CYAN")

                    print("\n📋 Quick Summary:")
                    print(f"  {result.quick_summary}")

                    print("\n📄 Detailed Synthesis:")
                    print(f"  {result.detailed_synthesis}")

                    if result.extracted_info:
                        print("\n📊 Extracted Info:")
                        print(f"  Category: {result.extracted_info.category.value}")
                        print(f"  Urgency: {result.extracted_info.urgency}")
                        if result.extracted_info.budget:
                            print(f"  Budget: €{result.extracted_info.budget}")

                    print("\n" + "-" * 50)

                except Exception as e:
                    self.print_error(f"Synthesis failed for deliberation {numero}: {str(e)}")

        except Exception as e:
            self.print_error(f"Synthesis error: {str(e)}")
            return 1

        return 0

    def command_test_connection(self, args):
        """Test connection to all services."""
        try:
            from workflow_orchestrator import ODGWorkflowOrchestrator
            from ai_synthesizer import AISynthesizer
            from notion_integrator import NotionIntegrator

            self.print_header("TESTING CONNECTIONS")

            # Initialize orchestrator
            orchestrator = ODGWorkflowOrchestrator(
                notion_token=self.notion_token,
                notion_database_id=self.notion_database_id,
                anthropic_api_key=self.anthropic_api_key,
            )

            # Run health check
            health_status = orchestrator.health_check()

            self.print_info(f"Overall status: {health_status['overall_status']}")

            # Print component status
            for component, status in health_status["components"].items():
                if status["status"] == "healthy":
                    self.print_success(f"{component}: {status['message']}")
                elif status["status"] == "error":
                    self.print_error(f"{component}: {status['message']}")
                else:
                    self.print_warning(f"{component}: {status['message']}")

            # Test specific connections if requested
            if args.detailed:
                self.print_colored("\n🔍 Detailed Connection Tests:", "MAGENTA", bold=True)

                # Test Notion connection
                if self.notion_token and self.notion_database_id:
                    try:
                        notion = NotionIntegrator(self.notion_token, self.notion_database_id)
                        # Test database access
                        notion.get_sync_statistics()
                        self.print_success("Notion: Database accessible")
                        self.print_info(f"  Database ID: {self.notion_database_id}")
                    except Exception as e:
                        self.print_error(f"Notion: {str(e)}")

                # Test AI Synthesizer
                if self.anthropic_api_key:
                    try:
                        synthesizer = AISynthesizer(self.anthropic_api_key)
                        test_delib = {
                            "oggetto": "Test deliberation",
                            "numero": "1",
                            "tipo_atto": "Test",
                        }
                        summary = synthesizer.generate_quick_summary(test_delib)
                        self.print_success("AI Synthesizer: Working")
                        self.print_info(f"  Test summary: {summary[:50]}...")
                    except Exception as e:
                        self.print_error(f"AI Synthesizer: {str(e)}")

        except Exception as e:
            self.print_error(f"Connection test error: {str(e)}")
            return 1

        return 0

    def command_check_publication(self, args):
        """Check publication status of unpublished deliberations."""
        try:
            from workflow_orchestrator import ODGWorkflowOrchestrator

            self.print_header("CHECKING PUBLICATION STATUS")

            # Initialize orchestrator
            orchestrator = ODGWorkflowOrchestrator(
                notion_token=self.notion_token,
                notion_database_id=self.notion_database_id,
                anthropic_api_key=self.anthropic_api_key,
            )

            # Run publication check
            result = orchestrator.run_publication_check(days_back=args.days)

            if "error" in result:
                self.print_error(f"Publication check failed: {result['error']}")
                return 1

            self.print_success("Publication check completed!")
            self.print_info(f"Total checked: {result.get('total_checked', 0)}")
            self.print_info(f"Newly published: {result.get('newly_published', 0)}")
            self.print_info(f"Still unpublished: {result.get('still_unpublished', 0)}")

            if result.get("errors", 0) > 0:
                self.print_warning(f"Errors encountered: {result['errors']}")

            # Show details if available
            if result.get("details") and args.verbose:
                self.print_colored("\n📋 Publication Details:", "MAGENTA", bold=True)
                for detail in result["details"]:
                    status = detail.get("status", "unknown")
                    if status == "newly_published":
                        self.print_success(
                            f"  Seduta {detail['seduta']}, Numero {detail['numero']}: PUBLISHED")
                        if detail.get("url"):
                            self.print_info(f"    URL: {detail['url']}")
                        if detail.get("dgr_numero"):
                            self.print_info(f"    DGR: {detail['dgr_numero']}")

        except Exception as e:
            self.print_error(f"Publication check error: {str(e)}")
            return 1

        return 0

    def command_test_scraping(self, args):
        """Test decreto scraping functionality."""
        try:
            from decreto_scraper import DecretoScraper, LogLevel

            self.print_header("TESTING DECRETO SCRAPING")

            # Validate arguments
            if not args.seduta or not args.numero:
                raise ODGCLIError("Both --seduta and --numero are required for scraping test")

            # Initialize scraper with appropriate settings
            scraper = DecretoScraper(
                debug_mode=args.verbose,
                log_level=LogLevel.DEBUG if args.verbose else LogLevel.INFO,
                verify_ssl=not args.allow_unverified,
                timeout=args.timeout,
                rate_limit=args.rate_limit
            )

            self.print_info(f"Testing scraping for Seduta {args.seduta}, Numero {args.numero}")

            if args.oggetto:
                self.print_info(f"Object filter: {args.oggetto[:50]}...")

            # Perform scraping test
            start_time = time.time()

            scraping_result = scraper.verify_decreto_publication(
                str(args.seduta),
                str(args.numero),
                args.oggetto or "Test deliberation",  # Provide default object text
                args.data_seduta
            )

            duration = time.time() - start_time

            # Print results
            if scraping_result.get("found"):
                self.print_success(f"Decreto found in {duration:.2f}s!")
                self.print_info(f"URL: {scraping_result.get('url')}")

                if scraping_result.get("dgr_numero"):
                    self.print_info(
                        f"DGR: {scraping_result.get('dgr_numero')}/{scraping_result.get('dgr_anno', 'N/A')}")

                if scraping_result.get("data_pubblicazione"):
                    self.print_info(f"Published: {scraping_result.get('data_pubblicazione')}")
            else:
                self.print_warning(f"Decreto not found after {duration:.2f}s")

            # Show debug information if verbose
            if args.verbose and scraping_result.get("debug_info"):
                debug_info = scraping_result["debug_info"]
                self.print_colored("\n🐛 Debug Information:", "MAGENTA", bold=True)

                if debug_info.get("strategies_attempted"):
                    print(f"  Strategies attempted: {len(debug_info['strategies_attempted'])}")
                    for i, strategy in enumerate(debug_info["strategies_attempted"], 1):
                        print(f"    {i}. {strategy}")

                if debug_info.get("performance_metrics"):
                    metrics = debug_info["performance_metrics"]
                    print(f"  Total duration: {metrics.get('total_duration', 0):.2f}s")
                    print(f"  Requests made: {metrics.get('total_requests', 0)}")
                    print(f"  Average response time: {metrics.get('avg_response_time', 0):.2f}s")

            # Show SSL information if available
            if scraping_result.get("ssl_info"):
                ssl_info = scraping_result["ssl_info"]
                self.print_colored("\n🔒 SSL Information:", "CYAN", bold=True)
                print(f"  Fallback used: {ssl_info.get('fallback_used', False)}")
                print(f"  Failed attempts: {ssl_info.get('failed_attempts', 0)}")
                if ssl_info.get("certificate_error"):
                    self.print_warning(f"  Certificate error: {ssl_info['certificate_error']}")

        except ODGCLIError as e:
            self.print_error(str(e))
            return 1
        except Exception as e:
            self.print_error(f"Scraping test error: {str(e)}")
            if args.verbose:
                import traceback
                print(traceback.format_exc())
            return 1

        return 0

    def command_health_check(self, args):
        """Perform comprehensive system health check."""
        try:
            from system_monitor import SystemMonitor, AlertThresholds

            self.print_header("SYSTEM HEALTH CHECK")

            # Initialize system monitor
            thresholds = AlertThresholds(
                min_success_rate=args.min_success_rate,
                max_response_time_ms=args.max_response_time,
                ssl_expiry_warning_days=args.ssl_warning_days,
                consecutive_failures_threshold=args.failure_threshold
            )

            monitor = SystemMonitor(alert_thresholds=thresholds)

            # Perform comprehensive health check
            self.print_info("Running comprehensive health check...")
            health_status = monitor.check_decreto_site_health()

            # Display overall status
            overall_status = health_status["overall_status"]
            if overall_status == "healthy":
                self.print_success(f"Overall Status: {overall_status.upper()}")
            elif overall_status == "warning":
                self.print_warning(f"Overall Status: {overall_status.upper()}")
            elif overall_status == "degraded":
                self.print_warning(f"Overall Status: {overall_status.upper()}")
            else:
                self.print_error(f"Overall Status: {overall_status.upper()}")

            # Display key metrics
            response_time = health_status.get("response_time_ms", 0)
            self.print_info(f"Response Time: {response_time:.1f}ms")

            ssl_status = health_status.get("ssl_status", {})
            ssl_valid = ssl_status.get("valid", False)
            if ssl_valid:
                self.print_success("SSL Certificate: Valid")
                if ssl_status.get("expires_in_days"):
                    self.print_info(f"SSL Expires in: {ssl_status['expires_in_days']} days")
            else:
                self.print_error("SSL Certificate: Invalid")
                if ssl_status.get("error"):
                    self.print_error(f"SSL Error: {ssl_status['error']}")

            connectivity = health_status.get("connectivity", {})
            if connectivity.get("status") == "success":
                self.print_success(
                    f"Connectivity: OK ({connectivity.get('connection_time_ms', 0):.1f}ms)")
            else:
                self.print_error(
                    f"Connectivity: Failed - {connectivity.get('error', 'Unknown error')}")

            # Show recommendations
            recommendations = health_status.get("recommendations", [])
            if recommendations:
                self.print_colored("\n💡 Recommendations:", "YELLOW", bold=True)
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")

            # Show detailed information if verbose
            if args.verbose:
                self.print_colored("\n📊 Detailed Health Information:", "MAGENTA", bold=True)

                # Show SSL details
                if ssl_status:
                    print("\nSSL Certificate Details:")
                    if ssl_status.get("issuer"):
                        issuer = ssl_status["issuer"]
                        print(f"  Issuer: {issuer.get('organizationName', 'Unknown')}")
                    if ssl_status.get("subject"):
                        subject = ssl_status["subject"]
                        print(f"  Subject: {subject.get('commonName', 'Unknown')}")
                    if ssl_status.get("expires_date"):
                        print(f"  Expires: {ssl_status['expires_date']}")

                # Show scraping test details
                scraping_test = health_status.get("scraping_test", {})
                if scraping_test:
                    print("\nScraping Test Results:")
                    print(f"  Connectivity Test: {scraping_test.get('connectivity_test', False)}")
                    print(f"  Test Duration: {scraping_test.get('test_time_ms', 0):.1f}ms")
                    print(
                        f"  Scraper Initialized: {scraping_test.get('scraper_initialized', False)}")

            # Get and display current metrics summary
            if args.show_metrics:
                self.print_colored("\n📈 Current Metrics Summary:", "CYAN", bold=True)
                summary = monitor.get_current_metrics_summary()
                print(f"  Status: {summary.get('status', 'unknown')}")
                print(f"  Success Rate (24h): {summary.get('success_rate', 0):.1f}%")
                print(f"  Avg Response Time: {summary.get('avg_response_time_ms', 0):.1f}ms")
                print(f"  Total Checks: {summary.get('total_checks', 0)}")
                print(f"  SSL Errors (24h): {summary.get('ssl_errors_24h', 0)}")
                print(f"  Consecutive Failures: {summary.get('consecutive_failures', 0)}")

            # Generate report if requested
            if args.generate_report:
                self.print_info("\nGenerating HTML health report...")
                try:
                    monitor.generate_health_report(days_back=args.report_days)
                    self.print_success("HTML health report generated successfully")
                except Exception as e:
                    self.print_error(f"Failed to generate HTML report: {e}")

        except Exception as e:
            self.print_error(f"Health check error: {str(e)}")
            if args.verbose:
                import traceback
                print(traceback.format_exc())
            return 1

        return 0

    def command_fix_ssl(self, args):
        """Apply SSL fixes automatically."""
        try:
            self.print_header("APPLYING SSL FIXES")

            if args.allow_unverified:
                self.print_warning("SSL certificate verification will be disabled")

                # Test with unverified SSL
                from decreto_scraper import DecretoScraper, LogLevel

                self.print_info("Testing decreto scraper with SSL verification disabled...")

                scraper = DecretoScraper(
                    debug_mode=args.verbose,
                    log_level=LogLevel.INFO,
                    verify_ssl=False,  # Disable SSL verification
                    timeout=30
                )

                # Test connectivity
                try:
                    test_result = scraper._test_site_connectivity()
                    if test_result:
                        self.print_success("✅ Site connectivity test passed with SSL disabled")
                    else:
                        self.print_error("❌ Site connectivity test failed even with SSL disabled")
                        return 1
                except Exception as e:
                    self.print_error(f"Connectivity test failed: {e}")
                    return 1

                # Update configuration files to use unverified SSL
                if args.update_config:
                    self.print_info("Updating configuration files...")
                    try:
                        # Update config.yaml if it exists
                        config_path = Path("config.yaml")
                        if config_path.exists():
                            import yaml
                            with open(config_path, 'r') as f:
                                config = yaml.safe_load(f)

                            if not config:
                                config = {}

                            config.setdefault('decreto_scraper', {})['verify_ssl'] = False
                            config.setdefault('decreto_scraper', {})['allow_unverified_ssl'] = True

                            with open(config_path, 'w') as f:
                                yaml.dump(config, f, default_flow_style=False)

                            self.print_success("Updated config.yaml with SSL settings")
                        else:
                            self.print_warning("config.yaml not found, skipping config update")

                    except Exception as e:
                        self.print_error(f"Failed to update configuration: {e}")

            elif args.update_certificates:
                self.print_info("Updating system certificates...")
                # This would typically require system-level operations
                self.print_warning("Certificate update requires system administrator privileges")
                self.print_info("Recommended actions:")
                print("  1. Update system certificate bundle")
                print("  2. Install missing intermediate certificates")
                print("  3. Contact site administrator about certificate issues")

            elif args.test_fallback:
                self.print_info("Testing SSL fallback strategies...")

                from decreto_scraper import DecretoScraper, LogLevel

                # Test with various SSL configurations
                test_configs = [
                    {"verify_ssl": True, "name": "Standard SSL verification"},
                    {"verify_ssl": False, "name": "Disabled SSL verification"},
                ]

                for config in test_configs:
                    self.print_info(f"Testing: {config['name']}")
                    try:
                        scraper = DecretoScraper(
                            debug_mode=False,
                            log_level=LogLevel.ERROR,
                            verify_ssl=config["verify_ssl"],
                            timeout=10
                        )

                        result = scraper._test_site_connectivity()
                        if result:
                            self.print_success(f"  ✅ {config['name']}: Working")
                        else:
                            self.print_error(f"  ❌ {config['name']}: Failed")

                    except Exception as e:
                        self.print_error(f"  ❌ {config['name']}: Error - {e}")

            else:
                # Show available SSL fix options
                self.print_info("Available SSL fix options:")
                print("  --allow-unverified    Disable SSL certificate verification")
                print("  --update-certificates Update system certificate bundle")
                print("  --test-fallback       Test different SSL configurations")
                print("  --update-config       Update configuration files")

                self.print_warning("Please specify an SSL fix option to apply")
                return 1

        except Exception as e:
            self.print_error(f"SSL fix error: {str(e)}")
            if args.verbose:
                import traceback
                print(traceback.format_exc())
            return 1

        return 0

    def command_retry_failed(self, args):
        """Retry decreti that failed scraping."""
        try:
            self.print_header("RETRYING FAILED DECRETI")

            # This would typically load failed decreti from a log file or database
            # For now, we'll implement a placeholder that shows the concept

            if args.from_file:
                self.print_info(f"Loading failed decreti from: {args.from_file}")

                # Validate file exists
                failed_file = self.validate_file_exists(args.from_file)

                # Load failed decreti (assuming JSON format)
                import json
                try:
                    with open(failed_file, 'r') as f:
                        failed_decreti = json.load(f)
                except json.JSONDecodeError as e:
                    raise ODGCLIError(f"Invalid JSON in failed decreti file: {e}")

            else:
                # Get failed decreti from recent logs or database
                self.print_info("Searching for failed decreti in recent logs...")
                failed_decreti = self._get_failed_decreti_from_logs(args.days_back)

            if not failed_decreti:
                self.print_info("No failed decreti found to retry")
                return 0

            self.print_info(f"Found {len(failed_decreti)} failed decreti to retry")

            # Initialize scraper for retries
            from decreto_scraper import DecretoScraper, LogLevel

            scraper = DecretoScraper(
                debug_mode=args.verbose,
                log_level=LogLevel.INFO,
                verify_ssl=not args.allow_unverified,
                timeout=args.timeout,
                rate_limit=1.0  # Conservative rate limiting for retries
            )

            # Track retry results
            retry_stats = {
                "total": len(failed_decreti),
                "successful": 0,
                "still_failed": 0,
                "errors": 0
            }

            # Retry each failed decreto
            for i, decreto in enumerate(failed_decreti, 1):
                seduta = decreto.get("seduta", "")
                numero = decreto.get("numero", "")
                oggetto = decreto.get("oggetto", "")

                self.print_info(
                    f"Retrying {i}/{len(failed_decreti)}: Seduta {seduta}, Numero {numero}")

                try:
                    # Perform retry with specified max attempts
                    for attempt in range(args.max_retries):
                        try:
                            if attempt > 0:
                                import time
                                delay = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                                self.print_info(
                                    f"  Attempt {attempt + 1}/{args.max_retries} (after {delay}s delay)")
                                time.sleep(delay)

                            result = scraper.verify_decreto_publication(
                                str(seduta), str(numero), oggetto
                            )

                            if result.get("found"):
                                self.print_success(f"  ✅ Found: {result.get('url')}")
                                retry_stats["successful"] += 1

                                # Update the decreto with new information if requested
                                if args.update_notion and self.notion_token:
                                    self._update_notion_with_retry_result(decreto, result)

                                break  # Success, exit retry loop

                        except Exception as retry_error:
                            if attempt == args.max_retries - 1:  # Last attempt
                                self.print_error(
                                    f"  ❌ All {args.max_retries} attempts failed: {retry_error}")
                                retry_stats["still_failed"] += 1
                            else:
                                self.print_warning(
                                    f"  ⚠️ Attempt {attempt + 1} failed: {retry_error}")
                    else:
                        # All attempts failed
                        retry_stats["still_failed"] += 1

                except Exception as e:
                    self.print_error(f"  ❌ Error processing decreto: {e}")
                    retry_stats["errors"] += 1

            # Print final statistics
            self.print_colored("\n📊 Retry Results:", "MAGENTA", bold=True)
            print(f"  Total attempted: {retry_stats['total']}")
            print(f"  Successfully found: {retry_stats['successful']}")
            print(f"  Still failed: {retry_stats['still_failed']}")
            print(f"  Errors: {retry_stats['errors']}")

            success_rate = (retry_stats["successful"] / retry_stats["total"]
                            ) * 100 if retry_stats["total"] > 0 else 0
            print(f"  Success rate: {success_rate:.1f}%")

            if retry_stats["successful"] > 0:
                self.print_success(f"Successfully recovered {retry_stats['successful']} decreti!")

            if retry_stats["still_failed"] > 0:
                self.print_warning(
                    f"{retry_stats['still_failed']} decreti still failed - may need manual investigation")

        except ODGCLIError as e:
            self.print_error(str(e))
            return 1
        except Exception as e:
            self.print_error(f"Retry failed decreti error: {str(e)}")
            if args.verbose:
                import traceback
                print(traceback.format_exc())
            return 1

        return 0

    def command_generate_report(self, args):
        """Generate detailed error report."""
        try:
            self.print_header("GENERATING ERROR REPORT")

            # Import required modules
            from datetime import datetime

            self.print_info(f"Generating report for last {args.days} days")

            # Collect data from various sources
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "period_days": args.days,
                "scraping_errors": [],
                "ssl_errors": [],
                "health_metrics": [],
                "failed_decreti": [],
                "system_status": {}
            }

            # Collect scraping errors from logs
            if args.include_scraping:
                self.print_info("Collecting scraping error data...")
                report_data["scraping_errors"] = self._collect_scraping_errors(args.days)

            # Collect SSL errors
            if args.include_ssl:
                self.print_info("Collecting SSL error data...")
                report_data["ssl_errors"] = self._collect_ssl_errors(args.days)

            # Collect health metrics
            if args.include_health:
                self.print_info("Collecting health metrics...")
                try:
                    from system_monitor import SystemMonitor
                    monitor = SystemMonitor()

                    # Get current health status
                    health_status = monitor.check_decreto_site_health()
                    report_data["system_status"] = health_status

                    # Get metrics summary
                    metrics_summary = monitor.get_current_metrics_summary()
                    report_data["health_metrics"] = metrics_summary

                except Exception as e:
                    self.print_warning(f"Could not collect health metrics: {e}")

            # Generate report based on format
            if args.format == "html":
                report_path = self._generate_html_report(report_data, args.output)
            elif args.format == "json":
                report_path = self._generate_json_report(report_data, args.output)
            elif args.format == "markdown":
                report_path = self._generate_markdown_report(report_data, args.output)
            else:
                raise ODGCLIError(f"Unsupported report format: {args.format}")

            self.print_success(f"Report generated: {report_path}")

            # Open report if requested
            if args.open and args.format == "html":
                import webbrowser
                webbrowser.open(f"file://{os.path.abspath(report_path)}")
                self.print_info("Report opened in browser")

            # Print summary
            self.print_colored("\n📋 Report Summary:", "CYAN", bold=True)
            print(f"  Period: {args.days} days")
            print(f"  Format: {args.format.upper()}")
            print(f"  Scraping errors: {len(report_data['scraping_errors'])}")
            print(f"  SSL errors: {len(report_data['ssl_errors'])}")
            print(
                f"  System status: {report_data['system_status'].get('overall_status', 'unknown')}")

        except ODGCLIError as e:
            self.print_error(str(e))
            return 1
        except Exception as e:
            self.print_error(f"Report generation error: {str(e)}")
            if args.verbose:
                import traceback
                print(traceback.format_exc())
            return 1

        return 0

    # Helper methods for new commands

    def _get_failed_decreti_from_logs(self, days_back: int) -> List[Dict]:
        """Extract failed decreti from log files."""
        # This is a placeholder implementation
        # In a real system, this would parse log files to find failed scraping attempts
        return []

    def _update_notion_with_retry_result(self, decreto: Dict, result: Dict):
        """Update Notion database with retry result."""
        # This would update the Notion page with the successful scraping result
        pass

    def _collect_scraping_errors(self, days: int) -> List[Dict]:
        """Collect scraping errors from logs."""
        # This would parse log files to extract scraping errors
        return []

    def _collect_ssl_errors(self, days: int) -> List[Dict]:
        """Collect SSL errors from logs."""
        # This would parse log files to extract SSL errors
        return []

    def _generate_html_report(self, data: Dict, output_path: str) -> str:
        """Generate HTML error report."""
        from datetime import datetime

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ODG Error Report - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .error-section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #dc3545; }}
                .warning-section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ffc107; }}
                .success-section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #28a745; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏛️ ODG System Error Report</h1>
                <p>Generated: {data['timestamp']}</p>
                <p>Period: {data['period_days']} days</p>
            </div>
            
            <div class="{'error-section' if data['system_status'].get('overall_status') == 'critical' else 'warning-section' if data['system_status'].get('overall_status') == 'degraded' else 'success-section'}">
                <h2>System Status: {data['system_status'].get('overall_status', 'unknown').upper()}</h2>
                <div class="metric">Response Time: {data['system_status'].get('response_time_ms', 0):.1f}ms</div>
                <div class="metric">SSL Valid: {data['system_status'].get('ssl_status', {}).get('valid', False)}</div>
                <div class="metric">Connectivity: {data['system_status'].get('connectivity', {}).get('status', 'unknown')}</div>
            </div>
            
            <h2>📊 Error Summary</h2>
            <table>
                <tr><th>Error Type</th><th>Count</th><th>Status</th></tr>
                <tr><td>Scraping Errors</td><td>{len(data['scraping_errors'])}</td><td>{'⚠️' if len(data['scraping_errors']) > 0 else '✅'}</td></tr>
                <tr><td>SSL Errors</td><td>{len(data['ssl_errors'])}</td><td>{'⚠️' if len(data['ssl_errors']) > 0 else '✅'}</td></tr>
            </table>
            
            <h2>💡 Recommendations</h2>
            <ul>
        """

        recommendations = data['system_status'].get('recommendations', [])
        for rec in recommendations:
            html_content += f"<li>{rec}</li>"

        html_content += """
            </ul>
            
            <footer>
                <p><small>Generated by ODG CLI Tool</small></p>
            </footer>
        </body>
        </html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

    def _generate_json_report(self, data: Dict, output_path: str) -> str:
        """Generate JSON error report."""
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return output_path

    def _generate_markdown_report(self, data: Dict, output_path: str) -> str:
        """Generate Markdown error report."""
        from datetime import datetime

        md_content = f"""# ODG System Error Report

**Generated:** {data['timestamp']}  
**Period:** {data['period_days']} days  
**System Status:** {data['system_status'].get('overall_status', 'unknown').upper()}

## 📊 System Overview

- **Response Time:** {data['system_status'].get('response_time_ms', 0):.1f}ms
- **SSL Status:** {'✅ Valid' if data['system_status'].get('ssl_status', {}).get('valid', False) else '❌ Invalid'}
- **Connectivity:** {data['system_status'].get('connectivity', {}).get('status', 'unknown')}

## 🚨 Error Summary

| Error Type | Count | Status |
|------------|-------|--------|
| Scraping Errors | {len(data['scraping_errors'])} | {'⚠️' if len(data['scraping_errors']) > 0 else '✅'} |
| SSL Errors | {len(data['ssl_errors'])} | {'⚠️' if len(data['ssl_errors']) > 0 else '✅'} |

## 💡 Recommendations

"""

        recommendations = data['system_status'].get('recommendations', [])
        for i, rec in enumerate(recommendations, 1):
            md_content += f"{i}. {rec}\n"

        md_content += f"""
## 📈 Health Metrics

- **Success Rate (24h):** {data['health_metrics'].get('success_rate', 0):.1f}%
- **Average Response Time:** {data['health_metrics'].get('avg_response_time_ms', 0):.1f}ms
- **Total Checks:** {data['health_metrics'].get('total_checks', 0)}
- **SSL Errors (24h):** {data['health_metrics'].get('ssl_errors_24h', 0)}

---
*Report generated by ODG CLI Tool*
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return output_path

    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description="ODG Liguria Workflow - Command Line Interface",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s process --pdf data/input/ODG_10072025.pdf
  %(prog)s process --pdf file.pdf --no-scraping --verbose
  %(prog)s verify
  %(prog)s dashboard --output public/dashboard.html --open
  %(prog)s synthesis --seduta 3927 --numbers 1 2 3 --type esecutiva
  %(prog)s test-connection --detailed
  %(prog)s test-scraping --seduta 3930 --numero 1 --verbose
  %(prog)s health-check --verbose --show-metrics
  %(prog)s fix-ssl --allow-unverified --update-config
  %(prog)s retry-failed --max-retries 3 --allow-unverified
  %(prog)s generate-report --format html --output error_report.html
            """,
        )

        parser.add_argument("--version", action="version", version="ODG Liguria Workflow v1.0.0")

        # Create subparsers
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Process command
        process_parser = subparsers.add_parser(
            "process", help="Process ODG PDF through complete workflow"
        )
        process_parser.add_argument("--pdf", required=True, help="Path to ODG PDF file")
        process_parser.add_argument(
            "--no-scraping", action="store_true", help="Skip decreto scraping"
        )
        process_parser.add_argument("--no-synthesis", action="store_true", help="Skip AI synthesis")
        process_parser.add_argument("--no-notion", action="store_true", help="Skip Notion sync")
        process_parser.add_argument(
            "--scraping-mode",
            choices=["immediate", "deferred"],
            default="deferred",
            help="Scraping mode: immediate (during process) or deferred (separate check)"
        )
        process_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

        # Verify command
        verify_parser = subparsers.add_parser("verify", help="Verify publication status")
        verify_parser.add_argument(
            "--days", type=int, default=30, help="Days to check back (default: 30)"
        )

        # Dashboard command
        dashboard_parser = subparsers.add_parser("dashboard", help="Generate HTML dashboard")
        dashboard_parser.add_argument(
            "--output", "-o", default="dashboard.html", help="Output HTML file"
        )
        dashboard_parser.add_argument(
            "--source", choices=["backup", "notion"], default="backup", help="Data source"
        )
        dashboard_parser.add_argument(
            "--backup-dir", default="data/backups", help="Backup directory"
        )
        dashboard_parser.add_argument(
            "--open", action="store_true", help="Open dashboard in browser"
        )

        # Synthesis command
        synthesis_parser = subparsers.add_parser("synthesis", help="Generate detailed synthesis")
        synthesis_parser.add_argument("--seduta", required=True, help="Session number")
        synthesis_parser.add_argument(
            "--numbers", nargs="+", type=int, required=True, help="Deliberation numbers"
        )
        synthesis_parser.add_argument(
            "--type",
            choices=[
                "executive",
                "esecutiva",
                "operational",
                "operativa",
                "communicative",
                "comunicativa",
            ],
            default="executive",
            help="Synthesis type",
        )

        # Test connection command
        test_parser = subparsers.add_parser(
            "test-connection", help="Test connection to all services"
        )
        test_parser.add_argument(
            "--detailed", action="store_true", help="Run detailed connection tests"
        )

        # Check publication command
        check_parser = subparsers.add_parser(
            "check-publication", help="Check publication status of unpublished deliberations"
        )
        check_parser.add_argument(
            "--days", type=int, default=30, help="Days to check back (default: 30)"
        )
        check_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed results"
        )

        # Test scraping command
        test_scraping_parser = subparsers.add_parser(
            "test-scraping", help="Test decreto scraping functionality"
        )
        test_scraping_parser.add_argument(
            "--seduta", required=True, help="Session number (e.g., 3930)"
        )
        test_scraping_parser.add_argument(
            "--numero", required=True, help="Deliberation number (e.g., 1)"
        )
        test_scraping_parser.add_argument(
            "--oggetto", help="Object text for better matching"
        )
        test_scraping_parser.add_argument(
            "--data-seduta", help="Session date (YYYY-MM-DD format)"
        )
        test_scraping_parser.add_argument(
            "--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)"
        )
        test_scraping_parser.add_argument(
            "--rate-limit", type=float, default=1.0, help="Rate limit in seconds between requests (default: 1.0)"
        )
        test_scraping_parser.add_argument(
            "--allow-unverified", action="store_true", help="Allow unverified SSL certificates"
        )
        test_scraping_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed debug information"
        )

        # Health check command
        health_check_parser = subparsers.add_parser(
            "health-check", help="Perform comprehensive system health check"
        )
        health_check_parser.add_argument(
            "--min-success-rate", type=float, default=80.0,
            help="Minimum success rate threshold in %% (default: 80.0)"
        )
        health_check_parser.add_argument(
            "--max-response-time", type=float, default=10000.0,
            help="Maximum acceptable response time in ms (default: 10000.0)"
        )
        health_check_parser.add_argument(
            "--ssl-warning-days", type=int, default=30,
            help="Days before SSL expiry to warn (default: 30)"
        )
        health_check_parser.add_argument(
            "--failure-threshold", type=int, default=3,
            help="Consecutive failures before alert (default: 3)"
        )
        health_check_parser.add_argument(
            "--show-metrics", action="store_true", help="Show current metrics summary"
        )
        health_check_parser.add_argument(
            "--generate-report", action="store_true", help="Generate HTML health report"
        )
        health_check_parser.add_argument(
            "--report-days", type=int, default=7, help="Days to include in report (default: 7)"
        )
        health_check_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed health information"
        )

        # Fix SSL command
        fix_ssl_parser = subparsers.add_parser(
            "fix-ssl", help="Apply SSL fixes automatically"
        )
        fix_ssl_group = fix_ssl_parser.add_mutually_exclusive_group()
        fix_ssl_group.add_argument(
            "--allow-unverified", action="store_true",
            help="Disable SSL certificate verification (workaround)"
        )
        fix_ssl_group.add_argument(
            "--update-certificates", action="store_true",
            help="Update system certificate bundle"
        )
        fix_ssl_group.add_argument(
            "--test-fallback", action="store_true",
            help="Test different SSL configurations"
        )
        fix_ssl_parser.add_argument(
            "--update-config", action="store_true",
            help="Update configuration files with SSL settings"
        )
        fix_ssl_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed SSL fix information"
        )

        # Retry failed command
        retry_failed_parser = subparsers.add_parser(
            "retry-failed", help="Retry decreti that failed scraping"
        )
        retry_failed_parser.add_argument(
            "--max-retries", type=int, default=3, help="Maximum retry attempts (default: 3)"
        )
        retry_failed_parser.add_argument(
            "--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)"
        )
        retry_failed_parser.add_argument(
            "--allow-unverified", action="store_true", help="Allow unverified SSL certificates"
        )
        retry_failed_parser.add_argument(
            "--from-file", help="Load failed decreti from JSON file"
        )
        retry_failed_parser.add_argument(
            "--days-back", type=int, default=7,
            help="Days to look back for failed decreti (default: 7)"
        )
        retry_failed_parser.add_argument(
            "--update-notion", action="store_true",
            help="Update Notion with successful retry results"
        )
        retry_failed_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed retry information"
        )

        # Generate report command
        generate_report_parser = subparsers.add_parser(
            "generate-report", help="Generate detailed error report"
        )
        generate_report_parser.add_argument(
            "--output", "-o", required=True, help="Output file path"
        )
        generate_report_parser.add_argument(
            "--format", choices=["html", "json", "markdown"], default="html",
            help="Report format (default: html)"
        )
        generate_report_parser.add_argument(
            "--days", type=int, default=7, help="Days to include in report (default: 7)"
        )
        generate_report_parser.add_argument(
            "--include-scraping", action="store_true", default=True,
            help="Include scraping errors in report"
        )
        generate_report_parser.add_argument(
            "--include-ssl", action="store_true", default=True,
            help="Include SSL errors in report"
        )
        generate_report_parser.add_argument(
            "--include-health", action="store_true", default=True,
            help="Include health metrics in report"
        )
        generate_report_parser.add_argument(
            "--open", action="store_true", help="Open report in browser (HTML only)"
        )
        generate_report_parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed report generation info"
        )

        return parser

    def run(self, args: Optional[List[str]] = None):
        """Run CLI with provided arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        if not parsed_args.command:
            parser.print_help()
            return 1

        # Route to appropriate command handler
        command_handlers = {
            "process": self.command_process,
            "verify": self.command_verify,
            "dashboard": self.command_dashboard,
            "synthesis": self.command_synthesis,
            "test-connection": self.command_test_connection,
            "check-publication": self.command_check_publication,
            "test-scraping": self.command_test_scraping,
            "health-check": self.command_health_check,
            "fix-ssl": self.command_fix_ssl,
            "retry-failed": self.command_retry_failed,
            "generate-report": self.command_generate_report,
        }

        handler = command_handlers.get(parsed_args.command)
        if handler:
            return handler(parsed_args)
        else:
            self.print_error(f"Unknown command: {parsed_args.command}")
            return 1


def main():
    """Main entry point for CLI."""
    cli = ODGCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
