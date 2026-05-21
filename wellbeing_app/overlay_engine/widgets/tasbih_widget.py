import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

class TasbihWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.CENTER)
    
    self.target = 33
    self.dhikr_text = 'سبحان الله'
    self.size = 'large'
    self.count = 0
    
    # 1. Dhikr text label (centered top)
    self.dhikr_label = Gtk.Label()
    self.dhikr_label.set_halign(Gtk.Align.CENTER)
    self.append(self.dhikr_label)
    
    # 2. Large count display
    self.count_label = Gtk.Label()
    self.count_label.set_halign(Gtk.Align.CENTER)
    self.append(self.count_label)
    
    # 3. Target label below count
    self.target_label = Gtk.Label()
    self.target_label.set_halign(Gtk.Align.CENTER)
    self.append(self.target_label)
    
    # 4. Small reset button centered or bottom right
    self.reset_button = Gtk.Button(label="Reset")
    self.reset_button.set_halign(Gtk.Align.END)
    self.reset_button.add_css_class("flat")
    self.reset_button.connect("clicked", self._on_reset_clicked)
    self.append(self.reset_button)
    
    # Event controllers
    # Click anywhere on the box to increment
    click_gesture = Gtk.GestureClick.new()
    click_gesture.connect("pressed", self._on_box_clicked)
    self.add_controller(click_gesture)
    
    # Keypress anywhere to increment
    key_controller = Gtk.EventControllerKey.new()
    key_controller.connect("key-pressed", self._on_key_pressed)
    self.add_controller(key_controller)
    
    # Ensure widget can receive keyboard focus
    self.set_focusable(True)
    self.grab_focus()

  def load_config(self, config: dict):
    self.target = config.get('target', 33)
    self.dhikr_text = config.get('dhikr_text', 'سبحان الله')
    self.size = config.get('size', 'large')
    self.count = 0
    self._update_ui()

  def _update_ui(self):
    # Render Arabic text
    self.dhikr_label.set_markup(f'<span font_size="28000" foreground="#50c8b4" weight="bold">{self.dhikr_text}</span>')
    
    # Render Large Counter
    font_size_px = 72 if self.size == 'large' else (48 if self.size == 'medium' else 32)
    self.count_label.set_markup(f'<span font_size="{font_size_px * 1024}" foreground="#ffffff" weight="bold">{self.count}</span>')
    
    # Render target offset
    self.target_label.set_markup(f'<span font_size="16000" foreground="#aaaaaa">/ {self.target}</span>')

  def increment(self):
    self.count += 1
    self._update_ui()
    
    # Flash green on target reached
    if self.count == self.target:
      self._flash_success()

  def _flash_success(self):
    # Briefly add a class or update markup to bright green
    self.count_label.set_markup(f'<span font_size="72000" foreground="#34c759" weight="bold">{self.count}</span>')
    # Play click sound or mock action
    print("[TASBIH] Target reached!")
    
    # Revert to normal style in 1 second
    GLib.timeout_add_seconds(1, lambda: self._update_ui() or False)

  def _on_box_clicked(self, gesture, n_press, x, y):
    # Only increment if reset button was NOT clicked directly
    self.increment()

  def _on_key_pressed(self, controller, keyval, keycode, state):
    # Any key increments (except Escape or Tab to avoid interfering with general overlay closure)
    if keyval not in [Gdk.KEY_Escape, Gdk.KEY_Tab]:
      self.increment()
      return True
    return False

  def _on_reset_clicked(self, button):
    self.count = 0
    self._update_ui()

  def start_animations(self):
    pass

  def stop_animations(self):
    pass
