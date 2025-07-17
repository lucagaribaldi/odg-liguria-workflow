"""
Unit tests for Decreto Scraper module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from decreto_scraper import DecretoScraper


class TestDecretoScraper:
    """Test suite for DecretoScraper class."""

    def test_init(self):
        """Test DecretoScraper initialization."""
        scraper = DecretoScraper()
        assert scraper is not None
        assert scraper.base_url == "https://decretidigitali.regione.liguria.it"
        assert scraper.rate_limit == 1.0
        assert scraper.max_retries == 3
        assert scraper.timeout == 30

    def test_init_custom_params(self):
        """Test DecretoScraper with custom parameters."""
        scraper = DecretoScraper(
            base_url="https://custom.url",
            rate_limit=0.5,
            max_retries=5,
            timeout=60
        )
        assert scraper.base_url == "https://custom.url"
        assert scraper.rate_limit == 0.5
        assert scraper.max_retries == 5
        assert scraper.timeout == 60

    @patch('decreto_scraper.time.sleep')
    def test_rate_limit(self, mock_sleep):
        """Test rate limiting functionality."""
        scraper = DecretoScraper(rate_limit=1.0)
        
        # First call should not sleep
        scraper._rate_limit()
        mock_sleep.assert_not_called()
        
        # Second call should sleep
        scraper._rate_limit()
        mock_sleep.assert_called_once()

    @patch('decreto_scraper.requests.Session.get')
    def test_make_request_success(self, mock_get):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        scraper = DecretoScraper()
        response = scraper._make_request("https://test.com")
        
        assert response == mock_response
        mock_get.assert_called_once()

    @patch('decreto_scraper.requests.Session.get')
    @patch('decreto_scraper.time.sleep')
    def test_make_request_retry(self, mock_sleep, mock_get):
        """Test HTTP request with retry logic."""
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            Mock()
        ]
        
        scraper = DecretoScraper(max_retries=3)
        response = scraper._make_request("https://test.com")
        
        assert response is not None
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('decreto_scraper.requests.Session.get')
    def test_make_request_failure(self, mock_get):
        """Test HTTP request complete failure."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        scraper = DecretoScraper(max_retries=2)
        response = scraper._make_request("https://test.com")
        
        assert response is None
        assert mock_get.call_count == 2

    @patch.object(DecretoScraper, '_search_by_numero_and_date')
    def test_verify_decreto_publication_found(self, mock_search):
        """Test decreto verification when found."""
        mock_search.return_value = {
            'found': True,
            'url': 'https://test.com/decreto/123',
            'data_pubblicazione': '2025-07-15',
            'dgr_numero': '123',
            'dgr_anno': '2025'
        }
        
        scraper = DecretoScraper()
        result = scraper.verify_decreto_publication("3929", "1", "Test oggetto", "2025-07-10")
        
        assert result['found'] is True
        assert result['url'] == 'https://test.com/decreto/123'
        assert result['data_pubblicazione'] == '2025-07-15'
        assert result['dgr_numero'] == '123'
        assert result['dgr_anno'] == '2025'

    @patch.object(DecretoScraper, '_search_by_numero_and_date')
    @patch.object(DecretoScraper, '_search_by_oggetto_and_date')
    @patch.object(DecretoScraper, '_search_by_seduta_and_numero')
    @patch.object(DecretoScraper, '_search_by_numero')
    def test_verify_decreto_publication_not_found(self, mock_search1, mock_search2, mock_search3, mock_search4):
        """Test decreto verification when not found."""
        # All search strategies return not found
        mock_search1.return_value = {'found': False, 'url': None, 'data_pubblicazione': None, 'dgr_numero': None, 'dgr_anno': None}
        mock_search2.return_value = {'found': False, 'url': None, 'data_pubblicazione': None, 'dgr_numero': None, 'dgr_anno': None}
        mock_search3.return_value = {'found': False, 'url': None, 'data_pubblicazione': None, 'dgr_numero': None, 'dgr_anno': None}
        mock_search4.return_value = {'found': False, 'url': None, 'data_pubblicazione': None, 'dgr_numero': None, 'dgr_anno': None}
        
        scraper = DecretoScraper()
        result = scraper.verify_decreto_publication("3929", "1", "Test oggetto", "2025-07-10")
        
        assert result['found'] is False
        assert result['url'] is None
        assert result['data_pubblicazione'] is None
        assert result['dgr_numero'] is None
        assert result['dgr_anno'] is None

    def test_extract_key_terms(self):
        """Test key terms extraction from oggetto."""
        scraper = DecretoScraper()
        
        oggetto = "Approvazione del bilancio di previsione per l'anno 2025"
        terms = scraper._extract_key_terms(oggetto)
        
        assert 'approvazione' in terms
        assert 'bilancio' in terms
        assert 'previsione' in terms
        assert 'anno' in terms
        assert len(terms) <= 5

    def test_extract_dgr_info(self):
        """Test DGR information extraction."""
        scraper = DecretoScraper()
        
        text = "DGR n. 123/2025 del 15/07/2025"
        dgr_info = scraper._extract_dgr_info(text)
        
        assert dgr_info is not None
        assert dgr_info['numero'] == '123'
        assert dgr_info['anno'] == '2025'

    def test_extract_date_info(self):
        """Test date information extraction."""
        scraper = DecretoScraper()
        
        text = "Pubblicato il 15/07/2025"
        date_info = scraper._extract_date_info(text)
        
        assert date_info is not None
        assert date_info == '2025-07-15'

    def test_normalize_date_string(self):
        """Test date string normalization."""
        scraper = DecretoScraper()
        
        # Test different formats
        assert scraper._normalize_date_string("15/07/2025") == "2025-07-15"
        assert scraper._normalize_date_string("2025-07-15") == "2025-07-15"
        assert scraper._normalize_date_string("15-07-2025") == "2025-07-15"
        assert scraper._normalize_date_string("invalid") is None

    def test_calculate_match_score(self):
        """Test match score calculation."""
        scraper = DecretoScraper()
        
        # Create mock link element
        link = Mock()
        link.get_text.return_value = "DGR n. 123 - Test deliberation"
        link.get.return_value = "/decreto/123"
        
        score = scraper._calculate_match_score(link, "123", "Test deliberation")
        
        assert score > 0.5  # Should have good score due to number match
        assert score < 1.0  # Should not be perfect match