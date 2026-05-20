from hijri_converter import Gregorian
from datetime import date

HIJRI_MONTHS = [
  'Muharram', 'Safar', "Rabi' al-Awwal", "Rabi' al-Thani",
  'Jumada al-Ula', 'Jumada al-Akhirah', 'Rajab', "Sha'ban",
  'Ramadan', 'Shawwal', "Dhu al-Qi'dah", 'Dhu al-Hijjah'
]

def gregorian_to_hijri(greg_date: date) -> str:
  if hasattr(greg_date, 'date'):
    greg_date = greg_date.date()
  
  hijri = Gregorian(greg_date.year, greg_date.month, greg_date.day).to_hijri()
  month_name = HIJRI_MONTHS[hijri.month - 1]
  return f"{hijri.day} {month_name} {hijri.year}"
