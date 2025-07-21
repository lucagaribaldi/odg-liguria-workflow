#!/usr/bin/env python3
"""
Test anti-duplicate functionality by trying to sync a few records again
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from notion_integrator import NotionIntegrator

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    print("🧪 TESTING ANTI-DUPLICATE FUNCTIONALITY")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Notion credentials
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Missing Notion credentials")
        return 1
    
    # Initialize Notion integrator
    integrator = NotionIntegrator(notion_token, database_id)
    
    # Test with a few deliberations that should already exist
    test_deliberations = [
        {
            "seduta": "3928",
            "numero": "1",
            "tipo_atto": "Disegno di legge di iniziativa della Giunta regionale",
            "oggetto": "Disposizioni di carattere fiscale e altre disposizioni di adeguamento normativo",
            "proponente": "BUCCI Marco",
            "fs_flag": False,
            "data_seduta": "2025-07-03",
            "sintesi_rapida": "Test deliberation"
        },
        {
            "seduta": "3929",
            "numero": "1",
            "tipo_atto": "Deliberazione",
            "oggetto": "AZIENDA PUBBLICA DI SERVIZI ALLA PERSONA",
            "proponente": "BUCCI Marco",
            "fs_flag": True,
            "data_seduta": "2025-07-10",
            "sintesi_rapida": "Test deliberation"
        },
        {
            "seduta": "3999",  # This should be new
            "numero": "999",
            "tipo_atto": "Deliberazione",
            "oggetto": "Test deliberation that should be new",
            "proponente": "TEST",
            "fs_flag": False,
            "data_seduta": "2025-07-18",
            "sintesi_rapida": "This should be created"
        }
    ]
    
    print(f"🔄 Testing with {len(test_deliberations)} deliberations...")
    print("Expected result: 2 duplicates avoided, 1 new record created")
    print()
    
    # Sync test deliberations
    stats = integrator.sync_deliberations(test_deliberations)
    
    print("📊 TEST RESULTS:")
    print("-" * 30)
    print(f"➕ Created: {stats.get('created', 0)}")
    print(f"⏭️  Duplicates avoided: {stats.get('duplicates_avoided', 0)}")
    print(f"❌ Errors: {stats.get('errors', 0)}")
    
    # Expected results
    expected_duplicates = 2
    expected_created = 1
    
    success = (
        stats.get('duplicates_avoided', 0) >= expected_duplicates and
        stats.get('created', 0) <= expected_created and
        stats.get('errors', 0) == 0
    )
    
    if success:
        print(f"\n✅ ANTI-DUPLICATE TEST PASSED!")
        print(f"   - Correctly avoided {stats.get('duplicates_avoided', 0)} duplicates")
        print(f"   - Created {stats.get('created', 0)} new records")
    else:
        print(f"\n❌ ANTI-DUPLICATE TEST FAILED!")
        print(f"   - Expected: {expected_duplicates} duplicates avoided, {expected_created} created")
        print(f"   - Actual: {stats.get('duplicates_avoided', 0)} duplicates avoided, {stats.get('created', 0)} created")
        
        # Clean up the test record if it was created
        if stats.get('created', 0) > 0:
            print("   - Note: You may need to manually delete the test record from Notion")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())