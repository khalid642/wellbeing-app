import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from wellbeing_app.gui.pages.dashboard import DashboardPage
from wellbeing_app.gui.pages.prayer_settings import PrayerSettingsPage
from wellbeing_app.gui.pages.adhan_settings import AdhanSettingsPage
from wellbeing_app.gui.main_window import MainWindow
from wellbeing_app.storage.database import init_db

# Initialize GTK/Adw
Adw.init()

class TestMainWindowAndPages(unittest.TestCase):

  def setUp(self):
    init_db()

  def test_dashboard_page(self):
    page = DashboardPage()
    self.assertIsInstance(page, Gtk.ScrolledWindow)
    
    # Check that grid dictionary exists
    self.assertTrue(len(page._prayer_labels) > 0)
    self.assertIn('fajr', page._prayer_labels)

  def test_prayer_settings_page(self):
    dash = DashboardPage()
    page = PrayerSettingsPage(dashboard_page=dash)
    self.assertIsInstance(page, Gtk.ScrolledWindow)
    
    # Check location fields are created
    self.assertIsNotNone(page._mode_row)
    self.assertIsNotNone(page._lat_row)
    self.assertIsNotNone(page._lon_row)
    self.assertIsNotNone(page._tz_row)

  def test_adhan_settings_page(self):
    page = AdhanSettingsPage()
    self.assertIsInstance(page, Gtk.ScrolledWindow)
    
    # Check 5 expanders exist
    self.assertEqual(len(page.expanders), 5)
    self.assertIn('fajr', page.expanders)

  def test_main_window(self):
    win = MainWindow()
    self.assertIsInstance(win, Adw.ApplicationWindow)
    self.assertEqual(win.get_title(), "Wellbeing App")
    
    # Check stack exists
    self.assertIsNotNone(win.content_stack)
    self.assertIsNotNone(win.nav_list)
    
    # Check stack pages exist
    self.assertIsNotNone(win.content_stack.get_child_by_name('dashboard'))
    self.assertIsNotNone(win.content_stack.get_child_by_name('prayer'))
    self.assertIsNotNone(win.content_stack.get_child_by_name('adhan'))
    self.assertIsNotNone(win.content_stack.get_child_by_name('jamah'))
    self.assertIsNotNone(win.content_stack.get_child_by_name('widgets'))

if __name__ == '__main__':
  unittest.main()
