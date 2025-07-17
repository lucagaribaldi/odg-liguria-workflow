"""
Pytest configuration and fixtures for ODG Liguria Workflow tests.
"""
import os
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import shutil

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF file for testing."""
    return Path(__file__).parent.parent / "data" / "input" / "ODG_10072025.pdf"


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    with patch('notion_client.Client') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    with patch('anthropic.Anthropic') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_requests():
    """Mock requests for web scraping tests."""
    with patch('requests.Session') as mock_session:
        mock_instance = Mock()
        mock_session.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_deliberation():
    """Sample deliberation data for testing."""
    return {
        "numero": "1",
        "tipo_atto": "Deliberazione",
        "oggetto": "Test deliberation object",
        "proponente": "Test Proponent",
        "fs_flag": True,
        "order": 1,
        "seduta": "3929",
        "data_seduta": "2025-07-10"
    }


@pytest.fixture
def sample_session_info():
    """Sample session info for testing."""
    return {
        "numero_seduta": "3929",
        "data_seduta": "2025-07-10",
        "anno": "2025"
    }


@pytest.fixture
def env_vars():
    """Set up environment variables for testing."""
    env_vars = {
        'NOTION_TOKEN': 'test_token',
        'NOTION_DATABASE_ID': 'test_db_id',
        'ANTHROPIC_API_KEY': 'test_anthropic_key'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    yield