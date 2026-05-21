import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import time
import logging

logger = logging.getLogger(__name__)

# Initialize GStreamer
Gst.init(None)

class GstPlayer:

  def __init__(self, uri_or_test: str, is_test_tone: bool = False, loop: bool = False):
    self.uri_or_test = uri_or_test
    self.is_test_tone = is_test_tone
    self.loop = loop
    self._fade_timer_id = None
    
    if is_test_tone:
      # Parse GStreamer pipeline for test tone
      self.pipeline = Gst.parse_launch("audiotestsrc freq=440 ! volume name=vol ! autoaudiosink")
      self.vol_elem = self.pipeline.get_by_name("vol")
    else:
      self.pipeline = Gst.ElementFactory.make("playbin", None)
      self.pipeline.set_property("uri", uri_or_test)
      self.vol_elem = self.pipeline
      
    # Listen on bus for EOS
    bus = self.pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", self._on_message)

  def _on_message(self, bus, message):
    if message.type == Gst.MessageType.EOS:
      if self.loop:
        # Seek back to start for looping
        success = self.pipeline.seek_simple(
          Gst.Format.TIME,
          Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
          0
        )
        if not success:
          # Fallback if seek fails
          self.pipeline.set_state(Gst.State.NULL)
          self.pipeline.set_state(Gst.State.PLAYING)
      else:
        self.pipeline.set_state(Gst.State.NULL)

  def set_volume(self, volume: float):
    if self.vol_elem:
      self.vol_elem.set_property("volume", max(0.0, min(1.0, volume)))

  def get_volume(self) -> float:
    if self.vol_elem:
      return self.vol_elem.get_property("volume")
    return 1.0

  def play(self):
    self.pipeline.set_state(Gst.State.PLAYING)

  def stop(self):
    self._clear_fade_timer()
    self.pipeline.set_state(Gst.State.NULL)

  def is_playing(self) -> bool:
    success, state, pending = self.pipeline.get_state(0)
    return success == Gst.StateChangeReturn.SUCCESS and state == Gst.State.PLAYING

  def _clear_fade_timer(self):
    if self._fade_timer_id:
      try:
        GLib.source_remove(self._fade_timer_id)
      except Exception:
        pass
      self._fade_timer_id = None

  def fade_in(self, target_volume: float, duration_seconds: float):
    self._clear_fade_timer()
    self.set_volume(0.0)
    self.play()
    
    if duration_seconds <= 0:
      self.set_volume(target_volume)
      return
      
    start_time = time.time()
    
    def on_tick():
      elapsed = time.time() - start_time
      if elapsed >= duration_seconds:
        self.set_volume(target_volume)
        self._fade_timer_id = None
        return False
      self.set_volume(target_volume * (elapsed / duration_seconds))
      return True
      
    self._fade_timer_id = GLib.timeout_add(50, on_tick)

  def fade_out(self, duration_seconds: float, callback=None):
    self._clear_fade_timer()
    initial_volume = self.get_volume()
    
    if duration_seconds <= 0:
      self.stop()
      if callback:
        callback()
      return
      
    start_time = time.time()
    
    def on_tick():
      elapsed = time.time() - start_time
      if elapsed >= duration_seconds:
        self.stop()
        self._fade_timer_id = None
        if callback:
          callback()
        return False
      self.set_volume(initial_volume * (1.0 - (elapsed / duration_seconds)))
      return True
      
    self._fade_timer_id = GLib.timeout_add(50, on_tick)


class AudioEngine:

  def __init__(self):
    self._adhan_player = None
    self._iqamah_player = None
    self._ambient_players = {}

  def play_adhan(self, audio_file: str, volume: float = 1.0, fade_in_seconds: float = 1.5):
    if self._adhan_player:
      self._adhan_player.stop()
      self._adhan_player = None
      
    is_test = (audio_file == "sine")
    uri = audio_file if is_test else self._to_uri(audio_file)
    
    self._adhan_player = GstPlayer(uri, is_test_tone=is_test, loop=False)
    self._adhan_player.fade_in(volume, fade_in_seconds)

  def play_iqamah(self, audio_file: str, volume: float = 1.0):
    if self._iqamah_player:
      self._iqamah_player.stop()
      self._iqamah_player = None
      
    is_test = (audio_file == "sine")
    uri = audio_file if is_test else self._to_uri(audio_file)
    
    self._iqamah_player = GstPlayer(uri, is_test_tone=is_test, loop=False)
    self._iqamah_player.play()
    self._iqamah_player.set_volume(volume)

  def play_ambient(self, audio_file: str, loop: bool = True, volume: float = 0.4):
    if audio_file in self._ambient_players:
      self._ambient_players[audio_file].stop()
      del self._ambient_players[audio_file]
      
    is_test = (audio_file == "sine")
    uri = audio_file if is_test else self._to_uri(audio_file)
    
    player = GstPlayer(uri, is_test_tone=is_test, loop=loop)
    player.play()
    player.set_volume(volume)
    self._ambient_players[audio_file] = player

  def stop_all(self, fade_out_seconds: float = 1.5):
    if self._adhan_player:
      self._adhan_player.fade_out(fade_out_seconds, lambda: setattr(self, '_adhan_player', None))
    if self._iqamah_player:
      self._iqamah_player.fade_out(fade_out_seconds, lambda: setattr(self, '_iqamah_player', None))
      
    for path, player in list(self._ambient_players.items()):
      def make_stop_cb(p_path):
        return lambda: self._ambient_players.pop(p_path, None)
      player.fade_out(fade_out_seconds, make_stop_cb(path))

  def set_volume(self, channel: str, volume: float):
    if channel == 'adhan':
      if self._adhan_player:
        self._adhan_player.set_volume(volume)
    elif channel == 'iqamah':
      if self._iqamah_player:
        self._iqamah_player.set_volume(volume)
    elif channel == 'ambient':
      for player in self._ambient_players.values():
        player.set_volume(volume)

  def is_playing(self, channel: str) -> bool:
    if channel == 'adhan':
      return self._adhan_player is not None and self._adhan_player.is_playing()
    elif channel == 'iqamah':
      return self._iqamah_player is not None and self._iqamah_player.is_playing()
    elif channel == 'ambient':
      return any(player.is_playing() for player in self._ambient_players.values())
    return False

  def _to_uri(self, path: str) -> str:
    if path.startswith("file://") or path.startswith("http://") or path.startswith("https://"):
      return path
    return "file://" + os.path.abspath(path)
