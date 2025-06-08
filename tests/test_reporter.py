import json
import xml.etree.ElementTree as ET
from moltest.reporter import (
    generate_json_report,
    generate_markdown_report,
    generate_junit_xml_report,
)


def test_generate_reports(tmp_path):
    scenario_results = [
        {"id": "role1:alpha", "status": "passed", "duration": 1.0, "return_code": 0},
        {"id": "role2:beta", "status": "failed", "duration": 2.0, "return_code": 1},
        {"id": "role3:gamma", "status": "skipped", "return_code": 0},
    ]

    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    xml_path = tmp_path / "report.xml"

    generate_json_report(scenario_results, str(json_path), overall_duration=3.0)
    generate_markdown_report(scenario_results, str(md_path), overall_duration=3.0)
    generate_junit_xml_report(scenario_results, str(xml_path), overall_duration=3.0)

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

    tree = ET.parse(xml_path)
    root = tree.getroot()
    assert root.tag == "testsuite"
    assert root.attrib["tests"] == "3"
    assert root.attrib["failures"] == "1"
    assert root.attrib["skipped"] == "1"
    cases = root.findall("testcase")
    assert len(cases) == 3
    fail_case = [c for c in cases if c.attrib["name"] == "beta"][0]
    assert fail_case.find("failure") is not None
    skip_case = [c for c in cases if c.attrib["name"] == "gamma"][0]
    assert skip_case.find("skipped") is not None


def test_generate_reports_empty(tmp_path):
    json_path = tmp_path / "empty.json"
    md_path = tmp_path / "empty.md"
    xml_path = tmp_path / "empty.xml"

    generate_json_report([], str(json_path))
    generate_markdown_report([], str(md_path))
    generate_junit_xml_report([], str(xml_path))

    data = json.loads(json_path.read_text())
    assert data["total_scenarios"] == 0
    assert data["scenarios"] == []
    assert data["passed"] == 0
    assert data["failed"] == 0
    assert data["other"] == 0

    md_content = md_path.read_text()
    assert "No scenario results to report." in md_content

    tree = ET.parse(xml_path)
    root = tree.getroot()
    assert root.attrib["tests"] == "0"
    assert root.attrib["failures"] == "0"


def test_no_color_output(capsys):
    from moltest.reporter import (
        print_scenario_result,
        print_summary_table,
        print_scenario_start,
    )

    print_scenario_result("role1:alpha", "passed", duration=1.0, color_enabled=False)
    out1 = capsys.readouterr().out
    assert "\x1b[" not in out1
    assert "PASSED" in out1

    print_summary_table([
        {"id": "role1:alpha", "status": "passed", "duration": 1.0}
    ], color_enabled=False)
    out2 = capsys.readouterr().out
    assert "\x1b[" not in out2
    assert "role1:alpha" in out2

    print_scenario_start("role1:alpha", color_enabled=False)
    out3 = capsys.readouterr().out
    assert "\x1b[" not in out3
    assert "RUNNING: role1:alpha" in out3

