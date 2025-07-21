#!/usr/bin/env python3
"""
ODG Liguria Workflow - Command Line Interface
Command line interface for all ODG workflow operations.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

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
                        self.print_success(f"  Seduta {detail['seduta']}, Numero {detail['numero']}: PUBLISHED")
                        if detail.get("url"):
                            self.print_info(f"    URL: {detail['url']}")
                        if detail.get("dgr_numero"):
                            self.print_info(f"    DGR: {detail['dgr_numero']}")

        except Exception as e:
            self.print_error(f"Publication check error: {str(e)}")
            return 1

        return 0

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
