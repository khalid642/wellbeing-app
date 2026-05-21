import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import logging

from wellbeing_app.storage.database import get_connection, db
from wellbeing_app.prayer.engine import PrayerEngine
from wellbeing_app.prayer.jamah import JamahStore
from wellbeing_app.daemon.logger import setup_logger
from wellbeing_app.overlay_engine.overlay_manager import OverlayManager
from wellbeing_app.overlay_engine.overlay_window import OverlayConfig


class WellbeingDaemon:

  def __init__(self):
    self.logger = setup_logger()
    self.logger.info("Initializing WellbeingDaemon...")
    
    # Load configurations
    self._load_config()
    
    # Instantiate Engines
    self.prayer_engine = PrayerEngine(
      latitude=self.latitude,
      longitude=self.longitude,
      timezone=self.timezone_str,
      calculation_method=self.calculation_method,
      madhab=self.madhab,
      high_lat_rule=self.high_lat_rule
    )
    self.jamah_store = JamahStore()
    
    # Schedulers
    self.eyecare_scheduler = EyeCareScheduler(self)
    self.reminder_scheduler = ReminderScheduler(self)
    
    # Callbacks registry
    self._callbacks = {
      'ADHAN_TIME': [],
      'IQAMAH_TIME': [],
      'LOCK_OVERLAY_TRIGGER': [],
      'EYECARE_OVERLAY_TRIGGER': [],
      'REMINDER_TRIGGER': []
    }
    
    self.scheduled_events = []
    self._daily_timer_id = None
    
    # Overlay Manager integration
    self.overlay_manager = OverlayManager.get()
    self.overlay_manager.on_dismissed(self._on_overlay_dismissed)


  def _load_config(self):
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
        
      try:
        self.tz = ZoneInfo(self.timezone_str)
      except Exception:
        self.logger.warning(f"Invalid timezone '{self.timezone_str}' in database, falling back to UTC.")
        self.timezone_str = 'UTC'
        self.tz = ZoneInfo('UTC')

  def register_callback(self, event_type: str, callback):
    if event_type in self._callbacks:
      self._callbacks[event_type].append(callback)
    else:
      self.logger.warning(f"Attempted to register callback for unknown event type: {event_type}")

  def start(self):
    self.logger.info("Starting WellbeingDaemon scheduler...")
    
    # 1. Schedule events for today
    self._schedule_today_events()
    
    # 2. Schedule daily recalculation at midnight
    self._schedule_daily_recalculation()
    
    # 3. Start EyeCare and Reminder schedulers
    self.eyecare_scheduler.start()
    self.reminder_scheduler.start()

  def stop(self):
    self.logger.info("Stopping WellbeingDaemon...")
    self.stop_all_events()
    
    if self._daily_timer_id:
      try:
        GLib.source_remove(self._daily_timer_id)
      except Exception:
        pass
      self._daily_timer_id = None
      
    self.eyecare_scheduler.stop()
    if hasattr(self.reminder_scheduler, 'stop'):
      self.reminder_scheduler.stop()

  def stop_all_events(self):
    for event in self.scheduled_events:
      try:
        GLib.source_remove(event['timer_id'])
      except Exception:
        pass
    self.scheduled_events = []

  def _schedule_today_events(self):
    self.stop_all_events()
    
    now = datetime.now(self.tz)
    today = now.date()
    
    prayer_schedule = self.prayer_engine.get_today_schedule(today)
    jamah_times = self.jamah_store.get_all_jamah_times()
    iqamah_offset = self.jamah_store.get_iqamah_offset()
    
    # Load adhan delay/enable states from DB
    adhan_delays = {}
    adhan_enabled = {}
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT prayer, delay_seconds, enabled FROM adhan_config")
      for row in cursor.fetchall():
        p_name, delay, enabled = row
        adhan_delays[p_name.lower()] = delay
        adhan_enabled[p_name.lower()] = bool(enabled)
        
    for prayer in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
      # 1. Schedule ADHAN_TIME
      prayer_dt = prayer_schedule.get(prayer)
      if prayer_dt:
        delay = adhan_delays.get(prayer, 0)
        enabled = adhan_enabled.get(prayer, True)
        
        if enabled:
          adhan_dt = prayer_dt + timedelta(seconds=delay)
          if adhan_dt > now:
            self._schedule_event('ADHAN_TIME', prayer, adhan_dt, self._fire_adhan)
            
      # 2. Schedule IQAMAH_TIME
      if self.jamah_store.is_enabled(prayer):
        jamah_time_str = jamah_times.get(prayer)
        if jamah_time_str:
          try:
            h, m = map(int, jamah_time_str.split(':'))
            jamah_dt = datetime(today.year, today.month, today.day, h, m, tzinfo=self.tz)
            iqamah_dt = jamah_dt - timedelta(minutes=iqamah_offset)
            
            if iqamah_dt > now:
              self._schedule_event('IQAMAH_TIME', prayer, iqamah_dt, self._fire_iqamah)
          except Exception as e:
            self.logger.error(f"Error parsing jamah time '{jamah_time_str}' for {prayer}: {e}")

    # Log all scheduled events
    self.logger.info("Today's Scheduled Events:")
    for event in sorted(self.scheduled_events, key=lambda x: x['time']):
      self.logger.info(f"  {event['name']} for {event['prayer']} at {event['time'].strftime('%Y-%m-%d %H:%M:%S')}")

  def _schedule_event(self, event_name: str, prayer_name: str, event_time: datetime, callback):
    now = datetime.now(self.tz)
    delay_seconds = int((event_time - now).total_seconds())
    if delay_seconds < 0:
      delay_seconds = 0
      
    timer_id = GLib.timeout_add_seconds(delay_seconds, callback, prayer_name)
    
    self.scheduled_events.append({
      'name': event_name,
      'prayer': prayer_name,
      'time': event_time,
      'timer_id': timer_id
    })

  def _schedule_daily_recalculation(self):
    if self._daily_timer_id:
      try:
        GLib.source_remove(self._daily_timer_id)
      except Exception:
        pass
      self._daily_timer_id = None
      
    now = datetime.now(self.tz)
    tomorrow = now.date() + timedelta(days=1)
    target = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 1, tzinfo=self.tz)
    
    delay_seconds = int((target - now).total_seconds())
    if delay_seconds < 0:
      delay_seconds = 0
      
    self._daily_timer_id = GLib.timeout_add_seconds(
      delay_seconds,
      self._recalculate_daily
    )
    self.logger.info(f"Scheduled next daily recalculation in {delay_seconds} seconds (at {target.strftime('%Y-%m-%d %H:%M:%S')})")

  def _recalculate_daily(self):
    self.logger.info("Triggering daily recalculation...")
    self._schedule_today_events()
    self._schedule_daily_recalculation()
    return False

  def _fire_adhan(self, prayer_name):
    self.logger.info(f"Event fired: ADHAN_TIME for {prayer_name}")
    for cb in self._callbacks['ADHAN_TIME']:
      try:
        cb(prayer_name)
      except Exception as e:
        self.logger.error(f"Error in ADHAN_TIME callback: {e}")
    return False

  def _fire_iqamah(self, prayer_name):
    self.logger.info(f"Event fired: IQAMAH_TIME for {prayer_name}")
    for cb in self._callbacks['IQAMAH_TIME']:
      try:
        cb(prayer_name)
      except Exception as e:
        self.logger.error(f"Error in IQAMAH_TIME callback: {e}")
        
    self.logger.info(f"Scheduling LOCK_OVERLAY_TRIGGER in 30 seconds for {prayer_name}")
    GLib.timeout_add_seconds(30, self._fire_lock_overlay, prayer_name)
    return False

  def _fire_lock_overlay(self, prayer_name):
    self.logger.info(f"Event fired: LOCK_OVERLAY_TRIGGER for {prayer_name}")
    for cb in self._callbacks['LOCK_OVERLAY_TRIGGER']:
      try:
        cb(prayer_name)
      except Exception as e:
        self.logger.error(f"Error in LOCK_OVERLAY_TRIGGER callback: {e}")
        
    widgets = db.get_overlay_widgets('salah_lock')
    lock_duration = 900
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT value FROM app_config WHERE key = 'salah_lock_duration_seconds'")
      row = cursor.fetchone()
      if row:
        try:
          lock_duration = int(row[0])
        except Exception:
          pass
          
    config = OverlayConfig(
      mode='locked',
      duration_seconds=lock_duration,
      widgets=widgets,
      overlay_id='salah_lock'
    )
    self.overlay_manager.show_overlay(config)
    return False

  def _fire_zikr_overlay(self):
    if self.overlay_manager.is_overlay_active():
      return
    widgets = db.get_overlay_widgets('zikr')
    config = OverlayConfig(
      mode='unlocked',
      duration_seconds=0,
      widgets=widgets,
      overlay_id='zikr'
    )
    self.overlay_manager.show_overlay(config)

  def _on_overlay_dismissed(self, config, dismissed_by: str):
    if config and config.overlay_id == 'eyecare':
      if dismissed_by == 'timer_expired_keypress':
        self._fire_zikr_overlay()



class EyeCareScheduler:

  def __init__(self, daemon):
    self.daemon = daemon
    self._timer_id = None

  def start(self):
    self.stop()
    
    # Read settings
    interval_minutes = 20
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT value FROM app_config WHERE key = 'eyecare_interval_minutes'")
      row = cursor.fetchone()
      if row:
        try:
          interval_minutes = int(row[0])
        except Exception:
          pass
          
    self.daemon.logger.info(f"Starting EyeCareScheduler with interval {interval_minutes} minutes")
    
    def tick():
      self._fire_eyecare()
      return True
      
    self._timer_id = GLib.timeout_add_seconds(interval_minutes * 60, tick)

  def _fire_eyecare(self):
    if self.daemon.overlay_manager.is_overlay_active():
      self.daemon.logger.info("EyeCareScheduler skipped: another overlay is active")
      return
      
    # Read lock duration
    lock_seconds = 20
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT value FROM app_config WHERE key = 'eyecare_lock_seconds'")
      row = cursor.fetchone()
      if row:
        try:
          lock_seconds = int(row[0])
        except Exception:
          pass
          
    self.daemon.logger.info("Triggering EyeCare screen overlay")
    
    widgets = db.get_overlay_widgets('eyecare')
    config = OverlayConfig(
      mode='locked',
      duration_seconds=lock_seconds,
      widgets=widgets,
      background_blur=True,
      password=None,
      auto_close=False,
      overlay_id='eyecare'
    )
    self.daemon.overlay_manager.show_overlay(config)

  def stop(self):
    if self._timer_id:
      try:
        GLib.source_remove(self._timer_id)
      except Exception:
        pass
      self._timer_id = None


class ReminderScheduler:
  """Stub. Fully implemented in Phase 13."""

  def __init__(self, daemon):
    self.daemon = daemon

  def start(self):
    pass


def run_daemon():
  daemon = WellbeingDaemon()
  daemon.start()
  
  loop = GLib.MainLoop()
  
  import signal
  def handle_signal(sig, frame):
    daemon.logger.info("Signal received, stopping daemon...")
    daemon.stop()
    loop.quit()
    
  signal.signal(signal.SIGINT, handle_signal)
  signal.signal(signal.SIGTERM, handle_signal)
  
  try:
    loop.run()
  except KeyboardInterrupt:
    daemon.logger.info("KeyboardInterrupt received, stopping daemon...")
    daemon.stop()
