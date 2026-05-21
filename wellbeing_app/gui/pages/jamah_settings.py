import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from wellbeing_app.prayer.jamah import JamahStore
import re

class JamahSettingsPage(Gtk.ScrolledWindow):
  def __init__(self):
    super().__init__()
    self.set_propagate_natural_width(True)
    self.set_propagate_natural_height(False)
    
    self.jamah_store = JamahStore()
    self._time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
    
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    inner.set_margin_top(24)
    inner.set_margin_bottom(24)
    inner.set_margin_start(24)
    inner.set_margin_end(24)
    self.set_child(inner)

    # Group 1: Iqamah
    iqamah_group = Adw.PreferencesGroup(title='Iqamah')
    
    iqamah_row = Adw.ActionRow(
      title='Iqamah Offset',
      subtitle='Minutes before Jamah that iqamah audio plays'
    )
    
    spin = Gtk.SpinButton.new_with_range(1, 30, 1)
    spin.set_value(self.jamah_store.get_iqamah_offset())
    spin.set_valign(Gtk.Align.CENTER)
    spin.connect('value-changed', self._on_spin_changed)
    iqamah_row.add_suffix(spin)
    
    iqamah_group.add(iqamah_row)
    inner.append(iqamah_group)
    
    # Caption Label below Group 1
    caption_label = Gtk.Label(
      label='Iqamah time is not shown in the app. It triggers the lock screen internally.'
    )
    caption_label.add_css_class('caption')
    caption_label.add_css_class('dim-label')
    caption_label.set_wrap(True)
    caption_label.set_xalign(0.0)
    caption_label.set_margin_start(12)
    caption_label.set_margin_top(4)
    inner.append(caption_label)
    
    # Spacer
    spacer = Gtk.Box()
    spacer.set_margin_top(8)
    inner.append(spacer)
    
    # Group 2: Jamah Times
    jamah_group = Adw.PreferencesGroup(title='Jamah Times')
    
    for prayer_name in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
      prayer_key = prayer_name.lower()
      
      row = Adw.ActionRow(title=prayer_name)
      
      time_entry = Gtk.Entry()
      time_entry.set_placeholder_text('HH:MM')
      time_entry.set_max_length(5)
      time_entry.set_width_chars(6)
      time_entry.set_valign(Gtk.Align.CENTER)
      
      val = self.jamah_store.get_jamah_time(prayer_key)
      if val:
        time_entry.set_text(val)
        
      time_entry.connect('changed', self._on_time_changed, prayer_key)
      
      clear_btn = Gtk.Button()
      clear_btn.set_icon_name('edit-clear-symbolic')
      clear_btn.add_css_class('flat')
      clear_btn.set_valign(Gtk.Align.CENTER)
      clear_btn.set_tooltip_text('Clear jamah time')
      clear_btn.connect('clicked', self._on_clear, prayer_key, time_entry)
      
      toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
      toggle.set_active(self.jamah_store.is_enabled(prayer_key))
      toggle.connect('notify::active', self._on_enabled_changed, prayer_key)
      
      row.add_suffix(time_entry)
      row.add_suffix(clear_btn)
      row.add_suffix(toggle)
      
      jamah_group.add(row)
      
    inner.append(jamah_group)

  def _on_spin_changed(self, spin):
    val = int(spin.get_value())
    self.jamah_store.set_iqamah_offset(val)

  def _on_time_changed(self, entry, prayer_key):
    new_text = entry.get_text()
    if self._time_pattern.match(new_text):
      entry.remove_css_class('error')
      self.jamah_store.set_jamah_time(prayer_key, new_text)
    else:
      entry.add_css_class('error')

  def _on_clear(self, button, prayer_key, time_entry):
    self.jamah_store.clear_jamah_time(prayer_key)
    time_entry.set_text('')
    time_entry.remove_css_class('error')

  def _on_enabled_changed(self, toggle, pspec, prayer_key):
    active = toggle.get_active()
    if active:
      self.jamah_store.enable(prayer_key)
    else:
      self.jamah_store.disable(prayer_key)
