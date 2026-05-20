import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

FALLBACK = (21.3891, 39.8579, 'Asia/Riyadh', 'Mecca')

def auto_detect_location() -> tuple[float, float, str, str]:
  try:
    url = 'http://ip-api.com/json/?fields=lat,lon,timezone,city,status'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=4) as resp:
      data = json.loads(resp.read().decode())
    
    if data.get('status') != 'success':
      raise ValueError(f"ip-api returned: {data.get('status')}")
    
    lat  = float(data['lat'])
    lon  = float(data['lon'])
    tz   = data['timezone']
    city = data.get('city', 'Unknown')
    
    if not (-90 <= lat <= 90):
      raise ValueError(f"Invalid lat from API: {lat}")
    if not (-180 <= lon <= 180):
      raise ValueError(f"Invalid lon from API: {lon}")
    
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
      ZoneInfo(tz)
    except ZoneInfoNotFoundError:
      raise ValueError(f"Unknown timezone from API: {tz}")
    
    logger.info(f"Detected location: {city} ({lat}, {lon}) {tz}")
    return lat, lon, tz, city
  
  except Exception as e:
    logger.warning(f"Location detection failed: {e}. Using fallback (Mecca).")
    return FALLBACK
