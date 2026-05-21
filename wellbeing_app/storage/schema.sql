CREATE TABLE IF NOT EXISTS app_config (
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
  audio_file_list TEXT,
  random_selection INTEGER DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS overlay_widget_assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  overlay_slot TEXT NOT NULL,
  widget_template_id INTEGER REFERENCES widget_templates(id),
  display_order INTEGER DEFAULT 0,
  enabled INTEGER DEFAULT 1
);
