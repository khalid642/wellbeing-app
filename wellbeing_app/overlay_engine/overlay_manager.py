from wellbeing_app.overlay_engine.overlay_window import OverlayWindow, OverlayConfig

class OverlayManager:
  _instance = None

  @classmethod
  def get(cls):
    if cls._instance is None:
      cls._instance = OverlayManager()
    return cls._instance

  def __init__(self):
    self._current: OverlayWindow | None = None
    self._queue: list[OverlayConfig] = []
    self._callbacks: list = []

  def show_overlay(self, config: OverlayConfig):
    if self._current is not None:
      self._queue.append(config)
      return
    self._show(config)

  def _show(self, config: OverlayConfig):
    win = OverlayWindow(config)
    win.connect('overlay-dismissed', self._on_dismissed)
    self._current = win
    win.present()

  def _on_dismissed(self, window, dismissed_by: str):
    config = self._current.config if self._current else None
    self._current = None
    
    # Notify callbacks
    for cb in self._callbacks:
      try:
        cb(config, dismissed_by)
      except Exception:
        pass
        
    # Process queue
    if self._queue:
      next_config = self._queue.pop(0)
      self._show(next_config)

  def on_dismissed(self, callback):
    self._callbacks.append(callback)

  def dismiss_current(self):
    if self._current:
      self._current._dismiss('escape')

  def is_overlay_active(self) -> bool:
    return self._current is not None
