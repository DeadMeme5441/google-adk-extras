"""Shared test configuration and fixtures for pytest."""

import pytest
import tempfile
import os
import sys

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="adk_test_")
    yield temp_dir
    # Cleanup after all tests
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_file_path(temp_dir):
    """Create a temporary file path for tests."""
    import uuid
    return os.path.join(temp_dir, str(uuid.uuid4()))


@pytest.fixture(scope="session")
def sample_text_blob():
    """Create a sample text blob for testing."""
    from google.genai.types import Blob, Part
    test_data = b"Hello, World! This is a test artifact."
    blob = Blob(data=test_data, mime_type="text/plain")
    return Part(inline_data=blob)


@pytest.fixture(scope="session")
def sample_image_blob():
    """Create a sample image blob for testing."""
    from google.genai.types import Blob, Part
    test_data = b"fake image data"  # In reality, this would be actual image bytes
    blob = Blob(data=test_data, mime_type="image/png")
    return Part(inline_data=blob)