import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango
import html

class TextWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL)
    self.label = Gtk.Label()
    self.label.set_wrap(True)
    self.label.set_halign(Gtk.Align.CENTER)
    self.label.set_valign(Gtk.Align.CENTER)
    self.append(self.label)
    
  def load_config(self, config: dict):
    text = config.get('text', '')
    font_size = config.get('font_size', 18)
    align = config.get('align', 'center')
    bold = config.get('bold', False)
    color = config.get('color', '#ffffff')
    
    if align == 'left':
      self.label.set_xalign(0.0)
    elif align == 'right':
      self.label.set_xalign(1.0)
    else:
      self.label.set_xalign(0.5)
      
    bold_start = "<b>" if bold else ""
    bold_end = "</b>" if bold else ""
    
    escaped_text = html.escape(text)
    markup = f'<span font_size="{font_size * 1024}" foreground="{color}">{bold_start}{escaped_text}{bold_end}</span>'
    self.label.set_markup(markup)

  def start_animations(self):
    pass

  def stop_animations(self):
    pass
