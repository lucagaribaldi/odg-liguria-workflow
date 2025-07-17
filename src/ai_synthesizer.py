"""
AI Synthesizer for ODG deliberations.
Generates natural language summaries and extracts key information from deliberations.
"""

import logging
import re
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class SynthesisType(Enum):
    """Types of synthesis available."""
    QUICK = "quick"
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    COMMUNICATIVE = "communicative"


class Category(Enum):
    """Categories for deliberation classification."""
    SANITA = "sanità"
    BILANCI = "bilanci"
    GOVERNANCE = "governance"
    AMBIENTE = "ambiente"
    TURISMO = "turismo"
    TRASPORTI = "trasporti"
    SOCIALE = "sociale"
    LAVORO = "lavoro"
    FORMAZIONE = "formazione"
    CULTURA = "cultura"
    SPORT = "sport"
    PROTEZIONE_CIVILE = "protezione_civile"
    URBANISTICA = "urbanistica"
    AGRICOLTURA = "agricoltura"
    ALTRO = "altro"


@dataclass
class ExtractedInfo:
    """Container for extracted information from deliberation."""
    budget: Optional[str] = None
    dates: List[str] = None
    stakeholders: List[str] = None
    category: Category = Category.ALTRO
    keywords: List[str] = None
    urgency: str = "normale"
    
    def __post_init__(self):
        if self.dates is None:
            self.dates = []
        if self.stakeholders is None:
            self.stakeholders = []
        if self.keywords is None:
            self.keywords = []


@dataclass
class SynthesisResult:
    """Container for synthesis results."""
    quick_summary: str
    detailed_synthesis: str
    extracted_info: ExtractedInfo
    synthesis_type: SynthesisType
    confidence: float
    generated_with_ai: bool


class AISynthesizer:
    """AI-powered synthesizer for ODG deliberations."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize the AI synthesizer.
        
        Args:
            anthropic_api_key: Optional API key for Anthropic Claude
        """
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Initialize Anthropic client if available
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_api_key)
                self.logger.info("Anthropic client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Anthropic client: {str(e)}")
        elif not ANTHROPIC_AVAILABLE:
            self.logger.info("Anthropic library not available, using rule-based synthesis")
        
        # Load patterns and rules
        self._load_patterns()
        self._load_category_rules()
        
        self.logger.info("AISynthesizer initialized")
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_patterns(self) -> None:
        """Load regex patterns for information extraction."""
        self.patterns = {
            'budget': [
                r'(?:euro|€|EUR)\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:euro|€|EUR)',
                r'(?:budget|bilancio|stanziamento|finanziamento)\s*[:\s]*(?:euro|€|EUR)?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'(?:costo|spesa|importo)\s*[:\s]*(?:euro|€|EUR)?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
            ],
            'dates': [
                r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
                r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',
                r'(?:dal|fino al|entro il|dal|al)\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
                r'(?:anno|esercizio)\s*(\d{4})'
            ],
            'stakeholders': [
                r'(?:Azienda|ASL|Ospedale|Policlinico|ARPAL|A\.Li\.Sa\.)\s*["\']?([^"\'.\n]+)["\']?',
                r'(?:Comune|Provincia|Regione|Ministero)\s*(?:di|del|della)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'(?:Università|Istituto|Fondazione|Associazione)\s*(?:di|del|della)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'(?:Direttore|Assessore|Presidente|Sindaco)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            ],
            'urgency': [
                r'(?:urgente|urgenza|immediato|straordinario|eccezionale)',
                r'(?:fuori sacco|FS)',
                r'(?:proroga|scadenza|termine)'
            ]
        }
    
    def _load_category_rules(self) -> None:
        """Load rules for automatic categorization."""
        self.category_keywords = {
            Category.SANITA: [
                'sanità', 'sanitario', 'salute', 'ospedale', 'asl', 'policlinico',
                'medico', 'sanitaria', 'arpal', 'farmaceutico', 'terapia',
                'prevenzione', 'diagnosi', 'cura', 'paziente', 'malattia'
            ],
            Category.BILANCI: [
                'bilancio', 'budget', 'finanziario', 'contabilità', 'euro',
                'spesa', 'entrata', 'costo', 'investimento', 'stanziamento',
                'rendiconto', 'previsione', 'economico', 'fondo', 'risorsa'
            ],
            Category.GOVERNANCE: [
                'governance', 'amministrazione', 'direttore', 'nomina', 'incarico',
                'consiglio', 'commissione', 'rappresentante', 'delega',
                'organo', 'statutario', 'regolamento', 'procedura'
            ],
            Category.AMBIENTE: [
                'ambiente', 'ambientale', 'ecologia', 'inquinamento', 'rifiuti',
                'sostenibilità', 'verde', 'parco', 'natura', 'protezione',
                'clima', 'energia', 'rinnovabile', 'emissioni'
            ],
            Category.TURISMO: [
                'turismo', 'turistico', 'promozione', 'valorizzazione',
                'accoglienza', 'ricettività', 'eventi', 'manifestazione',
                'cultura', 'patrimonio', 'museo', 'attrazione'
            ],
            Category.TRASPORTI: [
                'trasporti', 'mobilità', 'traffico', 'viabilità', 'strada',
                'autostrada', 'ferrovia', 'porto', 'aeroporto', 'trasporto',
                'pubblico', 'privato', 'logistica'
            ],
            Category.SOCIALE: [
                'sociale', 'assistenza', 'welfare', 'famiglia', 'minori',
                'anziani', 'disabili', 'inclusione', 'integrazione',
                'servizi', 'sostegno', 'aiuto', 'supporto'
            ],
            Category.LAVORO: [
                'lavoro', 'occupazione', 'disoccupazione', 'impiego',
                'lavoratore', 'dipendente', 'contratto', 'sindacato',
                'formazione', 'professionale', 'qualifica', 'competenza'
            ],
            Category.FORMAZIONE: [
                'formazione', 'educazione', 'istruzione', 'scuola',
                'università', 'studente', 'docente', 'corso',
                'didattica', 'apprendimento', 'qualifica', 'diploma'
            ],
            Category.CULTURA: [
                'cultura', 'culturale', 'arte', 'artistico', 'museo',
                'biblioteca', 'teatro', 'cinema', 'musica', 'libro',
                'patrimonio', 'storico', 'tradizione'
            ],
            Category.SPORT: [
                'sport', 'sportivo', 'atleta', 'palestra', 'impianto',
                'gara', 'competizione', 'federazione', 'società',
                'attività', 'fisica', 'benessere'
            ],
            Category.PROTEZIONE_CIVILE: [
                'protezione', 'civile', 'emergenza', 'calamità', 'rischio',
                'sicurezza', 'prevenzione', 'soccorso', 'allerta',
                'intervento', 'disaster', 'catastrofe'
            ],
            Category.URBANISTICA: [
                'urbanistica', 'urbanistico', 'edilizia', 'costruzione',
                'piano', 'regolatore', 'territorio', 'area', 'zona',
                'sviluppo', 'riqualificazione', 'ristrutturazione'
            ],
            Category.AGRICOLTURA: [
                'agricoltura', 'agricolo', 'agrario', 'coltivazione',
                'produzione', 'azienda', 'terreno', 'sostegno',
                'sviluppo', 'rurale', 'campagna', 'prodotto'
            ]
        }
    
    def generate_quick_summary(self, deliberation: Dict) -> str:
        """
        Generate a quick summary (150-200 characters).
        
        Args:
            deliberation: Deliberation data dictionary
            
        Returns:
            Quick summary string
        """
        try:
            if self.anthropic_client:
                return self._generate_ai_quick_summary(deliberation)
            else:
                return self._generate_rule_based_quick_summary(deliberation)
        except Exception as e:
            self.logger.error(f"Error generating quick summary: {str(e)}")
            return self._generate_fallback_summary(deliberation)
    
    def generate_detailed_synthesis(self, deliberation: Dict, 
                                  synthesis_type: SynthesisType = SynthesisType.EXECUTIVE) -> SynthesisResult:
        """
        Generate detailed synthesis with extracted information.
        
        Args:
            deliberation: Deliberation data dictionary
            synthesis_type: Type of synthesis to generate
            
        Returns:
            SynthesisResult object
        """
        try:
            self.logger.info(f"Generating {synthesis_type.value} synthesis")
            
            # Extract information
            extracted_info = self._extract_information(deliberation)
            
            # Generate summaries
            quick_summary = self.generate_quick_summary(deliberation)
            
            if self.anthropic_client:
                detailed_synthesis = self._generate_ai_detailed_synthesis(
                    deliberation, synthesis_type, extracted_info
                )
                generated_with_ai = True
                confidence = 0.9
            else:
                detailed_synthesis = self._generate_rule_based_detailed_synthesis(
                    deliberation, synthesis_type, extracted_info
                )
                generated_with_ai = False
                confidence = 0.7
            
            return SynthesisResult(
                quick_summary=quick_summary,
                detailed_synthesis=detailed_synthesis,
                extracted_info=extracted_info,
                synthesis_type=synthesis_type,
                confidence=confidence,
                generated_with_ai=generated_with_ai
            )
            
        except Exception as e:
            self.logger.error(f"Error generating detailed synthesis: {str(e)}")
            return self._generate_fallback_synthesis(deliberation, synthesis_type)
    
    def _extract_information(self, deliberation: Dict) -> ExtractedInfo:
        """Extract structured information from deliberation."""
        oggetto = deliberation.get('oggetto', '')
        proponente = deliberation.get('proponente', '')
        
        # Extract budget information
        budget = self._extract_budget(oggetto)
        
        # Extract dates
        dates = self._extract_dates(oggetto)
        
        # Extract stakeholders
        stakeholders = self._extract_stakeholders(oggetto + ' ' + proponente)
        
        # Categorize
        category = self._categorize_deliberation(deliberation)
        
        # Extract keywords
        keywords = self._extract_keywords(oggetto)
        
        # Determine urgency
        urgency = self._determine_urgency(deliberation)
        
        return ExtractedInfo(
            budget=budget,
            dates=dates,
            stakeholders=stakeholders,
            category=category,
            keywords=keywords,
            urgency=urgency
        )
    
    def _extract_budget(self, text: str) -> Optional[str]:
        """Extract budget information from text."""
        for pattern in self.patterns['budget']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        dates = []
        for pattern in self.patterns['dates']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        return list(set(dates))  # Remove duplicates
    
    def _extract_stakeholders(self, text: str) -> List[str]:
        """Extract stakeholders from text."""
        stakeholders = []
        for pattern in self.patterns['stakeholders']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            stakeholders.extend([match.strip() for match in matches])
        return list(set(stakeholders))  # Remove duplicates
    
    def _categorize_deliberation(self, deliberation: Dict) -> Category:
        """Automatically categorize deliberation."""
        text = (deliberation.get('oggetto', '') + ' ' + 
                deliberation.get('proponente', '')).lower()
        
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            if category_scores[best_category] > 0:
                return best_category
        
        return Category.ALTRO
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Simple keyword extraction - can be enhanced with NLP
        words = re.findall(r'\b[a-zA-Zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{4,}\b', text.lower())
        
        # Remove common words
        stop_words = {
            'della', 'delle', 'degli', 'dello', 'alla', 'alle', 'allo',
            'nella', 'nelle', 'nello', 'sulla', 'sulle', 'sullo',
            'dalla', 'dalle', 'dallo', 'della', 'delle', 'degli',
            'questo', 'questa', 'questi', 'queste', 'quello', 'quella',
            'quelli', 'quelle', 'anche', 'ancora', 'dove', 'come',
            'quando', 'mentre', 'prima', 'dopo', 'durante', 'senza'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Return most frequent keywords
        keyword_counts = {}
        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        return sorted(keyword_counts.keys(), key=lambda x: keyword_counts[x], reverse=True)[:10]
    
    def _determine_urgency(self, deliberation: Dict) -> str:
        """Determine urgency level of deliberation."""
        text = (deliberation.get('oggetto', '') + ' ' + 
                str(deliberation.get('fs_flag', ''))).lower()
        
        if deliberation.get('fs_flag', False):
            return 'alta'
        
        for pattern in self.patterns['urgency']:
            if re.search(pattern, text, re.IGNORECASE):
                return 'alta'
        
        return 'normale'
    
    def _generate_ai_quick_summary(self, deliberation: Dict) -> str:
        """Generate quick summary using AI."""
        try:
            prompt = f"""
            Crea un riassunto molto breve (150-200 caratteri) per questa deliberazione:
            
            Numero: {deliberation.get('numero', 'N/A')}
            Tipo: {deliberation.get('tipo_atto', 'N/A')}
            Oggetto: {deliberation.get('oggetto', 'N/A')}
            Proponente: {deliberation.get('proponente', 'N/A')}
            
            Il riassunto deve essere chiaro, conciso e informativo.
            """
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary = response.content[0].text.strip()
            
            # Ensure it's within character limit
            if len(summary) > 200:
                summary = summary[:197] + "..."
            
            return summary
            
        except Exception as e:
            self.logger.error(f"AI quick summary generation failed: {str(e)}")
            return self._generate_rule_based_quick_summary(deliberation)
    
    def _generate_rule_based_quick_summary(self, deliberation: Dict) -> str:
        """Generate quick summary using rule-based approach."""
        oggetto = deliberation.get('oggetto', '')
        tipo_atto = deliberation.get('tipo_atto', '')
        
        # Extract key elements
        key_terms = self._extract_key_terms_for_summary(oggetto)
        
        # Generate summary
        if key_terms:
            summary = f"{tipo_atto}: {' '.join(key_terms[:3])}"
        else:
            summary = f"{tipo_atto}: {oggetto[:100]}"
        
        # Truncate to fit limit
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary
    
    def _extract_key_terms_for_summary(self, text: str) -> List[str]:
        """Extract key terms for summary generation."""
        # Simple extraction of meaningful terms
        important_words = []
        
        # Look for organization names
        orgs = re.findall(r'\b[A-Z][A-Z\.]+\b', text)
        important_words.extend(orgs)
        
        # Look for capitalized words (likely proper nouns)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        important_words.extend(proper_nouns[:3])
        
        # Look for action words
        actions = ['nomina', 'approvazione', 'deliberazione', 'decreto', 'autorizzazione']
        for action in actions:
            if action.lower() in text.lower():
                important_words.append(action)
        
        return important_words[:5]
    
    def _generate_ai_detailed_synthesis(self, deliberation: Dict, 
                                      synthesis_type: SynthesisType, 
                                      extracted_info: ExtractedInfo) -> str:
        """Generate detailed synthesis using AI."""
        try:
            # Customize prompt based on synthesis type
            if synthesis_type == SynthesisType.EXECUTIVE:
                style = "esecutivo, focalizzato su impatti e decisioni chiave"
            elif synthesis_type == SynthesisType.OPERATIONAL:
                style = "operativo, con dettagli implementativi e procedure"
            elif synthesis_type == SynthesisType.COMMUNICATIVE:
                style = "comunicativo, adatto al pubblico generale"
            else:
                style = "generale"
            
            prompt = f"""
            Genera una sintesi dettagliata in stile {style} per questa deliberazione:
            
            Numero: {deliberation.get('numero', 'N/A')}
            Tipo: {deliberation.get('tipo_atto', 'N/A')}
            Oggetto: {deliberation.get('oggetto', 'N/A')}
            Proponente: {deliberation.get('proponente', 'N/A')}
            Categoria: {extracted_info.category.value}
            Budget: {extracted_info.budget or 'N/A'}
            Urgenza: {extracted_info.urgency}
            
            La sintesi deve essere completa, professionale e ben strutturata.
            """
            
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            self.logger.error(f"AI detailed synthesis generation failed: {str(e)}")
            return self._generate_rule_based_detailed_synthesis(
                deliberation, synthesis_type, extracted_info
            )
    
    def _generate_rule_based_detailed_synthesis(self, deliberation: Dict, 
                                              synthesis_type: SynthesisType, 
                                              extracted_info: ExtractedInfo) -> str:
        """Generate detailed synthesis using rule-based approach."""
        parts = []
        
        # Header
        parts.append(f"**{deliberation.get('tipo_atto', 'Atto')} n. {deliberation.get('numero', 'N/A')}**")
        
        # Category and urgency
        parts.append(f"Categoria: {extracted_info.category.value.title()}")
        if extracted_info.urgency == 'alta':
            parts.append("⚠️ **Urgenza elevata**")
        
        # Main content
        oggetto = deliberation.get('oggetto', '')
        if len(oggetto) > 300:
            parts.append(f"Oggetto: {oggetto[:300]}...")
        else:
            parts.append(f"Oggetto: {oggetto}")
        
        # Proponent
        parts.append(f"Proponente: {deliberation.get('proponente', 'N/A')}")
        
        # Budget if available
        if extracted_info.budget:
            parts.append(f"Budget: €{extracted_info.budget}")
        
        # Stakeholders
        if extracted_info.stakeholders:
            parts.append(f"Stakeholder coinvolti: {', '.join(extracted_info.stakeholders[:3])}")
        
        # Dates
        if extracted_info.dates:
            parts.append(f"Date rilevanti: {', '.join(extracted_info.dates)}")
        
        return '\n\n'.join(parts)
    
    def _generate_fallback_summary(self, deliberation: Dict) -> str:
        """Generate fallback summary when all else fails."""
        oggetto = deliberation.get('oggetto', 'Deliberazione senza oggetto')
        if len(oggetto) > 180:
            return oggetto[:177] + "..."
        return oggetto
    
    def _generate_fallback_synthesis(self, deliberation: Dict, 
                                   synthesis_type: SynthesisType) -> SynthesisResult:
        """Generate fallback synthesis when all else fails."""
        quick_summary = self._generate_fallback_summary(deliberation)
        
        detailed_synthesis = f"""
        **Deliberazione n. {deliberation.get('numero', 'N/A')}**
        
        Tipo: {deliberation.get('tipo_atto', 'N/A')}
        Oggetto: {deliberation.get('oggetto', 'N/A')}
        Proponente: {deliberation.get('proponente', 'N/A')}
        
        *Sintesi generata automaticamente*
        """
        
        extracted_info = ExtractedInfo()
        
        return SynthesisResult(
            quick_summary=quick_summary,
            detailed_synthesis=detailed_synthesis,
            extracted_info=extracted_info,
            synthesis_type=synthesis_type,
            confidence=0.5,
            generated_with_ai=False
        )


def main():
    """Example usage of the AISynthesizer."""
    # Initialize with API key from environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    synthesizer = AISynthesizer(anthropic_api_key=api_key)
    
    # Example deliberation
    deliberation = {
        'numero': '1',
        'tipo_atto': 'Deliberazione',
        'oggetto': 'AZIENDA PUBBLICA DI SERVIZI ALLA PERSONA OPERE PIE RIUNITE DEVOTO MARINI SIVORI - CONSIGLIO DI AMMINISTRAZIONE - SCELTA RAPPRESENTANTE REGIONALE',
        'proponente': 'BUCCI Marco',
        'fs_flag': True
    }
    
    try:
        # Generate quick summary
        quick = synthesizer.generate_quick_summary(deliberation)
        print(f"Quick Summary: {quick}")
        
        # Generate detailed synthesis
        detailed = synthesizer.generate_detailed_synthesis(
            deliberation, 
            SynthesisType.EXECUTIVE
        )
        
        print(f"\nDetailed Synthesis:")
        print(detailed.detailed_synthesis)
        
        print(f"\nExtracted Info:")
        print(f"Category: {detailed.extracted_info.category.value}")
        print(f"Urgency: {detailed.extracted_info.urgency}")
        print(f"Generated with AI: {detailed.generated_with_ai}")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()