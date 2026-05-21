import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import logging
from wellbeing_app.storage.database import get_connection
from wellbeing_app.prayer.location import auto_detect_location

logger = logging.getLogger(__name__)

CALCULATION_FRIENDLY = [
  'Muslim World League', 'Egyptian', 'Karachi',
  'Umm Al-Qura', 'Dubai', 'Kuwait', 'Qatar',
  'Singapore', 'North America', 'France', 'Moonsighting'
]

CALCULATION_KEYS = [
  'MuslimWorldLeague', 'Egyptian', 'Karachi',
  'UmmAlQura', 'Dubai', 'Kuwait', 'Qatar',
  'Singapore', 'NorthAmerica', 'France', 'Moonsighting'
]

MADHAB_FRIENDLY = ['Shafi / Maliki / Hanbali', 'Hanafi']
MADHAB_KEYS = ['shafi', 'hanafi']

HIGH_LAT_FRIENDLY = ['Middle of Night', 'Seventh of Night', 'Angle Based', 'None']
HIGH_LAT_KEYS = ['MiddleOfTheNight', 'SeventhOfTheNight', 'AngleBased', 'None']

class PrayerSettingsPage(Gtk.ScrolledWindow):

  def __init__(self, dashboard_page=None):
    super().__init__()
    self.set_propagate_natural_width(True)
    self.set_propagate_natural_height(False)
    self.dashboard_page = dashboard_page
    
    self._build_ui()
    self._load_settings()

  def _build_ui(self):
    self.inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    self.inner.set_margin_top(24)
    self.inner.set_margin_bottom(24)
    self.inner.set_margin_start(24)
    self.inner.set_margin_end(24)
    self.set_child(self.inner)
    
    # --- Group 1: Location Settings ---
    location_group = Adw.PreferencesGroup(title='Location')
    self.inner.append(location_group)
    
    # 1. Location Mode
    self._mode_row = Adw.ComboRow(title='Location Mode')
    model_mode = Gtk.StringList.new(['Manual', 'Auto-detect'])
    self._mode_row.set_model(model_mode)
    self._mode_row.connect('notify::selected', self._on_mode_changed)
    location_group.add(self._mode_row)
    
    # 2. Latitude
    self._lat_row = Adw.EntryRow(title='Latitude')
    location_group.add(self._lat_row)
    
    # 3. Longitude
    self._lon_row = Adw.EntryRow(title='Longitude')
    location_group.add(self._lon_row)
    
    # 4. Timezone
    self._tz_row = Adw.EntryRow(title='Timezone')
    location_group.add(self._tz_row)
    
    # 5. Geolocation Action Row
    detect_row = Adw.ActionRow(
      title='Detect Location Now',
      subtitle='Uses IP geolocation to populate fields'
    )
    self._detect_btn = Gtk.Button(label='Detect')
    self._detect_btn.add_css_class('suggested-action')
    self._detect_btn.set_valign(Gtk.Align.CENTER)
    self._detect_btn.connect('clicked', self._on_detect_clicked)
    detect_row.add_suffix(self._detect_btn)
    location_group.add(detect_row)
    
    # --- Group 2: Calculation Settings ---
    calc_group = Adw.PreferencesGroup(title='Calculation')
    self.inner.append(calc_group)
    
    # 1. Method
    self._method_row = Adw.ComboRow(title='Calculation Method')
    model_method = Gtk.StringList.new(CALCULATION_FRIENDLY)
    self._method_row.set_model(model_method)
    calc_group.add(self._method_row)
    
    # 2. Madhab
    self._madhab_row = Adw.ComboRow(title='Madhab')
    model_madhab = Gtk.StringList.new(MADHAB_FRIENDLY)
    self._madhab_row.set_model(model_madhab)
    calc_group.add(self._madhab_row)
    
    # 3. High Lat Rule
    self._high_lat_row = Adw.ComboRow(title='High Latitude Rule')
    model_high_lat = Gtk.StringList.new(HIGH_LAT_FRIENDLY)
    self._high_lat_row.set_model(model_high_lat)
    calc_group.add(self._high_lat_row)
    
    # --- Group 3: Actions ---
    action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    action_box.set_hexpand(True)
    action_box.set_halign(Gtk.Align.END)
    
    self._save_btn = Gtk.Button(label='Save and Recalculate')
    self._save_btn.add_css_class('suggested-action')
    self._save_btn.set_margin_top(8)
    self._save_btn.connect('clicked', self._on_save_clicked)
    
    action_box.append(self._save_btn)
    self.inner.append(action_box)

  def _load_settings(self):
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
        SELECT location_mode, latitude, longitude, timezone, calculation_method, madhab, high_lat_rule
        FROM prayer_config
        LIMIT 1
      """)
      row = cursor.fetchone()
      if row:
        mode, lat, lon, tz, method, madhab, high_lat = row
        
        self._mode_row.set_selected(1 if mode == 'auto' else 0)
        self._lat_row.set_text(str(lat))
        self._lon_row.set_text(str(lon))
        self._tz_row.set_text(str(tz))
        
        # Method Combo selection
        if method in CALCULATION_KEYS:
          self._method_row.set_selected(CALCULATION_KEYS.index(method))
        # Madhab Combo
        if madhab in MADHAB_KEYS:
          self._madhab_row.set_selected(MADHAB_KEYS.index(madhab))
        # High Lat
        if high_lat in HIGH_LAT_KEYS:
          self._high_lat_row.set_selected(HIGH_LAT_KEYS.index(high_lat))
          
    self._update_fields_sensitivity()

  def _on_mode_changed(self, combo, pspec):
    self._update_fields_sensitivity()

  def _update_fields_sensitivity(self):
    is_manual = self._mode_row.get_selected() == 0
    self._lat_row.set_sensitive(is_manual)
    self._lon_row.set_sensitive(is_manual)
    self._tz_row.set_sensitive(is_manual)
    self._detect_btn.set_sensitive(not is_manual)

  def _on_detect_clicked(self, btn):
    self._detect_btn.set_sensitive(False)
    # Perform IP Geolocation in background
    def detect_thread():
      lat, lon, tz, city = auto_detect_location()
      GLib.idle_add(self._on_detection_complete, lat, lon, tz, city)
      
    import threading
    threading.Thread(target=detect_thread, daemon=True).start()

  def _on_detection_complete(self, lat, lon, tz, city):
    self._lat_row.set_text(f"{lat:.4f}")
    self._lon_row.set_text(f"{lon:.4f}")
    self._tz_row.set_text(tz)
    self._detect_btn.set_sensitive(True)
    logger.info(f"Populated detected location for {city}")

  def _on_save_clicked(self, btn):
    mode = 'auto' if self._mode_row.get_selected() == 1 else 'manual'
    try:
      lat = float(self._lat_row.get_text())
      lon = float(self._lon_row.get_text())
    except ValueError:
      # Simple error dialog if lat/lon invalid
      dialog = Gtk.MessageDialog(
        transient_for=self.get_root(),
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text="Invalid Input: Latitude and Longitude must be floating point numbers."
      )
      dialog.connect('response', lambda d, r: d.destroy())
      dialog.present()
      return

    tz = self._tz_row.get_text().strip()
    
    method_idx = self._method_row.get_selected()
    method = CALCULATION_KEYS[method_idx]
    
    madhab_idx = self._madhab_row.get_selected()
    madhab = MADHAB_KEYS[madhab_idx]
    
    high_lat_idx = self._high_lat_row.get_selected()
    high_lat = HIGH_LAT_KEYS[high_lat_idx]
    
    with get_connection() as conn:
      conn.execute("""
        UPDATE prayer_config
        SET location_mode = ?, latitude = ?, longitude = ?, timezone = ?,
            calculation_method = ?, madhab = ?, high_lat_rule = ?
      """, (mode, lat, lon, tz, method, madhab, high_lat))
      conn.commit()
      
    logger.info("Prayer configurations successfully updated in SQLite database")
    
    # Invalidate Cache & Refresh Dashboard
    if self.dashboard_page:
      self.dashboard_page.refresh_data()
      
    dialog = Gtk.MessageDialog(
      transient_for=self.get_root(),
      modal=True,
      message_type=Gtk.MessageType.INFO,
      buttons=Gtk.ButtonsType.OK,
      text="Settings saved and calculations recalculated successfully."
    )
    dialog.connect('response', lambda d, r: d.destroy())
    dialog.present()
