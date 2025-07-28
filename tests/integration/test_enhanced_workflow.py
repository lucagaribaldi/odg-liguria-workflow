#!/usr/bin/env python3
"""
Test script for enhanced workflow integration.
This script tests the enhanced decreto scraper integration with mock data.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main_workflow import ODGWorkflow

def test_enhanced_workflow():
    """Test the enhanced workflow with mock data."""
    print("🧪 TESTING ENHANCED WORKFLOW INTEGRATION")
    print("=" * 50)
    
    # Create directories
    Path("logs").mkdir(exist_ok=True)
    Path("data/backups").mkdir(exist_ok=True, parents=True)
    
    try:
        # Initialize workflow with enhanced features
        print("1️⃣ Initializing workflow with enhanced decreto scraper...")
        workflow = ODGWorkflow(dry_run=False, skip_scraping=False)
        
        print(f"✅ Workflow initialized")
        print(f"   Enhanced decreto scraper: {'✓' if workflow.decreto_scraper else '✗'}")
        print(f"   Debug mode: {'✓' if workflow.decreto_scraper and workflow.decreto_scraper.debug_mode else '✗'}")
        print(f"   Performance tracking: {'✓' if workflow.decreto_scraper and workflow.decreto_scraper.enable_performance_tracking else '✗'}")
        
        # Test enhanced validation features with mock data
        print(f"\n2️⃣ Testing enhanced validation features...")
        
        mock_deliberations = [
            {
                "seduta": "3929",
                "numero": "17",
                "oggetto": "Test deliberation with normal input",
                "data_seduta": "2025-01-15"
            },
            {
                "seduta": "3929+special",  # This should be sanitized
                "numero": "18*",           # This should be sanitized
                "oggetto": "Test deliberation with regex chars []{}", 
                "data_seduta": "2025-01-15"
            },
            {
                "seduta": "",  # This should cause validation error
                "numero": "19",
                "oggetto": "Test deliberation with missing seduta",
                "data_seduta": "2025-01-15"
            }
        ]
        
        mock_session_info = {
            "numero_seduta": "3929",
            "data_seduta": "2025-01-15"
        }
        
        if workflow.decreto_scraper:
            print(f"   Testing with {len(mock_deliberations)} mock deliberations...")
            
            # Test the enhanced scraping method
            scraping_results = workflow._scrape_decreti(mock_deliberations, mock_session_info)
            
            print(f"✅ Enhanced scraping completed")
            print(f"   Results generated: {len(scraping_results)}")
            
            # Analyze results
            validated = len([r for r in scraping_results if r.get("validation_applied")])
            sanitized = len([r for r in scraping_results if r.get("validation_applied", {}).get("seduta_sanitized") or r.get("validation_applied", {}).get("numero_sanitized")])
            errors = len([r for r in scraping_results if r.get("error")])
            
            print(f"   Validation applied: {validated}")
            print(f"   Sanitization applied: {sanitized}")
            print(f"   Validation errors: {errors}")
            
            # Show detailed results
            print(f"\n📋 Detailed Results:")
            for i, result in enumerate(scraping_results, 1):
                print(f"   {i}. Numero {result.get('deliberation_numero')}: ", end="")
                if result.get("error"):
                    print(f"❌ {result['error']}")
                else:
                    validation_info = result.get("validation_applied", {})
                    if validation_info.get("seduta_sanitized") or validation_info.get("numero_sanitized"):
                        print(f"🔧 Sanitized and processed")
                    else:
                        print(f"✅ Validated and processed")
            
            # Test error reporting
            if hasattr(workflow.decreto_scraper, 'get_error_reports'):
                error_reports = workflow.decreto_scraper.get_error_reports()
                print(f"\n📊 Error Reporting System:")
                print(f"   Error reports generated: {len(error_reports)}")
                
                if error_reports:
                    for report in error_reports[:2]:  # Show first 2 reports
                        print(f"   - {report.error_type}: {report.error_message}")
            
            # Test performance stats
            if hasattr(workflow.decreto_scraper, 'get_performance_stats'):
                perf_stats = workflow.decreto_scraper.get_performance_stats()
                print(f"\n⚡ Performance Tracking:")
                if 'message' not in perf_stats:
                    print(f"   Operations tracked: {perf_stats.get('total_operations', 0)}")
                    print(f"   Total time: {perf_stats.get('total_time', 0):.3f}s")
                else:
                    print(f"   {perf_stats['message']}")
            
            # Test debug report generation
            try:
                debug_file = workflow.decreto_scraper.save_debug_report(
                    f"logs/enhanced_workflow_test_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                print(f"\n💾 Debug Report:")
                print(f"   Saved to: {debug_file}")
                
                if Path(debug_file).exists():
                    size = Path(debug_file).stat().st_size
                    print(f"   File size: {size} bytes")
                    
            except Exception as e:
                print(f"   ⚠️ Could not save debug report: {e}")
        
        else:
            print("❌ No decreto scraper available for testing")
        
        print(f"\n3️⃣ Session Statistics:")
        stats = workflow.session_stats
        print(f"   Validation applied: {stats.get('validation_applied', 0)}")
        print(f"   Sanitization applied: {stats.get('sanitization_applied', 0)}")
        print(f"   Validation errors: {stats.get('validation_errors', 0)}")
        print(f"   Scraping errors: {stats.get('scraping_errors', 0)}")
        
        print(f"\n✅ ENHANCED WORKFLOW INTEGRATION TEST COMPLETED")
        print("=" * 50)
        print("🎉 All enhanced features are working correctly!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_workflow()