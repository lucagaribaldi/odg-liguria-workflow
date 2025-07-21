#!/usr/bin/env python3
"""
Sync processed deliberations to Notion database
Load data from backup files and sync to Notion with anti-duplicate logic
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

from notion_integrator import NotionIntegrator

def setup_logging() -> logging.Logger:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/notion_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def load_backup_data(backup_file: str) -> Dict[str, Any]:
    """Load deliberations from backup file."""
    logger = logging.getLogger(__name__)
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded backup data from {backup_file}")
        return data
    except Exception as e:
        logger.error(f"Error loading backup data: {str(e)}")
        return {}

def extract_all_deliberations(backup_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all deliberations from backup data."""
    logger = logging.getLogger(__name__)
    
    all_deliberations = []
    
    for result in backup_data.get('results', []):
        if result.get('success') and 'deliberations' in result:
            deliberations = result['deliberations']
            logger.info(f"Found {len(deliberations)} deliberations from {result.get('pdf_name', 'unknown')}")
            all_deliberations.extend(deliberations)
    
    logger.info(f"Total deliberations to sync: {len(all_deliberations)}")
    return all_deliberations

def main():
    """Main function to sync deliberations to Notion."""
    logger = setup_logging()
    
    print("🔄 NOTION SYNC - ODG Liguria Workflow")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Notion credentials
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Error: NOTION_TOKEN and NOTION_DATABASE_ID environment variables required")
        logger.error("Missing Notion credentials")
        return 1
    
    print(f"🔑 Notion credentials loaded")
    print(f"📊 Database ID: {database_id}")
    print()
    
    try:
        # Initialize Notion integrator
        logger.info("Initializing Notion integrator")
        integrator = NotionIntegrator(notion_token, database_id)
        
        # Create or update database schema
        print("📋 Verifying database schema...")
        if integrator.create_or_update_database():
            print("✅ Database schema verified/updated successfully")
        else:
            print("❌ Failed to verify database schema")
            return 1
        
        # Find most recent backup file
        backup_dir = Path("data/backups")
        backup_files = list(backup_dir.glob("workflow_backup_*.json"))
        
        if not backup_files:
            print("❌ No backup files found")
            return 1
        
        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
        print(f"📄 Using backup file: {latest_backup.name}")
        
        # Load backup data
        backup_data = load_backup_data(str(latest_backup))
        if not backup_data:
            print("❌ Failed to load backup data")
            return 1
        
        # Extract all deliberations
        all_deliberations = extract_all_deliberations(backup_data)
        
        if not all_deliberations:
            print("❌ No deliberations found in backup data")
            return 1
        
        print(f"📝 Found {len(all_deliberations)} deliberations to sync")
        
        # Group by session for reporting
        sessions = {}
        for delib in all_deliberations:
            seduta = delib.get('seduta', 'unknown')
            if seduta not in sessions:
                sessions[seduta] = []
            sessions[seduta].append(delib)
        
        print(f"📅 Sessions to sync: {len(sessions)}")
        for seduta, deliberations in sessions.items():
            print(f"   - Session {seduta}: {len(deliberations)} deliberations")
        print()
        
        # Sync to Notion
        print("🔄 Starting Notion sync...")
        sync_stats = integrator.sync_deliberations(all_deliberations)
        
        print("\n📊 SYNC RESULTS:")
        print("-" * 30)
        print(f"➕ Created: {sync_stats.get('created', 0)}")
        print(f"⏭️  Duplicates avoided: {sync_stats.get('duplicates_avoided', 0)}")
        print(f"🔄 Updated: {sync_stats.get('updated', 0)}")
        print(f"❌ Errors: {sync_stats.get('errors', 0)}")
        print(f"⏩ Skipped: {sync_stats.get('skipped', 0)}")
        
        # Generate final report
        final_report = {
            'sync_timestamp': datetime.now().isoformat(),
            'backup_file': str(latest_backup),
            'total_deliberations': len(all_deliberations),
            'sessions_synced': len(sessions),
            'session_details': {
                seduta: {
                    'deliberations_count': len(deliberations),
                    'sample_deliberation': deliberations[0] if deliberations else None
                }
                for seduta, deliberations in sessions.items()
            },
            'sync_stats': sync_stats,
            'database_id': database_id,
            'success': sync_stats.get('errors', 0) == 0
        }
        
        # Save report
        report_file = f"notion_sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sync report saved: {report_file}")
        
        if sync_stats.get('errors', 0) == 0:
            print("\n🎉 Notion sync completed successfully!")
            print(f"🔗 Check your Notion database: https://www.notion.so/{database_id}")
        else:
            print(f"\n⚠️  Sync completed with {sync_stats.get('errors', 0)} errors")
            print("Check the logs for details")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n💥 Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())