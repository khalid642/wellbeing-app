import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import cairo
import math
import time

class BreathingWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.CENTER)
    
    # Custom config defaults
    self.mode = 'box'
    self.inhale_seconds = 4
    self.hold_seconds = 4
    self.exhale_seconds = 4
    self.hold_post_seconds = 4 # for box breathing hold-after-exhale
    
    # Internal animation state
    self._timer_id = None
    self._start_time = 0.0
    self._current_phase = "Breathe in"
    self._phase_remaining = 4.0
    self._animation_progress = 0.0 # 0.0 to 1.0 representing inner circle size ratio
    
    # Cairo Drawing Area
    self.drawing_area = Gtk.DrawingArea()
    self.drawing_area.set_content_width(300)
    self.drawing_area.set_content_height(300)
    self.drawing_area.set_draw_func(self._on_draw)
    self.append(self.drawing_area)
    
    # Phase countdown label placed below circle
    self.countdown_label = Gtk.Label()
    self.countdown_label.set_markup('<span font_size="18000" foreground="#ffffff">Ready</span>')
    self.append(self.countdown_label)

  def load_config(self, config: dict):
    self.mode = config.get('mode', 'box')
    if self.mode == '4-7-8':
      self.inhale_seconds = config.get('inhale_seconds', 4)
      self.hold_seconds = config.get('hold_seconds', 7)
      self.exhale_seconds = config.get('exhale_seconds', 8)
      self.hold_post_seconds = 0
    else: # 'box'
      self.inhale_seconds = config.get('inhale_seconds', 4)
      self.hold_seconds = config.get('hold_seconds', 4)
      self.exhale_seconds = config.get('exhale_seconds', 4)
      self.hold_post_seconds = config.get('hold_post_seconds', 4)
      
    self._reset_state()

  def _reset_state(self):
    self._start_time = time.time()
    self._current_phase = "Breathe in"
    self._phase_remaining = float(self.inhale_seconds)
    self._animation_progress = 0.0
    self.drawing_area.queue_draw()

  def _on_draw(self, drawing_area, cr, width, height):
    # Draw background blur or black transparent circle
    cx = width / 2.0
    cy = height / 2.0
    outer_radius = min(width, height) / 2.0 - 20
    
    # Pulse outer ring opacity dynamically
    pulse = 0.4 + 0.2 * math.sin(time.time() * 2.0 * math.pi / 4.0)
    
    # Draw outer ring (soft teal: rgba(80, 200, 180, pulse))
    cr.set_source_rgba(80/255.0, 200/255.0, 180/255.0, pulse)
    cr.set_line_width(4)
    cr.arc(cx, cy, outer_radius, 0, 2 * math.pi)
    cr.stroke()
    
    # Draw inner circle (solid breathing volume)
    # Target scale ranges from 0.15 (contracted) to 1.0 (expanded) of outer_radius
    current_radius = outer_radius * (0.2 + 0.75 * self._animation_progress)
    cr.set_source_rgba(80/255.0, 200/255.0, 180/255.0, 0.45)
    cr.arc(cx, cy, current_radius, 0, 2 * math.pi)
    cr.fill()
    
    # Draw center phase label text in drawing area
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(24)
    
    extents = cr.text_extents(self._current_phase)
    tx = cx - (extents.width / 2.0 + extents.x_bearing)
    ty = cy - (extents.height / 2.0 + extents.y_bearing)
    cr.move_to(tx, ty)
    cr.show_text(self._current_phase)

  def _tick(self):
    now = time.time()
    elapsed = now - self._start_time
    
    # Define phase lengths
    if self.mode == '4-7-8':
      phases = [
        ("Breathe in", float(self.inhale_seconds)),
        ("Hold", float(self.hold_seconds)),
        ("Breathe out", float(self.exhale_seconds))
      ]
    else: # 'box'
      phases = [
        ("Breathe in", float(self.inhale_seconds)),
        ("Hold", float(self.hold_seconds)),
        ("Breathe out", float(self.exhale_seconds)),
        ("Hold", float(self.hold_post_seconds))
      ]
      
    total_cycle = sum(p[1] for p in phases)
    cycle_time = elapsed % total_cycle
    
    # Find current phase & calculate parameters
    accumulated = 0.0
    for name, duration in phases:
      if cycle_time < accumulated + duration:
        self._current_phase = name
        phase_elapsed = cycle_time - accumulated
        self._phase_remaining = math.ceil(duration - phase_elapsed)
        
        # Calculate animation progression
        ratio = phase_elapsed / duration
        if name == "Breathe in":
          # Smooth ease-in-out expansion
          self._animation_progress = math.sin(ratio * math.pi / 2.0)
        elif name == "Breathe out":
          # Smooth ease-in-out contraction
          self._animation_progress = 1.0 - math.sin(ratio * math.pi / 2.0)
        elif name == "Hold":
          # Static size depending on whether it is post-inhale or post-exhale
          if phases.index((name, duration)) == 1:
            self._animation_progress = 1.0 # hold after inhale
          else:
            self._animation_progress = 0.0 # hold after exhale
        break
      accumulated += duration
      
    # Update countdown label below circle
    self.countdown_label.set_markup(f'<span font_size="18000" foreground="#ffffff" weight="bold">{int(self._phase_remaining)}s</span>')
    self.drawing_area.queue_draw()
    return True

  def start_animations(self):
    self.stop_animations()
    self._reset_state()
    # Tick at ~60fps (16ms interval)
    self._timer_id = GLib.timeout_add(16, self._tick)

  def stop_animations(self):
    if self._timer_id:
      try:
        GLib.source_remove(self._timer_id)
      except Exception:
        pass
      self._timer_id = None
