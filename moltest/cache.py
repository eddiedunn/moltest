"""
Handles the caching of molecule test results.

Cache file: .moltest_cache.json in the project root.
Cache format:
{
    "moltest_version": "1.0.0",
    "last_run": "<ISO_TIMESTAMP>",
    "scenarios": {
        "<role_name>:<scenario_name>": "passed" | "failed"
    }
}
"""

import json
import os
from datetime import datetime, timezone

CACHE_FILENAME = ".moltest_cache.json"
CACHE_VERSION = "1.0.0"


def get_empty_cache_structure():
    """Returns a dictionary representing an empty cache."""
    return {
        "moltest_version": CACHE_VERSION,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "scenarios": {}
    }


def load_cache(cache_dir_path: str = ".") -> dict:
    """Loads the cache data from the .moltest_cache.json file.

    Args:
        cache_dir_path: The directory where the cache file is located.

    Returns:
        A dictionary containing the cache data, or an empty cache structure
        if the file doesn't exist or is corrupted.
    """
    cache_file_path = os.path.join(cache_dir_path, CACHE_FILENAME)
    try:
        with open(cache_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Basic validation (can be expanded)
            if not isinstance(data, dict) or \
               data.get("moltest_version") != CACHE_VERSION or \
               not isinstance(data.get("scenarios"), dict):
                print(f"Warning: Cache file {cache_file_path} has invalid structure or version. Reinitializing.")
                return get_empty_cache_structure()
            return data
    except FileNotFoundError:
        # If the cache file doesn't exist, return a new empty structure
        return get_empty_cache_structure()
    except json.JSONDecodeError:
        print(f"Error: Cache file {cache_file_path} is corrupted. Reinitializing.")
        return get_empty_cache_structure()
    except OSError as e:
        print(f"Error reading cache file {cache_file_path}: {e}. Reinitializing.")
        return get_empty_cache_structure()

def save_cache(cache_data: dict, cache_dir_path: str = ".") -> bool:
    """Saves the cache data to the .moltest_cache.json file atomically.

    Args:
        cache_data: The dictionary containing the cache data to save.
        cache_dir_path: The directory where the cache file should be saved.

    Returns:
        True if saving was successful, False otherwise.
    """
    cache_file_path = os.path.join(cache_dir_path, CACHE_FILENAME)
    temp_file_path = cache_file_path + ".tmp"

    # Update the last_run timestamp before saving
    cache_data["last_run"] = datetime.now(timezone.utc).isoformat()
    cache_data["moltest_version"] = CACHE_VERSION # Ensure version is current

    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4)
        # Atomically replace the old cache file with the new one
        # os.replace is atomic on POSIX and Windows (Python 3.3+)
        os.replace(temp_file_path, cache_file_path)
        return True
    except (IOError, OSError) as e:
        print(f"Error saving cache file {cache_file_path}: {e}")
        # Attempt to clean up the temporary file if it exists
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as cleanup_e:
                print(f"Error cleaning up temporary cache file {temp_file_path}: {cleanup_e}")
        return False


def update_scenario_status(cache_data: dict, scenario_key: str, status: str):
    """Updates the status of a scenario in the cache data.

    Args:
        cache_data: The cache data dictionary.
        scenario_key: The key for the scenario (e.g., "role_name:scenario_name").
        status: The new status for the scenario ("passed" or "failed").
    """
    if status not in ["passed", "failed"]:
        print(f"Warning: Invalid status '{status}' for scenario '{scenario_key}'. Status not updated.")
        return

    if "scenarios" not in cache_data or not isinstance(cache_data["scenarios"], dict):
        # This should ideally not happen if cache is loaded/initialized correctly
        cache_data["scenarios"] = {}
    
    cache_data["scenarios"][scenario_key] = status
    # The cache will be saved by the calling function if needed


def get_scenario_status(cache_data: dict, scenario_key: str) -> str | None:
    """Retrieves the status of a specific scenario from the cache data.

    Args:
        cache_data: The cache data dictionary.
        scenario_key: The key for the scenario (e.g., "role_name:scenario_name").

    Returns:
        The status of the scenario ("passed" or "failed"), or None if not found.
    """
    return cache_data.get("scenarios", {}).get(scenario_key)


def get_failed_scenarios(cache_data: dict) -> list[str]:
    """Retrieves a list of all scenarios marked as 'failed' in the cache data.

    Args:
        cache_data: The cache data dictionary.

    Returns:
        A list of scenario keys that have a status of "failed".
    """
    failed_scenarios = []
    for scenario_key, status in cache_data.get("scenarios", {}).items():
        if status == "failed":
            failed_scenarios.append(scenario_key)
    return failed_scenarios
