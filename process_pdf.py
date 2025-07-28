#!/usr/bin/env python3
"""
Process PDF files with anti-duplicate system.
Processes PDFs in the input folder and syncs to Notion with duplicate avoidance.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_parser import ODGPDFParser
from notion_integrator import NotionIntegrator
from decreto_scraper import DecretoScraper, LogLevel

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/process_pdf.log')
        ]
    )

def process_pdf_file(pdf_path: str) -> dict:
    """Process a single PDF file with anti-duplicate system."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        parser = ODGPDFParser()
        
        # Get credentials from environment
        notion_token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")
        
        if not notion_token or not database_id:
            raise ValueError("Missing NOTION_TOKEN or NOTION_DATABASE_ID environment variables")
        
        integrator = NotionIntegrator(notion_token, database_id)
        
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Parse PDF
        result = parser.parse_odg(pdf_path)
        deliberations = result.get("deliberations", [])
        
        logger.info(f"Parsed {len(deliberations)} deliberations from PDF")
        
        # Sync to Notion with anti-duplicate logic
        sync_stats = integrator.sync_deliberations(deliberations)
        
        logger.info(f"Sync completed: {sync_stats}")
        
        return {
            "success": True,
            "pdf_file": pdf_path,
            "total_deliberations": len(deliberations),
            "sync_stats": sync_stats,
            "session_info": result.get("session_info", {})
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
        return {
            "success": False,
            "pdf_file": pdf_path,
            "error": str(e)
        }

def main():
    """Main function to process PDF files."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting PDF processing with anti-duplicate system")
    
    # Process PDFs in order
    input_dir = Path("data/input")
    pdf_files = ["ODG_03072025.pdf", "ODG_10072025.pdf"]
    
    results = []
    
    for pdf_file in pdf_files:
        pdf_path = input_dir / pdf_file
        
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            continue
        
        logger.info(f"Processing: {pdf_file}")
        result = process_pdf_file(str(pdf_path))
        results.append(result)
        
        # Print summary
        if result["success"]:
            stats = result["sync_stats"]
            logger.info(f"✅ {pdf_file} processed successfully:")
            logger.info(f"   - Created: {stats.get('created', 0)}")
            logger.info(f"   - Duplicates avoided: {stats.get('duplicates_avoided', 0)}")
            logger.info(f"   - Errors: {stats.get('errors', 0)}")
        else:
            logger.error(f"❌ {pdf_file} failed: {result['error']}")
        
        print("-" * 50)
    
    # Final summary
    total_created = sum(r["sync_stats"].get("created", 0) for r in results if r["success"])
    total_duplicates = sum(r["sync_stats"].get("duplicates_avoided", 0) for r in results if r["success"])
    total_errors = sum(r["sync_stats"].get("errors", 0) for r in results if r["success"])
    
    logger.info("📊 FINAL SUMMARY:")
    logger.info(f"   - Total created: {total_created}")
    logger.info(f"   - Total duplicates avoided: {total_duplicates}")
    logger.info(f"   - Total errors: {total_errors}")
    logger.info(f"   - Files processed: {len([r for r in results if r['success']])}")
    
    return results

if __name__ == "__main__":
    main()