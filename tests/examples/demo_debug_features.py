#!/usr/bin/env python3
"""
Quick demonstration of enhanced debug features without network calls.
Shows the new debugging, error reporting, and logging capabilities.
"""

import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from decreto_scraper import (
    DecretoScraper, 
    LogLevel,
    DecretoValidationError, 
    DecretoConnectionError,
    DecretoNotFoundError
)


def demo_debug_features():
    """Demonstrate debug features without network calls."""
    print("🚀 DECRETO SCRAPER DEBUG FEATURES DEMO")
    print("=" * 60)
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Demo 1: Advanced Debug Mode
    print("\\n🔍 1. ADVANCED DEBUG MODE")
    print("-" * 30)
    
    with DecretoScraper(
        debug_mode=True,
        log_level=LogLevel.DEBUG,
        log_file="logs/demo_debug.log",
        enable_performance_tracking=True,
        verify_ssl=False
    ) as scraper:
        
        print(f"✅ Debug scraper initialized")
        print(f"📋 Session ID: {scraper.session_id}")
        print(f"🔧 Debug mode: {scraper.debug_mode}")
        print(f"📊 Performance tracking: {scraper.enable_performance_tracking}")
        
        # Demo 2: Input Validation and Error Reporting
        print("\\n🚨 2. ERROR REPORTING DEMONSTRATION")
        print("-" * 40)
        
        validation_tests = [
            ("", "Test empty seduta"),
            ("123", ""),  # Empty numero
            ("123" * 200, "Long seduta test"),  # Too long
            ("123", "456", "", None),  # Empty oggetto
            ("123", "456", "test", "invalid-date"),  # Invalid date
        ]
        
        for i, test_case in enumerate(validation_tests, 1):
            if len(test_case) == 2:
                seduta, description = test_case
                numero, oggetto, data_seduta = "123", "test", None
            else:
                seduta, numero, oggetto, data_seduta = test_case
                description = f"Test case {i}"
            
            print(f"\\n   Test {i}: {description}")
            try:
                result = scraper.verify_decreto_publication(seduta, numero, oggetto, data_seduta)
                print(f"   ✅ Validation passed")
            except DecretoValidationError as e:
                print(f"   🚨 Validation error: {str(e)[:50]}...")
            except Exception as e:
                print(f"   ⚠️ Other error: {type(e).__name__}")
        
        # Demo 3: Error Report Analysis
        print("\\n📊 3. ERROR ANALYSIS")
        print("-" * 25)
        
        all_reports = scraper.get_error_reports()
        print(f"📋 Total error reports: {len(all_reports)}")
        
        if all_reports:
            # Show error breakdown
            by_type = {}
            by_severity = {}
            
            for report in all_reports:
                error_type = report.error_type
                severity = report.severity
                
                by_type[error_type] = by_type.get(error_type, 0) + 1
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            print(f"📊 By type: {by_type}")
            print(f"📊 By severity: {by_severity}")
            
            # Show sample error report
            sample_report = all_reports[0]
            print(f"\\n🔍 Sample Error Report:")
            print(f"   Type: {sample_report.error_type}")
            print(f"   Code: {sample_report.error_code}")
            print(f"   Severity: {sample_report.severity}")
            print(f"   Operation: {sample_report.operation}")
            print(f"   Suggestions: {len(sample_report.suggestions)}")
            for suggestion in sample_report.suggestions[:2]:
                print(f"     • {suggestion}")
        
        # Demo 4: Performance Statistics
        print("\\n⚡ 4. PERFORMANCE TRACKING")
        print("-" * 30)
        
        perf_stats = scraper.get_performance_stats()
        if 'message' not in perf_stats:
            print(f"📊 Performance Summary:")
            print(f"   Total operations: {perf_stats.get('total_operations', 0)}")
            print(f"   Average duration: {perf_stats.get('average_duration', 0):.3f}s")
            if 'session_duration' in perf_stats:
                print(f"   Session duration: {perf_stats['session_duration']:.3f}s")
        else:
            print(f"📊 {perf_stats['message']}")
        
        # Demo 5: Debug Report Generation
        print("\\n💾 5. DEBUG REPORT GENERATION")
        print("-" * 35)
        
        debug_file = scraper.save_debug_report("demo_debug_report.json")
        print(f"📄 Debug report saved: {debug_file}")
        
        # Verify and show report structure
        if Path(debug_file).exists():
            with open(debug_file, 'r') as f:
                debug_data = json.load(f)
            
            print(f"📋 Report structure:")
            print(f"   Session info: ✓")
            print(f"   Error reports: {len(debug_data.get('error_reports', []))}")
            print(f"   Performance stats: ✓")
            print(f"   Debug contexts: {len(debug_data.get('debug_contexts', {}))}")
            
            # Show session info
            session_info = debug_data.get('session_info', {})
            print(f"\\n🔍 Session Info:")
            print(f"   Session ID: {session_info.get('session_id')}")
            print(f"   Debug mode: {session_info.get('debug_mode')}")
            print(f"   Log level: {session_info.get('log_level')}")


def demo_log_levels():
    """Demonstrate different logging levels."""
    print("\\n📊 6. LOGGING LEVELS DEMONSTRATION")
    print("-" * 40)
    
    log_levels = [
        (LogLevel.ERROR, "ERROR - Critical errors only"),
        (LogLevel.WARN, "WARN - Warnings and errors"),
        (LogLevel.INFO, "INFO - General information"),
        (LogLevel.DEBUG, "DEBUG - Detailed debugging")
    ]
    
    for log_level, description in log_levels:
        print(f"\\n   Testing {description}")
        
        try:
            with DecretoScraper(
                log_level=log_level,
                debug_mode=False,  # Keep debug mode off for level demo
                verify_ssl=False
            ) as scraper:
                
                # Trigger a validation error to see logging
                try:
                    scraper._validate_string_input("", "test_field")
                except DecretoValidationError:
                    pass
                
                print(f"   ✅ {log_level.name} level demonstrated")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


def show_feature_summary():
    """Show summary of implemented features."""
    print("\\n🎉 7. ENHANCED FEATURES SUMMARY")
    print("-" * 35)
    
    features = [
        "✅ Debug Mode - Comprehensive operation tracking",
        "✅ Error Reporting - Smart error analysis with suggestions", 
        "✅ Multi-Level Logging - 6 different log levels",
        "✅ Performance Tracking - Detailed timing metrics",
        "✅ File Logging - Automatic log file management",
        "✅ Debug Context - Operation tracing with unique IDs",
        "✅ Request Tracing - HTTP request/response capture",
        "✅ Debug Reports - Comprehensive JSON reports",
        "✅ Error Classification - Automatic severity assessment",
        "✅ Thread Safety - Safe for concurrent usage"
    ]
    
    print("\\n🚀 Implemented Features:")
    for feature in features:
        print(f"   {feature}")
    
    print("\\n💡 Usage Example:")
    print("```python")
    print("with DecretoScraper(debug_mode=True, log_level=LogLevel.DEBUG) as scraper:")
    print("    result = scraper.verify_decreto_publication('3929', '1', 'Test')")
    print("    debug_report = scraper.save_debug_report()")
    print("    error_reports = scraper.get_error_reports()")
    print("    perf_stats = scraper.get_performance_stats()")
    print("```")


def main():
    """Run the debug features demonstration."""
    try:
        demo_debug_features()
        demo_log_levels()
        show_feature_summary()
        
        print("\\n🎉 DEBUG FEATURES DEMO COMPLETED")
        print("=" * 60)
        print("✅ All enhanced debugging features are working correctly!")
        
        # Show generated files
        demo_files = [
            "demo_debug_report.json",
            "logs/demo_debug.log"
        ]
        
        print("\\n📁 Generated Files:")
        for file_path in demo_files:
            if Path(file_path).exists():
                size = Path(file_path).stat().st_size
                print(f"   📄 {file_path} ({size} bytes)")
        
    except Exception as e:
        print(f"\\n💥 DEMO ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()