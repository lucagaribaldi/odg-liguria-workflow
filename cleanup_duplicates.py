#!/usr/bin/env python3
"""
Cleanup duplicate records in Notion database
Keeps only the most recent record for each seduta+numero combination
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

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
            logging.FileHandler(f'logs/cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

class NotionDuplicatesCleaner:
    """Clean duplicate records from Notion database."""
    
    def __init__(self, notion_token: str, database_id: str):
        """Initialize the cleaner."""
        self.integrator = NotionIntegrator(notion_token, database_id)
        self.logger = logging.getLogger(__name__)
        
    def get_all_pages(self) -> List[Dict]:
        """Get all pages from the database with detailed info."""
        try:
            pages = []
            has_more = True
            next_cursor = None
            
            while has_more:
                query_params = {"database_id": self.integrator.database_id, "page_size": 100}
                
                if next_cursor:
                    query_params["start_cursor"] = next_cursor
                
                response = self.integrator._make_notion_request("query_database", **query_params)
                
                for page in response["results"]:
                    # Extract key properties
                    properties = page["properties"]
                    seduta = self.integrator._extract_property_value(properties, "Seduta", "number")
                    numero = self.integrator._extract_property_value(properties, "Numero", "number")
                    
                    pages.append({
                        "id": page["id"],
                        "seduta": seduta,
                        "numero": numero,
                        "created_time": page["created_time"],
                        "last_edited_time": page["last_edited_time"],
                        "properties": properties
                    })
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
            
            self.logger.info(f"Retrieved {len(pages)} total pages from database")
            return pages
            
        except Exception as e:
            self.logger.error(f"Error getting pages: {str(e)}")
            return []
    
    def identify_duplicates(self, pages: List[Dict]) -> Dict[str, List[Dict]]:
        """Identify duplicates based on seduta+numero."""
        groups = defaultdict(list)
        
        for page in pages:
            seduta = page["seduta"]
            numero = page["numero"]
            
            # Skip pages without proper seduta/numero (like test records)
            if seduta is None or numero is None:
                self.logger.warning(f"Page {page['id']} missing seduta or numero - will be flagged for review")
                groups["INVALID"].append(page)
                continue
            
            key = f"{seduta}_{numero}"
            groups[key].append(page)
        
        # Find actual duplicates (groups with more than 1 page)
        duplicates = {}
        unique_count = 0
        
        for key, group in groups.items():
            if key == "INVALID":
                duplicates[key] = group
            elif len(group) > 1:
                # Sort by last_edited_time to keep the most recent
                group.sort(key=lambda x: x["last_edited_time"], reverse=True)
                duplicates[key] = group
                self.logger.info(f"Found {len(group)} duplicates for {key}")
            else:
                unique_count += 1
        
        self.logger.info(f"Found {len(duplicates)} groups with duplicates, {unique_count} unique records")
        return duplicates
    
    def create_cleanup_plan(self, duplicates: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Create a plan for cleaning up duplicates."""
        plan = {
            "total_pages": 0,
            "pages_to_keep": 0,
            "pages_to_delete": 0,
            "invalid_pages": 0,
            "groups": {}
        }
        
        for key, group in duplicates.items():
            if key == "INVALID":
                plan["invalid_pages"] = len(group)
                plan["groups"][key] = {
                    "count": len(group),
                    "action": "review_manually",
                    "pages": [{"id": p["id"], "seduta": p["seduta"], "numero": p["numero"]} for p in group]
                }
            else:
                # Keep the most recent (first in sorted list), delete the rest
                to_keep = group[0]
                to_delete = group[1:]
                
                plan["pages_to_keep"] += 1
                plan["pages_to_delete"] += len(to_delete)
                
                plan["groups"][key] = {
                    "count": len(group),
                    "keep": {
                        "id": to_keep["id"],
                        "created": to_keep["created_time"],
                        "last_edited": to_keep["last_edited_time"]
                    },
                    "delete": [
                        {
                            "id": p["id"], 
                            "created": p["created_time"],
                            "last_edited": p["last_edited_time"]
                        } for p in to_delete
                    ]
                }
        
        plan["total_pages"] = plan["pages_to_keep"] + plan["pages_to_delete"] + plan["invalid_pages"]
        return plan
    
    def execute_cleanup(self, plan: Dict[str, Any], dry_run: bool = True) -> Dict[str, int]:
        """Execute the cleanup plan."""
        stats = {"deleted": 0, "errors": 0, "skipped": 0}
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No actual deletions will be performed")
        
        for key, group_plan in plan["groups"].items():
            if key == "INVALID":
                self.logger.warning(f"Skipping {len(group_plan['pages'])} invalid pages - manual review needed")
                stats["skipped"] += len(group_plan["pages"])
                continue
            
            if "delete" not in group_plan:
                continue
            
            for page_info in group_plan["delete"]:
                try:
                    page_id = page_info["id"]
                    
                    if dry_run:
                        self.logger.info(f"DRY RUN: Would delete page {page_id} for {key}")
                    else:
                        # Delete the page
                        self.integrator._make_notion_request(
                            "update_page",
                            page_id=page_id,
                            archived=True  # Archive instead of permanent delete
                        )
                        self.logger.info(f"Archived duplicate page {page_id} for {key}")
                        stats["deleted"] += 1
                        
                        # Rate limiting
                        import time
                        time.sleep(0.5)  # Be extra careful with deletions
                        
                except Exception as e:
                    self.logger.error(f"Error deleting page {page_id}: {str(e)}")
                    stats["errors"] += 1
        
        return stats

def main():
    """Main function."""
    logger = setup_logging()
    
    print("🧹 NOTION DUPLICATES CLEANUP")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Notion credentials
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Error: NOTION_TOKEN and NOTION_DATABASE_ID environment variables required")
        return 1
    
    try:
        # Initialize cleaner
        cleaner = NotionDuplicatesCleaner(notion_token, database_id)
        
        # Step 1: Get all pages
        print("📊 Step 1: Analyzing database...")
        pages = cleaner.get_all_pages()
        
        if not pages:
            print("❌ No pages found in database")
            return 1
        
        print(f"📄 Found {len(pages)} total pages")
        
        # Step 2: Identify duplicates
        print("\n🔍 Step 2: Identifying duplicates...")
        duplicates = cleaner.identify_duplicates(pages)
        
        if not duplicates:
            print("✅ No duplicates found - database is clean!")
            return 0
        
        # Step 3: Create cleanup plan
        print("\n📋 Step 3: Creating cleanup plan...")
        plan = cleaner.create_cleanup_plan(duplicates)
        
        # Display plan
        print(f"\n📊 CLEANUP PLAN:")
        print("-" * 30)
        print(f"📄 Total pages: {plan['total_pages']}")
        print(f"✅ Pages to keep: {plan['pages_to_keep']}")
        print(f"🗑️  Pages to delete: {plan['pages_to_delete']}")
        print(f"⚠️  Invalid pages: {plan['invalid_pages']}")
        
        print(f"\n📋 DUPLICATE GROUPS:")
        duplicate_groups = [k for k in plan['groups'].keys() if k != "INVALID" and plan['groups'][k].get('delete')]
        for key in duplicate_groups[:5]:  # Show first 5 groups
            group = plan['groups'][key]
            print(f"   - {key}: {group['count']} copies (keeping 1, deleting {len(group['delete'])})")
        
        if len(duplicate_groups) > 5:
            print(f"   ... and {len(duplicate_groups) - 5} more groups")
        
        if plan['invalid_pages'] > 0:
            print(f"\n⚠️  INVALID PAGES:")
            invalid_pages = plan['groups'].get('INVALID', {}).get('pages', [])
            for page in invalid_pages[:3]:
                print(f"   - Page {page['id']}: seduta={page['seduta']}, numero={page['numero']}")
            if len(invalid_pages) > 3:
                print(f"   ... and {len(invalid_pages) - 3} more invalid pages")
        
        # Step 4: Execute cleanup (dry run first)
        print(f"\n🧪 Step 4: Dry run...")
        dry_stats = cleaner.execute_cleanup(plan, dry_run=True)
        
        print(f"\nDRY RUN RESULTS:")
        print(f"   - Would delete: {dry_stats.get('deleted', 0) + plan['pages_to_delete']} pages")
        print(f"   - Would skip: {dry_stats['skipped']} pages")
        print(f"   - Expected final count: {plan['pages_to_keep'] + plan['invalid_pages']} pages")
        
        # Ask for confirmation
        print(f"\n❓ PROCEED WITH ACTUAL CLEANUP?")
        print(f"This will archive {plan['pages_to_delete']} duplicate pages.")
        print(f"Expected result: ~50 unique deliberations remaining.")
        
        response = input("Type 'yes' to proceed, anything else to cancel: ").lower().strip()
        
        if response == 'yes':
            print(f"\n🔥 Executing cleanup...")
            real_stats = cleaner.execute_cleanup(plan, dry_run=False)
            
            print(f"\n✅ CLEANUP COMPLETED!")
            print(f"📊 FINAL RESULTS:")
            print(f"   - Deleted: {real_stats['deleted']} pages")
            print(f"   - Errors: {real_stats['errors']} pages")
            print(f"   - Skipped: {real_stats['skipped']} pages")
            
            # Save cleanup report
            report = {
                "timestamp": datetime.now().isoformat(),
                "plan": plan,
                "execution_stats": real_stats,
                "database_id": database_id
            }
            
            report_file = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Cleanup report saved: {report_file}")
            
            if real_stats['errors'] == 0:
                print(f"\n🎉 Database cleanup successful!")
                print(f"🔗 Check your database: https://www.notion.so/{database_id}")
            else:
                print(f"\n⚠️  Cleanup completed with {real_stats['errors']} errors")
        else:
            print("❌ Cleanup cancelled by user")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n💥 Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())