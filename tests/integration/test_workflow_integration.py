"""
Integration tests for the complete ODG workflow.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from workflow_orchestrator import ODGWorkflowOrchestrator, WorkflowMetrics


class TestWorkflowIntegration:
    """Integration tests for the complete workflow."""

    @pytest.fixture
    def mock_orchestrator(self, env_vars):
        """Create a mock orchestrator for testing."""
        with patch('workflow_orchestrator.ODGPDFParser'), \
             patch('workflow_orchestrator.DecretoScraper'), \
             patch('workflow_orchestrator.AISynthesizer'), \
             patch('workflow_orchestrator.NotionIntegrator'):
            
            orchestrator = ODGWorkflowOrchestrator(
                notion_token=env_vars['NOTION_TOKEN'],
                notion_database_id=env_vars['NOTION_DATABASE_ID'],
                anthropic_api_key=env_vars['ANTHROPIC_API_KEY']
            )
            yield orchestrator

    def test_workflow_metrics_initialization(self):
        """Test WorkflowMetrics initialization."""
        metrics = WorkflowMetrics()
        
        assert metrics.total_deliberations == 0
        assert metrics.parsed_successfully == 0
        assert metrics.scraped_successfully == 0
        assert metrics.synthesized_successfully == 0
        assert metrics.synced_to_notion == 0
        assert metrics.errors == 0
        assert metrics.start_time is not None
        assert metrics.end_time is None

    def test_workflow_metrics_rates(self, sample_deliberation):
        """Test WorkflowMetrics rate calculations."""
        metrics = WorkflowMetrics()
        metrics.total_deliberations = 10
        metrics.parsed_successfully = 10
        metrics.scraped_successfully = 8
        metrics.synthesized_successfully = 9
        metrics.synced_to_notion = 7
        
        assert metrics.parsing_rate == 100.0
        assert metrics.scraping_rate == 80.0
        assert metrics.synthesis_rate == 90.0
        assert metrics.success_rate == 70.0

    @patch('workflow_orchestrator.ODGPDFParser')
    @patch('workflow_orchestrator.DecretoScraper')
    @patch('workflow_orchestrator.AISynthesizer')
    @patch('workflow_orchestrator.NotionIntegrator')
    def test_process_odg_pdf_success(self, mock_notion, mock_ai, mock_scraper, mock_parser, env_vars, temp_dir):
        """Test successful PDF processing workflow."""
        # Setup mocks
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.parse_odg.return_value = {
            'deliberations': [
                {
                    'numero': '1',
                    'tipo_atto': 'Deliberazione',
                    'oggetto': 'Test deliberation',
                    'proponente': 'Test Proponent',
                    'fs_flag': True
                }
            ],
            'session_info': {
                'numero_seduta': '3929',
                'data_seduta': '2025-07-10',
                'anno': '2025'
            }
        }
        
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.verify_decreto_publication.return_value = {
            'found': True,
            'url': 'https://test.com/decreto/1',
            'data_pubblicazione': '2025-07-15',
            'dgr_numero': '123',
            'dgr_anno': '2025'
        }
        
        mock_ai_instance = Mock()
        mock_ai.return_value = mock_ai_instance
        mock_synthesis_result = Mock()
        mock_synthesis_result.quick_summary = "Test summary"
        mock_synthesis_result.detailed_synthesis = "Test detailed synthesis"
        mock_synthesis_result.extracted_info = {}
        mock_synthesis_result.confidence = 0.8
        mock_synthesis_result.generated_with_ai = True
        mock_ai_instance.generate_detailed_synthesis.return_value = mock_synthesis_result
        
        mock_notion_instance = Mock()
        mock_notion.return_value = mock_notion_instance
        mock_notion_instance.sync_deliberations.return_value = {
            'created': 1,
            'updated': 0,
            'errors': 0
        }
        
        # Create test PDF file
        test_pdf = temp_dir / "test.pdf"
        test_pdf.write_text("dummy pdf content")
        
        # Initialize orchestrator
        orchestrator = ODGWorkflowOrchestrator(
            notion_token=env_vars['NOTION_TOKEN'],
            notion_database_id=env_vars['NOTION_DATABASE_ID'],
            anthropic_api_key=env_vars['ANTHROPIC_API_KEY'],
            backup_dir=str(temp_dir)
        )
        
        # Process PDF
        result = orchestrator.process_odg_pdf(str(test_pdf))
        
        # Verify results
        assert result.success is True
        assert result.metrics.total_deliberations == 1
        assert result.metrics.parsed_successfully == 1
        assert result.metrics.scraped_successfully == 1
        assert result.metrics.synthesized_successfully == 1
        assert result.metrics.synced_to_notion == 1
        assert result.metrics.errors == 0
        assert len(result.deliberations) == 1
        assert result.backup_path is not None

    @patch('workflow_orchestrator.ODGPDFParser')
    def test_process_odg_pdf_parsing_failure(self, mock_parser, env_vars, temp_dir):
        """Test PDF processing with parsing failure."""
        # Setup mock to raise exception
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.parse_odg.side_effect = Exception("PDF parsing failed")
        
        # Create test PDF file
        test_pdf = temp_dir / "test.pdf"
        test_pdf.write_text("dummy pdf content")
        
        # Initialize orchestrator
        orchestrator = ODGWorkflowOrchestrator(
            notion_token=env_vars['NOTION_TOKEN'],
            notion_database_id=env_vars['NOTION_DATABASE_ID'],
            anthropic_api_key=env_vars['ANTHROPIC_API_KEY'],
            backup_dir=str(temp_dir)
        )
        
        # Process PDF
        result = orchestrator.process_odg_pdf(str(test_pdf))
        
        # Verify results
        assert result.success is False
        assert result.metrics.total_deliberations == 0
        assert result.metrics.errors == 1
        assert len(result.errors) == 1
        assert "PDF parsing failed" in result.errors[0]

    def test_health_check(self, mock_orchestrator):
        """Test system health check."""
        health_status = mock_orchestrator.health_check()
        
        assert 'timestamp' in health_status
        assert 'overall_status' in health_status
        assert 'components' in health_status
        assert 'pdf_parser' in health_status['components']
        assert 'decreto_scraper' in health_status['components']
        assert 'ai_synthesizer' in health_status['components']
        assert 'notion_integrator' in health_status['components']

    def test_workflow_statistics(self, mock_orchestrator):
        """Test workflow statistics generation."""
        stats = mock_orchestrator.get_workflow_statistics(days=30)
        
        assert 'period_days' in stats
        assert 'total_workflows' in stats
        assert 'successful_workflows' in stats
        assert 'total_deliberations' in stats
        assert 'avg_success_rate' in stats
        assert 'timestamp' in stats

    @pytest.mark.requires_api
    def test_daily_verification(self, mock_orchestrator):
        """Test daily verification process."""
        verification_results = mock_orchestrator.run_daily_verification()
        
        assert 'timestamp' in verification_results
        assert 'verified_count' in verification_results
        assert 'newly_published' in verification_results
        assert 'errors' in verification_results
        assert 'details' in verification_results