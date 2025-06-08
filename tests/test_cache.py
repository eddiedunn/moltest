import json
from moltest.cache import (
    load_cache,
    save_cache,
    update_scenario_status,
    get_scenario_status,
    get_failed_scenarios,
    CACHE_FILENAME,
)


def test_save_and_load_cycle(tmp_path):
    """Statuses are preserved when saving and reloading the cache."""
    # Load should initialize an empty structure
    cache = load_cache(tmp_path)
    assert cache["scenarios"] == {}

    # Update a couple of scenario statuses
    update_scenario_status(cache, "role1:default", "passed")
    update_scenario_status(cache, "role2:other", "failed")

    # Query using helper functions
    assert get_scenario_status(cache, "role1:default") == "passed"
    assert get_scenario_status(cache, "role2:other") == "failed"
    assert get_scenario_status(cache, "missing",) is None
    assert get_failed_scenarios(cache) == ["role2:other"]

    # Save the cache
    assert save_cache(cache, tmp_path) is True

    cache_file = tmp_path / CACHE_FILENAME
    assert cache_file.exists()

    # Contents on disk should include our scenarios
    on_disk = json.loads(cache_file.read_text())
    assert on_disk["scenarios"] == cache["scenarios"]

    # Loading again should return the same data
    loaded = load_cache(tmp_path)
    assert loaded["scenarios"] == cache["scenarios"]
    assert get_scenario_status(loaded, "role1:default") == "passed"
    assert get_failed_scenarios(loaded) == ["role2:other"]


def test_load_cache_handles_missing_and_invalid(tmp_path):
    """load_cache returns an empty structure for missing or invalid files."""
    # No file present
    data = load_cache(tmp_path)
    assert data["scenarios"] == {}

    cache_path = tmp_path / CACHE_FILENAME

    # Corrupted JSON
    cache_path.write_text("{invalid json")
    corrupted = load_cache(tmp_path)
    assert corrupted["scenarios"] == {}

    # Valid JSON but wrong structure/version
    cache_path.write_text(json.dumps({"moltest_version": "bad", "scenarios": []}))
    invalid = load_cache(tmp_path)
    assert invalid["scenarios"] == {}

