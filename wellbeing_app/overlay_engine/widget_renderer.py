import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

# Import actual widget classes
from wellbeing_app.overlay_engine.widgets.text_widget import TextWidget
from wellbeing_app.overlay_engine.widgets.clock_widget import ClockWidget
from wellbeing_app.overlay_engine.widgets.countdown_timer_widget import CountdownTimerWidget
from wellbeing_app.overlay_engine.widgets.breathing_widget import BreathingWidget
from wellbeing_app.overlay_engine.widgets.tasbih_widget import TasbihWidget
from wellbeing_app.overlay_engine.widgets.prayer_info_widget import PrayerInfoWidget

class WidgetRenderer:

  @staticmethod
  def create_widget(wc) -> Gtk.Widget:
    widget_type = wc.widget_type
    config = wc.config or {}
    
    widget = None
    
    if widget_type == 'text_widget':
      widget = TextWidget()
    elif widget_type == 'clock_widget':
      widget = ClockWidget()
    elif widget_type == 'countdown_timer_widget':
      widget = CountdownTimerWidget()
    elif widget_type == 'breathing_widget':
      widget = BreathingWidget()
    elif widget_type == 'tasbih_widget':
      widget = TasbihWidget()
    elif widget_type == 'prayer_info_widget':
      widget = PrayerInfoWidget()
    else:
      # Unknown fallback label
      return Gtk.Label(label=f'[{widget_type}]')
      
    # Load configuration and initiate transitions
    try:
      widget.load_config(config)
      widget.start_animations()
    except Exception as e:
      import logging
      logger = logging.getLogger(__name__)
      logger.error(f"Failed to load or animate widget {widget_type}: {e}")
      
    return widget
