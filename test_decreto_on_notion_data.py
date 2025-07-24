#!/usr/bin/env python3
"""
Test the decreto scraper on actual deliberations from our Notion database
"""

import json
from decreto_scraper_final import DecretoScraperFinal

def load_notion_deliberations():
    """Load deliberations from our Notion backup."""
    try:
        with open('data/backups/workflow_backup_20250718_152226.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract all deliberations from all PDF results
        all_deliberations = []
        for result in data.get('results', []):
            deliberations = result.get('deliberations', [])
            all_deliberations.extend(deliberations)
        
        return all_deliberations
    except FileNotFoundError:
        print("❌ backup file not found")
        return []

def test_decreto_verification():
    """Test decreto verification on real Notion data."""
    
    print("🔍 TESTING DECRETO VERIFICATION ON NOTION DATA")
    print("=" * 60)
    
    # Load deliberations
    deliberations = load_notion_deliberations()
    
    if not deliberations:
        print("No deliberations found in backup")
        return
    
    print(f"📋 Loaded {len(deliberations)} deliberations from Notion")
    
    # Initialize scraper
    scraper = DecretoScraperFinal()
    
    # Test on first 5 deliberations
    test_deliberations = deliberations[:5]
    
    results = []
    
    for i, delib in enumerate(test_deliberations, 1):
        print(f"\n🧪 TEST {i}/5")
        print(f"Deliberation: {delib.get('numero')} - {delib.get('titolo', '')[:50]}...")
        
        verification_result = scraper.verify_deliberation_exists(delib)
        results.append({
            'deliberation': delib,
            'verification': verification_result
        })
        
        if verification_result.get('found'):
            print(f"  ✅ FOUND on decreto website!")
            print(f"     Search term: {verification_result.get('search_term')}")
            print(f"     Context: {verification_result.get('match_context', '')[:80]}...")
        else:
            print(f"  ❌ NOT FOUND on decreto website")
            print(f"     Searched: {verification_result.get('searched_terms', [])}")
    
    # Summary
    found_count = sum(1 for r in results if r['verification'].get('found'))
    print(f"\n📊 VERIFICATION SUMMARY")
    print(f"Total tested: {len(results)}")
    print(f"Found on decreto site: {found_count}")
    print(f"Not found: {len(results) - found_count}")
    print(f"Success rate: {found_count/len(results)*100:.1f}%")
    
    # Save detailed results
    with open('decreto_verification_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: decreto_verification_results.json")

if __name__ == "__main__":
    test_decreto_verification()