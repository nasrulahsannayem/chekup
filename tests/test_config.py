"""Tests for chekup.config."""
import tempfile
import os
from chekup.config import AppConfig, Config, load_config, ConfigError


def test_default_config():
    cfg = AppConfig()
    assert cfg.refresh_interval == 2.0
    assert cfg.docker_enabled is False  # safe default
    assert cfg.services_custom == []
    assert cfg.diagnostics_enabled is True


def test_load_config_yaml(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "refresh_interval: 5.0\n"
        "docker_enabled: true\n"
        "docker_containers:\n"
        "  - test-container\n"
        "services_custom:\n"
        "  - nginx\n"
        "healthchecks:\n"
        "  - url: https://example.com\n"
        "    timeout: 5\n"
        "    expect_status: 200\n"
    )
    cfg = load_config(str(yaml_file))
    assert cfg.refresh_interval == 5.0
    assert cfg.docker_enabled is True
    assert cfg.docker_containers == ["test-container"]
    assert cfg.services_custom == ["nginx"]
    assert len(cfg.healthchecks) == 1
    assert cfg.healthchecks[0]["url"] == "https://example.com"


def test_load_config_missing_file():
    # Non-existent file returns defaults
    cfg = load_config("/nonexistent/chekup.yaml")
    assert cfg.refresh_interval == 2.0
