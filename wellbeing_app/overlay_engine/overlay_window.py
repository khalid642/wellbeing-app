import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, GObject
from dataclasses import dataclass, field
import os
import time
import logging

from wellbeing_app.overlay_engine.widget_renderer import WidgetRenderer

logger = logging.getLogger(__name__)

@dataclass
class WidgetConfig:
  template_id: int
  widget_type: str
  config: dict
  display_order: int = 0

@dataclass
class OverlayConfig:
  mode: str                  # 'locked' or 'unlocked'
  duration_seconds: int      # lock duration or auto-close duration
  widgets: list              # list[WidgetConfig]
  overlay_id: str            # 'salah_lock', 'eyecare', 'zikr', 'reminder_{id}'
  background_blur: bool = True
  password: str | None = None
  auto_close: bool = False


class OverlayWindow(Gtk.Window):

  __gsignals__ = {
    'overlay-dismissed': (
      GObject.SignalFlags.RUN_FIRST,
      None,
      (str,)
    )
  }

  def __init__(self, config: OverlayConfig):
    super().__init__()
    self.config = config
    
    self.remaining_seconds = config.duration_seconds
    self.phase_2_auto_close_id = None
    self.countdown_timer_id = None
    self.auto_close_timer_id = None
    self.safety_watchdog_id = None
    
    self.set_decorated(False)
    self._setup_style()
    self._setup_layout()
    self._setup_layer()
    self.load_widgets()
    self._setup_events()
    
    if self.config.mode == 'locked':
      self.set_cursor_from_name("none")
    
    # 20-second safety fallback watchdog to prevent accidental lockouts during development
    if os.environ.get('WELLBEING_TEST_MODE') != '1':
      self.safety_watchdog_id = GLib.timeout_add_seconds(20, self._safety_watchdog_trigger)
    
    self.connect("realize", self._on_realize)
    
    # Start fade-in animation
    self._fade_in()

  def _setup_style(self):
    self.add_css_class("overlay-window")
    self.css_provider = Gtk.CssProvider()
    css = """
    .overlay-window {
        background-color: rgba(0, 0, 0, 0.72);
    }
    .overlay-window .overlay-card {
        background-color: rgba(255, 255, 255, 0.08);
        border-style: solid;
        border-width: 1px;
        border-color: rgba(255, 255, 255, 0.18);
        border-radius: 24px;
        padding: 32px;
    }
    .overlay-window .error {
        border-style: solid;
        border-width: 1px;
        border-color: #ff3b30;
    }
    .overlay-window .timer-label {
        font-size: 48px;
        font-weight: bold;
        color: #ffffff;
    }
    .overlay-window .continue-label {
        font-size: 24px;
        color: rgba(255, 255, 255, 0.8);
    }
    .overlay-window .title-1 {
        font-size: 32px;
        font-weight: bold;
        color: #ffffff;
    }
    .overlay-window .title-lg {
        font-size: 64px;
        font-weight: bold;
        color: #ffffff;
    }
    """
    self.css_provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_display(
      Gdk.Display.get_default(),
      self.css_provider,
      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

  def _setup_layout(self):
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    main_box.set_halign(Gtk.Align.CENTER)
    main_box.set_valign(Gtk.Align.CENTER)
    
    self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    self.card.add_css_class("overlay-card")
    
    main_box.append(self.card)
    self.set_child(main_box)

  def _setup_layer(self):
    wayland = os.environ.get('WAYLAND_DISPLAY') is not None
    if wayland:
      try:
        gi.require_version('GtkLayerShell', '0.1')
        from gi.repository import GtkLayerShell
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        
        # Grab keyboard exclusively for both locked and unlocked modes
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
          
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
      except Exception as e:
        logger.warning(f"Failed to initialize GtkLayerShell: {e}. Falling back to standard fullscreen.")
        self.fullscreen()
    else:
      self.fullscreen()

  def _setup_events(self):
    controller = Gtk.EventControllerKey.new()
    controller.connect("key-pressed", self._on_key_pressed)
    self.add_controller(controller)

  def _on_realize(self, widget):
    self.xdisplay = None
    logger.info(f"Overlay is in {self.config.mode} mode. Performing strict X11 input grab for both pointer and keyboard.")
    GLib.timeout_add(100, self._perform_grab)

  def _perform_grab(self):
    native = self.get_native()
    if native:
      surface = native.get_surface()
      if surface:
        try:
          gi.require_version('GdkX11', '4.0')
          from gi.repository import GdkX11
          if isinstance(surface, GdkX11.X11Surface):
            xid = surface.get_xid()
            import ctypes
            libX11 = ctypes.cdll.LoadLibrary("libX11.so.6")
            
            libX11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            libX11.XOpenDisplay.restype = ctypes.c_void_p
            libX11.XGrabKeyboard.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
            libX11.XGrabKeyboard.restype = ctypes.c_int
            libX11.XGrabPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            libX11.XGrabPointer.restype = ctypes.c_int
            libX11.XFlush.argtypes = [ctypes.c_void_p]
            libX11.XFlush.restype = ctypes.c_int
            
            self.xdisplay = libX11.XOpenDisplay(None)
            if self.xdisplay:
              k_status = libX11.XGrabKeyboard(self.xdisplay, xid, True, 1, 1, 0)
              # event_mask = motion + click + release = 76
              p_status = libX11.XGrabPointer(self.xdisplay, xid, True, 76, 1, 1, 0, 0, 0)
              libX11.XFlush(self.xdisplay)
              logger.info(f"Strict X11 input grab completed: Keyboard={k_status}, Pointer={p_status}")
            else:
              logger.warning("Could not open X11 Display pointer.")
        except Exception as e:
          logger.error(f"Failed to perform strict X11 grabs: {e}")
    return False

  def _safety_watchdog_trigger(self):
    logger.warning("SAFETY WATCHDOG TIMEOUT: Releasing grabs and dismissing overlay to prevent lockouts.")
    self._release_grab()
    self._dismiss('safety_watchdog')
    return False

  def _release_grab(self):
    if hasattr(self, 'xdisplay') and self.xdisplay:
      try:
        import ctypes
        libX11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        libX11.XUngrabKeyboard.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        libX11.XUngrabPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        libX11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        
        libX11.XUngrabKeyboard(self.xdisplay, 0)
        libX11.XUngrabPointer(self.xdisplay, 0)
        libX11.XCloseDisplay(self.xdisplay)
        self.xdisplay = None
        logger.info("Successfully released strict X11 keyboard and pointer grabs")
      except Exception as e:
        logger.error(f"Error releasing strict X11 grab: {e}")

  def load_widgets(self):
    self.loaded_widgets = []
    # Load all configured widgets
    for wc in self.config.widgets:
      widget = WidgetRenderer.create_widget(wc)
      if widget:
        self.card.append(widget)
        self.loaded_widgets.append(widget)
        
    # Locked mode countdown structures
    self.countdown_label = Gtk.Label()
    self.countdown_label.add_css_class("timer-label")
    self.countdown_label.set_halign(Gtk.Align.CENTER)
    self.card.append(self.countdown_label)
    
    self.continue_label = Gtk.Label()
    self.continue_label.add_css_class("continue-label")
    self.continue_label.set_halign(Gtk.Align.CENTER)
    self.card.append(self.continue_label)
    
    if self.config.mode == 'locked':
      self._update_countdown_ui()
      
      # Add password / PIN field if set
      if self.config.password is not None:
        self.pin_entry = Gtk.Entry()
        self.pin_entry.set_placeholder_text("Enter PIN to Bypass")
        self.pin_entry.set_visibility(False)
        self.pin_entry.set_halign(Gtk.Align.CENTER)
        self.pin_entry.set_width_chars(12)
        self.pin_entry.connect("activate", lambda e: self._check_password())
        self.card.append(self.pin_entry)
        
      if self.remaining_seconds > 0:
        self.countdown_timer_id = GLib.timeout_add_seconds(1, self._on_countdown_tick)
      else:
        self._enter_phase_2()
    else:
      self.countdown_label.set_visible(False)
      self.continue_label.set_visible(False)
      
      if self.config.auto_close and self.config.duration_seconds > 0:
        self.auto_close_timer_id = GLib.timeout_add_seconds(
          self.config.duration_seconds,
          lambda: self._dismiss('timer_expired_timeout')
        )

  def _update_countdown_ui(self):
    mins, secs = divmod(self.remaining_seconds, 60)
    self.countdown_label.set_text(f"{mins:02d}:{secs:02d}")
    self.continue_label.set_text("Focus Session Active")

  def _on_countdown_tick(self):
    if self.remaining_seconds > 0:
      self.remaining_seconds -= 1
      self._update_countdown_ui()
      return True
    else:
      self._enter_phase_2()
      self.countdown_timer_id = None
      return False

  def _enter_phase_2(self):
    self.countdown_label.set_text("00:00")
    if self.config.password is not None:
      self.continue_label.set_text("Enter PIN to unlock")
    else:
      self.continue_label.set_text("Press Enter or Space to continue")
      auto_close_secs = 30 if os.environ.get('WELLBEING_TEST_MODE') == '1' else 5
      self.phase_2_auto_close_id = GLib.timeout_add_seconds(
        auto_close_secs,
        lambda: self._dismiss('timer_expired_timeout')
      )

  def _check_password(self):
    if not hasattr(self, 'pin_entry'):
      return
    entered = self.pin_entry.get_text()
    if entered == self.config.password:
      self._dismiss('password_accepted')
    else:
      self.pin_entry.add_css_class("error")
      def clear_err():
        self.pin_entry.remove_css_class("error")
        return False
      GLib.timeout_add_seconds(1, clear_err)
      self.pin_entry.set_text("")

  def _on_key_pressed(self, controller, keyval, keycode, state):
    # UNLOCKED mode key handling - allows Escape, Enter, Space, Q, q to quiet it
    if self.config.mode == 'unlocked':
      if keyval in [Gdk.KEY_Escape, Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space, Gdk.KEY_q, Gdk.KEY_Q]:
        self._dismiss('key_dismiss')
        return True
      return False
      
    # LOCKED mode key handling
    if self.remaining_seconds > 0:
      if self.config.password is not None:
        if keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:
          self._check_password()
          return True
      return False
      
    # LOCKED mode Phase 2 (countdown is 0)
    if self.config.password is not None:
      if keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:
        self._check_password()
        return True
      return False
    else:
      if keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space]:
        if self.phase_2_auto_close_id:
          GLib.source_remove(self.phase_2_auto_close_id)
          self.phase_2_auto_close_id = None
        self._dismiss('timer_expired_keypress')
        return True
      return False

  def _fade_in(self):
    self.set_opacity(0.0)
    start_time = time.time()
    fade_duration = 0.4
    
    def step():
      elapsed = time.time() - start_time
      if elapsed >= fade_duration:
        self.set_opacity(1.0)
        return False
      self.set_opacity(elapsed / fade_duration)
      return True
      
    GLib.timeout_add(16, step)

  def _dismiss(self, reason: str):
    # Stop animations for all widgets
    if hasattr(self, 'loaded_widgets'):
      for widget in self.loaded_widgets:
        if hasattr(widget, 'stop_animations'):
          try:
            widget.stop_animations()
          except Exception:
            pass
            
    # Stop timers
    if self.countdown_timer_id:
      GLib.source_remove(self.countdown_timer_id)
      self.countdown_timer_id = None
    if self.phase_2_auto_close_id:
      GLib.source_remove(self.phase_2_auto_close_id)
      self.phase_2_auto_close_id = None
    if self.auto_close_timer_id:
      GLib.source_remove(self.auto_close_timer_id)
      self.auto_close_timer_id = None
    if self.safety_watchdog_id:
      GLib.source_remove(self.safety_watchdog_id)
      self.safety_watchdog_id = None
      
    # Release seat grabs
    self._release_grab()
    
    # Release CSS provider
    if hasattr(self, 'css_provider') and self.css_provider:
      try:
        Gtk.StyleContext.remove_provider_for_display(
          Gdk.Display.get_default(),
          self.css_provider
        )
      except Exception:
        pass
    
    self.emit('overlay-dismissed', reason)
    self.destroy()
