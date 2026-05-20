import os
from pathlib import Path

base_dir = Path("/home/amanah/projects/wellbeing-app")

files = {
    "wellbeing_app/__init__.py": "",
    "wellbeing_app/daemon/__init__.py": "",
    "wellbeing_app/storage/__init__.py": "",
    "wellbeing_app/settings/__init__.py": "",
    "wellbeing_app/gui/__init__.py": "",
    "wellbeing_app/gui/pages/__init__.py": "",
    "wellbeing_app/themes/__init__.py": "",
    
    "wellbeing_app/constants.py": """import os
from pathlib import Path

APP_ID = "com.github.amanah.wellbeing"
APP_NAME = "Wellbeing App"

XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
XDG_STATE_HOME = os.environ.get('XDG_STATE_HOME', os.path.expanduser('~/.local/state'))

CONFIG_DIR = Path(XDG_CONFIG_HOME) / "wellbeing-app"
CACHE_DIR = Path(XDG_CACHE_HOME) / "wellbeing-app"
LOGS_DIR = Path(XDG_STATE_HOME) / "wellbeing-app"
DB_PATH = CONFIG_DIR / "wellbeing.db"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
""",

    "wellbeing_app/storage/schema.sql": """CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS prayer_config (
  id INTEGER PRIMARY KEY,
  location_mode TEXT DEFAULT 'manual',
  latitude REAL DEFAULT 21.3891,
  longitude REAL DEFAULT 39.8579,
  timezone TEXT DEFAULT 'Asia/Riyadh',
  calculation_method TEXT DEFAULT 'MuslimWorldLeague',
  madhab TEXT DEFAULT 'shafi',
  high_lat_rule TEXT DEFAULT 'AngleBased'
);

CREATE TABLE IF NOT EXISTS jamah_times (
  prayer TEXT PRIMARY KEY,
  time TEXT,
  enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS adhan_config (
  id INTEGER PRIMARY KEY,
  prayer TEXT,
  audio_file TEXT,
  delay_seconds INTEGER DEFAULT 0,
  volume REAL DEFAULT 0.8,
  enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS iqamah_config (
  id INTEGER PRIMARY KEY,
  global_offset_minutes INTEGER DEFAULT 5
);

CREATE TABLE IF NOT EXISTS zikr_sequences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  loop_mode TEXT DEFAULT 'once'
);

CREATE TABLE IF NOT EXISTS zikr_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sequence_id INTEGER REFERENCES zikr_sequences(id),
  step_order INTEGER,
  selection_mode TEXT CHECK(selection_mode IN ('fixed','random_one','random_n')),
  n_count INTEGER DEFAULT 1,
  widget_ids TEXT,
  duration_seconds INTEGER DEFAULT 30,
  transition TEXT DEFAULT 'fade'
);

CREATE TABLE IF NOT EXISTS widget_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  category TEXT,
  widget_type TEXT,
  config_json TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  is_active INTEGER DEFAULT 0,
  config_json TEXT
);
""",

    "wellbeing_app/storage/database.py": """import sqlite3
import importlib.resources
from wellbeing_app.constants import DB_PATH

def init_db():
    schema_path = importlib.resources.files('wellbeing_app.storage').joinpath('schema.sql')
    schema = schema_path.read_text()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executescript(schema)
        
        cursor.execute("SELECT COUNT(*) FROM prayer_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute(\"\"\"
                INSERT INTO prayer_config 
                (location_mode, latitude, longitude, timezone, calculation_method, madhab, high_lat_rule)
                VALUES ('manual', 21.3891, 39.8579, 'Asia/Riyadh', 'MuslimWorldLeague', 'shafi', 'AngleBased')
            \"\"\")
            
        cursor.execute("SELECT COUNT(*) FROM iqamah_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO iqamah_config (global_offset_minutes) VALUES (5)")
            
        cursor.execute("SELECT COUNT(*) FROM jamah_times")
        if cursor.fetchone()[0] == 0:
            for prayer in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
                cursor.execute("INSERT INTO jamah_times (prayer, time, enabled) VALUES (?, NULL, 1)", (prayer,))
                
        conn.commit()

def get_connection():
    return sqlite3.connect(DB_PATH)
""",

    "wellbeing_app/settings/config.py": """from wellbeing_app.storage.database import get_connection

def get_config_value(key: str, default=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return default

def set_config_value(key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO app_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        conn.commit()
""",

    "wellbeing_app/daemon/service.py": """import time
import logging
from wellbeing_app.constants import LOGS_DIR

def run_daemon():
    log_file = LOGS_DIR / "daemon.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("WellbeingDaemon")
    logger.info("Daemon started")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Daemon stopped")
""",

    "wellbeing_app/gui/pages/dashboard.py": """import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk

class DashboardPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.set_margin_top(48)
        self.set_margin_bottom(48)
        self.set_margin_start(48)
        self.set_margin_end(48)
        
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        welcome_label = Gtk.Label(label="Welcome to Wellbeing App")
        welcome_label.add_css_class("title-1")
        self.append(welcome_label)

        subtitle_label = Gtk.Label(label="Your Islamic digital companion")
        subtitle_label.add_css_class("dim-label")
        self.append(subtitle_label)

        glass_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        glass_card.add_css_class("glass-card")
        glass_card.set_margin_top(24)
        glass_card.set_size_request(300, 200)
        
        card_label = Gtk.Label(label="Dashboard Placeholder")
        card_label.set_valign(Gtk.Align.CENTER)
        card_label.set_vexpand(True)
        glass_card.append(card_label)
        
        self.append(glass_card)
""",

    "wellbeing_app/gui/main_window.py": """import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from wellbeing_app.gui.pages.dashboard import DashboardPage

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Wellbeing App")
        self.set_default_size(800, 600)
        
        # Ensure we respect system light/dark mode by using the default style manager
        Adw.StyleManager.get_default()
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)
        
        self.dashboard = DashboardPage()
        main_box.append(self.dashboard)
        
        self.set_content(main_box)
""",

    "wellbeing_app/gui/application.py": """import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw, Gio
import importlib.resources
from wellbeing_app.gui.main_window import MainWindow
from wellbeing_app.constants import APP_ID

class WellbeingApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._load_css()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        try:
            css_path = importlib.resources.files('wellbeing_app.themes').joinpath('style.css')
            css_provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Error loading CSS: {e}")
""",

    "wellbeing_app/themes/style.css": """/* Glassmorphism styling */
.glass-card {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 16px;
    transition: all 200ms ease;
}

.glass-card:hover {
    background: rgba(255, 255, 255, 0.12);
}

/* Ensure interactive elements have smooth transitions */
button, entry, scale, switch {
    transition: all 200ms ease;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .glass-card:hover {
        background: rgba(255, 255, 255, 0.08);
    }
}
""",

    "wellbeing_app/main.py": """import sys
import argparse
from wellbeing_app.storage.database import init_db
from wellbeing_app.gui.application import WellbeingApplication
from wellbeing_app.daemon.service import run_daemon

def main():
    parser = argparse.ArgumentParser(description="Wellbeing App")
    parser.add_argument('--daemon', action='store_true', help="Run the background daemon")
    args, remaining = parser.parse_known_args()

    init_db()

    if args.daemon:
        run_daemon()
    else:
        app = WellbeingApplication()
        sys.exit(app.run([sys.argv[0]] + remaining))

if __name__ == "__main__":
    main()
""",

    "data/wellbeing-app.desktop": """[Desktop Entry]
Name=Wellbeing App
Comment=Islamic digital wellbeing environment
Exec=wellbeing-app
Icon=wellbeing-app
Terminal=false
Type=Application
Categories=Utility;
""",

    "data/icons/wellbeing-app.svg": """<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <rect width="256" height="256" rx="64" fill="#3584e4"/>
  <circle cx="128" cy="128" r="64" fill="#ffffff" opacity="0.8"/>
  <path d="M 128 80 L 128 176 M 80 128 L 176 128" stroke="#3584e4" stroke-width="16" stroke-linecap="round"/>
</svg>
""",

    "systemd/wellbeing-app.service": """[Unit]
Description=Wellbeing App Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=%h/.local/bin/wellbeing-app --daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
""",

    "setup.py": """from setuptools import setup, find_packages

setup(
    name="wellbeing-app",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "wellbeing_app.themes": ["*.css"],
        "wellbeing_app.storage": ["*.sql"],
    },
)
""",

    "pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "wellbeing-app"
version = "0.1.0"
description = "A modern Islamic wellbeing and focus application"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "PyGObject>=3.46.0"
]

[project.scripts]
wellbeing-app = "wellbeing_app.main:main"
""",

    "README.md": """# Wellbeing App

A production Linux desktop application built with Python 3.13+, GTK4, and Libadwaita.
"""
}

for filepath, content in files.items():
    full_path = base_dir / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)

print("Project skeleton generated.")
