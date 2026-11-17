#!/opt/chekup/venv/bin/python
import os, sys, time, subprocess, urllib.request
from datetime import datetime

import psutil
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static, DataTable
from textual import events

VERSION = "4.2"

def run(args, timeout=3):
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.stdout.strip()
    except Exception:
        return ""

def human(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def age(seconds):
    d = int(seconds // 86400)
    h = int(seconds % 86400 // 3600)
    m = int(seconds % 3600 // 60)
    return f"{d}d {h}h {m}m"

def service(name):
    return run(["systemctl", "is-active", name]) or "unknown"

def docker_info(name):
    value = run([
        "docker", "inspect", "-f",
        "{{.State.Status}}|{{.RestartCount}}", name
    ])
    if not value or "|" not in value:
        return "not found", "?"
    return value.split("|", 1)

def router_health():
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8001/health",
            headers={"User-Agent": "chekup-readonly"}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            return f"HTTP {response.status}"
    except Exception:
        return "UNREACHABLE"

# Persistent process handles preserve CPU sampling between refreshes.
PROC_CACHE = {}

def process_list():
    result = []
    seen = set()
    now = time.time()

    for p in psutil.process_iter([
        "pid", "ppid", "name", "username",
        "status", "create_time", "cmdline"
    ]):
        try:
            info = p.info
            pid = info["pid"]
            created = info["create_time"]
            key = (pid, created)
            seen.add(key)

            cached = PROC_CACHE.get(key)
            if cached is None:
                cached = p
                PROC_CACHE[key] = cached
                cpu_value = cached.cpu_percent(None)
            else:
                cpu_value = cached.cpu_percent(None)

            result.append({
                "pid": pid,
                "ppid": info["ppid"],
                "name": info["name"] or "?",
                "user": info["username"] or "?",
                "state": info["status"] or "?",
                "age": now - created,
                "cpu": cpu_value,
                "ram": p.memory_percent(),
                "cmd": " ".join(info["cmdline"] or [])[:240]
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess, TypeError, KeyError):
            continue

    # Discard handles for processes that exited or whose PID was reused.
    for key in list(PROC_CACHE):
        if key not in seen:
            PROC_CACHE.pop(key, None)

    return result

def one_shot():
    from rich.console import Console
    from rich.table import Table
    c = Console()
    c.print("[bold cyan]VPS COMMAND CENTER — ONE SHOT[/]")
    m = psutil.virtual_memory()
    c.print(f"CPU: {psutil.cpu_percent(0.3):.1f}% | "
            f"RAM: {m.percent:.1f}% | "
            f"Available: {human(m.available)}")
    t = Table()
    for x in ("PID", "PROCESS", "CPU", "RAM", "STATE"):
        t.add_column(x)
    for p in sorted(process_list(), key=lambda x: x["cpu"], reverse=True)[:15]:
        t.add_row(str(p["pid"]), p["name"],
                  f"{p['cpu']:.1f}%", f"{p['ram']:.1f}%", p["state"])
    c.print(t)
    c.print("[green]Read-only. No process actions performed.[/]")

class Chekup(App):
    TITLE = "VPS COMMAND CENTER"
    SUB_TITLE = "Live System Intelligence"

    CSS = """
    Screen {
        background: #080e1a;
    }
    #banner {
        height: 3;
        content-align: center middle;
        background: #142544;
        color: #ffffff;
        text-style: bold;
    }
    #metrics {
        height: 9;
        layout: grid;
        grid-size: 4 1;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
        margin: 0 1;
    }
    .metric {
        height: 9;
        border: round #315078;
        padding: 0 1;
        background: #101b2d;
    }
    #main {
        height: 1fr;
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
        grid-gutter: 1;
        margin: 0 1;
    }
    .panel {
        border: round #315078;
        padding: 0 1;
        background: #0d1728;
        height: 1fr;
    }
    #process {
        height: 1fr;
    }
    #alerts, #details {
        height: 1fr;
        overflow-y: auto;
    }
    #statusbar {
        height: 1;
        background: #142544;
        color: #b9d5ff;
        content-align: center middle;
    }
    Screen {
        overflow-y: auto;
    }
    .compact #metrics {
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        height: 10;
    }
    .compact .metric {
        height: 5;
        padding: 0 1;
    }
    .compact #main {
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
        height: 1fr;
    }
    .compact .panel {
        height: 1fr;
        min-height: 6;
    }
    .tiny #metrics {
        grid-size: 1 4;
        grid-columns: 1fr;
        height: auto;
    }
    .tiny .metric {
        height: 5;
    }
    .tiny #main {
        grid-size: 1 4;
        grid-columns: 1fr;
        grid-rows: auto auto auto auto;
        height: auto;
    }
    .tiny .panel {
        height: 12;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_now", "Refresh"),
        ("d", "toggle_details", "Details"),
    ]

    def __init__(self):
        super().__init__()
        self.frame = 0
        self.details = False
        self.last_logs = []
        self.last_log_time = 0
        self.last_services = {}
        self.last_processes = []
        self.cpu_history = []
        self.ram_history = []
        self.cpu = 0
        self.refreshing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◈ VPS LIVE COMMAND CENTER ◈", id="banner")
        with Container(id="metrics"):
            yield Static(id="cpu", classes="metric")
            yield Static(id="ram", classes="metric")
            yield Static(id="disk", classes="metric")
            yield Static(id="host", classes="metric")
        with Container(id="main"):
            yield Static(id="services", classes="panel")
            yield Static(id="hermes", classes="panel")
            yield DataTable(id="process", classes="panel")
            yield Static(id="alerts", classes="panel")
        yield Static("Starting live monitor...", id="statusbar")
        yield Footer()

    def on_mount(self):
        self.query_one("#process", DataTable).add_columns(
            "PID", "PROCESS", "CPU", "RAM", "STATE"
        )
        self.cpu = psutil.cpu_percent(None)
        self.set_interval(2, self.refresh_dashboard)
        self.refresh_dashboard()

    def on_resize(self, event: events.Resize):
        width = event.size.width
        if width < 70:
            self.add_class("compact", "tiny")
        elif width < 100:
            self.add_class("compact")
            self.remove_class("tiny")
        else:
            self.remove_class("compact", "tiny")

    def action_refresh_now(self):
        self.refresh_dashboard()

    def action_toggle_details(self):
        self.details = not self.details
        self.refresh_dashboard()

    def refresh_dashboard(self):
        if self.refreshing:
            return
        self.refreshing = True
        try:
            self.update_dashboard()
        except Exception as e:
            self.query_one("#statusbar").update(
                f"[!] Dashboard update error: {str(e)[:120]}"
            )
        finally:
            self.refreshing = False

    def update_dashboard(self):
        self.frame += 1
        now = datetime.now()
        spin = ["◐", "◓", "◑", "◒"][self.frame % 4]

        cpu = psutil.cpu_percent(None)
        mem = psutil.virtual_memory()
        uptime = time.time() - psutil.boot_time()
        self.cpu_history.append(cpu)
        self.ram_history.append(mem.percent)
        self.cpu_history = self.cpu_history[-20:]
        self.ram_history = self.ram_history[-20:]

        disks = []
        for path in ("/", "/mnt/storage2"):
            try:
                d = psutil.disk_usage(path)
                disks.append((path, d.percent, human(d.used), human(d.total)))
            except Exception:
                pass

        def bar(value, width=18):
            value = max(0, min(100, value))
            filled = int(value / 100 * width)
            color = "green" if value < 70 else "yellow" if value < 90 else "red"
            return f"[{color}]{'━' * filled}[/][#45536b]{'━' * (width-filled)}[/]"

        self.query_one("#cpu").update(
            f"[bold cyan]CPU[/]\n"
            f"[bold white]{cpu:5.1f}%[/]\n{bar(cpu)}\n"
            f"[dim]Load: {' / '.join(f'{x:.2f}' for x in os.getloadavg())}[/]"
        )
        self.query_one("#ram").update(
            f"[bold cyan]MEMORY[/]\n"
            f"[bold white]{mem.percent:5.1f}%[/]\n{bar(mem.percent)}\n"
            f"[dim]Free: {human(mem.available)}[/]"
        )

        disk_lines = ["[bold cyan]STORAGE[/]"]
        for path, pct, used, total in disks:
            disk_lines.append(f"{path}: [bold]{pct:.0f}%[/] {bar(pct, 12)}")
            disk_lines.append(f"[dim]{used} / {total}[/]")
        self.query_one("#disk").update("\n".join(disk_lines))

        self.query_one("#host").update(
            f"[bold cyan]SERVER[/]\n"
            f"[bold white]{os.uname().nodename}[/]\n"
            f"Uptime: {age(uptime)}\n"
            f"[dim]{now.strftime('%d %b %Y %H:%M:%S')}[/]"
        )

        if self.frame % 3 == 1 or not self.last_services:
            self.last_services = {
                "Docker": service("docker"),
                "SSH": service("ssh"),
                "MariaDB": service("mariadb"),
                "Postfix": service("postfix"),
                "Dovecot": service("dovecot"),
                "Nginx": run(["systemctl", "is-active", "nginx"]) or "unknown"
            }

        service_lines = ["[bold cyan]SERVICE MONITOR[/]"]
        for name, state in self.last_services.items():
            # Nginx systemd failure may coexist with live Nginx listeners.
            if name == "Nginx" and state != "active":
                sockets = run(["ss", "-H", "-lnt"])
                if ":80 " in sockets or ":443 " in sockets:
                    state = "unit " + state + " / listener active"
            good = state == "active" or "listener active" in state
            service_lines.append(
                f"{'🟢' if good else '🟡'} {name:<10} "
                f"[{'green' if good else 'yellow'}]{state}[/]"
            )
        self.query_one("#services").update("\n".join(service_lines))

        hermes, hrestart = docker_info("hermes-agent")
        freeapi, frestart = docker_info("freellmapi")
        router = router_health()

        hlines = [
            "[bold magenta]HERMES & NUPUR[/]",
            f"Hermes Agent: [{'green' if hermes == 'running' else 'red'}]{hermes}[/]",
            f"Restart count: {hrestart}",
            f"FreeLLM API: [{'green' if freeapi == 'running' else 'yellow'}]{freeapi}[/]",
            f"FreeLLM restarts: {frestart}",
            f"Nupur Router: [{'green' if router.startswith('HTTP 2') else 'yellow'}]{router}[/]",
            "",
            "[dim]Monitoring only — no automatic action[/]"
        ]
        self.query_one("#hermes").update("\n".join(hlines))

        self.last_processes = process_list()
        top = sorted(self.last_processes, key=lambda x: x["cpu"], reverse=True)
        table = self.query_one("#process", DataTable)
        table.clear()
        for p in top[:12]:
            state = p["state"]
            table.add_row(
                str(p["pid"]), p["name"][:18],
                f"{p['cpu']:.1f}%", f"{p['ram']:.1f}%",
                state[:10]
            )

        alerts = []
        zombies = [p for p in self.last_processes if p["state"] == "zombie"]
        if cpu >= 85:
            alerts.append("[bold red]HIGH CPU[/] — inspect top processes.")
        if mem.percent >= 90:
            alerts.append("[bold red]HIGH RAM[/] — inspect memory consumers.")
        if zombies:
            alerts.append(
                f"[yellow]{len(zombies)} zombie process(es)[/] — inspect parent PID."
            )
        if hermes != "running":
            alerts.append("[red]Hermes is not running — inspect container logs.[/]")
        try:
            if int(hrestart) >= 5:
                alerts.append(f"[yellow]Hermes restart count is {hrestart}.[/]")
        except Exception:
            pass
        if router == "UNREACHABLE":
            alerts.append("[yellow]Nupur health endpoint unreachable.[/]")
        if not alerts:
            alerts.append("[green]No immediate threshold alerts.[/]")
        alerts.append("")
        alerts.append("[dim]Old uptime alone does not mean stale.[/]")
        alerts.append("[dim]Every recommendation requires human review.[/]")

        if self.details:
            alerts.extend(["", "[bold]TOP PROCESS DETAILS[/]"])
            by_pid = {p["pid"]: p for p in self.last_processes}
            for p in top[:6]:
                parent = by_pid.get(p["ppid"])
                parent_name = parent["name"] if parent else (
                    "system/adopted" if p["ppid"] == 1 else "not in sample"
                )
                alerts.append(
                    f"[cyan]PID {p['pid']}[/] PPID {p['ppid']} "
                    f"({parent_name})"
                )
                alerts.append(
                    f"{p['name']} | CPU {p['cpu']:.1f}% | "
                    f"RAM {p['ram']:.1f}% | {p['state']} | "
                    f"age {age(p['age'])}"
                )
                alerts.append(f"[dim]{p['cmd'][:150]}[/]")
        self.query_one("#alerts").update("\n".join(alerts))

        # Expensive log query is rate-limited to once every 30 seconds.
        if time.time() - self.last_log_time > 30:
            logs = run([
                "docker", "logs", "--since", "15m",
                "--tail", "120", "hermes-agent"
            ], timeout=5)
            self.last_logs = [
                x[:130] for x in logs.splitlines()
                if any(k in x.lower() for k in (
                    "error", "exception", "failed", "traceback",
                    "unable to open database"
                ))
            ][-3:]
            self.last_log_time = time.time()

        log_summary = "\n".join(self.last_logs) or "No matching recent Hermes errors."
        self.query_one("#statusbar").update(
            f"{spin} LIVE  {now.strftime('%H:%M:%S')}  |  "
            f"Refresh: 2s  |  q Quit  •  r Refresh  •  d Details  |  "
            f"READ-ONLY — NO PROCESS WILL BE STOPPED"
        )
        self.sub_title = (
            "Recent Hermes logs: " + log_summary.replace("\n", " | ")[:100]
        )

if __name__ == "__main__":
    if "--version" in sys.argv:
        print("Chekup TUI", VERSION)
    elif "--once" in sys.argv:
        one_shot()
    else:
        Chekup().run()
