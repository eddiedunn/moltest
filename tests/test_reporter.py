import json
from moltest.reporter import generate_json_report, generate_markdown_report


def test_generate_reports(tmp_path):
    scenario_results = [
        {"id": "role1:alpha", "status": "passed", "duration": 1.0, "return_code": 0},
        {"id": "role2:beta", "status": "failed", "duration": 2.0, "return_code": 1},
        {"id": "role3:gamma", "status": "skipped", "return_code": 0},
    ]

    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"

    generate_json_report(scenario_results, str(json_path), overall_duration=3.0)
    generate_markdown_report(scenario_results, str(md_path), overall_duration=3.0)

    data = json.loads(json_path.read_text())
    assert data["total_scenarios"] == 3
    assert data["passed"] == 1
    assert data["failed"] == 1
    assert data["other"] == 1
    assert data["overall_duration"] == 3.0

    first = data["scenarios"][0]
    assert first["id"] == "role1:alpha"
    assert first["name"] == "alpha"
    assert first["role"] == "role1"
    assert first["status"] == "passed"

    md_lines = md_path.read_text().splitlines()
    assert md_lines[0].startswith("# Molecule Test Execution Report")
    assert "- **Total Scenarios:** 3" in md_lines
    assert "| role2:beta | ❌ Failed | 2.00 |" in md_lines


def test_generate_reports_empty(tmp_path):
    json_path = tmp_path / "empty.json"
    md_path = tmp_path / "empty.md"

    generate_json_report([], str(json_path))
    generate_markdown_report([], str(md_path))

    data = json.loads(json_path.read_text())
    assert data["total_scenarios"] == 0
    assert data["scenarios"] == []
    assert data["passed"] == 0
    assert data["failed"] == 0
    assert data["other"] == 0

    md_content = md_path.read_text()
    assert "No scenario results to report." in md_content

