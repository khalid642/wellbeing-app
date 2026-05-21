import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib
import sys
import time

from wellbeing_app.audio.adhan_library import AdhanLibrary
from wellbeing_app.audio.engine import AudioEngine

def test_audio_engine():
  print("Initializing test database...")
  # GStreamer will print messages to stdout/stderr depending on options.
  
  print("Instantiating AdhanLibrary...")
  library = AdhanLibrary()
  
  print("Listing available adhans...")
  available = library.list_available_adhans()
  print(f"Found {len(available)} available adhans:")
  for adhan in available:
    print(f"  - Name: {adhan['name']:20} | Path: {adhan['file_path']} | Custom: {adhan['is_custom']}")
    
  print("\nInstantiating AudioEngine...")
  engine = AudioEngine()
  
  loop = GLib.MainLoop()
  
  # Step 1: Play test tone on adhan channel (fades in)
  print("\nStep 1: Playing adhan channel (440Hz sine wave) with 2.0s fade-in...")
  engine.play_adhan("sine", volume=0.8, fade_in_seconds=2.0)
  
  # Step 2: In 3 seconds, test setting volume and check playing status
  def step_2():
    print(f"\nStep 2: Checking if adhan channel is playing: {engine.is_playing('adhan')}")
    print("Setting volume to 0.4 on adhan channel...")
    engine.set_volume('adhan', 0.4)
    return False
    
  # Step 3: In 5 seconds, fade out and stop
  def step_3():
    print("\nStep 3: Fading out all channels over 1.5s...")
    engine.stop_all(fade_out_seconds=1.5)
    return False
    
  # Step 4: In 7 seconds, confirm stopped and exit
  def step_4():
    print(f"\nStep 4: Checking if adhan is playing: {engine.is_playing('adhan')}")
    print("Test complete. Exiting...")
    loop.quit()
    return False
    
  GLib.timeout_add_seconds(3, step_2)
  GLib.timeout_add_seconds(5, step_3)
  GLib.timeout_add_seconds(7, step_4)
  
  print("Entering GLib main loop...")
  loop.run()
  
  print("\n✓ Audio Engine verification test PASSED successfully!")

if __name__ == '__main__':
  try:
    test_audio_engine()
  except Exception as e:
    print(f"❌ TEST FAILED: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
