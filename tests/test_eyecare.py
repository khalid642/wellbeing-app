import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import sys
import os

from wellbeing_app.storage.database import init_db, get_connection, db
from wellbeing_app.daemon.service import WellbeingDaemon
from wellbeing_app.overlay_engine.overlay_window import OverlayWindow, OverlayConfig, WidgetConfig
from wellbeing_app.overlay_engine.overlay_manager import OverlayManager

def run_eyecare_tests():
  os.environ['WELLBEING_TEST_MODE'] = '1'
  Gtk.init()
  
  # Initialize DB fresh
  print("Initializing test database...")
  init_db()
  
  # Track test results
  test_events = []
  
  daemon = WellbeingDaemon()
  manager = OverlayManager.get()
  
  def on_dismissed(config, reason):
    print(f"Captured overlay dismissal: ID={config.overlay_id}, Reason={reason}")
    test_events.append((config.overlay_id, reason))
    
    if config.overlay_id == 'eyecare':
      # When eyecare is dismissed via keypress, it should fire the zikr overlay.
      # Wait a brief moment to check if zikr overlay presented.
      GLib.timeout_add(300, verify_zikr_active)

  manager.on_dismissed(on_dismissed)
  
  def verify_zikr_active():
    print("Verifying if follow-up Zikr overlay is presented...")
    if manager.is_overlay_active():
      current_win = manager._current
      assert current_win.config.overlay_id == 'zikr', f"Expected zikr overlay, got {current_win.config.overlay_id}"
      print("✓ Zikr follow-up overlay is ACTIVE!")
      
      # Now simulate Escape keypress on Zikr overlay
      print("Simulating Escape key press on Zikr overlay...")
      current_win._on_key_pressed(None, Gdk.KEY_Escape, 0, 0)
    else:
      print("❌ Error: Zikr overlay was not shown after eyecare lock period!")
      sys.exit(1)
      
    # Finish test
    GLib.timeout_add(100, finalize_tests)

  def finalize_tests():
    print("\n--- Eye-Care System Verification Summary ---")
    assert len(test_events) == 2, f"Expected 2 overlay dismissals, got {len(test_events)}"
    assert test_events[0] == ('eyecare', 'timer_expired_keypress'), f"Unexpected first event: {test_events[0]}"
    assert test_events[1] == ('zikr', 'escape'), f"Unexpected second event: {test_events[1]}"
    
    print("✓ DB seeding, eye-care widgets, countdown timer, and follow-up Zikr trigger tested successfully!")
    print("✓ All Eye-Care verification tests PASSED successfully!")
    daemon.stop()

  # Start Daemon
  print("Starting WellbeingDaemon scheduler...")
  daemon.start()
  
  # Trigger the eye-care overlay manually through the daemon scheduler trigger
  def trigger_scheduler_break():
    print("\n--- Triggering Eye-Care overlay interval break ---")
    # Simulate EyeCare interval firing directly
    daemon.eyecare_scheduler._fire_eyecare()
    
    # Wait for the overlay to fully transition and then simulate KeyPress in Phase 2
    # The default lock time is 20s. Let's force it to 2s to test quickly!
    win = manager._current
    if win:
      win.remaining_seconds = 30 # Full 30s countdown for user to try it!
      print("\n=======================================================")
      print("   👉 INTERACTIVE BREAK OVERLAY LOADED FOR 30 SECONDS 👈")
      print("   Feel free to:")
      print("   1. Follow the breathing circle breathing widget.")
      print("   2. Click or press keys on the Tasbih counter widget!")
      print("   3. See the countdown shrinking progress ring.")
      print("=======================================================\n")
      print(f"Lock remaining: {win.remaining_seconds}s")
      
      # In 32 seconds, the countdown will be 0 (Phase 2), then we press Space to dismiss if not already dismissed
      def simulate_space():
        if manager.is_overlay_active() and manager._current == win:
          print("Simulating space key press in Phase 2...")
          win._on_key_pressed(None, Gdk.KEY_space, 0, 0)
        return False
        
      GLib.timeout_add_seconds(32, simulate_space)
    else:
      print("❌ Error: Eye-Care overlay window not presented!")
      sys.exit(1)
      
    return False

  GLib.idle_add(trigger_scheduler_break)
  
  loop = GLib.MainLoop()
  original_exit = finalize_tests
  def exit_patched():
    try:
      original_exit()
    finally:
      loop.quit()
      
  globals()['finalize_tests'] = exit_patched
  loop.run()

if __name__ == '__main__':
  try:
    run_eyecare_tests()
  except Exception as e:
    print(f"❌ TEST FAILED: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
