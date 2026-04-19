"""
Pytest configuration and fixtures for Citation-LLM tests.
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = MagicMock()
    mock.create_all = MagicMock()
    mock.session.add = MagicMock()
    mock.session.commit = MagicMock()
    return mock


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF bytes for testing (minimal valid PDF)."""
    return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'


@pytest.fixture
def sample_auth_token():
    """Sample JWT token for testing."""
    return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature'


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'id': 'test-user-uuid',
        'email': 'test@example.com',
        'full_name': 'Test User',
        'password': 'password123'
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        'id': 'test-doc-uuid',
        'title': 'Test Academic Paper',
        'filename': 'test_paper.pdf',
        'file_path': '/uploads/test_doc.pdf',
        'status': 'ready',
        'total_pages': 10,
        'total_chunks': 25
    }


@pytest.fixture
def sample_chunk_data():
    """Sample chunk data for testing."""
    return [
        {
            'id': 'chunk-1',
            'text': 'This is the first chunk of text from the document.',
            'page_number': 1,
            'chunk_index': 0,
            'similarity': 0.95
        },
        {
            'id': 'chunk-2',
            'text': 'The second chunk contains more information.',
            'page_number': 1,
            'chunk_index': 1,
            'similarity': 0.85
        },
        {
            'id': 'chunk-3',
            'text': 'A third chunk with different content.',
            'page_number': 2,
            'chunk_index': 2,
            'similarity': 0.75
        }
    ]


@pytest.fixture
def sample_llm_results():
    """Sample LLM results for testing."""
    return [
        {
            'model_name': 'openai/gpt-4o',
            'answer_text': 'Based on the document, the main finding is X.',
            'latency_ms': 1200,
            'tokens_used': 150,
            'success': True
        },
        {
            'model_name': 'anthropic/claude-3-5-sonnet',
            'answer_text': 'The research shows that X is the primary result.',
            'latency_ms': 1500,
            'tokens_used': 140,
            'success': True
        },
        {
            'model_name': 'google/gemini-1.5-flash',
            'answer_text': 'According to the paper, X represents the key contribution.',
            'latency_ms': 800,
            'tokens_used': 160,
            'success': True
        }
    ]
