from datetime import datetime

def validate_schedule(schedule: dict) -> list[str]:
  errors = []
  
  fajr    = schedule.get('fajr')
  sunrise = schedule.get('sunrise')
  dhuhr   = schedule.get('dhuhr')
  asr     = schedule.get('asr')
  maghrib = schedule.get('maghrib')
  isha    = schedule.get('isha')
  
  for name, val in schedule.items():
    if val is None:
      errors.append(f"Missing prayer time: {name}")
  
  if errors:
    return errors
  
  for name, val in schedule.items():
    if val.tzinfo is None:
      errors.append(f"{name} is timezone-naive — must be aware datetime")
  
  if fajr >= sunrise:
    errors.append(
      f"CRITICAL: Fajr ({fajr.strftime('%H:%M')}) is not before "
      f"sunrise ({sunrise.strftime('%H:%M')}). "
      f"Difference: {int((fajr-sunrise).total_seconds()/60)} min"
    )
  
  if sunrise >= dhuhr:
    errors.append(f"Sunrise ({sunrise.strftime('%H:%M')}) >= Dhuhr ({dhuhr.strftime('%H:%M')})")
  
  if dhuhr >= asr:
    errors.append(f"Dhuhr ({dhuhr.strftime('%H:%M')}) >= Asr ({asr.strftime('%H:%M')})")
  
  if asr >= maghrib:
    errors.append(f"Asr ({asr.strftime('%H:%M')}) >= Maghrib ({maghrib.strftime('%H:%M')})")
  
  if maghrib >= isha:
    errors.append(f"Maghrib ({maghrib.strftime('%H:%M')}) >= Isha ({isha.strftime('%H:%M')})")
  
  fajr_to_sunrise = (sunrise - fajr).total_seconds() / 60
  if fajr_to_sunrise < 30:
    errors.append(
      f"WARNING: Fajr is only {fajr_to_sunrise:.0f} min before sunrise. "
      f"This is unusually close — verify coordinates and calculation method."
    )
  
  if not (11 <= dhuhr.hour <= 14):
    errors.append(
      f"WARNING: Dhuhr at {dhuhr.strftime('%H:%M')} is outside expected "
      f"range (11:00–14:00). Check timezone setting."
    )
  
  return errors
