#!/usr/bin/env python3
"""
Batch process all PDF files in the input directory.
This script processes all PDF files with the new anti-duplicate system.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_parser import ODGPDFParser
from notion_integrator import NotionIntegrator

def setup_logging() -> logging.Logger:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/batch_process.log')
        ]
    )
    return logging.getLogger(__name__)

def find_pdf_files(input_dir: Path) -> List[Path]:
    """Find all PDF files in the input directory."""
    pdf_files = []
    for file_path in input_dir.glob('*.pdf'):
        if file_path.is_file():
            pdf_files.append(file_path)
    
    # Sort by name for consistent processing order
    pdf_files.sort(key=lambda x: x.name)
    return pdf_files

def process_single_pdf(pdf_path: Path, parser: ODGPDFParser, integrator: NotionIntegrator = None) -> Dict[str, Any]:
    """Process a single PDF file."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Processing PDF: {pdf_path.name}")
        
        # Parse PDF
        result = parser.parse_odg(str(pdf_path))
        deliberations = result.get("deliberations", [])
        session_info = result.get("session_info", {})
        
        logger.info(f"Parsed {len(deliberations)} deliberations from {pdf_path.name}")
        logger.info(f"Session: {session_info.get('numero_seduta', 'N/A')}, Date: {session_info.get('data_seduta', 'N/A')}")
        
        # Sync to Notion if integrator is available
        sync_stats = {}
        if integrator:
            try:
                sync_stats = integrator.sync_deliberations(deliberations)
                logger.info(f"Sync stats for {pdf_path.name}: {sync_stats}")
            except Exception as e:
                logger.error(f"Notion sync failed for {pdf_path.name}: {str(e)}")
                sync_stats = {"error": str(e)}
        else:
            logger.info(f"No Notion integrator available, skipping sync for {pdf_path.name}")
            sync_stats = {"skipped": "no_integrator"}
        
        return {
            "success": True,
            "pdf_file": str(pdf_path),
            "pdf_name": pdf_path.name,
            "total_deliberations": len(deliberations),
            "session_info": session_info,
            "sync_stats": sync_stats,
            "deliberations": deliberations
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path.name}: {str(e)}")
        return {
            "success": False,
            "pdf_file": str(pdf_path),
            "pdf_name": pdf_path.name,
            "error": str(e)
        }

def simulate_batch_processing(input_dir: Path) -> Dict[str, Any]:
    """Simulate batch processing without Notion integration."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting batch processing simulation (no Notion sync)")
    
    # Find PDF files
    pdf_files = find_pdf_files(input_dir)
    logger.info(f"Found {len(pdf_files)} PDF files: {[f.name for f in pdf_files]}")
    
    if not pdf_files:
        logger.warning("No PDF files found in input directory")
        return {"success": False, "error": "No PDF files found"}
    
    # Initialize parser
    parser = ODGPDFParser()
    
    # Process each PDF
    results = []
    total_stats = {
        "files_processed": 0,
        "files_failed": 0,
        "total_deliberations": 0,
        "total_sessions": set()
    }
    
    for pdf_path in pdf_files:
        result = process_single_pdf(pdf_path, parser)
        results.append(result)
        
        if result["success"]:
            total_stats["files_processed"] += 1
            total_stats["total_deliberations"] += result["total_deliberations"]
            
            session_info = result.get("session_info", {})
            if session_info.get("numero_seduta"):
                total_stats["total_sessions"].add(session_info["numero_seduta"])
        else:
            total_stats["files_failed"] += 1
    
    # Convert set to list for JSON serialization
    total_stats["total_sessions"] = list(total_stats["total_sessions"])
    total_stats["sessions_count"] = len(total_stats["total_sessions"])
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "total_stats": total_stats
    }

def real_batch_processing(input_dir: Path) -> Dict[str, Any]:
    """Real batch processing with Notion integration."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting real batch processing with Notion integration")
    
    # Get credentials from environment
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        logger.error("Missing NOTION_TOKEN or NOTION_DATABASE_ID environment variables")
        return {"success": False, "error": "Missing Notion credentials"}
    
    # Find PDF files
    pdf_files = find_pdf_files(input_dir)
    logger.info(f"Found {len(pdf_files)} PDF files: {[f.name for f in pdf_files]}")
    
    if not pdf_files:
        logger.warning("No PDF files found in input directory")
        return {"success": False, "error": "No PDF files found"}
    
    # Initialize components
    parser = ODGPDFParser()
    integrator = NotionIntegrator(notion_token, database_id)
    
    # Ensure database schema is up to date
    if not integrator.create_or_update_database():
        logger.error("Failed to update database schema")
        return {"success": False, "error": "Database schema update failed"}
    
    # Process each PDF
    results = []
    total_stats = {
        "files_processed": 0,
        "files_failed": 0,
        "total_deliberations": 0,
        "total_created": 0,
        "total_duplicates_avoided": 0,
        "total_errors": 0,
        "unique_sessions": set()
    }
    
    for pdf_path in pdf_files:
        result = process_single_pdf(pdf_path, parser, integrator)
        results.append(result)
        
        if result["success"]:
            total_stats["files_processed"] += 1
            total_stats["total_deliberations"] += result["total_deliberations"]
            
            # Aggregate sync stats
            sync_stats = result.get("sync_stats", {})
            if isinstance(sync_stats, dict):
                total_stats["total_created"] += sync_stats.get("created", 0)
                total_stats["total_duplicates_avoided"] += sync_stats.get("duplicates_avoided", 0)
                total_stats["total_errors"] += sync_stats.get("errors", 0)
            
            session_info = result.get("session_info", {})
            if session_info.get("numero_seduta"):
                total_stats["unique_sessions"].add(session_info["numero_seduta"])
        else:
            total_stats["files_failed"] += 1
    
    # Convert set to list for JSON serialization
    total_stats["unique_sessions"] = list(total_stats["unique_sessions"])
    total_stats["sessions_count"] = len(total_stats["unique_sessions"])
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "total_stats": total_stats
    }

def main():
    """Main function."""
    logger = setup_logging()
    
    print("🚀 ODG LIGURIA BATCH PDF PROCESSOR")
    print("=" * 50)
    
    # Setup paths
    input_dir = Path("data/input")
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        print(f"❌ Input directory not found: {input_dir}")
        return
    
    # Check if Notion credentials are available
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if notion_token and database_id:
        print("🔗 Notion credentials found - will sync to Notion")
        batch_result = real_batch_processing(input_dir)
    else:
        print("⚠️  Notion credentials not found - simulation mode only")
        batch_result = simulate_batch_processing(input_dir)
    
    # Print results
    if batch_result["success"]:
        total_stats = batch_result["total_stats"]
        
        print("\n📊 BATCH PROCESSING RESULTS:")
        print("-" * 30)
        print(f"✅ Files processed: {total_stats['files_processed']}")
        print(f"❌ Files failed: {total_stats['files_failed']}")
        print(f"📄 Total deliberations: {total_stats['total_deliberations']}")
        print(f"📅 Unique sessions: {total_stats.get('sessions_count', len(total_stats.get('unique_sessions', [])))}")
        print(f"🗂️  Sessions: {total_stats.get('total_sessions', [])}")
        
        if 'total_created' in total_stats:
            print(f"➕ Created in Notion: {total_stats['total_created']}")
            print(f"⏭️  Duplicates avoided: {total_stats['total_duplicates_avoided']}")
            print(f"⚠️  Errors: {total_stats['total_errors']}")
        
        print("\n📋 FILE DETAILS:")
        print("-" * 30)
        for result in batch_result["results"]:
            if result["success"]:
                session_info = result.get("session_info", {})
                sync_stats = result.get("sync_stats", {})
                
                print(f"✅ {result['pdf_name']}")
                print(f"   - Session: {session_info.get('numero_seduta', 'N/A')}")
                print(f"   - Date: {session_info.get('data_seduta', 'N/A')}")
                print(f"   - Deliberations: {result['total_deliberations']}")
                
                if isinstance(sync_stats, dict) and 'created' in sync_stats:
                    print(f"   - Created: {sync_stats.get('created', 0)}")
                    print(f"   - Duplicates: {sync_stats.get('duplicates_avoided', 0)}")
                elif sync_stats.get('skipped') == 'no_integrator':
                    print(f"   - Notion sync: Skipped (no credentials)")
                
            else:
                print(f"❌ {result['pdf_name']}: {result['error']}")
        
        # Save detailed results
        results_file = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(batch_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
    else:
        print(f"\n❌ Batch processing failed: {batch_result.get('error', 'Unknown error')}")
    
    logger.info("Batch processing completed")

if __name__ == "__main__":
    main()