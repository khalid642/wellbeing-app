import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from wellbeing_app.gui.pages.dashboard import DashboardPage

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Wellbeing App")
        self.set_default_size(800, 600)
        
        # Ensure we respect system light/dark mode by using the default style manager
        Adw.StyleManager.get_default()
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)
        
        self.dashboard = DashboardPage()
        main_box.append(self.dashboard)
        
        self.set_content(main_box)
