from pathlib import Path

from moltest.discovery import discover_scenarios


def test_discover_scenarios_excludes_venv(tmp_path):
    """discover_scenarios finds scenarios and skips '.venv' directories."""
    # Create first scenario
    role1_scenario = tmp_path / "roles" / "role1" / "molecule" / "alpha"
    role1_scenario.mkdir(parents=True)
    (role1_scenario / "molecule.yml").write_text("{}")

    # Create second scenario
    role2_scenario = tmp_path / "roles" / "role2" / "molecule" / "beta"
    role2_scenario.mkdir(parents=True)
    (role2_scenario / "molecule.yml").write_text("{}")

    # Scenario inside .venv should be ignored
    venv_scenario = tmp_path / ".venv" / "roles" / "venvrole" / "molecule" / "ignored"
    venv_scenario.mkdir(parents=True)
    (venv_scenario / "molecule.yml").write_text("{}")

    scenarios = discover_scenarios(tmp_path)

    assert len(scenarios) == 2
    ids = [s["id"] for s in scenarios]
    assert ids == ["role1:alpha", "role2:beta"]

    assert scenarios[0]["execution_path"] == str((tmp_path / "roles" / "role1").resolve())
    assert scenarios[1]["execution_path"] == str((tmp_path / "roles" / "role2").resolve())
    assert all(Path(s["molecule_file_path"]).exists() for s in scenarios)
