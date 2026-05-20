import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from wellbeing_app.gui.pages.jamah_settings import JamahSettingsPage
from wellbeing_app.prayer.jamah import JamahStore
from wellbeing_app.storage.database import init_db

# Initialize GTK/Adw
Adw.init()

class TestJamahSettingsPage(unittest.TestCase):
  
  def setUp(self):
    init_db()
    self.store = JamahStore()
    # Ensure starting state
    self.store.set_iqamah_offset(5)
    self.store.set_jamah_time('fajr', '05:30')
    self.store.enable('fajr')
    
    self.page = JamahSettingsPage()

  def test_initial_values(self):
    # Verify JamahSettingsPage is instantiated successfully
    self.assertIsInstance(self.page, Gtk.ScrolledWindow)
    
    # We can inspect and change spin values
    self.assertEqual(self.store.get_iqamah_offset(), 5)

  def test_on_time_changed_validation(self):
    # Get a dummy entry
    entry = Gtk.Entry()
    
    # Valid time format
    entry.set_text("12:34")
    self.page._on_time_changed(entry, "dhuhr")
    self.assertFalse(entry.has_css_class("error"))
    self.assertEqual(self.store.get_jamah_time("dhuhr"), "12:34")
    
    # Invalid time format
    entry.set_text("25:61")
    self.page._on_time_changed(entry, "dhuhr")
    self.assertTrue(entry.has_css_class("error"))

  def test_on_clear(self):
    entry = Gtk.Entry()
    entry.set_text("12:34")
    entry.add_css_class("error")
    
    self.page._on_clear(None, "dhuhr", entry)
    self.assertEqual(entry.get_text(), "")
    self.assertFalse(entry.has_css_class("error"))
    self.assertIsNone(self.store.get_jamah_time("dhuhr"))

  def test_on_enabled_changed(self):
    toggle = Gtk.Switch()
    
    toggle.set_active(True)
    self.page._on_enabled_changed(toggle, None, "fajr")
    self.assertTrue(self.store.is_enabled("fajr"))
    
    toggle.set_active(False)
    self.page._on_enabled_changed(toggle, None, "fajr")
    self.assertFalse(self.store.is_enabled("fajr"))

if __name__ == '__main__':
  unittest.main()
