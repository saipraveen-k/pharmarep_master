import pytest

from backend.orchestrator import run_orchestration


@pytest.mark.asyncio
async def test_orchestrator_smoke():
    async def cb(pct, ws):
        pass

    result = await run_orchestration(
        query_id="test-1",
        query_text="Alzheimer disease",
        max_results=5,
        status_callback=cb,
    )
    assert "candidates" in result
