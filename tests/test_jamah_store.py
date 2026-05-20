import unittest
from wellbeing_app.storage.database import init_db
from wellbeing_app.prayer.jamah import JamahStore

class TestJamahStore(unittest.TestCase):
  
  def setUp(self):
    init_db()
    self.store = JamahStore()

  def test_get_and_set_jamah_time(self):
    # Set valid time
    self.store.set_jamah_time('fajr', '05:30')
    self.assertEqual(self.store.get_jamah_time('fajr'), '05:30')
    self.assertTrue(self.store.is_jamah_set('fajr'))
    
    # Check invalid format
    with self.assertRaises(ValueError):
      self.store.set_jamah_time('fajr', '5:30')
    with self.assertRaises(ValueError):
      self.store.set_jamah_time('fajr', '25:30')
    with self.assertRaises(ValueError):
      self.store.set_jamah_time('fajr', '05:60')
    with self.assertRaises(ValueError):
      self.store.set_jamah_time('fajr', 'abcd')
      
    # Clear time
    self.store.clear_jamah_time('fajr')
    self.assertIsNone(self.store.get_jamah_time('fajr'))
    self.assertFalse(self.store.is_jamah_set('fajr'))

  def test_enable_disable(self):
    self.store.enable('dhuhr')
    self.assertTrue(self.store.is_enabled('dhuhr'))
    self.store.disable('dhuhr')
    self.assertFalse(self.store.is_enabled('dhuhr'))

  def test_get_all_jamah_times(self):
    self.store.set_jamah_time('asr', '16:45')
    self.store.clear_jamah_time('isha')
    all_times = self.store.get_all_jamah_times()
    self.assertEqual(all_times['asr'], '16:45')
    self.assertIsNone(all_times['isha'])

  def test_iqamah_offset(self):
    self.store.set_iqamah_offset(10)
    self.assertEqual(self.store.get_iqamah_offset(), 10)
    with self.assertRaises(ValueError):
      self.store.set_iqamah_offset(0)
    with self.assertRaises(ValueError):
      self.store.set_iqamah_offset(35)

if __name__ == '__main__':
  unittest.main()
