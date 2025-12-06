import pytest

from backend.workers.trials import TrialsWorker


@pytest.mark.asyncio
async def test_trials_worker_mock():
    w = TrialsWorker()
    items = await w.fetch_raw_items("Alzheimer disease", "", 1)
    assert items
    assert "raw_text" in items[0]
