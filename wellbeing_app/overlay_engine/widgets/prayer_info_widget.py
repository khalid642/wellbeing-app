import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from datetime import datetime, date
from zoneinfo import ZoneInfo
import logging

from wellbeing_app.storage.database import get_connection
from wellbeing_app.prayer.engine import PrayerEngine
from wellbeing_app.prayer.jamah import JamahStore

logger = logging.getLogger(__name__)

class PrayerInfoWidget(Gtk.Box):

  def __init__(self):
    super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.CENTER)
    
    self.show_prayer_name = True
    self.show_time = True
    self.show_jamah = True
    self.font_size = 24
    
    self.label = Gtk.Label()
    self.label.set_halign(Gtk.Align.CENTER)
    self.append(self.label)

  def load_config(self, config: dict):
    self.show_prayer_name = config.get('show_prayer_name', True)
    self.show_time = config.get('show_time', True)
    self.show_jamah = config.get('show_jamah', True)
    self.font_size = config.get('font_size', 24)
    
    self._update_info()

  def _update_info(self):
    # 1. Load configuration from DB to build PrayerEngine
    latitude, longitude, timezone_str = 21.3891, 39.8579, 'Asia/Riyadh'
    calculation_method, madhab, high_lat_rule = 'MuslimWorldLeague', 'shafi', 'AngleBased'
    
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
        SELECT latitude, longitude, timezone, calculation_method, madhab, high_lat_rule 
        FROM prayer_config 
        LIMIT 1
      """)
      row = cursor.fetchone()
      if row:
        latitude, longitude, timezone_str, calculation_method, madhab, high_lat_rule = row
        
    try:
      tz = ZoneInfo(timezone_str)
    except Exception:
      tz = ZoneInfo('UTC')
      
    engine = PrayerEngine(
      latitude=latitude,
      longitude=longitude,
      timezone=timezone_str,
      calculation_method=calculation_method,
      madhab=madhab,
      high_lat_rule=high_lat_rule
    )
    
    jamah_store = JamahStore()
    
    # 2. Get today's schedule and locate the current/upcoming prayer
    now = datetime.now(tz)
    today = now.date()
    schedule = engine.get_today_schedule(today)
    
    # Determine which prayer we are currently closest to
    # Standard sequence: fajr, dhuhr, asr, maghrib, isha
    prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']
    active_prayer = 'fajr'
    
    # Find the upcoming prayer, or fall back to last if all passed
    for p in prayers:
      p_time = schedule.get(p)
      if p_time and p_time > now:
        active_prayer = p
        break
    else:
      active_prayer = 'isha'
      
    p_dt = schedule.get(active_prayer)
    p_time_str = p_dt.strftime('%H:%M') if p_dt else "N/A"
    
    # Get manual jamah time
    jamah_time = jamah_store.get_jamah_time(active_prayer)
    jamah_enabled = jamah_store.is_enabled(active_prayer)
    
    # 3. Construct markup text dynamically
    lines = []
    if self.show_prayer_name:
      lines.append(f'<span font_size="{int(self.font_size * 1.3 * 1024)}" foreground="#50c8b4" weight="bold">{active_prayer.capitalize()}</span>')
      
    if self.show_time:
      lines.append(f'<span font_size="{self.font_size * 1024}" foreground="#ffffff">Adhan: {p_time_str}</span>')
      
    if self.show_jamah:
      if jamah_enabled and jamah_time:
        lines.append(f'<span font_size="{int(self.font_size * 0.9 * 1024)}" foreground="#bbbbbb">Jamah: {jamah_time}</span>')
      else:
        lines.append(f'<span font_size="{int(self.font_size * 0.9 * 1024)}" foreground="#888888">Jamah: Not Set</span>')
        
    self.label.set_markup('\n'.join(lines))

  def start_animations(self):
    pass

  def stop_animations(self):
    pass
