"""
Unit tests for PDF Parser module.
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from pdf_parser import ODGPDFParser


class TestODGPDFParser:
    """Test suite for ODGPDFParser class."""

    def test_init(self):
        """Test ODGPDFParser initialization."""
        parser = ODGPDFParser()
        assert parser is not None
        assert hasattr(parser, 'logger')

    @patch('pdf_parser.pdfplumber.open')
    def test_parse_odg_success(self, mock_pdf_open, sample_pdf_path):
        """Test successful ODG parsing."""
        # Mock PDF content
        mock_page = Mock()
        mock_page.extract_text.return_value = """
        SEDUTA N. 3929 DEL 10/07/2025
        
        • N° d'ordine in ODG: 1 FS
        Tipo Atto: Deliberazione
        Oggetto: Test deliberation
        Proponente: Test Proponent
        
        • N° d'ordine in ODG: 2
        Tipo Atto: Deliberazione
        Oggetto: Another test deliberation
        Proponente: Another Proponent
        """
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        parser = ODGPDFParser()
        result = parser.parse_odg(str(sample_pdf_path))
        
        assert result is not None
        assert 'session_info' in result
        assert 'deliberations' in result
        assert len(result['deliberations']) == 2
        assert result['session_info']['numero_seduta'] == '3929'
        assert result['session_info']['data_seduta'] == '2025-07-10'

    @patch('pdf_parser.pdfplumber.open')
    def test_parse_odg_file_not_found(self, mock_pdf_open):
        """Test ODG parsing with file not found."""
        mock_pdf_open.side_effect = FileNotFoundError("File not found")
        
        parser = ODGPDFParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_odg("nonexistent.pdf")

    @patch('pdf_parser.pdfplumber.open')
    def test_parse_odg_invalid_format(self, mock_pdf_open):
        """Test ODG parsing with invalid PDF format."""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Invalid PDF content"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        parser = ODGPDFParser()
        result = parser.parse_odg("test.pdf")
        
        # Should return empty results for invalid format
        assert result['deliberations'] == []
        assert result['session_info'] == {}

    def test_extract_session_info(self):
        """Test session info extraction."""
        parser = ODGPDFParser()
        
        text = "SEDUTA N. 3929 DEL 10/07/2025"
        session_info = parser._extract_session_info(text)
        
        assert session_info['numero_seduta'] == '3929'
        assert session_info['data_seduta'] == '2025-07-10'
        assert session_info['anno'] == '2025'

    def test_extract_deliberations(self):
        """Test deliberations extraction."""
        parser = ODGPDFParser()
        
        text = """
        • N° d'ordine in ODG: 1 FS
        Tipo Atto: Deliberazione
        Oggetto: Test deliberation
        Proponente: Test Proponent
        """
        
        deliberations = parser._extract_deliberations(text)
        
        assert len(deliberations) == 1
        assert deliberations[0]['numero'] == '1'
        assert deliberations[0]['fs_flag'] is True
        assert deliberations[0]['tipo_atto'] == 'Deliberazione'
        assert deliberations[0]['oggetto'] == 'Test deliberation'
        assert deliberations[0]['proponente'] == 'Test Proponent'