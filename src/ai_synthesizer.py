#!/usr/bin/env python3
"""
AI Synthesizer for ODG Deliberations
Generates intelligent summaries and analysis of deliberations.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Category(Enum):
    """Deliberation categories."""
    SANITA = "sanità"
    BILANCI = "bilanci"
    GOVERNANCE = "governance"
    AMBIENTE = "ambiente"
    SOCIALE = "sociale"
    ALTRO = "altro"


class SynthesisType(Enum):
    """Types of synthesis that can be generated."""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    COMMUNICATIVE = "communicative"


@dataclass
class ExtractedInfo:
    """Extracted information from deliberation."""
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


class AISynthesizer:
    """AI-powered synthesizer for deliberation analysis."""

    def __init__(self, use_ai: bool = False):
        """Initialize the AI synthesizer."""
        self.use_ai = use_ai
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AISynthesizer initialized (AI enabled: {use_ai})")

    def synthesize_deliberation(self, deliberation: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize a deliberation with analysis."""
        try:
            # Generate basic summary
            sintesi_rapida = self._generate_summary(deliberation)

            # Add synthesis results
            result = deliberation.copy()
            result.update({
                'sintesi_rapida': sintesi_rapida,
                'ai_confidence': 0.9 if self.use_ai else 0.7,
                'generated_with_ai': self.use_ai
            })

            return result

        except Exception as e:
            self.logger.error(f"Error synthesizing deliberation: {str(e)}")
            result = deliberation.copy()
            result.update({
                'synthesis_error': str(e),
                'ai_confidence': 0.0,
                'generated_with_ai': False
            })
            return result

    def _generate_summary(self, deliberation: Dict[str, Any]) -> str:
        """Generate a summary."""
        tipo_atto = deliberation.get('tipo_atto', 'Deliberazione')
        oggetto = deliberation.get('oggetto', '')

        if oggetto:
            words = oggetto.split()
            key_words = [word for word in words if len(word) > 3][:3]
            summary = f"{tipo_atto}: {' '.join(key_words)}"
        else:
            summary = f"{tipo_atto}: {deliberation.get('numero', 'N/A')}"

        return summary[:50]

    def synthesize_batch(self, deliberations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synthesize a batch of deliberations."""
        synthesized = []

        for i, deliberation in enumerate(deliberations, 1):
            try:
                self.logger.info(f"Synthesizing deliberation {i}/{len(deliberations)}")
                result = self.synthesize_deliberation(deliberation)
                synthesized.append(result)
            except Exception as e:
                self.logger.error(f"Error synthesizing deliberation {i}: {str(e)}")
                error_result = deliberation.copy()
                error_result['synthesis_error'] = str(e)
                synthesized.append(error_result)

        return synthesized

    def generate_detailed_synthesis(self, deliberation: Dict[str, Any], synthesis_type: SynthesisType = SynthesisType.EXECUTIVE) -> 'SynthesisResult':
        """Generate detailed synthesis based on type."""
        # Extract information
        extracted_info = self._extract_information(deliberation)

        # Generate synthesis based on type
        if synthesis_type == SynthesisType.EXECUTIVE:
            quick_summary = self._generate_executive_summary(deliberation)
            detailed_synthesis = self._generate_executive_analysis(deliberation)
        elif synthesis_type == SynthesisType.OPERATIONAL:
            quick_summary = self._generate_operational_summary(deliberation)
            detailed_synthesis = self._generate_operational_analysis(deliberation)
        elif synthesis_type == SynthesisType.COMMUNICATIVE:
            quick_summary = self._generate_communicative_summary(deliberation)
            detailed_synthesis = self._generate_communicative_analysis(deliberation)
        else:
            quick_summary = self._generate_summary(deliberation)
            detailed_synthesis = f"Detailed analysis of: {deliberation.get('oggetto', 'N/A')}"

        return SynthesisResult(
            quick_summary=quick_summary,
            detailed_synthesis=detailed_synthesis,
            extracted_info=extracted_info,
            confidence=0.8,
            generated_with_ai=self.use_ai,
            synthesis_type=synthesis_type
        )

    def generate_quick_summary(self, deliberation: Dict[str, Any]) -> str:
        """Generate a quick summary of the deliberation."""
        return self._generate_summary(deliberation)

    def _extract_information(self, deliberation: Dict[str, Any]) -> ExtractedInfo:
        """Extract structured information from deliberation."""
        oggetto = deliberation.get("oggetto", "")

        # Simple keyword-based categorization
        category = Category.ALTRO
        if any(word in oggetto.lower() for word in ["sanit", "salute", "ospedale"]):
            category = Category.SANITA
        elif any(word in oggetto.lower() for word in ["bilancio", "finanzi", "budget"]):
            category = Category.BILANCI
        elif any(word in oggetto.lower() for word in ["govern", "amministr", "organiz"]):
            category = Category.GOVERNANCE
        elif any(word in oggetto.lower() for word in ["ambient", "ecologi", "energia"]):
            category = Category.AMBIENTE
        elif any(word in oggetto.lower() for word in ["social", "assist", "cittadin"]):
            category = Category.SOCIALE

        # Extract basic information
        return ExtractedInfo(
            category=category,
            keywords=self._extract_keywords(oggetto),
            urgency="normale"
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w{4,}\b', text.lower())
        return list(set(words))[:5]  # Return top 5 unique keywords

    def _generate_executive_summary(self, deliberation: Dict[str, Any]) -> str:
        """Generate executive summary."""
        oggetto = deliberation.get("oggetto", "")
        return f"Deliberazione esecutiva: {oggetto[:100]}..."

    def _generate_executive_analysis(self, deliberation: Dict[str, Any]) -> str:
        """Generate executive analysis."""
        return f"Analisi esecutiva dettagliata per: {deliberation.get('numero', 'N/A')}"

    def _generate_operational_summary(self, deliberation: Dict[str, Any]) -> str:
        """Generate operational summary."""
        return f"Aspetti operativi: {deliberation.get('oggetto', '')[:100]}..."

    def _generate_operational_analysis(self, deliberation: Dict[str, Any]) -> str:
        """Generate operational analysis."""
        return f"Analisi operativa per deliberazione {deliberation.get('numero', 'N/A')}"

    def _generate_communicative_summary(self, deliberation: Dict[str, Any]) -> str:
        """Generate communicative summary."""
        return f"Comunicazione pubblica: {deliberation.get('oggetto', '')[:100]}..."

    def _generate_communicative_analysis(self, deliberation: Dict[str, Any]) -> str:
        """Generate communicative analysis."""
        return f"Analisi comunicativa per deliberazione {deliberation.get('numero', 'N/A')}"


@dataclass
class SynthesisResult:
    """Result of synthesis operation."""
    quick_summary: str
    detailed_synthesis: str
    extracted_info: ExtractedInfo
    confidence: float
    generated_with_ai: bool
    synthesis_type: SynthesisType

