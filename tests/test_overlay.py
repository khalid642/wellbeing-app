import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import sys
import os

from wellbeing_app.overlay_engine.overlay_window import OverlayWindow, WidgetConfig, OverlayConfig
from wellbeing_app.overlay_engine.overlay_manager import OverlayManager

def run_overlay_tests():
  # Initialize GTK
  os.environ['WELLBEING_TEST_MODE'] = '1'
  Gtk.init()
  
  manager = OverlayManager.get()
  
  # Track results
  test_results = []
  
  def on_dismissed(config, reason):
    print(f"Captured overlay dismissal: ID={config.overlay_id}, Reason={reason}")
    test_results.append((config.overlay_id, reason))
    
    if config.overlay_id == 'test_locked':
      GLib.timeout_add(100, run_test_2)
    elif config.overlay_id == 'test_unlocked':
      GLib.timeout_add(100, exit_test)

  manager.on_dismissed(on_dismissed)
  
  def run_test_1():
    print("\n=======================================================")
    print("   👉 TEST 1: LOCKED OVERLAY LOADED FOR 30 SECONDS 👈")
    print("   This overlay is LOCKED!")
    print("   - Verify that your MOUSE CURSOR is completely HIDDEN.")
    print("   - Verify that your system shortcuts do not leak to i3wm.")
    print("   - After 30 seconds (countdown reaches 00:00), press")
    print("     Space or Enter key to dismiss and move to Test 2.")
    print("=======================================================\n")
    wc = WidgetConfig(template_id=99, widget_type='text_widget', config={'text': 'Locked Test'})
    config = OverlayConfig(
      mode='locked',
      duration_seconds=30,
      widgets=[wc],
      overlay_id='test_locked'
    )
    manager.show_overlay(config)
    
    # Simulate Space key press in 32 seconds if the user hasn't manually dismissed it
    def simulate_space():
      if manager.is_overlay_active() and manager._current and manager._current.config.overlay_id == 'test_locked':
        print("Simulating space key press in Phase 2...")
        win = manager._current
        win._on_key_pressed(None, Gdk.KEY_space, 0, 0)
      return False
      
    GLib.timeout_add_seconds(32, simulate_space)
    return False

  def run_test_2():
    print("\n=======================================================")
    print("   👉 TEST 2: UNLOCKED OVERLAY LOADED FOR 30 SECONDS 👈")
    print("   This overlay is UNLOCKED!")
    print("   - Verify that your MOUSE CURSOR IS VISIBLE.")
    print("   - Verify that pressing Space or Enter does NOT dismiss it.")
    print("   - Press ONLY the ESCAPE key to dismiss and exit tests.")
    print("=======================================================\n")
    wc = WidgetConfig(template_id=99, widget_type='text_widget', config={'text': 'Unlocked Test (ESC to Close)'})
    config = OverlayConfig(
      mode='unlocked',
      duration_seconds=0,
      widgets=[wc],
      overlay_id='test_unlocked'
    )
    manager.show_overlay(config)
    
    # Simulate Escape key press in 32 seconds if the user hasn't manually dismissed it
    def simulate_escape():
      if manager.is_overlay_active() and manager._current and manager._current.config.overlay_id == 'test_unlocked':
        print("Simulating Escape key press...")
        win = manager._current
        win._on_key_pressed(None, Gdk.KEY_Escape, 0, 0)
      return False
      
    GLib.timeout_add_seconds(32, simulate_escape)
    return False

  def exit_test():
    print("\n--- Verification Summary ---")
    t1_found = False
    t2_found = False
    for o_id, reason in test_results:
      if o_id == 'test_locked':
        t1_found = True
        print(f"Test 1 Locked Overlay Dismissal: {reason}")
        assert reason in ['timer_expired_keypress', 'safety_watchdog'], f"Unexpected reason: {reason}"
      elif o_id == 'test_unlocked':
        t2_found = True
        print(f"Test 2 Unlocked Overlay Dismissal: {reason}")
        assert reason == 'escape', f"Expected escape, got {reason}"
        
    assert t1_found, "Test 1 was not completed"
    assert t2_found, "Test 2 was not completed"
    print("✓ All overlay system tests PASSED successfully!")

  GLib.idle_add(run_test_1)
  
  loop = GLib.MainLoop()
  
  original_exit = exit_test
  def exit_patched():
    try:
      original_exit()
    finally:
      loop.quit()
      
  globals()['exit_test'] = exit_patched
  loop.run()

if __name__ == '__main__':
  try:
    run_overlay_tests()
  except Exception as e:
    print(f"❌ TEST FAILED: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
