import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
import sys
import time
from datetime import datetime, date, timedelta
from wellbeing_app.storage.database import init_db, get_connection
from wellbeing_app.daemon.service import WellbeingDaemon

def test_daemon_execution():
  print("Initializing test database...")
  init_db()
  
  # Seed database with some manual settings for testing
  with get_connection() as conn:
    cursor = conn.cursor()
    # Ensure some adhan delays are set
    cursor.execute("UPDATE adhan_config SET enabled = 1, delay_seconds = 0")
    
    # Configure London coordinates in database to verify calculations
    cursor.execute("""
      UPDATE prayer_config 
      SET latitude = 51.5074, longitude = -0.1278, timezone = 'Europe/London', 
          calculation_method = 'MuslimWorldLeague', madhab = 'shafi', high_lat_rule = 'AngleBased'
    """)
    
    # Enable some Jamah times
    cursor.execute("UPDATE jamah_times SET enabled = 1")
    cursor.execute("UPDATE jamah_times SET time = '13:30' WHERE prayer = 'dhuhr'")
    cursor.execute("UPDATE jamah_times SET time = '17:30' WHERE prayer = 'asr'")
    conn.commit()

  print("Instantiating WellbeingDaemon...")
  daemon = WellbeingDaemon()
  
  # Register mock callbacks to verify callbacks can be registered
  daemon.register_callback('ADHAN_TIME', lambda p: print(f"[MOCK] ADHAN_TIME callback triggered for {p}"))
  daemon.register_callback('IQAMAH_TIME', lambda p: print(f"[MOCK] IQAMAH_TIME callback triggered for {p}"))
  daemon.register_callback('LOCK_OVERLAY_TRIGGER', lambda p: print(f"[MOCK] LOCK_OVERLAY_TRIGGER callback triggered for {p}"))
  
  print("Starting daemon scheduler...")
  daemon.start()
  
  print("\n--- Scheduled Events for Today ---")
  if not daemon.scheduled_events:
    print("  (No upcoming events remaining for today)")
  for event in sorted(daemon.scheduled_events, key=lambda x: x['time']):
    print(f"  Event: {event['name']:20} | Prayer: {event['prayer']:8} | Time: {event['time'].strftime('%Y-%m-%d %H:%M:%S')}")
  print("----------------------------------\n")
  
  loop = GLib.MainLoop()
  
  def on_timeout():
    print("Test timeout reached (5 seconds). Stopping daemon...")
    daemon.stop()
    print("Stopping GLib main loop...")
    loop.quit()
    return False

  # Schedule loop shutdown in 5 seconds
  GLib.timeout_add_seconds(5, on_timeout)
  
  print("Entering GLib main loop for 5 seconds...")
  loop.run()
  
  print("✓ Daemon ran successfully without import errors or crashes.")

if __name__ == '__main__':
  try:
    test_daemon_execution()
  except Exception as e:
    print(f"❌ TEST FAILED: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
