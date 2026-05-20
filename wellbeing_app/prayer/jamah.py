import re
from wellbeing_app.storage.database import get_connection

class JamahStore:

  def __init__(self):
    self._time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')

  def get_jamah_time(self, prayer: str) -> str | None:
    prayer = prayer.lower()
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT time FROM jamah_times WHERE prayer = ?", (prayer,))
      row = cursor.fetchone()
      if row:
        return row[0]
    return None

  def set_jamah_time(self, prayer: str, time_str: str):
    prayer = prayer.lower()
    if not self._time_pattern.match(time_str):
      raise ValueError(f"Invalid time format: {time_str}. Must be HH:MM.")
    
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("UPDATE jamah_times SET time = ? WHERE prayer = ?", (time_str, prayer))
      conn.commit()

  def clear_jamah_time(self, prayer: str):
    prayer = prayer.lower()
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("UPDATE jamah_times SET time = NULL WHERE prayer = ?", (prayer,))
      conn.commit()

  def get_all_jamah_times(self) -> dict:
    times = {}
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT prayer, time FROM jamah_times")
      for row in cursor.fetchall():
        times[row[0]] = row[1]
    return times

  def is_jamah_set(self, prayer: str) -> bool:
    return self.get_jamah_time(prayer) is not None

  def is_enabled(self, prayer: str) -> bool:
    prayer = prayer.lower()
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT enabled FROM jamah_times WHERE prayer = ?", (prayer,))
      row = cursor.fetchone()
      if row:
        return bool(row[0])
    return False

  def enable(self, prayer: str):
    prayer = prayer.lower()
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("UPDATE jamah_times SET enabled = 1 WHERE prayer = ?", (prayer,))
      conn.commit()

  def disable(self, prayer: str):
    prayer = prayer.lower()
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("UPDATE jamah_times SET enabled = 0 WHERE prayer = ?", (prayer,))
      conn.commit()

  def get_iqamah_offset(self) -> int:
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT global_offset_minutes FROM iqamah_config LIMIT 1")
      row = cursor.fetchone()
      if row:
        return int(row[0])
    return 5

  def set_iqamah_offset(self, offset: int):
    if not (1 <= offset <= 30):
      raise ValueError(f"Iqamah offset must be between 1 and 30 minutes, got {offset}")
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("UPDATE iqamah_config SET global_offset_minutes = ?", (offset,))
      conn.commit()
