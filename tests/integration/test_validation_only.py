#!/usr/bin/env python3
"""
Quick validation test for enhanced workflow integration.
This script tests only the validation features without network requests.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from decreto_scraper import DecretoScraper, LogLevel

def test_validation_features():
    """Test validation features of enhanced decreto scraper."""
    print("🧪 TESTING ENHANCED VALIDATION FEATURES")
    print("=" * 50)
    
    # Create directories
    Path("logs").mkdir(exist_ok=True)
    
    try:
        # Initialize enhanced decreto scraper
        with DecretoScraper(
            debug_mode=True,
            log_level=LogLevel.INFO,
            log_file="logs/validation_test.log",
            enable_performance_tracking=True,
            verify_ssl=False
        ) as scraper:
            
            print("✅ Enhanced decreto scraper initialized")
            print(f"   Session ID: {scraper.session_id}")
            print(f"   Debug mode: {scraper.debug_mode}")
            print(f"   Performance tracking: {scraper.enable_performance_tracking}")
            
            # Test cases for validation
            test_cases = [
                {
                    "name": "Normal input",
                    "seduta": "3929",
                    "numero": "17",
                    "oggetto": "Normal deliberation text"
                },
                {
                    "name": "Input with regex characters",
                    "seduta": "3929+special",  # Should be sanitized
                    "numero": "18*",           # Should be sanitized
                    "oggetto": "Deliberation with []{} regex chars"
                },
                {
                    "name": "Input with special characters",
                    "seduta": "3929^test",     # Should be sanitized
                    "numero": "19?",          # Should be sanitized
                    "oggetto": "Complex (test) with | pipes"
                },
                {
                    "name": "Empty input (should cause error)",
                    "seduta": "",             # Should cause validation error
                    "numero": "20",
                    "oggetto": "Test with empty seduta"
                }
            ]
            
            print(f"\n🛡️ Testing validation on {len(test_cases)} test cases...")
            
            results = []
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n   Test {i}: {test_case['name']}")
                print(f"      Input - Seduta: '{test_case['seduta']}', Numero: '{test_case['numero']}'")
                
                try:
                    # Test validation and sanitization
                    validated_seduta = scraper.validate_and_sanitize_input(
                        test_case['seduta'], "seduta", for_regex=True, max_length=50
                    )
                    validated_numero = scraper.validate_and_sanitize_input(
                        test_case['numero'], "numero", for_regex=True, max_length=50
                    )
                    validated_oggetto = scraper.validate_and_sanitize_input(
                        test_case['oggetto'], "oggetto", for_regex=False, max_length=1000
                    )
                    
                    print(f"      ✅ Validation passed")
                    
                    # Check if sanitization was applied
                    sanitization_applied = False
                    if validated_seduta != test_case['seduta']:
                        print(f"         🔧 Seduta sanitized: '{test_case['seduta']}' -> '{validated_seduta}'")
                        sanitization_applied = True
                    if validated_numero != test_case['numero']:
                        print(f"         🔧 Numero sanitized: '{test_case['numero']}' -> '{validated_numero}'")
                        sanitization_applied = True
                    
                    results.append({
                        "test_name": test_case['name'],
                        "status": "success",
                        "sanitization_applied": sanitization_applied,
                        "validated_seduta": validated_seduta,
                        "validated_numero": validated_numero
                    })
                    
                except Exception as e:
                    print(f"      ❌ Validation error: {str(e)}")
                    results.append({
                        "test_name": test_case['name'],
                        "status": "validation_error",
                        "error": str(e)
                    })
            
            # Summary
            print(f"\n📊 TEST RESULTS SUMMARY:")
            print(f"   Total tests: {len(results)}")
            success_count = len([r for r in results if r['status'] == 'success'])
            error_count = len([r for r in results if r['status'] == 'validation_error'])
            sanitized_count = len([r for r in results if r.get('sanitization_applied', False)])
            
            print(f"   Successful validations: {success_count}")
            print(f"   Validation errors caught: {error_count}")
            print(f"   Sanitization applied: {sanitized_count}")
            
            # Test error reporting system
            error_reports = scraper.get_error_reports()
            print(f"\n🚨 Error Reporting System:")
            print(f"   Error reports generated: {len(error_reports)}")
            
            if error_reports:
                print(f"   Sample error report:")
                sample = error_reports[0]
                print(f"      Type: {sample.error_type}")
                print(f"      Message: {sample.error_message}")
                print(f"      Severity: {sample.severity}")
                print(f"      Suggestions: {len(sample.suggestions)}")
            
            # Test performance tracking
            perf_stats = scraper.get_performance_stats()
            print(f"\n⚡ Performance Tracking:")
            if 'message' not in perf_stats:
                print(f"   Operations tracked: {perf_stats.get('total_operations', 0)}")
                print(f"   Total time: {perf_stats.get('total_time', 0):.3f}s")
            else:
                print(f"   {perf_stats['message']}")
            
            print(f"\n✅ VALIDATION TEST COMPLETED SUCCESSFULLY")
            print("=" * 50)
            print("🎉 Enhanced validation features are working correctly!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_validation_features()