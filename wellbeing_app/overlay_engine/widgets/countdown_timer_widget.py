import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import cairo
import math
import time

class CountdownTimerWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.CENTER)
    
    self.duration_seconds = 20
    self.show_ring = True
    self.font_size = 32
    
    self.remaining_seconds = 20
    self.start_time = 0.0
    self._timer_id = None
    
    # Drawing area for the ring
    self.drawing_area = Gtk.DrawingArea()
    self.drawing_area.set_content_width(200)
    self.drawing_area.set_content_height(200)
    self.drawing_area.set_draw_func(self._on_draw)
    self.append(self.drawing_area)

  def load_config(self, config: dict):
    self.duration_seconds = config.get('duration_seconds', 20)
    self.show_ring = config.get('show_ring', True)
    self.font_size = config.get('font_size', 32)
    self.remaining_seconds = self.duration_seconds
    self.drawing_area.queue_draw()

  def start_countdown(self, seconds: int):
    self.duration_seconds = seconds
    self.remaining_seconds = seconds
    self.start_animations()

  def _on_draw(self, drawing_area, cr, width, height):
    cx = width / 2.0
    cy = height / 2.0
    radius = min(width, height) / 2.0 - 15
    
    # 1. Draw circular ring if enabled
    if self.show_ring:
      # Draw elapsed background arc (full circle, dim white)
      cr.set_source_rgba(255/255.0, 255/255.0, 255/255.0, 0.15)
      cr.set_line_width(6)
      cr.arc(cx, cy, radius, 0, 2 * math.pi)
      cr.stroke()
      
      # Draw remaining arc (shrinks from top: -pi/2)
      ratio = 0.0
      if self.duration_seconds > 0:
        ratio = max(0.0, min(1.0, float(self.remaining_seconds) / float(self.duration_seconds)))
        
      if ratio > 0:
        cr.set_source_rgba(255/255.0, 255/255.0, 255/255.0, 0.70)
        cr.set_line_width(8)
        # Start angle is -pi/2 (top), end angle goes clockwise
        start_angle = -math.pi / 2.0
        end_angle = start_angle + (2 * math.pi * ratio)
        cr.arc(cx, cy, radius, start_angle, end_angle)
        cr.stroke()
        
    # 2. Draw MM:SS text in center
    mins, secs = divmod(max(0, int(self.remaining_seconds)), 60)
    time_str = f"{mins:02d}:{secs:02d}"
    
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(self.font_size)
    
    extents = cr.text_extents(time_str)
    tx = cx - (extents.width / 2.0 + extents.x_bearing)
    ty = cy - (extents.height / 2.0 + extents.y_bearing)
    cr.move_to(tx, ty)
    cr.show_text(time_str)

  def start_animations(self):
    self.stop_animations()
    self.start_time = time.time()
    
    def tick():
      elapsed = time.time() - self.start_time
      self.remaining_seconds = max(0.0, float(self.duration_seconds) - elapsed)
      self.drawing_area.queue_draw()
      
      if self.remaining_seconds <= 0:
        self._timer_id = None
        return False
      return True
      
    # Smooth progress: redraw every 100ms for continuous ring animation
    self._timer_id = GLib.timeout_add(100, tick)

  def stop_animations(self):
    if self._timer_id:
      try:
        GLib.source_remove(self._timer_id)
      except Exception:
        pass
      self._timer_id = None
