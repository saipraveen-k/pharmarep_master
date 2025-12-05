import pytest
from backend.workers.patents import PatentsWorker

@pytest.mark.asyncio
async def test_patents_worker_mock():
    w = PatentsWorker()
    items = await w.fetch_raw_items("Alzheimer disease", "", 1)
    assert items
    assert "raw_text" in items[0]
