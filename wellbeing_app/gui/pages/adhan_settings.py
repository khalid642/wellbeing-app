import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

import os
import logging
from wellbeing_app.storage.database import get_connection
from wellbeing_app.audio.engine import AudioEngine

logger = logging.getLogger(__name__)

PRAYERS = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']

class AdhanSettingsPage(Gtk.ScrolledWindow):

  def __init__(self):
    super().__init__()
    self.set_propagate_natural_width(True)
    self.set_propagate_natural_height(False)
    
    self.audio_engine = AudioEngine()
    self._is_playing_prayer = None
    
    self._build_ui()
    self._load_settings()

  def _build_ui(self):
    self.inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    self.inner.set_margin_top(24)
    self.inner.set_margin_bottom(24)
    self.inner.set_margin_start(24)
    self.inner.set_margin_end(24)
    self.set_child(self.inner)
    
    pref_group = Adw.PreferencesGroup(
      title='Adhan Settings',
      description='Configure audio, volume, and trigger offsets for each prayer calling.'
    )
    self.inner.append(pref_group)
    
    self.expanders = {}
    self.toggles = {}
    self.spins = {}
    self.file_labels = {}
    self.scales = {}
    self.test_buttons = {}
    
    for prayer in PRAYERS:
      expander = Adw.ExpanderRow()
      expander.set_title(prayer.capitalize())
      pref_group.add(expander)
      self.expanders[prayer] = expander
      
      # 1. Enable Toggle
      row_toggle = Adw.ActionRow(title='Enable Adhan')
      toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
      toggle.connect('notify::active', self._on_toggle, prayer)
      row_toggle.add_suffix(toggle)
      row_toggle.set_activatable_widget(toggle)
      expander.add_row(row_toggle)
      self.toggles[prayer] = toggle
      
      # 2. Delay
      row_delay = Adw.ActionRow(
        title='Delay',
        subtitle='Minutes after prayer time'
      )
      spin = Gtk.SpinButton.new_with_range(0, 60, 1)
      spin.set_valign(Gtk.Align.CENTER)
      spin.connect('value-changed', self._on_delay, prayer)
      row_delay.add_suffix(spin)
      expander.add_row(row_delay)
      self.spins[prayer] = spin
      
      # 3. Audio File
      row_audio = Adw.ActionRow(title='Audio File')
      file_label = Gtk.Label(label='Default')
      file_label.add_css_class('dim-label')
      file_label.set_valign(Gtk.Align.CENTER)
      
      browse_btn = Gtk.Button(label='Browse')
      browse_btn.add_css_class('flat')
      browse_btn.set_valign(Gtk.Align.CENTER)
      browse_btn.connect('clicked', self._on_browse, prayer)
      
      row_audio.add_suffix(file_label)
      row_audio.add_suffix(browse_btn)
      expander.add_row(row_audio)
      self.file_labels[prayer] = file_label
      
      # 4. Volume
      row_volume = Adw.ActionRow(title='Volume')
      scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
      scale.set_hexpand(True)
      scale.set_size_request(150, -1)
      scale.set_valign(Gtk.Align.CENTER)
      scale.connect('value-changed', self._on_volume, prayer)
      row_volume.add_suffix(scale)
      expander.add_row(row_volume)
      self.scales[prayer] = scale
      
      # 5. Test button
      row_test = Adw.ActionRow(title='Test Adhan')
      test_btn = Gtk.Button(label='Play Now')
      test_btn.add_css_class('flat')
      test_btn.set_valign(Gtk.Align.CENTER)
      test_btn.connect('clicked', self._on_test, prayer)
      row_test.add_suffix(test_btn)
      expander.add_row(row_test)
      self.test_buttons[prayer] = test_btn

  def _load_settings(self):
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT prayer, audio_file, delay_seconds, volume, enabled FROM adhan_config")
      for row in cursor.fetchall():
        prayer, audio_file, delay_secs, volume, enabled = row
        if prayer in self.expanders:
          self.toggles[prayer].set_active(enabled == 1)
          self.spins[prayer].set_value(delay_secs // 60)
          self.file_labels[prayer].set_label(os.path.basename(audio_file) if audio_file else 'Default')
          self.scales[prayer].set_value(int(volume * 100))

  def _on_toggle(self, switch, pspec, prayer):
    active = 1 if switch.get_active() else 0
    with get_connection() as conn:
      conn.execute("UPDATE adhan_config SET enabled = ? WHERE prayer = ?", (active, prayer))
      conn.commit()
    logger.info(f"Updated enable toggle for {prayer}: {active == 1}")

  def _on_delay(self, spin, prayer):
    delay_secs = int(spin.get_value()) * 60
    with get_connection() as conn:
      conn.execute("UPDATE adhan_config SET delay_seconds = ? WHERE prayer = ?", (delay_secs, prayer))
      conn.commit()
    logger.info(f"Updated delay seconds for {prayer}: {delay_secs}")

  def _on_volume(self, scale, prayer):
    volume = float(scale.get_value() / 100.0)
    with get_connection() as conn:
      conn.execute("UPDATE adhan_config SET volume = ? WHERE prayer = ?", (volume, prayer))
      conn.commit()
    if self._is_playing_prayer == prayer:
      self.audio_engine.set_volume('adhan', volume)
    logger.info(f"Updated volume for {prayer}: {volume:.2f}")

  def _on_browse(self, btn, prayer):
    dialog = Gtk.FileDialog.new()
    dialog.set_title('Select Adhan Audio')
    
    filter_ = Gtk.FileFilter()
    filter_.set_name('Audio Files')
    filter_.add_mime_type('audio/mpeg')
    filter_.add_mime_type('audio/ogg')
    filter_.add_mime_type('audio/wav')
    
    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_)
    dialog.set_filters(filters)
    
    # Open FileDialog
    dialog.open(self.get_root(), None, self._on_file_chosen, prayer)

  def _on_file_chosen(self, dialog, result, prayer):
    try:
      file = dialog.open_finish(result)
      path = file.get_path()
      basename = os.path.basename(path)
      
      self.file_labels[prayer].set_label(basename)
      
      with get_connection() as conn:
        conn.execute("UPDATE adhan_config SET audio_file = ? WHERE prayer = ?", (path, prayer))
        conn.commit()
      logger.info(f"Saved custom audio path for {prayer}: {path}")
    except GLib.Error as e:
      logger.info(f"File browsing dismissed or failed: {e}")

  def _on_test(self, btn, prayer):
    if self._is_playing_prayer == prayer:
      # Stop playback
      self.audio_engine.stop_all(fade_out_seconds=0.5)
      self._is_playing_prayer = None
      btn.set_label('Play Now')
      return

    # Stop any running adhan tests first
    self.audio_engine.stop_all(fade_out_seconds=0.1)
    
    # Revert label of previous playing button
    if self._is_playing_prayer and self._is_playing_prayer in self.test_buttons:
      self.test_buttons[self._is_playing_prayer].set_label('Play Now')
      
    # Load audio path & volume
    audio_path = None
    volume = 0.8
    with get_connection() as conn:
      row = conn.execute("SELECT audio_file, volume FROM adhan_config WHERE prayer = ?", (prayer,)).fetchone()
      if row:
        audio_path, volume = row
        
    if not audio_path:
      # Use test tone sine
      audio_path = "sine"
      
    logger.info(f"Testing adhan playback for {prayer} using {audio_path} at volume {volume}")
    self.audio_engine.play_adhan(audio_path, volume=volume, fade_in_seconds=0.5)
    
    self._is_playing_prayer = prayer
    btn.set_label('Stop')
    
    # Watchbus to check when playback is finished
    GLib.timeout_add(500, self._check_playback_finished, prayer, btn)

  def _check_playback_finished(self, prayer, btn):
    if self._is_playing_prayer != prayer:
      return False
      
    if not self.audio_engine.is_playing('adhan'):
      btn.set_label('Play Now')
      if self._is_playing_prayer == prayer:
        self._is_playing_prayer = None
      return False
      
    return True
