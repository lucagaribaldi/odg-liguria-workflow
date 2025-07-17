"""
PDF Parser for ODG (Ordine del Giorno) documents from Regione Liguria.
Extracts session data and deliberations from PDF files.
"""

import logging
import re
import pdfplumber
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class ODGPDFParser:
    """Parser for ODG PDF documents from Regione Liguria."""
    
    def __init__(self, log_level: str = "INFO"):
        """Initialize the parser with logging configuration."""
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
        # Common patterns for ODG documents
        self.session_patterns = {
            'numero_seduta': r'(?:Seduta|SEDUTA)\s+(?:N\.|n\.|NUM\.|num\.)\s*(\d+)',
            'numero_seduta_alt': r'della\s+Seduta\s+N°\s*(\d+)',
            'data_seduta': r'(?:del|DEL)\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
            'deliberazione': r'(?:Deliberazione|DELIBERAZIONE)\s+(?:N\.|n\.|NUM\.|num\.)\s*(\d+)',
            'tipo_atto': r'(?:DGR|DCR|DPR|DECRETO|ORDINANZA|CIRCOLARE)',
            'proponente': r'(?:Proponente|PROPONENTE|Assessore|ASSESSORE):?\s*([^\n]+)',
            'fs_flag': r'(?:FS|F\.S\.|FUORI SACCO|fuori sacco)'
        }
    
    def setup_logging(self, log_level: str) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/pdf_parser.log')
            ]
        )
    
    def parse_odg(self, pdf_path: str) -> Dict:
        """
        Parse ODG PDF and extract structured data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing session info and deliberations list
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            self.logger.info(f"Starting to parse PDF: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract all text from PDF
                full_text = self._extract_full_text(pdf)
                
                # Extract session information
                session_info = self._extract_session_info(full_text)
                
                # Extract deliberations
                deliberations = self._extract_deliberations(full_text)
                
                result = {
                    'pdf_file': str(pdf_path),
                    'parsing_date': datetime.now().isoformat(),
                    'session_info': session_info,
                    'deliberations': deliberations,
                    'total_deliberations': len(deliberations)
                }
                
                self.logger.info(f"Successfully parsed {len(deliberations)} deliberations")
                return result
                
        except Exception as e:
            self.logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise
    
    def _extract_full_text(self, pdf) -> str:
        """Extract all text from PDF pages."""
        full_text = ""
        for page_num, page in enumerate(pdf.pages):
            try:
                text = page.extract_text()
                if text:
                    full_text += f"\n--- PAGE {page_num + 1} ---\n{text}"
                    self.logger.debug(f"Extracted text from page {page_num + 1}")
            except Exception as e:
                self.logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
        
        return full_text
    
    def _extract_session_info(self, text: str) -> Dict:
        """Extract session number and date from text."""
        session_info = {
            'numero_seduta': None,
            'data_seduta': None,
            'anno': None
        }
        
        # Extract session number
        session_match = re.search(self.session_patterns['numero_seduta'], text, re.IGNORECASE)
        if not session_match:
            session_match = re.search(self.session_patterns['numero_seduta_alt'], text, re.IGNORECASE)
        if session_match:
            session_info['numero_seduta'] = session_match.group(1)
            self.logger.debug(f"Found session number: {session_info['numero_seduta']}")
        
        # Extract session date
        date_match = re.search(self.session_patterns['data_seduta'], text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            session_info['data_seduta'] = self._normalize_date(date_str)
            if session_info['data_seduta']:
                session_info['anno'] = session_info['data_seduta'][:4]
            self.logger.debug(f"Found session date: {session_info['data_seduta']}")
        
        return session_info
    
    def _extract_deliberations(self, text: str) -> List[Dict]:
        """Extract deliberations from text."""
        deliberations = []
        
        # Look for deliberation patterns in ODG format
        # Pattern: uf0b7 N° d'ordine in ODG: X [FS] (uf0b7 is the bullet character)
        pattern = r'\uf0b7\s*N°\s*d\'ordine\s*in\s*ODG:\s*(\d+)\s*(FS)?\s*\n\s*Tipo\s*Atto:\s*([^\n]+)\s*\n\s*Oggetto:\s*([^\uf0b7]+?)(?=\n\s*Amministratore\s*proponente:)\s*\n\s*Amministratore\s*proponente:\s*([^\n\uf0b7]+)'
        
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        for match in matches:
            numero, fs_flag, tipo_atto, oggetto, proponente = match
            
            # Clean up the extracted data
            oggetto = re.sub(r'\s+', ' ', oggetto.strip())
            proponente = proponente.strip()
            
            deliberation = {
                'numero': numero,
                'tipo_atto': tipo_atto.strip(),
                'oggetto': oggetto,
                'proponente': proponente,
                'fs_flag': bool(fs_flag),
                'order': len(deliberations) + 1
            }
            
            deliberations.append(deliberation)
            self.logger.debug(f"Extracted deliberation: {deliberation.get('numero', 'N/A')}")
        
        return deliberations
    
    def _parse_deliberation_section(self, section: str) -> Optional[Dict]:
        """Parse a single deliberation section."""
        deliberation = {
            'numero': None,
            'tipo_atto': None,
            'oggetto': None,
            'proponente': None,
            'fs_flag': False,
            'raw_text': section.strip()
        }
        
        # Extract deliberation number
        delib_match = re.search(r'(\d+)\.\s*', section)
        if delib_match:
            deliberation['numero'] = delib_match.group(1)
        
        # Extract type of act
        tipo_match = re.search(self.session_patterns['tipo_atto'], section, re.IGNORECASE)
        if tipo_match:
            deliberation['tipo_atto'] = tipo_match.group(0).upper()
        
        # Extract object/subject
        oggetto = self._extract_oggetto(section)
        if oggetto:
            deliberation['oggetto'] = oggetto
        
        # Extract proponent
        proponente_match = re.search(self.session_patterns['proponente'], section, re.IGNORECASE)
        if proponente_match:
            deliberation['proponente'] = proponente_match.group(1).strip()
        
        # Check for FS flag
        fs_match = re.search(self.session_patterns['fs_flag'], section, re.IGNORECASE)
        if fs_match:
            deliberation['fs_flag'] = True
        
        # Return only if we have at least a number or type
        if deliberation['numero'] or deliberation['tipo_atto']:
            return deliberation
        
        return None
    
    def _extract_oggetto(self, section: str) -> Optional[str]:
        """Extract the object/subject from a deliberation section."""
        # Remove deliberation number and type from the beginning
        cleaned_section = re.sub(r'^\d+\.\s*(?:DGR|DCR|DECRETO|ORDINANZA|CIRCOLARE)\s*', '', section, flags=re.IGNORECASE)
        
        # Look for object patterns
        lines = cleaned_section.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not re.match(r'^\s*(?:Proponente|PROPONENTE|Assessore)', line, re.IGNORECASE):
                # Clean up the line
                oggetto = re.sub(r'\s+', ' ', line)
                if oggetto and len(oggetto) > 10:
                    return oggetto
        
        return None
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO format (YYYY-MM-DD)."""
        try:
            # Handle different date formats
            date_patterns = [
                r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})',
                r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    parts = match.groups()
                    if len(parts[2]) == 4:  # Year is last
                        day, month, year = parts
                    else:  # Year is first
                        year, month, day = parts
                    
                    # Normalize to ISO format
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error normalizing date '{date_str}': {str(e)}")
            return None


def main():
    """Example usage of the ODGPDFParser."""
    parser = ODGPDFParser()
    
    # Example usage
    try:
        result = parser.parse_odg("data/input/sample_odg.pdf")
        print(f"Parsed {result['total_deliberations']} deliberations")
        
        for delib in result['deliberations']:
            print(f"- {delib['numero']}: {delib['tipo_atto']} - {delib['oggetto'][:50]}...")
            
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()