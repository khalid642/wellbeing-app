import sys
from datetime import date
from wellbeing_app.prayer.engine import PrayerEngine
from wellbeing_app.prayer.validator import validate_schedule

def test_london_shafi():
  engine = PrayerEngine(
    latitude=51.5074,
    longitude=-0.1278,
    timezone='Europe/London',
    calculation_method='MuslimWorldLeague',
    madhab='shafi'
  )
  target = date(2025, 6, 15)
  schedule = engine.get_today_schedule(target)
  display = engine.get_schedule_display(target)
  
  print("London Shafi 2025-06-15:")
  for name, t in display.items():
    print(f"  {name:8}: {t}")
  
  errors = validate_schedule(schedule)
  assert not errors, f"Validation failed: {errors}"
  
  # Check Fajr is before Sunrise
  assert schedule['fajr'] < schedule['sunrise'], \
    f"FAIL: Fajr {display['fajr']} >= Sunrise {display['sunrise']}"
  
  # Check approximate expected times
  # Allow ±5 minute tolerance for library differences
  fajr_hour = schedule['fajr'].hour
  fajr_min  = schedule['fajr'].minute
  assert fajr_hour == 2 and 44 <= fajr_min <= 54, \
    f"FAIL: Fajr should be ~02:49, got {display['fajr']}"
  
  sunrise_hour = schedule['sunrise'].hour
  sunrise_min  = schedule['sunrise'].minute
  assert sunrise_hour == 4 and 38 <= sunrise_min <= 48, \
    f"FAIL: Sunrise should be ~04:43, got {display['sunrise']}"
  
  dhuhr_hour = schedule['dhuhr'].hour
  dhuhr_min  = schedule['dhuhr'].minute
  assert dhuhr_hour == 13 and 0 <= dhuhr_min <= 7, \
    f"FAIL: Dhuhr should be ~13:02, got {display['dhuhr']}"
  
  asr_hour = schedule['asr'].hour
  asr_min  = schedule['asr'].minute
  assert asr_hour == 17 and 3 <= asr_min <= 13, \
    f"FAIL: Asr (Shafi) should be ~17:08, got {display['asr']}"
  
  maghrib_hour = schedule['maghrib'].hour
  maghrib_min  = schedule['maghrib'].minute
  assert maghrib_hour == 21 and 15 <= maghrib_min <= 25, \
    f"FAIL: Maghrib should be ~21:20, got {display['maghrib']}"
  
  isha_hour = schedule['isha'].hour
  isha_min  = schedule['isha'].minute
  assert isha_hour == 23 and 7 <= isha_min <= 17, \
    f"FAIL: Isha should be ~23:12, got {display['isha']}"

def test_hanafi_asr_later_than_shafi():
  target = date(2025, 6, 15)
  
  shafi_engine = PrayerEngine(
    latitude=51.5074,
    longitude=-0.1278,
    timezone='Europe/London',
    calculation_method='MuslimWorldLeague',
    madhab='shafi'
  )
  shafi_schedule = shafi_engine.get_today_schedule(target)
  shafi_asr = shafi_schedule['asr']
  
  hanafi_engine = PrayerEngine(
    latitude=51.5074,
    longitude=-0.1278,
    timezone='Europe/London',
    calculation_method='MuslimWorldLeague',
    madhab='hanafi'
  )
  hanafi_schedule = hanafi_engine.get_today_schedule(target)
  hanafi_asr = hanafi_schedule['asr']
  
  diff_minutes = (hanafi_asr - shafi_asr).total_seconds() / 60
  
  print(f"Asr Shadow check (Shafi vs Hanafi):")
  print(f"  Shafi Asr : {shafi_asr.strftime('%H:%M')}")
  print(f"  Hanafi Asr: {hanafi_asr.strftime('%H:%M')} (+{diff_minutes:.0f} min)")
  
  assert hanafi_asr > shafi_asr, \
    f"FAIL: Hanafi Asr ({hanafi_asr.strftime('%H:%M')}) should be " \
    f"LATER than Shafi Asr ({shafi_asr.strftime('%H:%M')})"
  
  assert diff_minutes >= 30, \
    f"FAIL: Hanafi/Shafi difference is only {diff_minutes:.0f} min. " \
    f"Expected at least 30 min. Madhab setting is not working."

if __name__ == '__main__':
  print("Running prayer time calculation accuracy validation...")
  try:
    test_london_shafi()
    print("✓ test_london_shafi: PASSED")
    
    test_hanafi_asr_later_than_shafi()
    print("✓ test_hanafi_asr_later_than_shafi: PASSED")
    
    print("\nALL ACCURACY CHECKS PASSED SUCCESSFULLY!")
    sys.exit(0)
  except AssertionError as e:
    print(f"\n❌ {e}")
    sys.exit(1)
