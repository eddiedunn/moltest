import json
from pathlib import Path

from moltest.config import load_config, save_config


def test_load_config_missing(tmp_path, monkeypatch):
    """load_config returns empty dict if config file does not exist."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = load_config()
    assert cfg == {}
    # directory should be created
    assert (tmp_path / 'moltest').exists()


def test_load_and_save_cycle(tmp_path, monkeypatch):
    """Data written with save_config is returned by load_config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    data = {"roles_path": "/some/path"}
    save_config(data)
    cfg_path = tmp_path / 'moltest' / 'config.json'
    assert cfg_path.exists()
    loaded = load_config()
    assert loaded == data
    # verify file content is valid JSON
    on_disk = json.loads(cfg_path.read_text())
    assert on_disk == data


def test_load_config_invalid_json(tmp_path, monkeypatch):
    """Corrupted config file results in empty dict."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_path = tmp_path / 'moltest' / 'config.json'
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text("{invalid")
    cfg = load_config()
    assert cfg == {}
