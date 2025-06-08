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


def test_discover_scenarios_reads_parameters(tmp_path):
    """Parameter files for scenarios should be parsed."""
    scenario_dir = tmp_path / "roles" / "role1" / "molecule" / "alpha"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "molecule.yml").write_text("{}")
    params_file = scenario_dir / "moltest.params.yml"
    params_file.write_text("- id: one\n  vars:\n    FOO: bar\n- id: two\n  vars:\n    BAZ: qux\n")

    scenarios = discover_scenarios(tmp_path)
    assert len(scenarios) == 1
    assert scenarios[0]["parameters"] == [
        {"id": "one", "vars": {"FOO": "bar"}},
        {"id": "two", "vars": {"BAZ": "qux"}},
    ]
