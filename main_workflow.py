#!/usr/bin/env python3
"""
ODG Liguria Workflow - Complete Processing Pipeline
This is the main workflow that orchestrates the entire process:
1. PDF parsing
2. Notion sync with anti-duplicate logic
3. Decreto scraping for publication status
4. Backup and reporting

Usage: python3 main_workflow.py [--pdf-file FILE] [--skip-scraping] [--dry-run]
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_parser import ODGPDFParser
from notion_integrator import NotionIntegrator
from decreto_scraper import DecretoScraper
from ai_synthesizer import AISynthesizer

def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/workflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

class ODGWorkflow:
    """Main ODG Liguria workflow orchestrator."""
    
    def __init__(self, dry_run: bool = False, skip_scraping: bool = False):
        """Initialize the workflow."""
        self.dry_run = dry_run
        self.skip_scraping = skip_scraping
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.pdf_parser = ODGPDFParser()
        self.notion_integrator = None
        self.decreto_scraper = None
        self.ai_synthesizer = AISynthesizer(use_ai=False)
        
        # Initialize Notion integrator if credentials are available
        notion_token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")
        
        if notion_token and database_id:
            self.notion_integrator = NotionIntegrator(notion_token, database_id)
            self.logger.info("Notion integrator initialized")
        else:
            self.logger.warning("Notion credentials not found - will skip Notion sync")
        
        # Initialize decreto scraper if not skipping
        if not skip_scraping:
            self.decreto_scraper = DecretoScraper(verify_ssl=False)
            self.logger.info("Decreto scraper initialized")
        
        # Stats tracking
        self.session_stats = {
            "start_time": datetime.now(),
            "files_processed": 0,
            "files_failed": 0,
            "total_deliberations": 0,
            "notion_created": 0,
            "notion_duplicates": 0,
            "notion_errors": 0,
            "decreti_found": 0,
            "decreti_not_found": 0,
            "scraping_errors": 0
        }
    
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF file through the complete workflow."""
        self.logger.info(f"Starting workflow for PDF: {pdf_path.name}")
        
        result = {
            "pdf_file": str(pdf_path),
            "pdf_name": pdf_path.name,
            "success": False,
            "steps": {
                "parsing": {"success": False, "error": None},
                "notion_sync": {"success": False, "error": None, "stats": {}},
                "decreto_scraping": {"success": False, "error": None, "results": []}
            }
        }
        
        try:
            # Step 1: Parse PDF
            self.logger.info(f"Step 1: Parsing PDF {pdf_path.name}")
            
            if self.dry_run:
                self.logger.info("DRY RUN: Would parse PDF")
                result["steps"]["parsing"] = {"success": True, "dry_run": True}
                result["deliberations"] = []
                result["session_info"] = {}
            else:
                parsed_data = self.pdf_parser.parse_odg(str(pdf_path))
                result["deliberations"] = parsed_data.get("deliberations", [])
                result["session_info"] = parsed_data.get("session_info", {})
                result["steps"]["parsing"] = {"success": True, "count": len(result["deliberations"])}
                
                self.logger.info(f"Successfully parsed {len(result['deliberations'])} deliberations")
                self.session_stats["total_deliberations"] += len(result["deliberations"])
                
                # Step 1.5: AI Synthesis
                if result["deliberations"]:
                    self.logger.info("Step 1.5: AI Synthesis")
                    result["deliberations"] = self.ai_synthesizer.synthesize_batch(result["deliberations"])
            
            # Step 2: Notion Sync
            if self.notion_integrator and result["deliberations"]:
                self.logger.info(f"Step 2: Syncing to Notion")
                
                if self.dry_run:
                    self.logger.info("DRY RUN: Would sync to Notion")
                    result["steps"]["notion_sync"] = {"success": True, "dry_run": True}
                else:
                    sync_stats = self.notion_integrator.sync_deliberations(result["deliberations"])
                    result["steps"]["notion_sync"] = {"success": True, "stats": sync_stats}
                    
                    self.session_stats["notion_created"] += sync_stats.get("created", 0)
                    self.session_stats["notion_duplicates"] += sync_stats.get("duplicates_avoided", 0)
                    self.session_stats["notion_errors"] += sync_stats.get("errors", 0)
                    
                    self.logger.info(f"Notion sync completed: {sync_stats}")
            else:
                if not self.notion_integrator:
                    result["steps"]["notion_sync"] = {"success": False, "error": "No Notion integrator available"}
                else:
                    result["steps"]["notion_sync"] = {"success": False, "error": "No deliberations to sync"}
            
            # Step 3: Decreto Scraping
            if self.decreto_scraper and result["deliberations"]:
                self.logger.info(f"Step 3: Scraping decreti publication status")
                
                if self.dry_run:
                    self.logger.info("DRY RUN: Would scrape decreti")
                    result["steps"]["decreto_scraping"] = {"success": True, "dry_run": True}
                else:
                    scraping_results = self._scrape_decreti(result["deliberations"], result["session_info"])
                    result["steps"]["decreto_scraping"] = {"success": True, "results": scraping_results}
                    
                    found_count = len([r for r in scraping_results if r.get("found")])
                    self.session_stats["decreti_found"] += found_count
                    self.session_stats["decreti_not_found"] += len(scraping_results) - found_count
                    
                    self.logger.info(f"Decreto scraping completed: {found_count}/{len(scraping_results)} found")
            else:
                if not self.decreto_scraper:
                    result["steps"]["decreto_scraping"] = {"success": False, "error": "Decreto scraper disabled"}
                else:
                    result["steps"]["decreto_scraping"] = {"success": False, "error": "No deliberations to scrape"}
            
            # Mark as successful if parsing worked
            result["success"] = result["steps"]["parsing"]["success"]
            
            if result["success"]:
                self.session_stats["files_processed"] += 1
            else:
                self.session_stats["files_failed"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path.name}: {str(e)}")
            result["error"] = str(e)
            self.session_stats["files_failed"] += 1
            return result
    
    def _scrape_decreti(self, deliberations: List[Dict], session_info: Dict) -> List[Dict]:
        """Scrape decreto publication status for all deliberations."""
        scraping_results = []
        
        for i, deliberation in enumerate(deliberations, 1):
            try:
                self.logger.info(f"Scraping decreto {i}/{len(deliberations)}: {deliberation.get('numero', 'N/A')}")
                
                # Extract required fields
                seduta = deliberation.get("seduta") or session_info.get("numero_seduta")
                numero = deliberation.get("numero")
                oggetto = deliberation.get("oggetto", "")
                data_seduta = deliberation.get("data_seduta") or session_info.get("data_seduta")
                
                if not seduta or not numero:
                    self.logger.warning(f"Missing seduta or numero for deliberation {i}")
                    scraping_results.append({
                        "deliberation_numero": numero,
                        "found": False,
                        "error": "Missing required fields"
                    })
                    continue
                
                # Scrape decreto
                decreto_result = self.decreto_scraper.verify_decreto_publication(
                    seduta=str(seduta),
                    numero=str(numero),
                    oggetto=oggetto,
                    data_seduta=data_seduta
                )
                
                # Add deliberation info to result
                decreto_result["deliberation_numero"] = numero
                decreto_result["deliberation_seduta"] = seduta
                scraping_results.append(decreto_result)
                
                if decreto_result.get("found"):
                    self.logger.info(f"✅ Decreto {numero} found: {decreto_result.get('url', 'N/A')}")
                else:
                    self.logger.info(f"❌ Decreto {numero} not found")
                
            except Exception as e:
                self.logger.error(f"Error scraping decreto {deliberation.get('numero', 'N/A')}: {str(e)}")
                scraping_results.append({
                    "deliberation_numero": deliberation.get("numero"),
                    "found": False,
                    "error": str(e)
                })
                self.session_stats["scraping_errors"] += 1
        
        return scraping_results
    
    def process_directory(self, input_dir: Path, pdf_file: Optional[str] = None) -> Dict[str, Any]:
        """Process PDF files in a directory."""
        self.logger.info(f"Processing directory: {input_dir}")
        
        # Find PDF files
        if pdf_file:
            pdf_files = [input_dir / pdf_file]
            if not pdf_files[0].exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_files[0]}")
        else:
            pdf_files = list(input_dir.glob("*.pdf"))
            pdf_files.sort(key=lambda x: x.name)
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        if not pdf_files:
            return {"success": False, "error": "No PDF files found"}
        
        # Process each PDF
        results = []
        for pdf_path in pdf_files:
            result = self.process_pdf(pdf_path)
            results.append(result)
        
        # Create session summary
        session_summary = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "session_stats": self.session_stats,
            "results": results
        }
        
        # Calculate final stats
        self.session_stats["end_time"] = datetime.now()
        self.session_stats["duration_seconds"] = (
            self.session_stats["end_time"] - self.session_stats["start_time"]
        ).total_seconds()
        
        return session_summary
    
    def create_backup(self, results: Dict[str, Any]) -> str:
        """Create a backup file with the results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/backups/workflow_backup_{timestamp}.json"
        
        # Create backup directory if it doesn't exist
        os.makedirs("data/backups", exist_ok=True)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Backup created: {backup_file}")
        return backup_file

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="ODG Liguria Workflow - Complete Processing Pipeline")
    parser.add_argument("--pdf-file", help="Process specific PDF file instead of all files")
    parser.add_argument("--skip-scraping", action="store_true", help="Skip decreto scraping")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual processing)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--input-dir", default="data/input", help="Input directory for PDF files")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.debug)
    
    print("🚀 ODG LIGURIA COMPLETE WORKFLOW")
    print("=" * 50)
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No actual processing will occur")
    
    if args.skip_scraping:
        print("⏭️  SKIPPING decreto scraping")
    
    print()
    
    try:
        # Initialize workflow
        workflow = ODGWorkflow(dry_run=args.dry_run, skip_scraping=args.skip_scraping)
        
        # Process files
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        results = workflow.process_directory(input_dir, args.pdf_file)
        
        # Print results
        if results["success"]:
            stats = results["session_stats"]
            
            print("📊 WORKFLOW RESULTS:")
            print("-" * 30)
            print(f"⏱️  Duration: {stats['duration_seconds']:.1f} seconds")
            print(f"✅ Files processed: {stats['files_processed']}")
            print(f"❌ Files failed: {stats['files_failed']}")
            print(f"📄 Total deliberations: {stats['total_deliberations']}")
            
            if workflow.notion_integrator:
                print(f"➕ Notion created: {stats['notion_created']}")
                print(f"⏭️  Notion duplicates: {stats['notion_duplicates']}")
                print(f"⚠️  Notion errors: {stats['notion_errors']}")
            
            if workflow.decreto_scraper:
                print(f"🔍 Decreti found: {stats['decreti_found']}")
                print(f"❓ Decreti not found: {stats['decreti_not_found']}")
                print(f"🚫 Scraping errors: {stats['scraping_errors']}")
            
            print()
            
            # Print file details
            print("📋 FILE PROCESSING DETAILS:")
            print("-" * 30)
            for result in results["results"]:
                if result["success"]:
                    print(f"✅ {result['pdf_name']}")
                    if "session_info" in result:
                        session_info = result["session_info"]
                        print(f"   - Session: {session_info.get('numero_seduta', 'N/A')}")
                        print(f"   - Date: {session_info.get('data_seduta', 'N/A')}")
                        print(f"   - Deliberations: {len(result.get('deliberations', []))}")
                    
                    # Notion stats
                    notion_stats = result["steps"]["notion_sync"].get("stats", {})
                    if notion_stats:
                        print(f"   - Notion: {notion_stats.get('created', 0)} created, {notion_stats.get('duplicates_avoided', 0)} duplicates")
                    
                    # Decreto stats
                    decreto_results = result["steps"]["decreto_scraping"].get("results", [])
                    if decreto_results:
                        found = len([r for r in decreto_results if r.get("found")])
                        print(f"   - Decreti: {found}/{len(decreto_results)} found")
                    
                else:
                    print(f"❌ {result['pdf_name']}: {result.get('error', 'Unknown error')}")
            
            # Create backup
            backup_file = workflow.create_backup(results)
            print(f"\n💾 Backup saved to: {backup_file}")
            
        else:
            print(f"❌ Workflow failed: {results.get('error', 'Unknown error')}")
            return 1
        
        print("\n🎉 Workflow completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n💥 Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())