#!/usr/bin/env python3
"""
Analisi del nuovo PDF ODG_17072025.pdf
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_parser import ODGPDFParser
from ai_synthesizer import AISynthesizer

def analyze_new_pdf():
    """Analizza il nuovo PDF ODG_17072025.pdf"""
    
    # Initialize components
    parser = ODGPDFParser()
    synthesizer = AISynthesizer(use_ai=False)
    
    # Parse the new PDF
    pdf_path = "data/input/ODG_17072025.pdf"
    
    print("🔍 ANALISI DEL NUOVO PDF: ODG_17072025.pdf")
    print("=" * 60)
    
    try:
        # Parse PDF
        result = parser.parse_odg(pdf_path)
        
        # Display basic info
        session_info = result.get('session_info', {})
        deliberations = result.get('deliberations', [])
        
        print(f"📄 File: {result['pdf_file']}")
        print(f"📅 Data parsing: {result['parsing_date']}")
        print(f"📊 Totale deliberazioni: {result['total_deliberations']}")
        print()
        
        print("📋 INFORMAZIONI SESSIONE:")
        print(f"   - Numero seduta: {session_info.get('numero_seduta', 'N/A')}")
        print(f"   - Data seduta: {session_info.get('data_seduta', 'N/A')}")
        print(f"   - Anno: {session_info.get('anno', 'N/A')}")
        print()
        
        # Analyze deliberations
        print("📝 ANALISI DELIBERAZIONI:")
        print("-" * 40)
        
        # Count by type
        tipo_count = {}
        fs_count = 0
        
        for delib in deliberations:
            tipo = delib.get('tipo_atto', 'N/A')
            tipo_count[tipo] = tipo_count.get(tipo, 0) + 1
            
            if delib.get('fs_flag', False):
                fs_count += 1
        
        print(f"📊 Distribuzione per tipo:")
        for tipo, count in sorted(tipo_count.items()):
            print(f"   - {tipo}: {count}")
        
        print(f"🚨 Deliberazioni FS (Fuori Sacco): {fs_count}")
        print()
        
        # Show some examples
        print("📋 PRIME 5 DELIBERAZIONI:")
        print("-" * 40)
        
        for i, delib in enumerate(deliberations[:5], 1):
            print(f"{i}. Deliberazione {delib.get('numero', 'N/A')}")
            print(f"   - Tipo: {delib.get('tipo_atto', 'N/A')}")
            print(f"   - Oggetto: {delib.get('oggetto', 'N/A')[:80]}...")
            print(f"   - Proponente: {delib.get('proponente', 'N/A')}")
            print(f"   - FS: {'Sì' if delib.get('fs_flag', False) else 'No'}")
            print()
        
        # Show categories after AI synthesis
        print("🤖 SINTESI AI:")
        print("-" * 40)
        
        # Synthesize with AI
        synthesized_deliberations = synthesizer.synthesize_batch(deliberations)
        
        # Extract some example summaries
        for i, delib in enumerate(synthesized_deliberations[:3], 1):
            print(f"{i}. Deliberazione {delib.get('numero', 'N/A')}")
            print(f"   - Riassunto: {delib.get('sintesi_rapida', 'N/A')}")
            print(f"   - Confidence: {delib.get('ai_confidence', 'N/A')}")
            print()
        
        # Compare with other sessions
        print("📊 CONFRONTO CON ALTRE SESSIONI:")
        print("-" * 40)
        
        sessions_data = {
            "3928": {"date": "2025-07-03", "deliberations": 9, "file": "ODG_03072025.pdf"},
            "3929": {"date": "2025-07-10", "deliberations": 22, "file": "ODG_10072025.pdf"}, 
            "3930": {"date": "2025-07-17", "deliberations": 19, "file": "ODG_17072025.pdf"}
        }
        
        for session, data in sessions_data.items():
            print(f"   - Seduta {session}: {data['date']} - {data['deliberations']} deliberazioni")
        
        total_deliberations = sum(data['deliberations'] for data in sessions_data.values())
        print(f"   - TOTALE: {total_deliberations} deliberazioni in 3 sessioni")
        
        print()
        print("✅ Analisi completata con successo!")
        
        # Save detailed analysis
        analysis_result = {
            "pdf_file": pdf_path,
            "analysis_date": result['parsing_date'],
            "session_info": session_info,
            "total_deliberations": len(deliberations),
            "tipo_distribution": tipo_count,
            "fs_count": fs_count,
            "synthesized_deliberations": synthesized_deliberations,
            "comparison": sessions_data
        }
        
        analysis_file = "analysis_ODG_17072025.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Analisi dettagliata salvata in: {analysis_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante l'analisi: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_new_pdf()