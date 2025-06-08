import subprocess
import types
import pytest

from moltest.cli import check_dependencies


def test_check_dependencies_parses_molecule_output(mocker):
    """check_dependencies should parse modern molecule --version output."""
    ctx = types.SimpleNamespace()
    ctx.exit = mocker.Mock(side_effect=lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    molecule_out = "molecule 25.1.0 using python 3.11\n    ansible:2.15.0\n"
    ansible_out = "ansible [core 2.15.0]\n"

    def fake_run(cmd, capture_output=True, text=True, check=False):
        if cmd == ["molecule", "--version"]:
            return subprocess.CompletedProcess(cmd, 0, molecule_out, "")
        elif cmd == ["ansible", "--version"]:
            return subprocess.CompletedProcess(cmd, 0, ansible_out, "")
        raise FileNotFoundError

    mocker.patch("subprocess.run", side_effect=fake_run)

    check_dependencies(ctx)
    ctx.exit.assert_not_called()
