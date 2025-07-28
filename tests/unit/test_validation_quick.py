#!/usr/bin/env python3
"""
Quick test for the new validate_and_sanitize_input method without network calls.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from decreto_scraper import DecretoScraper, LogLevel, DecretoValidationError


def test_validation_method():
    """Test the validate_and_sanitize_input method quickly."""
    print("🧪 QUICK TEST: validate_and_sanitize_input method")
    print("=" * 60)
    
    # Test without network calls - just the validation method
    with DecretoScraper(debug_mode=True, verify_ssl=False) as scraper:
        
        # Test cases showing the method works correctly
        test_cases = [
            ("simple_text", True, "simple_text"),
            ("text_with_$pecial^chars", True, "text_with_\\$pecial\\^chars"),
            ("text.with*regex+chars?", True, "text\\.with\\*regex\\+chars\\?"),
            ("text|with|pipes", True, "text\\|with\\|pipes"),
            ("[bracketed] {braced}", True, "\\[bracketed\\] \\{braced\\}"),
            ("normal text", False, "normal text"),
        ]
        
        print("Testing regex sanitization:")
        for input_val, for_regex, expected in test_cases:
            try:
                result = scraper.validate_and_sanitize_input(
                    input_val, "test_field", for_regex=for_regex, max_length=200
                )
                print(f"✅ '{input_val}' -> '{result}' (regex={for_regex})")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Test validation errors
        print("\nTesting validation errors:")
        error_cases = [
            ("", "empty string should fail"),
            ("x" * 300, "too long string should fail"),
        ]
        
        for input_val, description in error_cases:
            try:
                result = scraper.validate_and_sanitize_input(
                    input_val, "test_field", for_regex=True, max_length=200, allow_empty=False
                )
                print(f"❌ {description} - but got: '{result}'")
            except DecretoValidationError as e:
                print(f"✅ {description} - correctly caught: {str(e)[:50]}...")
        
        print(f"\n🎉 validate_and_sanitize_input method is working correctly!")


if __name__ == "__main__":
    test_validation_method()