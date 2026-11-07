"""
What this Mac is and what it means: the tier from the memory, how well a model fits, and one model worker at a time on a small Mac.
"""

import pytest

from ocarina import hardware
from ocarina.tts import supervisor
from ocarina.tts.supervisor import Supervisor


@pytest.fixture(autouse=True)
def forget():
    hardware.info.cache_clear()
    yield
    hardware.info.cache_clear()


@pytest.mark.parametrize("ram, tier", [(8, "small"), (16, "medium"), (24, "large"), (32, "large"), (None, "large")])
def test_the_tier_follows_the_memory(ram, tier):
    assert hardware.tier_for(ram) == tier


def test_the_memory_can_be_faked_for_trying_another_mac(monkeypatch):
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "8")
    assert hardware.info()["tier"] == "small" and hardware.one_at_a_time() and hardware.mlx_cache_mb() == 256
    hardware.info.cache_clear()
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "32")
    assert not hardware.one_at_a_time() and hardware.mlx_cache_mb() is None


def test_a_model_fits_by_its_size_against_the_memory():
    gb = 1024**3
    assert hardware.fit(2.3 * gb, ram_gb=16) == "ok"
    assert hardware.fit(2.3 * gb, ram_gb=8) == "tight"
    assert hardware.fit(6.7 * gb, ram_gb=8) == "too big"
    assert hardware.fit(6.7 * gb, ram_gb=32) == "ok"
    assert hardware.fit(6.7 * gb, ram_gb=None) == "ok"


def test_the_hardware_is_reported_and_models_say_how_they_fit(client, monkeypatch):
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "8")
    assert client.get("/ocarina/api/system/hardware").json["tier"] == "small"
    assert all(m["fit"] in ("ok", "tight", "too big") for m in client.get("/ocarina/api/tts/models").json)


def test_a_small_mac_keeps_one_model_worker_alive(monkeypatch):
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "8")
    first, second = Supervisor("fake"), Supervisor("fake")
    try:
        first.complete("s", "hello")
        assert first._alive()  # pylint: disable=protected-access
        second.complete("s", "hello")
        assert second._alive() and not first._alive()  # pylint: disable=protected-access
        first.complete("s", "again")  # the first one simply starts again (and the second one gives way)
        assert first._alive() and not second._alive()  # pylint: disable=protected-access
    finally:
        first.unload()
        second.unload()


def test_a_large_mac_lets_workers_live_side_by_side(monkeypatch):
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "64")
    first, second = Supervisor("fake"), Supervisor("fake")
    try:
        first.complete("s", "hello")
        second.complete("s", "hello")
        assert first._alive() and second._alive()  # pylint: disable=protected-access
    finally:
        first.unload()
        second.unload()


def test_a_worker_in_the_middle_of_a_request_is_not_stopped(monkeypatch):
    monkeypatch.setenv("OCARINA_FAKE_RAM_GB", "8")
    busy = Supervisor("fake")
    busy.complete("s", "hello")
    busy._lock.acquire()  # pylint: disable=protected-access
    try:
        assert supervisor.release_idle(keep=None) == 0 and busy._alive()  # pylint: disable=protected-access
    finally:
        busy._lock.release()  # pylint: disable=protected-access
        busy.unload()
