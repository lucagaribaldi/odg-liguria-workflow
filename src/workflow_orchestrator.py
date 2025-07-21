"""
Workflow Orchestrator for ODG Liguria Workflow.
Coordinates the complete workflow: PDF → Parse → Scrape → Synthesize → Notion.
"""

import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import traceback

from pdf_parser import ODGPDFParser
from decreto_scraper import DecretoScraper
from ai_synthesizer import AISynthesizer, SynthesisType
from notion_integrator import NotionIntegrator, SyncDirection


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution."""

    total_deliberations: int = 0
    parsed_successfully: int = 0
    scraped_successfully: int = 0
    synthesized_successfully: int = 0
    synced_to_notion: int = 0
    errors: int = 0
    start_time: datetime = None
    end_time: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

    @property
    def duration(self) -> timedelta:
        """Calculate workflow duration."""
        end = self.end_time or datetime.now()
        return end - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_deliberations == 0:
            return 0.0
        return (self.synced_to_notion / self.total_deliberations) * 100

    @property
    def parsing_rate(self) -> float:
        """Calculate parsing success rate."""
        if self.total_deliberations == 0:
            return 0.0
        return (self.parsed_successfully / self.total_deliberations) * 100

    @property
    def scraping_rate(self) -> float:
        """Calculate scraping success rate."""
        if self.parsed_successfully == 0:
            return 0.0
        return (self.scraped_successfully / self.parsed_successfully) * 100

    @property
    def synthesis_rate(self) -> float:
        """Calculate synthesis success rate."""
        if self.parsed_successfully == 0:
            return 0.0
        return (self.synthesized_successfully / self.parsed_successfully) * 100

    @property
    def notion_sync_rate(self) -> float:
        """Calculate Notion sync success rate."""
        if self.synthesized_successfully == 0:
            return 0.0
        return (self.synced_to_notion / self.synthesized_successfully) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            **asdict(self),
            "duration_seconds": self.duration.total_seconds(),
            "success_rate": self.success_rate,
            "parsing_rate": self.parsing_rate,
            "scraping_rate": self.scraping_rate,
            "synthesis_rate": self.synthesis_rate,
            "notion_sync_rate": self.notion_sync_rate,
        }


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""

    success: bool
    metrics: WorkflowMetrics
    deliberations: List[Dict]
    errors: List[str]
    backup_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "metrics": self.metrics.to_dict(),
            "deliberations_count": len(self.deliberations),
            "errors": self.errors,
            "backup_path": self.backup_path,
            "timestamp": datetime.now().isoformat(),
        }


class ODGWorkflowOrchestrator:
    """Main orchestrator for the ODG workflow."""

    def __init__(
        self,
        notion_token: str,
        notion_database_id: str,
        anthropic_api_key: Optional[str] = None,
        backup_dir: str = "data/backups",
    ):
        """
        Initialize the workflow orchestrator.

        Args:
            notion_token: Notion API token
            notion_database_id: Notion database ID
            anthropic_api_key: Optional Anthropic API key
            backup_dir: Directory for backup files
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Initialize components
        try:
            self.pdf_parser = ODGPDFParser()
            self.decreto_scraper = DecretoScraper()
            self.ai_synthesizer = AISynthesizer(anthropic_api_key=anthropic_api_key)
            self.notion_integrator = NotionIntegrator(
                token=notion_token, database_id=notion_database_id
            )

            self.logger.info("ODGWorkflowOrchestrator initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {str(e)}")
            raise

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def process_odg_pdf(
        self,
        pdf_path: str,
        enable_scraping: bool = True,
        enable_synthesis: bool = True,
        enable_notion_sync: bool = True,
        scraping_mode: str = "immediate",  # "immediate" or "deferred"
    ) -> WorkflowResult:
        """
        Process a complete ODG PDF through the entire workflow.

        Args:
            pdf_path: Path to the PDF file
            enable_scraping: Whether to enable decreto scraping
            enable_synthesis: Whether to enable AI synthesis
            enable_notion_sync: Whether to sync to Notion
            scraping_mode: "immediate" or "deferred" scraping

        Returns:
            WorkflowResult object with metrics and results
        """
        metrics = WorkflowMetrics()
        deliberations = []
        errors = []

        try:
            self.logger.info(f"Starting workflow for PDF: {pdf_path}")

            # Step 1: Parse PDF
            self.logger.info("Step 1: Parsing PDF")
            try:
                pdf_result = self.pdf_parser.parse_odg(pdf_path)
                deliberations = pdf_result.get("deliberations", [])
                session_info = pdf_result.get("session_info", {})

                metrics.total_deliberations = len(deliberations)
                metrics.parsed_successfully = len(deliberations)

                self.logger.info(f"Parsed {len(deliberations)} deliberations from PDF")

            except Exception as e:
                error_msg = f"PDF parsing failed: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                metrics.errors += 1

                return WorkflowResult(
                    success=False, metrics=metrics, deliberations=[], errors=errors
                )

            # Step 2: Generate AI synthesis (if enabled)
            if enable_synthesis:
                self.logger.info("Step 2: Generating AI synthesis")
                deliberations = self._generate_synthesis(deliberations, metrics, errors)

            # Step 3: Sync to Notion (if enabled)
            if enable_notion_sync:
                self.logger.info("Step 3: Syncing to Notion")
                deliberations = self._sync_to_notion(deliberations, session_info, metrics, errors)

            # Step 4: Scrape decreto status (if enabled and mode is immediate)
            if enable_scraping and scraping_mode == "immediate":
                self.logger.info("Step 4: Scraping decreto status (immediate)")
                deliberations = self._scrape_decreto_status(
                    deliberations, session_info, metrics, errors
                )

            # Step 5: Create backup
            self.logger.info("Step 5: Creating backup")
            backup_path = self._create_backup(deliberations, session_info, metrics)

            # Finalize metrics
            metrics.end_time = datetime.now()

            # Determine overall success
            success = (
                metrics.errors == 0 and metrics.synced_to_notion == metrics.total_deliberations
            )

            self.logger.info(
                f"Workflow completed. Success: {success}, "
                f"Success rate: {metrics.success_rate:.1f}%"
            )

            return WorkflowResult(
                success=success,
                metrics=metrics,
                deliberations=deliberations,
                errors=errors,
                backup_path=backup_path,
            )

        except Exception as e:
            error_msg = f"Workflow failed with unexpected error: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())

            errors.append(error_msg)
            metrics.errors += 1
            metrics.end_time = datetime.now()

            return WorkflowResult(
                success=False, metrics=metrics, deliberations=deliberations, errors=errors
            )

    def _scrape_decreto_status(
        self,
        deliberations: List[Dict],
        session_info: Dict,
        metrics: WorkflowMetrics,
        errors: List[str],
    ) -> List[Dict]:
        """Scrape decreto publication status for deliberations."""
        updated_deliberations = []

        for deliberation in deliberations:
            try:
                # Extract info for scraping
                seduta = session_info.get("numero_seduta", "")
                numero = deliberation.get("numero", "")
                oggetto = deliberation.get("oggetto", "")
                data_seduta = session_info.get("data_seduta", "")

                # Scrape decreto status with enhanced information
                scraping_result = self.decreto_scraper.verify_decreto_publication(
                    seduta, numero, oggetto, data_seduta
                )

                # Update deliberation with all scraped information
                deliberation["pubblicato"] = scraping_result.get("found", False)
                deliberation["url_decreto"] = scraping_result.get("url")
                deliberation["data_pubblicazione"] = scraping_result.get("data_pubblicazione")
                deliberation["dgr_numero"] = scraping_result.get("dgr_numero")
                deliberation["dgr_anno"] = scraping_result.get("dgr_anno")

                if scraping_result.get("found"):
                    metrics.scraped_successfully += 1
                    self.logger.debug(f"Decreto {numero} found: {scraping_result.get('url')}")

                    # Log additional extracted information
                    if scraping_result.get("dgr_numero"):
                        self.logger.debug(
                            f"  DGR: {scraping_result.get('dgr_numero')}/{scraping_result.get('dgr_anno', 'N/A')}"
                        )
                    if scraping_result.get("data_pubblicazione"):
                        self.logger.debug(
                            f"  Published: {scraping_result.get('data_pubblicazione')}"
                        )
                else:
                    self.logger.debug(f"Decreto {numero} not found")

                updated_deliberations.append(deliberation)

            except Exception as e:
                error_msg = f"Scraping failed for deliberation {deliberation.get('numero', 'N/A')}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                metrics.errors += 1

                # Add deliberation without scraping info
                deliberation["pubblicato"] = False
                deliberation["url_decreto"] = None
                deliberation["data_pubblicazione"] = None
                deliberation["dgr_numero"] = None
                deliberation["dgr_anno"] = None
                updated_deliberations.append(deliberation)

        return updated_deliberations

    def _generate_synthesis(
        self, deliberations: List[Dict], metrics: WorkflowMetrics, errors: List[str]
    ) -> List[Dict]:
        """Generate AI synthesis for deliberations."""
        updated_deliberations = []

        for deliberation in deliberations:
            try:
                # Generate synthesis
                synthesis_result = self.ai_synthesizer.generate_detailed_synthesis(
                    deliberation, SynthesisType.EXECUTIVE
                )

                # Update deliberation
                deliberation["sintesi_rapida"] = synthesis_result.quick_summary
                deliberation["sintesi_dettagliata"] = synthesis_result.detailed_synthesis
                deliberation["extracted_info"] = synthesis_result.extracted_info
                deliberation["ai_confidence"] = synthesis_result.confidence
                deliberation["generated_with_ai"] = synthesis_result.generated_with_ai

                metrics.synthesized_successfully += 1
                self.logger.debug(
                    f"Synthesis generated for deliberation {deliberation.get('numero', 'N/A')}"
                )

                updated_deliberations.append(deliberation)

            except Exception as e:
                error_msg = f"Synthesis failed for deliberation {deliberation.get('numero', 'N/A')}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                metrics.errors += 1

                # Add deliberation without synthesis
                deliberation["sintesi_rapida"] = deliberation.get("oggetto", "")[:200]
                deliberation["sintesi_dettagliata"] = None
                deliberation["extracted_info"] = None
                updated_deliberations.append(deliberation)

        return updated_deliberations

    def _sync_to_notion(
        self,
        deliberations: List[Dict],
        session_info: Dict,
        metrics: WorkflowMetrics,
        errors: List[str],
    ) -> List[Dict]:
        """Sync deliberations to Notion."""
        try:
            # Add session info to deliberations
            for deliberation in deliberations:
                deliberation["seduta"] = session_info.get("numero_seduta")
                deliberation["data_seduta"] = session_info.get("data_seduta")

            # Sync to Notion
            sync_stats = self.notion_integrator.sync_deliberations(
                deliberations, SyncDirection.TO_NOTION
            )

            # Update metrics
            metrics.synced_to_notion = sync_stats.get("created", 0) + sync_stats.get("updated", 0)
            metrics.errors += sync_stats.get("errors", 0)

            # Log sync results
            self.logger.info(f"Notion sync completed: {sync_stats}")

            return deliberations

        except Exception as e:
            error_msg = f"Notion sync failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            metrics.errors += 1

            return deliberations

    def _create_backup(
        self, deliberations: List[Dict], session_info: Dict, metrics: WorkflowMetrics
    ) -> str:
        """Create backup files for the workflow results."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_num = session_info.get("numero_seduta", "unknown")

            # Create backup data structure
            backup_data = {
                "timestamp": timestamp,
                "session_info": session_info,
                "metrics": metrics.to_dict(),
                "deliberations": deliberations,
            }

            # JSON backup
            json_filename = f"odg_backup_{session_num}_{timestamp}.json"
            json_path = self.backup_dir / json_filename

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

            # CSV backup
            csv_filename = f"odg_backup_{session_num}_{timestamp}.csv"
            csv_path = self.backup_dir / csv_filename

            if deliberations:
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    fieldnames = [
                        "seduta",
                        "numero",
                        "tipo_atto",
                        "oggetto",
                        "proponente",
                        "fs_flag",
                        "pubblicato",
                        "url_decreto",
                        "sintesi_rapida",
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for delib in deliberations:
                        row = {key: delib.get(key, "") for key in fieldnames}
                        writer.writerow(row)

            self.logger.info(f"Backup created: {json_path}")
            return str(json_path)

        except Exception as e:
            self.logger.error(f"Backup creation failed: {str(e)}")
            return None

    def run_daily_verification(self) -> Dict[str, Any]:
        """
        Run daily verification of published decreti.

        Returns:
            Dictionary with verification results
        """
        try:
            self.logger.info("Starting daily verification")

            # Get recent deliberations from Notion
            # This would query Notion for deliberations from recent days
            # For now, we'll use a placeholder implementation

            verification_results = {
                "timestamp": datetime.now().isoformat(),
                "verified_count": 0,
                "newly_published": 0,
                "errors": 0,
                "details": [],
            }

            # TODO: Implement actual verification logic
            # 1. Query Notion for deliberations with pubblicato=False
            # 2. Re-scrape their publication status
            # 3. Update Notion with new status

            self.logger.info("Daily verification completed")
            return verification_results

        except Exception as e:
            self.logger.error(f"Daily verification failed: {str(e)}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    def run_publication_check(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Run publication status check for unpublished deliberations.

        Args:
            days_back: Number of days to look back for unpublished deliberations

        Returns:
            Dictionary with publication check results
        """
        try:
            self.logger.info(f"Starting publication check for last {days_back} days")
            
            # Get unpublished deliberations from Notion
            unpublished_deliberations = self._get_unpublished_deliberations(days_back)
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "total_checked": len(unpublished_deliberations),
                "newly_published": 0,
                "still_unpublished": 0,
                "errors": 0,
                "details": [],
            }
            
            # Check each unpublished deliberation
            for deliberation in unpublished_deliberations:
                try:
                    # Extract deliberation info
                    seduta = deliberation.get("seduta", "")
                    numero = deliberation.get("numero", "")
                    oggetto = deliberation.get("oggetto", "")
                    
                    # Check publication status
                    scraping_result = self.decreto_scraper.verify_decreto_publication(
                        seduta, numero, oggetto
                    )
                    
                    if scraping_result.get("found"):
                        # Update Notion with publication info
                        self._update_notion_publication_status(
                            deliberation, scraping_result
                        )
                        results["newly_published"] += 1
                        results["details"].append({
                            "seduta": seduta,
                            "numero": numero,
                            "status": "newly_published",
                            "url": scraping_result.get("url"),
                            "dgr_numero": scraping_result.get("dgr_numero"),
                        })
                    else:
                        results["still_unpublished"] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error checking deliberation {numero}: {str(e)}")
                    results["errors"] += 1
            
            self.logger.info(f"Publication check completed: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Publication check failed: {str(e)}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    def _get_unpublished_deliberations(self, days_back: int) -> List[Dict]:
        """Get unpublished deliberations from Notion database."""
        try:
            # This would query Notion for deliberations with pubblicato=False
            # For now, return empty list as placeholder
            self.logger.info(f"Querying Notion for unpublished deliberations (last {days_back} days)")
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting unpublished deliberations: {str(e)}")
            return []

    def _update_notion_publication_status(self, deliberation: Dict, scraping_result: Dict):
        """Update Notion page with publication status."""
        try:
            # This would update the Notion page with the publication info
            self.logger.info(f"Updating Notion for deliberation {deliberation.get('numero', 'N/A')}")
            # Implementation would go here
            
        except Exception as e:
            self.logger.error(f"Error updating Notion publication status: {str(e)}")

    def generate_detailed_synthesis(
        self, deliberation_id: str, synthesis_type: SynthesisType = SynthesisType.EXECUTIVE
    ) -> Dict[str, Any]:
        """
        Generate detailed synthesis for a specific deliberation.

        Args:
            deliberation_id: ID of the deliberation
            synthesis_type: Type of synthesis to generate

        Returns:
            Dictionary with synthesis results
        """
        try:
            self.logger.info(f"Generating detailed synthesis for deliberation {deliberation_id}")

            # TODO: Implement logic to retrieve deliberation from Notion
            # For now, return placeholder

            synthesis_result = {
                "deliberation_id": deliberation_id,
                "synthesis_type": synthesis_type.value,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Not implemented yet",
            }

            return synthesis_result

        except Exception as e:
            self.logger.error(f"Detailed synthesis generation failed: {str(e)}")
            return {
                "deliberation_id": deliberation_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_workflow_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get workflow statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        try:
            # This would analyze backup files or Notion data
            # For now, return placeholder

            stats = {
                "period_days": days,
                "total_workflows": 0,
                "successful_workflows": 0,
                "total_deliberations": 0,
                "avg_success_rate": 0.0,
                "avg_processing_time": 0.0,
                "error_summary": {},
                "timestamp": datetime.now().isoformat(),
            }

            return stats

        except Exception as e:
            self.logger.error(f"Statistics generation failed: {str(e)}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of all components.

        Returns:
            Dictionary with health status
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
        }

        # Check PDF Parser
        try:
            # Simple check - create parser instance
            parser = ODGPDFParser()
            health_status["components"]["pdf_parser"] = {
                "status": "healthy",
                "message": "PDF parser initialized successfully",
            }
        except Exception as e:
            health_status["components"]["pdf_parser"] = {"status": "error", "message": str(e)}
            health_status["overall_status"] = "degraded"

        # Check Decreto Scraper
        try:
            scraper = DecretoScraper()
            health_status["components"]["decreto_scraper"] = {
                "status": "healthy",
                "message": "Decreto scraper initialized successfully",
            }
        except Exception as e:
            health_status["components"]["decreto_scraper"] = {"status": "error", "message": str(e)}
            health_status["overall_status"] = "degraded"

        # Check AI Synthesizer
        try:
            synthesizer = AISynthesizer()
            health_status["components"]["ai_synthesizer"] = {
                "status": "healthy",
                "message": "AI synthesizer initialized successfully",
            }
        except Exception as e:
            health_status["components"]["ai_synthesizer"] = {"status": "error", "message": str(e)}
            health_status["overall_status"] = "degraded"

        # Check Notion Integrator
        try:
            # This would require valid credentials
            health_status["components"]["notion_integrator"] = {
                "status": "unknown",
                "message": "Requires valid credentials to test",
            }
        except Exception as e:
            health_status["components"]["notion_integrator"] = {
                "status": "error",
                "message": str(e),
            }

        return health_status


def main():
    """Example usage of the ODGWorkflowOrchestrator."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Get credentials
    notion_token = os.getenv("NOTION_TOKEN")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if not notion_token or not notion_database_id:
        print("Error: Missing Notion credentials")
        return

    try:
        # Initialize orchestrator
        orchestrator = ODGWorkflowOrchestrator(
            notion_token=notion_token,
            notion_database_id=notion_database_id,
            anthropic_api_key=anthropic_api_key,
        )

        # Run health check
        health = orchestrator.health_check()
        print(f"Health check: {health['overall_status']}")

        # Process example PDF
        pdf_path = "data/input/ODG_10072025.pdf"
        if os.path.exists(pdf_path):
            print(f"Processing PDF: {pdf_path}")

            result = orchestrator.process_odg_pdf(pdf_path)

            print(f"Workflow completed: {result.success}")
            print(f"Success rate: {result.metrics.success_rate:.1f}%")
            print(f"Processed {result.metrics.total_deliberations} deliberations")
            print(f"Backup created: {result.backup_path}")

            if result.errors:
                print(f"Errors: {result.errors}")
        else:
            print(f"PDF file not found: {pdf_path}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
