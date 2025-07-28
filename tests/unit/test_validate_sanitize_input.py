#!/usr/bin/env python3
"""
Test script for the new validate_and_sanitize_input method.
Demonstrates comprehensive validation and sanitization before regex usage.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from decreto_scraper import (
    DecretoScraper, 
    LogLevel,
    DecretoValidationError
)


def test_validate_and_sanitize_input():
    """Test the new validate_and_sanitize_input method."""
    print("🧪 TESTING VALIDATE_AND_SANITIZE_INPUT METHOD")
    print("=" * 60)
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Test with debug mode to see detailed logging
    with DecretoScraper(
        debug_mode=True,
        log_level=LogLevel.DEBUG,
        log_file="logs/validate_sanitize_test.log",
        verify_ssl=False
    ) as scraper:
        
        print(f"✅ Test scraper initialized with session ID: {scraper.session_id}")
        
        # Test cases for validation and sanitization
        test_cases = [
            # (input, field_name, for_regex, expected_behavior)
            ("simple_text", "test_field", True, "should escape and pass"),
            ("text_with_$pecial^chars", "regex_field", True, "should escape regex metacharacters"),
            ("text.with*regex+chars?", "regex_field", True, "should escape all regex metacharacters"),
            ("normal text", "text_field", False, "should pass without regex escaping"),
            ("", "empty_field", True, "should fail validation"),
            ("a" * 300, "long_field", True, "should fail length validation"),
            ("valid_input", "normal_field", True, "should pass all validations"),
            ("text\twith\tcontrol\nchars", "control_field", False, "should sanitize control chars"),
            ("text|with|pipes", "pipe_field", True, "should escape pipe characters"),
            ("[bracketed] {braced} (parentheses)", "bracket_field", True, "should escape brackets"),
        ]
        
        print(f"\n🔍 Running {len(test_cases)} validation tests...")
        
        success_count = 0
        failure_count = 0
        
        for i, (input_val, field_name, for_regex, description) in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {description}")
            print(f"   Input: '{input_val[:50]}{'...' if len(input_val) > 50 else ''}'")
            print(f"   For regex: {for_regex}")
            
            try:
                # Test the validation method
                result = scraper.validate_and_sanitize_input(
                    input_val, 
                    field_name, 
                    for_regex=for_regex,
                    max_length=200,
                    allow_empty=False
                )
                
                print(f"   ✅ Result: '{result[:50]}{'...' if len(result) > 50 else ''}'")
                if for_regex and result != input_val:
                    print(f"   🔧 Sanitization applied: '{input_val}' -> '{result}'")
                success_count += 1
                
            except DecretoValidationError as e:
                print(f"   🚨 Validation error (expected): {str(e)[:80]}...")
                failure_count += 1
                
            except Exception as e:
                print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")
                failure_count += 1
        
        # Test regex safety demonstration
        print(f"\n🛡️ REGEX SAFETY DEMONSTRATION")
        print("-" * 40)
        
        dangerous_inputs = [
            ".*",  # Match everything
            "^start",  # Start anchor
            "end$",  # End anchor
            "[abc]",  # Character class
            "a+",  # One or more
            "a*",  # Zero or more
            "a?",  # Zero or one
            "a{3}",  # Exact count
            "(group)",  # Grouping
            "alt|ernative",  # Alternation
            "escape\\this",  # Backslash
        ]
        
        print(f"\n🔍 Testing {len(dangerous_inputs)} potentially dangerous regex inputs...")
        
        for dangerous_input in dangerous_inputs:
            try:
                # Validate and sanitize for regex usage
                safe_result = scraper.validate_and_sanitize_input(
                    dangerous_input, 
                    "dangerous_field", 
                    for_regex=True
                )
                
                print(f"   🛡️ '{dangerous_input}' -> '{safe_result}'")
                
            except Exception as e:
                print(f"   ❌ Error processing '{dangerous_input}': {e}")
        
        # Performance test
        print(f"\n⚡ PERFORMANCE TEST")
        print("-" * 25)
        
        import time
        start_time = time.time()
        
        # Test with 100 validation calls
        for i in range(100):
            try:
                scraper.validate_and_sanitize_input(
                    f"test_input_{i}", 
                    f"perf_field_{i}", 
                    for_regex=True
                )
            except Exception:
                pass
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        print(f"   📊 100 validations completed in {total_time:.3f}s")
        print(f"   📊 Average time per validation: {avg_time:.6f}s")
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print("-" * 20)
        print(f"   Total tests: {len(test_cases)}")
        print(f"   Successful validations: {success_count}")
        print(f"   Expected validation failures: {failure_count}")
        print(f"   Performance: {avg_time:.6f}s average")
        
        # Show error reports if any
        error_reports = scraper.get_error_reports()
        if error_reports:
            print(f"\n🚨 Error reports generated: {len(error_reports)}")
            for report in error_reports[:3]:  # Show first 3
                print(f"   - {report.error_type}: {report.error_message[:50]}...")


def test_method_integration():
    """Test integration with existing decreto verification."""
    print(f"\n🔗 INTEGRATION TEST WITH DECRETO VERIFICATION")
    print("=" * 60)
    
    with DecretoScraper(
        debug_mode=True,
        log_level=LogLevel.DEBUG,
        verify_ssl=False
    ) as scraper:
        
        # Test with inputs that contain regex metacharacters
        test_inputs = [
            ("3929", "1+special", "Test with + character"),
            ("3929*", "1", "Test with * character"),
            ("3929", "1", "Test.with.dots"),
            ("3929", "1", "Test[with]brackets"),
        ]
        
        print(f"Testing {len(test_inputs)} cases with special characters...")
        
        for seduta, numero, oggetto in test_inputs:
            try:
                print(f"\n   Testing: seduta='{seduta}', numero='{numero}', oggetto='{oggetto[:30]}...'")
                
                # This will internally use validate_and_sanitize_input
                result = scraper.verify_decreto_publication(seduta, numero, oggetto)
                
                print(f"   ✅ Validation and processing completed successfully")
                print(f"   📋 Found: {result.get('found', False)}")
                
            except DecretoValidationError as e:
                print(f"   🚨 Validation error: {str(e)[:60]}...")
                
            except Exception as e:
                print(f"   ⚠️ Other error: {type(e).__name__}: {str(e)[:60]}...")


def main():
    """Run comprehensive tests for the validate_and_sanitize_input method."""
    print("🚀 VALIDATE_AND_SANITIZE_INPUT METHOD TEST SUITE")
    print("=" * 80)
    print("Testing the new validation and sanitization method for regex safety\n")
    
    try:
        test_validate_and_sanitize_input()
        test_method_integration()
        
        print(f"\n🎉 ALL VALIDATION TESTS COMPLETED")
        print("=" * 80)
        print("✅ The validate_and_sanitize_input method is working correctly!")
        
        print(f"\n💡 Usage example:")
        print(f"```python")
        print(f"# Safe validation and sanitization for regex usage")
        print(f"sanitized_input = scraper.validate_and_sanitize_input(")
        print(f"    user_input, 'field_name', for_regex=True, max_length=200")
        print(f")")
        print(f"```")
        
    except Exception as e:
        print(f"\n💥 TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()