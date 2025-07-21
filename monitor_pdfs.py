#!/usr/bin/env python3
"""
PDF Monitor for ODG Liguria Workflow
Monitors the input directory for new PDF files and triggers processing.

This script can be run as a daemon to continuously monitor for new files,
or as a one-time check to see if there are new files to process.

Usage:
    python3 monitor_pdfs.py                 # One-time check
    python3 monitor_pdfs.py --daemon        # Continuous monitoring
    python3 monitor_pdfs.py --check-only    # Check for new files without processing
"""

import sys
import os
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

@dataclass
class FileInfo:
    """Information about a monitored file."""
    path: str
    name: str
    size: int
    mtime: float
    hash_md5: str
    first_seen: str
    last_processed: Optional[str] = None
    processing_status: str = "new"  # new, processing, completed, failed
    error_message: Optional[str] = None

class PDFMonitor:
    """Monitor for new PDF files in the input directory."""
    
    def __init__(self, input_dir: str = "data/input", state_file: str = "data/monitor_state.json"):
        """Initialize the PDF monitor."""
        self.input_dir = Path(input_dir)
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self.known_files: Dict[str, FileInfo] = {}
        self.load_state()
        
        self.logger.info(f"PDFMonitor initialized for directory: {self.input_dir}")
    
    def load_state(self) -> None:
        """Load the monitoring state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Convert dict back to FileInfo objects
                for filename, file_data in state_data.items():
                    self.known_files[filename] = FileInfo(**file_data)
                
                self.logger.info(f"Loaded state for {len(self.known_files)} files")
            else:
                self.logger.info("No existing state file found, starting fresh")
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            self.known_files = {}
    
    def save_state(self) -> None:
        """Save the monitoring state to file."""
        try:
            # Convert FileInfo objects to dict
            state_data = {
                filename: asdict(file_info)
                for filename, file_info in self.known_files.items()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved state for {len(self.known_files)} files")
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            return "unknown"
    
    def scan_directory(self) -> List[FileInfo]:
        """Scan the input directory for PDF files."""
        current_files = []
        
        try:
            for file_path in self.input_dir.glob("*.pdf"):
                if file_path.is_file():
                    # Get file stats
                    stat = file_path.stat()
                    file_hash = self.calculate_file_hash(file_path)
                    
                    # Check if this is a new file or if it has changed
                    filename = file_path.name
                    
                    if filename in self.known_files:
                        known_file = self.known_files[filename]
                        
                        # Check if file has changed
                        if (known_file.size != stat.st_size or 
                            known_file.mtime != stat.st_mtime or
                            known_file.hash_md5 != file_hash):
                            
                            self.logger.info(f"File changed: {filename}")
                            
                            # Update the known file info
                            known_file.size = stat.st_size
                            known_file.mtime = stat.st_mtime
                            known_file.hash_md5 = file_hash
                            known_file.processing_status = "new"  # Mark as new since it changed
                            known_file.last_processed = None
                            known_file.error_message = None
                        
                        current_files.append(known_file)
                    else:
                        # New file
                        new_file = FileInfo(
                            path=str(file_path),
                            name=filename,
                            size=stat.st_size,
                            mtime=stat.st_mtime,
                            hash_md5=file_hash,
                            first_seen=datetime.now().isoformat(),
                            processing_status="new"
                        )
                        
                        self.known_files[filename] = new_file
                        current_files.append(new_file)
                        
                        self.logger.info(f"New file detected: {filename}")
            
            # Remove files that no longer exist
            existing_filenames = {f.name for f in current_files}
            removed_files = set(self.known_files.keys()) - existing_filenames
            
            for filename in removed_files:
                self.logger.info(f"File removed: {filename}")
                del self.known_files[filename]
            
            return current_files
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {str(e)}")
            return []
    
    def get_files_to_process(self) -> List[FileInfo]:
        """Get files that need to be processed."""
        files_to_process = []
        
        for file_info in self.known_files.values():
            if file_info.processing_status in ["new", "failed"]:
                files_to_process.append(file_info)
        
        return files_to_process
    
    def mark_file_processing(self, filename: str) -> None:
        """Mark a file as currently being processed."""
        if filename in self.known_files:
            self.known_files[filename].processing_status = "processing"
            self.save_state()
    
    def mark_file_completed(self, filename: str) -> None:
        """Mark a file as successfully processed."""
        if filename in self.known_files:
            self.known_files[filename].processing_status = "completed"
            self.known_files[filename].last_processed = datetime.now().isoformat()
            self.known_files[filename].error_message = None
            self.save_state()
    
    def mark_file_failed(self, filename: str, error_message: str) -> None:
        """Mark a file as failed to process."""
        if filename in self.known_files:
            self.known_files[filename].processing_status = "failed"
            self.known_files[filename].error_message = error_message
            self.save_state()
    
    def get_monitoring_stats(self) -> Dict:
        """Get statistics about monitored files."""
        stats = {
            "total_files": len(self.known_files),
            "new_files": 0,
            "processing_files": 0,
            "completed_files": 0,
            "failed_files": 0,
            "files_by_status": {}
        }
        
        for file_info in self.known_files.values():
            status = file_info.processing_status
            stats["files_by_status"][status] = stats["files_by_status"].get(status, 0) + 1
            
            if status == "new":
                stats["new_files"] += 1
            elif status == "processing":
                stats["processing_files"] += 1
            elif status == "completed":
                stats["completed_files"] += 1
            elif status == "failed":
                stats["failed_files"] += 1
        
        return stats

def process_new_files(monitor: PDFMonitor, dry_run: bool = False) -> Dict:
    """Process new files using the main workflow."""
    logger = logging.getLogger(__name__)
    
    # Get files to process
    files_to_process = monitor.get_files_to_process()
    
    if not files_to_process:
        logger.info("No new files to process")
        return {"processed": 0, "failed": 0, "results": []}
    
    logger.info(f"Found {len(files_to_process)} files to process")
    
    results = []
    processed_count = 0
    failed_count = 0
    
    for file_info in files_to_process:
        try:
            logger.info(f"Processing file: {file_info.name}")
            
            if dry_run:
                logger.info(f"DRY RUN: Would process {file_info.name}")
                monitor.mark_file_completed(file_info.name)
                processed_count += 1
                results.append({
                    "filename": file_info.name,
                    "status": "completed",
                    "dry_run": True
                })
            else:
                # Mark as processing
                monitor.mark_file_processing(file_info.name)
                
                # Import and run the main workflow
                from main_workflow import ODGWorkflow
                
                workflow = ODGWorkflow(skip_scraping=True)  # Skip scraping for speed
                
                # Process the single file
                pdf_path = Path(file_info.path)
                result = workflow.process_pdf(pdf_path)
                
                if result["success"]:
                    monitor.mark_file_completed(file_info.name)
                    processed_count += 1
                    logger.info(f"Successfully processed: {file_info.name}")
                else:
                    error_msg = result.get("error", "Unknown error")
                    monitor.mark_file_failed(file_info.name, error_msg)
                    failed_count += 1
                    logger.error(f"Failed to process {file_info.name}: {error_msg}")
                
                results.append({
                    "filename": file_info.name,
                    "status": "completed" if result["success"] else "failed",
                    "error": result.get("error") if not result["success"] else None,
                    "deliberations": len(result.get("deliberations", [])),
                    "session_info": result.get("session_info", {})
                })
                
        except Exception as e:
            error_msg = str(e)
            monitor.mark_file_failed(file_info.name, error_msg)
            failed_count += 1
            logger.error(f"Error processing {file_info.name}: {error_msg}")
            
            results.append({
                "filename": file_info.name,
                "status": "failed",
                "error": error_msg
            })
    
    return {
        "processed": processed_count,
        "failed": failed_count,
        "results": results
    }

def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="ODG Liguria PDF Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (continuous monitoring)")
    parser.add_argument("--check-only", action="store_true", help="Only check for new files, don't process")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual processing)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--input-dir", default="data/input", help="Input directory to monitor")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds (daemon mode)")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.debug)
    
    print("🔍 ODG LIGURIA PDF MONITOR")
    print("=" * 50)
    
    if args.daemon:
        print(f"📡 Running in daemon mode (polling every {args.interval}s)")
    elif args.check_only:
        print("👀 Check-only mode - will not process files")
    elif args.dry_run:
        print("🧪 Dry run mode - will not actually process files")
    
    print()
    
    try:
        # Initialize monitor
        monitor = PDFMonitor(args.input_dir)
        
        if args.daemon:
            # Daemon mode - continuous monitoring
            logger.info("Starting daemon mode")
            
            while True:
                try:
                    # Scan for new files
                    current_files = monitor.scan_directory()
                    
                    if not args.check_only:
                        # Process new files
                        processing_result = process_new_files(monitor, args.dry_run)
                        
                        if processing_result["processed"] > 0 or processing_result["failed"] > 0:
                            logger.info(f"Processing batch completed: {processing_result['processed']} processed, {processing_result['failed']} failed")
                    
                    # Wait before next check
                    time.sleep(args.interval)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping daemon")
                    break
                except Exception as e:
                    logger.error(f"Error in daemon loop: {str(e)}")
                    time.sleep(args.interval)
        else:
            # One-time check
            logger.info("Performing one-time check")
            
            # Scan for files
            current_files = monitor.scan_directory()
            
            # Get stats
            stats = monitor.get_monitoring_stats()
            
            print("📊 MONITORING RESULTS:")
            print("-" * 30)
            print(f"📁 Total files: {stats['total_files']}")
            print(f"🆕 New files: {stats['new_files']}")
            print(f"⚙️  Processing: {stats['processing_files']}")
            print(f"✅ Completed: {stats['completed_files']}")
            print(f"❌ Failed: {stats['failed_files']}")
            print()
            
            if stats['new_files'] > 0:
                print("🆕 NEW FILES DETECTED:")
                print("-" * 30)
                for file_info in monitor.get_files_to_process():
                    print(f"   - {file_info.name}")
                    print(f"     Size: {file_info.size} bytes")
                    print(f"     First seen: {file_info.first_seen}")
                    if file_info.processing_status == "failed":
                        print(f"     Error: {file_info.error_message}")
                print()
            
            if not args.check_only and stats['new_files'] > 0:
                # Process new files
                processing_result = process_new_files(monitor, args.dry_run)
                
                print("📋 PROCESSING RESULTS:")
                print("-" * 30)
                print(f"✅ Processed: {processing_result['processed']}")
                print(f"❌ Failed: {processing_result['failed']}")
                print()
                
                if processing_result['results']:
                    print("📄 FILE DETAILS:")
                    print("-" * 30)
                    for result in processing_result['results']:
                        status_icon = "✅" if result['status'] == 'completed' else "❌"
                        print(f"{status_icon} {result['filename']}")
                        
                        if result['status'] == 'completed':
                            if not result.get('dry_run'):
                                session_info = result.get('session_info', {})
                                print(f"     Session: {session_info.get('numero_seduta', 'N/A')}")
                                print(f"     Deliberations: {result.get('deliberations', 0)}")
                        else:
                            print(f"     Error: {result.get('error', 'Unknown error')}")
            
            elif args.check_only:
                print("👀 Check-only mode - no files processed")
            
            else:
                print("✨ No new files to process")
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n💥 Fatal error: {str(e)}")
        return 1
    
    print("\n🎉 Monitoring completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())