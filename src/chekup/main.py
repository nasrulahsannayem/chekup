"""Entry point for Chekup command-line interface.

Provides ``chekup`` command supporting ``--once`` to display a one‑shot summary
and the default full‑screen Textual TUI for continuous monitoring.
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from chekup.config import Config
from chekup.cli import parse_args
from chekup.ui.app import Chekup, human
from chekup.core import (
    cpu as cpu_module,
    memory as memory_module,
    disk as disk_module,
    network as network_module,
    processes as processes_module,
    system as system_module,
)
from chekup.monitoring import services as services_module
from chekup.monitoring import containers as containers_module
from chekup.monitoring import healthchecks as healthchecks_module
from chekup.diagnostics import engine as diagnostics_module

# Version string for user‑facing output
VERSION = "Chekup v4.2"

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args.version:
        print(VERSION)
        sys.exit(0)
    if args.once:
        # Run a one‑shot report
        console = Console()
        console.print("[bold cyan]VPS COMMAND CENTER — ONE SHOT[/]")
        cpu = cpu_module.get_cpu_percent(0.3)
        mem = memory_module.collect_memory()
        console.print(f"CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% | Available: {human(mem.available_mb)} MB")
        t = Table()
        for col in ("PID", "PROCESS", "CPU", "RAM", "STATE"):
            t.add_column(col)
        for p in processes_module.get_processes()[:15]:
            t.add_row(str(p.pid), p.name[:18], f"{p.cpu:.1f}%", f"{p.ram:.1f}%", p.state[:10])
        console.print(t)
        console.print("[green]Read-only. No process will be stopped.[/]")
        sys.exit(0)
    # Default run the full TUI app
    Chekup().run()
