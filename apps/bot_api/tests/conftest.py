"""
Test configuration and fixtures.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Import will work after dependencies are installed
# from src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


# @pytest_asyncio.fixture
# async def client():
#     """Async test client for FastAPI."""
#     async with AsyncClient(
#         transport=ASGITransport(app=app),
#         base_url="http://test"
#     ) as client:
#         yield client
