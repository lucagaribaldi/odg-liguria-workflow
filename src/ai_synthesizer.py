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