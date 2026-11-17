# chekup

**Professional System Monitoring & Diagnostic Tool**

[![Version](https://img.shields.io/badge/version-4.2-blue)]()
[![Python](https://img.shields.io/badge/python-3.10+-blueviolet)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

`chekup` is a comprehensive, professional-grade command-line tool designed for real-time system monitoring and diagnostics on Linux servers and VPS environments. It provides an interactive Terminal User Interface (TUI) as well as a quick one-shot CLI mode for instant system snapshots.

---

## 🚀 Features

- **Real-Time Metrics**: Detailed insights into CPU usage, memory consumption, disk utilization, and network traffic.
- **Process Tracking**: Monitor active processes with resource usage percentages.
- **Diagnostics Engine**: Proactive analysis of system health to detect anomalies (e.g., high CPU load, low memory).
- **Interactive TUI**: A responsive dashboard built with `Textual` and `Rich` for visual monitoring.
- **One-Shot Mode**: `chekup --once` for quick, scriptable system reports.
- **Modular Architecture**: Decoupled logic for core data collection, diagnostics, and UI.

---

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nasrulahsannayem/chekup.git
   cd chekup
   ```

2. **Install the package (editable mode):**
   ```bash
   pip install -e .
   ```

3. **Verify installation:**
   ```bash
   chekup --version
   ```

---

## 🛠️ Usage

### Launch Interactive TUI
Start the full monitoring dashboard:
```bash
chekup
```
*Press `Ctrl+C` to exit.*

### One-Shot Report
Get an immediate terminal table of system stats and top processes:
```bash
chekup --once
```

---

## 🏗️ Tech Stack

- **Language**: Python 3
- **UI**: [Textual](https://textual.textualize.io/) (TUI framework)
- **Formatting**: [Rich](https://rich.readthedocs.io/)
- **System Data**: `psutil`

---

## 🧪 Testing

Run the test suite:
```bash
PYTHONPATH=src python -m pytest tests/ -v
```

---

## 📜 License

MIT License © Nasrul Ahsan Nayem

See [LICENSE](LICENSE) for details.
