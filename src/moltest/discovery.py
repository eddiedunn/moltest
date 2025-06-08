#!/usr/bin/env python3

from pathlib import Path
import json
import yaml

# Common virtual environment directory names to exclude
VENV_NAMES = {'.venv', 'venv', 'env'}


def load_scenario_parameters(scenario_dir: Path) -> list[dict]:
    """Load parameter sets for a scenario from YAML or JSON files."""
    candidates = [
        scenario_dir / "moltest.params.yml",
        scenario_dir / "moltest.params.yaml",
        scenario_dir / "moltest.params.json",
    ]
    for f in candidates:
        if f.is_file():
            try:
                if f.suffix in {".yml", ".yaml"}:
                    data = yaml.safe_load(f.read_text())
                else:
                    data = json.loads(f.read_text())
            except Exception:
                return []

            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("params"), list):
                return data["params"]
            return []
    return []

def find_molecule_yamls(project_root: Path, exclude_venv: bool = True):
    """Finds all molecule.yml files, potentially excluding venv directories."""
    molecule_files = []
    # Search for directories named 'molecule'
    for molecule_dir_path in project_root.rglob('molecule'):
        if not molecule_dir_path.is_dir():
            continue

        # Check if we should exclude this because it's in a venv path
        if exclude_venv and any(part in VENV_NAMES for part in molecule_dir_path.parts):
            continue

        for scenario_dir in molecule_dir_path.iterdir():
            if scenario_dir.is_dir():
                molecule_yml_file = scenario_dir / 'molecule.yml'
                if molecule_yml_file.is_file():
                    molecule_files.append(molecule_yml_file)
    return molecule_files

def parse_scenario(molecule_yml_path: Path):
    """Parses a molecule.yml file to extract scenario details."""
    scenario_name = molecule_yml_path.parent.name
    molecule_dir = molecule_yml_path.parent.parent
    # Base execution path is typically the directory containing the 'molecule' directory
    # For a role: roles/my_role/molecule/default -> execution_path = roles/my_role
    # For project level: my_project/molecule/default -> execution_path = my_project
    execution_path = molecule_dir.parent

    role_name = None
    # Try to determine role name by convention: execution_path is the role_dir, and its parent is 'roles'
    if execution_path.parent.name == 'roles' or execution_path.name == 'roles': # a bit more flexible
        role_name = execution_path.name
    elif execution_path.parent.name == 'ansible_collections':
        # Path structure: .../ansible_collections/namespace/collection/roles/role_name/molecule/scenario
        parts = molecule_yml_path.parts
        try:
            roles_idx = parts.index('roles')
            if roles_idx + 1 < len(parts):
                role_name = parts[roles_idx + 1]
        except ValueError:
            pass # 'roles' not in path, or structure is different

    # Placeholder for actual molecule.yml parsing if needed for more details in future
    # try:
    # Placeholder for reading molecule.yml if needed in the future

    tags_file = molecule_yml_path.parent / 'moltest.tags'
    tags: list[str] = []
    if tags_file.is_file():
        content = tags_file.read_text().strip()
        if content:
            for line in content.splitlines():
                for tag in line.replace(',', ' ').split():
                    if tag:
                        tags.append(tag)

    params = load_scenario_parameters(molecule_yml_path.parent)

    return {
        'scenario_name': scenario_name,
        'role_name': role_name,
        'execution_path': str(execution_path.resolve()),
        'molecule_file_path': str(molecule_yml_path.resolve()),
        'tags': tags,
        'parameters': params,
    }

def generate_scenario_id(scenario_data: dict):
    """Generates a unique identifier for a scenario."""
    if scenario_data.get('role_name'):
        return f"{scenario_data['role_name']}:{scenario_data['scenario_name']}"
    return scenario_data['scenario_name']

def discover_scenarios(project_root: Path, exclude_venv: bool = True):
    """Discovers all Molecule scenarios, parses them, generates IDs, and sorts them."""
    molecule_yml_files = find_molecule_yamls(project_root, exclude_venv=exclude_venv)
    scenarios_data = []
    for f_path in molecule_yml_files:
        parsed_data = parse_scenario(f_path)
        parsed_data['id'] = generate_scenario_id(parsed_data)
        scenarios_data.append(parsed_data)
    
    # Sort scenarios by ID
    scenarios_data.sort(key=lambda s: s['id'])
    return scenarios_data

if __name__ == '__main__':
    current_project_root = Path('/Users/gdunn6/code/gdunn6/gdunn6_ansible')
    print(f"Discovering Molecule scenarios in: {current_project_root} (excluding venvs)")
    
    all_scenarios = discover_scenarios(current_project_root)
    
    if all_scenarios:
        print("\nDiscovered and sorted scenarios:")
        for scenario_data in all_scenarios:
            print(f"  ID: {scenario_data['id']}")
            print(f"    File: {scenario_data['molecule_file_path']}")
            print(f"    Scenario: {scenario_data['scenario_name']}")
            print(f"    Role: {scenario_data['role_name']}")
            print(f"    Exec Path: {scenario_data['execution_path']}")
    else:
        print("No molecule.yml files found (excluding venvs).")
