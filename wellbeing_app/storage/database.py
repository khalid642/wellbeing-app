import sqlite3
import importlib.resources
from wellbeing_app.constants import DB_PATH

def init_db():
    schema_path = importlib.resources.files('wellbeing_app.storage').joinpath('schema.sql')
    schema = schema_path.read_text()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executescript(schema)
        
        # 1. Seed app_config default variables
        cursor.execute("SELECT COUNT(*) FROM app_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO app_config (key, value) VALUES ('eyecare_interval_minutes', '20')")
            cursor.execute("INSERT INTO app_config (key, value) VALUES ('eyecare_lock_seconds', '20')")
            cursor.execute("INSERT INTO app_config (key, value) VALUES ('eyecare_enabled', '1')")
            cursor.execute("INSERT INTO app_config (key, value) VALUES ('salah_lock_duration_seconds', '900')")
            
        cursor.execute("SELECT COUNT(*) FROM prayer_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO prayer_config 
                (location_mode, latitude, longitude, timezone, calculation_method, madhab, high_lat_rule)
                VALUES ('manual', 21.3891, 39.8579, 'Asia/Riyadh', 'MuslimWorldLeague', 'shafi', 'AngleBased')
            """)
            
        cursor.execute("SELECT COUNT(*) FROM iqamah_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO iqamah_config (global_offset_minutes) VALUES (5)")
            
        cursor.execute("SELECT COUNT(*) FROM jamah_times")
        if cursor.fetchone()[0] == 0:
            for prayer in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
                cursor.execute("INSERT INTO jamah_times (prayer, time, enabled) VALUES (?, NULL, 1)", (prayer,))
                
        cursor.execute("SELECT COUNT(*) FROM adhan_config")
        if cursor.fetchone()[0] == 0:
            for prayer in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
                cursor.execute("INSERT INTO adhan_config (prayer, audio_file, delay_seconds, volume, enabled) VALUES (?, NULL, 0, 0.8, 1)", (prayer,))
                
        # Seed default widget templates
        cursor.execute("SELECT COUNT(*) FROM widget_templates")
        if cursor.fetchone()[0] == 0:
            # Salah Lock Widgets
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Default Clock', 'general', 'clock_widget', '{}')
            """)
            clock_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Default Countdown', 'general', 'countdown_timer_widget', '{}')
            """)
            countdown_id = cursor.lastrowid
            
            # Eye Care Widgets
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Eye Care Text 1', 'general', 'text_widget', '{"text": "Rest your eyes. Look 20 feet away."}')
            """)
            ec_text1_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Eye Care Breathing', 'general', 'breathing_widget', '{"mode": "box"}')
            """)
            ec_breath_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Eye Care Text 2', 'general', 'text_widget', '{"text": "Blink slowly 5 times. Relax your shoulders."}')
            """)
            ec_text2_id = cursor.lastrowid
            
            # Zikr Widgets
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Dhikr SubhanAllah', 'spiritual', 'tasbih_widget', '{"target": 33, "dhikr_text": "SubhanAllah"}')
            """)
            dhikr_tasbih_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO widget_templates (name, category, widget_type, config_json)
                VALUES ('Dhikr Praise', 'general', 'text_widget', '{"text": "سبحان الله وبحمده\\nGlory be to Allah and Praise Him"}')
            """)
            dhikr_text_id = cursor.lastrowid
            
            # 1. Seed Salah Lock Assignments
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('salah_lock', ?, 1, 1)
            """, (clock_id,))
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('salah_lock', ?, 2, 1)
            """, (countdown_id,))
            
            # 2. Seed Eye Care Assignments
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('eyecare', ?, 1, 1)
            """, (ec_text1_id,))
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('eyecare', ?, 2, 1)
            """, (ec_breath_id,))
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('eyecare', ?, 3, 1)
            """, (ec_text2_id,))
            
            # 3. Seed Zikr Assignments
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('zikr', ?, 1, 1)
            """, (dhikr_tasbih_id,))
            cursor.execute("""
                INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
                VALUES ('zikr', ?, 2, 1)
            """, (dhikr_text_id,))
            
        conn.commit()

def get_connection():
    return sqlite3.connect(DB_PATH)

class Database:
    def __init__(self):
        pass

    @property
    def conn(self):
        return get_connection()

    def get_overlay_widgets(self, slot: str) -> list:
        import json
        from wellbeing_app.overlay_engine.overlay_window import WidgetConfig
        with get_connection() as conn:
            rows = conn.execute('''
                SELECT wt.id, wt.widget_type, wt.config_json, owa.display_order
                FROM overlay_widget_assignments owa
                JOIN widget_templates wt ON wt.id = owa.widget_template_id
                WHERE owa.overlay_slot = ? AND owa.enabled = 1
                ORDER BY owa.display_order ASC
            ''', (slot,)).fetchall()

        return [
            WidgetConfig(
                template_id=row[0],
                widget_type=row[1],
                config=json.loads(row[2] or '{}'),
                display_order=row[3]
            )
            for row in rows
        ]

db = Database()
