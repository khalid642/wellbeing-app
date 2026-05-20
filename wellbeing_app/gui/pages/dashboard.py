import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk

class DashboardPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.set_margin_top(48)
        self.set_margin_bottom(48)
        self.set_margin_start(48)
        self.set_margin_end(48)
        
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        welcome_label = Gtk.Label(label="Welcome to Wellbeing App")
        welcome_label.add_css_class("title-1")
        self.append(welcome_label)

        subtitle_label = Gtk.Label(label="Your Islamic digital companion")
        subtitle_label.add_css_class("dim-label")
        self.append(subtitle_label)

        glass_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        glass_card.add_css_class("glass-card")
        glass_card.set_margin_top(24)
        glass_card.set_size_request(300, 200)
        
        card_label = Gtk.Label(label="Dashboard Placeholder")
        card_label.set_valign(Gtk.Align.CENTER)
        card_label.set_vexpand(True)
        glass_card.append(card_label)
        
        self.append(glass_card)
