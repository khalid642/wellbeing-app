import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Gdk
from datetime import datetime, date
import os
import logging

from wellbeing_app.storage.database import get_connection
from wellbeing_app.prayer.engine import PrayerEngine
from wellbeing_app.prayer.jamah import JamahStore
from wellbeing_app.prayer.hijri import gregorian_to_hijri

logger = logging.getLogger(__name__)

class DashboardPage(Gtk.ScrolledWindow):

  def __init__(self):
    super().__init__()
    self.set_propagate_natural_width(True)
    self.set_propagate_natural_height(True)
    
    self._prayer_labels = {}
    
    # Load configuration and create PrayerEngine
    self._reload_engine()
    
    self._build_ui()
    self.refresh_data()
    
    # Refresh data every 60 seconds
    GLib.timeout_add_seconds(60, self._on_refresh_tick)
    # Countdown tick every 1 second
    GLib.timeout_add_seconds(1, self._update_countdown)

  def _reload_engine(self):
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
        SELECT latitude, longitude, timezone, calculation_method, madhab, high_lat_rule 
        FROM prayer_config 
        LIMIT 1
      """)
      row = cursor.fetchone()
      if row:
        self.latitude, self.longitude, self.timezone_str, \
        self.calculation_method, self.madhab, self.high_lat_rule = row
      else:
        self.latitude, self.longitude, self.timezone_str = 21.3891, 39.8579, 'Asia/Riyadh'
        self.calculation_method, self.madhab, self.high_lat_rule = 'MuslimWorldLeague', 'shafi', 'AngleBased'
        
    self.prayer_engine = PrayerEngine(
      latitude=self.latitude,
      longitude=self.longitude,
      timezone=self.timezone_str,
      calculation_method=self.calculation_method,
      madhab=self.madhab,
      high_lat_rule=self.high_lat_rule
    )
    self.jamah_store = JamahStore()

  def _build_ui(self):
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
    content_box.set_margin_top(24)
    content_box.set_margin_bottom(24)
    content_box.set_margin_start(24)
    content_box.set_margin_end(24)
    content_box.set_hexpand(True)
    content_box.set_vexpand(True)
    
    self.set_child(content_box)
    
    # --- Section 1: Date Header ---
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    header_box.set_hexpand(True)
    
    left_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    self._date_label = Gtk.Label()
    self._date_label.add_css_class('title-2')
    self._date_label.set_xalign(0)
    
    self._hijri_label = Gtk.Label()
    self._hijri_label.add_css_class('body')
    self._hijri_label.add_css_class('dim-label')
    self._hijri_label.set_xalign(0)
    
    left_header.append(self._date_label)
    left_header.append(self._hijri_label)
    
    self._location_label = Gtk.Label()
    self._location_label.add_css_class('body')
    self._location_label.add_css_class('dim-label')
    self._location_label.set_hexpand(True)
    self._location_label.set_halign(Gtk.Align.END)
    self._location_label.set_valign(Gtk.Align.CENTER)
    
    header_box.append(left_header)
    header_box.append(self._location_label)
    content_box.append(header_box)
    
    # --- Section 2: Next Prayer Countdown ---
    countdown_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    countdown_card.add_css_class('card')
    countdown_card.set_hexpand(True)
    
    inner_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    inner_card.set_margin_top(20)
    inner_card.set_margin_bottom(20)
    inner_card.set_margin_start(20)
    inner_card.set_margin_end(20)
    inner_card.set_hexpand(True)
    
    caption_lbl = Gtk.Label(label='NEXT PRAYER')
    caption_lbl.add_css_class('caption')
    caption_lbl.add_css_class('dim-label')
    caption_lbl.set_xalign(0.5)
    
    self._next_prayer_name = Gtk.Label()
    self._next_prayer_name.add_css_class('title-1')
    self._next_prayer_name.set_xalign(0.5)
    
    self._countdown_label = Gtk.Label()
    self._countdown_label.add_css_class('display')
    self._countdown_label.set_xalign(0.5)
    
    self._next_prayer_time = Gtk.Label()
    self._next_prayer_time.add_css_class('body')
    self._next_prayer_time.add_css_class('dim-label')
    self._next_prayer_time.set_xalign(0.5)
    
    inner_card.append(caption_lbl)
    inner_card.append(self._next_prayer_name)
    inner_card.append(self._countdown_label)
    inner_card.append(self._next_prayer_time)
    countdown_card.append(inner_card)
    content_box.append(countdown_card)
    
    # --- Section 3: Prayer Times Grid ---
    grid_title = Gtk.Label(label="Today's Prayers")
    grid_title.set_xalign(0)
    grid_title.add_css_class('heading')
    content_box.append(grid_title)
    
    grid_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, homogeneous=True)
    grid_box.set_hexpand(True)
    
    for prayer_name in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
      card = self.make_prayer_card(prayer_name)
      grid_box.append(card)
      
    content_box.append(grid_box)
    
    # --- Section 4: Sunrise ---
    sunrise_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    sunrise_box.set_hexpand(True)
    
    sun_icon = Gtk.Image.new_from_icon_name('weather-clear-symbolic')
    sun_icon.add_css_class('dim-label')
    
    sun_title = Gtk.Label(label='Sunrise')
    sun_title.add_css_class('body')
    
    self._sunrise_label = Gtk.Label()
    self._sunrise_label.add_css_class('body')
    self._sunrise_label.add_css_class('dim-label')
    self._sunrise_label.set_hexpand(True)
    self._sunrise_label.set_xalign(1.0)
    
    sunrise_box.append(sun_icon)
    sunrise_box.append(sun_title)
    sunrise_box.append(self._sunrise_label)
    content_box.append(sunrise_box)

  def make_prayer_card(self, prayer_name: str) -> Gtk.Box:
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    outer.add_css_class('card')
    outer.set_hexpand(True)
    
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    inner.set_margin_top(16)
    inner.set_margin_bottom(16)
    inner.set_margin_start(12)
    inner.set_margin_end(12)
    inner.set_hexpand(True)
    
    name_lbl = Gtk.Label(label=prayer_name)
    name_lbl.add_css_class('heading')
    name_lbl.set_xalign(0)
    
    time_lbl = Gtk.Label()
    time_lbl.add_css_class('title-2')
    time_lbl.set_xalign(0)
    
    jamah_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    jamah_key = Gtk.Label(label='Jamah')
    jamah_key.add_css_class('caption')
    jamah_key.add_css_class('dim-label')
    
    jamah_val = Gtk.Label()
    jamah_val.add_css_class('caption')
    
    jamah_row.append(jamah_key)
    jamah_row.append(jamah_val)
    
    status_lbl = Gtk.Label()
    status_lbl.add_css_class('caption')
    status_lbl.set_xalign(0)
    
    inner.append(name_lbl)
    inner.append(time_lbl)
    inner.append(jamah_row)
    inner.append(status_lbl)
    outer.append(inner)
    
    self._prayer_labels[prayer_name.lower()] = {
      'time': time_lbl,
      'jamah': jamah_val,
      'status': status_lbl,
      'card': outer
    }
    
    return outer

  def _set_prayer_status(self, prayer_name: str, status: str):
    lbl = self._prayer_labels[prayer_name]['status']
    card = self._prayer_labels[prayer_name]['card']
    
    for cls in ['success', 'accent', 'dim-label']:
      lbl.remove_css_class(cls)
    card.remove_css_class('prayer-card-current')
    
    if status == 'current':
      lbl.set_label('● Now')
      lbl.add_css_class('success')
      card.add_css_class('prayer-card-current')
    elif status == 'next':
      lbl.set_label('● Next')
      lbl.add_css_class('accent')
    elif status == 'passed':
      lbl.set_label('Passed')
      lbl.add_css_class('dim-label')
    else:
      lbl.set_label('Upcoming')
      lbl.add_css_class('dim-label')

  def refresh_data(self):
    self._reload_engine()
    
    schedule = self.prayer_engine.get_today_schedule()
    display = self.prayer_engine.get_schedule_display()
    jamah = self.jamah_store.get_all_jamah_times()
    current_p = self.prayer_engine.get_current_prayer()
    next_p, next_t = self.prayer_engine.get_next_prayer()
    
    self._date_label.set_label(datetime.now().strftime('%A, %d %B %Y'))
    self._hijri_label.set_label(gregorian_to_hijri(date.today()))
    self._sunrise_label.set_label(display.get('sunrise', '—'))
    
    self._next_prayer_name.set_label(next_p.capitalize())
    self._next_prayer_time.set_label(f"at {next_t.strftime('%H:%M')}")
    
    # Location
    self._location_label.set_label(f"GPS: {self.latitude:.4f}, {self.longitude:.4f} ({self.timezone_str})")
    
    prayer_order = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']
    for prayer in prayer_order:
      self._prayer_labels[prayer]['time'].set_label(display.get(prayer, '—'))
      j = jamah.get(prayer)
      self._prayer_labels[prayer]['jamah'].set_label(j if j else '—')
      
    now = datetime.now(self.prayer_engine.tz)
    for prayer in prayer_order:
      if prayer == current_p:
        self._set_prayer_status(prayer, 'current')
      elif prayer == next_p:
        self._set_prayer_status(prayer, 'next')
      elif schedule[prayer] < now:
        self._set_prayer_status(prayer, 'passed')
      else:
        self._set_prayer_status(prayer, 'upcoming')

  def _on_refresh_tick(self):
    self.refresh_data()
    return GLib.SOURCE_CONTINUE

  def _update_countdown(self):
    secs = self.prayer_engine.get_remaining_seconds()
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    
    if h > 0:
      self._countdown_label.set_label(f"{h}:{m:02d}:{s:02d}")
    else:
      self._countdown_label.set_label(f"{m:02d}:{s:02d}")
      
    return GLib.SOURCE_CONTINUE
