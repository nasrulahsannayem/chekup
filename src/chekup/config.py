from dataclasses import dataclass, field
import yaml
import os
from typing import List, Dict, Any, Optional

class ConfigError(Exception):
    pass

@dataclass
class Config:
    refresh_interval: float = 2.0
    cpu: bool = True
    memory: bool = True
    disk: bool = True
    network: bool = True
    processes: bool = True
    disk_paths: tuple[str, ...] = ('/',)
    services_enabled: bool = True
    services_auto_discover: bool = True
    services_custom: List[str] = field(default_factory=list)
    docker_enabled: bool = False
    docker_containers: List[str] = field(default_factory=list)
    healthchecks: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics_enabled: bool = True
    cpu_warn: float = 70.0
    cpu_critical: float = 85.0
    mem_warn: float = 70.0
    mem_critical: float = 90.0
    disk_warn: float = 70.0
    disk_critical: float = 90.0
    read_only: bool = True  # Always true

def load_config(path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file; fall back to defaults if missing or malformed."""
    config_path = path if path else os.path.expanduser('~/.config/chekup/config.yaml')
    if not os.path.exists(config_path):
        return AppConfig()
    try:
        with open(config_path, 'r') as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigError(f"Failed to read config: {e}")
    cfg = AppConfig()
    from dataclasses import fields
    for field in fields(cfg):
        name = field.name
        if name in raw:
            val = raw[name]
            # Convert list to tuple for disk_paths
            if isinstance(getattr(cfg, name), tuple) and isinstance(val, list):
                val = tuple(val)
            setattr(cfg, name, val)
    return cfg

# Backward compatibility alias
AppConfig = Config  # alias
