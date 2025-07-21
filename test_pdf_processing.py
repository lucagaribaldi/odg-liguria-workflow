#!/usr/bin/env python3
"""
Test PDF processing with new anti-duplicate system.
This script tests the PDF parsing with the updated parser that includes session info.
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_parser import ODGPDFParser

def test_pdf_processing():
    """Test PDF processing with updated parser."""
    
    # Initialize parser
    parser = ODGPDFParser()
    
    # Test with first PDF
    pdf_path = "data/input/ODG_03072025.pdf"
    
    print(f"Testing PDF processing with: {pdf_path}")
    print("=" * 50)
    
    try:
        # Parse PDF
        result = parser.parse_odg(pdf_path)
        
        print(f"📄 PDF File: {result['pdf_file']}")
        print(f"📅 Parsing Date: {result['parsing_date']}")
        print(f"📊 Total Deliberations: {result['total_deliberations']}")
        print()
        
        # Print session info
        session_info = result.get('session_info', {})
        print("📋 SESSION INFO:")
        print(f"   - Numero Seduta: {session_info.get('numero_seduta', 'N/A')}")
        print(f"   - Data Seduta: {session_info.get('data_seduta', 'N/A')}")
        print(f"   - Anno: {session_info.get('anno', 'N/A')}")
        print()
        
        # Print deliberations
        deliberations = result.get('deliberations', [])
        print("📝 DELIBERATIONS:")
        print("-" * 30)
        
        for i, delib in enumerate(deliberations, 1):
            print(f"{i}. Deliberation {delib.get('numero', 'N/A')}")
            print(f"   - Tipo Atto: {delib.get('tipo_atto', 'N/A')}")
            print(f"   - Oggetto: {delib.get('oggetto', 'N/A')[:80]}...")
            print(f"   - Proponente: {delib.get('proponente', 'N/A')}")
            print(f"   - FS Flag: {delib.get('fs_flag', False)}")
            print(f"   - Seduta: {delib.get('seduta', 'N/A')}")
            print(f"   - Data Seduta: {delib.get('data_seduta', 'N/A')}")
            print()
        
        # Test anti-duplicate logic (simulate what NotionIntegrator would do)
        print("🔍 ANTI-DUPLICATE LOGIC TEST:")
        print("-" * 30)
        
        # Create a simulated existing database
        simulated_existing = [
            {"seduta": "3928", "numero": "1"},  # This would be found as duplicate
            {"seduta": "3928", "numero": "2"},  # This would be found as duplicate
        ]
        
        # Test each deliberation
        for delib in deliberations:
            seduta = delib.get('seduta')
            numero = delib.get('numero')
            
            # Check if this would be a duplicate
            is_duplicate = any(
                existing['seduta'] == seduta and existing['numero'] == numero
                for existing in simulated_existing
            )
            
            status = "DUPLICATE (would skip)" if is_duplicate else "NEW (would create)"
            print(f"   - Seduta {seduta}, Numero {numero}: {status}")
        
        print()
        print("✅ PDF processing test completed successfully!")
        
        # Save results for inspection
        output_file = "test_pdf_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"📁 Results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during PDF processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pdf_processing()