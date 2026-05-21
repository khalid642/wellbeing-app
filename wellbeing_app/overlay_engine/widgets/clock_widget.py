import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import time

class ClockWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL)
    self.label = Gtk.Label()
    self.label.set_halign(Gtk.Align.CENTER)
    self.label.set_valign(Gtk.Align.CENTER)
    self.append(self.label)
    
    self._timer_id = None
    self.show_seconds = True
    self.format_24h = True
    self.font_size = 48

  def load_config(self, config: dict):
    self.show_seconds = config.get('show_seconds', True)
    self.format_24h = config.get('format_24h', True)
    self.font_size = config.get('font_size', 48)
    self._update_time()

  def _update_time(self):
    fmt = ""
    if self.format_24h:
      fmt = "%H:%M:%S" if self.show_seconds else "%H:%M"
    else:
      fmt = "%I:%M:%S %p" if self.show_seconds else "%I:%M %p"
      
    current_time_str = time.strftime(fmt)
    markup = f'<span font_size="{self.font_size * 1024}" foreground="#ffffff" weight="bold">{current_time_str}</span>'
    self.label.set_markup(markup)

  def start_animations(self):
    self.stop_animations()
    self._update_time()
    
    def tick():
      self._update_time()
      return True
      
    self._timer_id = GLib.timeout_add_seconds(1, tick)

  def stop_animations(self):
    if self._timer_id:
      try:
        GLib.source_remove(self._timer_id)
      except Exception:
        pass
      self._timer_id = None
