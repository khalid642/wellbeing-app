import sqlite3
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
                
        conn.commit()

def get_connection():
    return sqlite3.connect(DB_PATH)
