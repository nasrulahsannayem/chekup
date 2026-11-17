"""Command-line interface."""

import argparse
import sys
from typing import List

from rich.console import Console
from rich.table import Table

from chekup.config import Config
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


VERSION = "Chekup v4.2"


def parse_args(argv: List[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="chekup")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--once", action="store_true", help="Run one-shot metrics")
    return parser.parse_args(argv)


def main(argv: List[str] = None):
    """Main entry point for the chekup CLI."""
    args = parse_args(argv)
    if args.version:
        print(VERSION)
        sys.exit(0)
    if args.once:
        console = Console()
        console.print("[bold cyan]VPS COMMAND CENTER — ONE SHOT[/]")
        cpu = cpu_module.get_cpu_percent(0.3)
        mem = memory_module.collect_memory()
        console.print(f"CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% | Available: {human(mem.available_mb)}")
        t = Table()
        for col in ("PID", "PROCESS", "CPU", "RAM", "STATE"):
            t.add_column(col)
        for p in processes_module.collect_processes()[:15]:
            t.add_row(str(p.pid), p.name[:18], f"{p.cpu_percent:.1f}%", f"{p.mem_percent:.1f}%", p.state[:10])
        console.print(t)
        console.print("[green]Read-only. No process will be stopped.[/]")
        sys.exit(0)
    Chekup().run()


if __name__ == "__main__":
    main()
