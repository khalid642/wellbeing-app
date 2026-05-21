import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw, GLib, Gio
import os
import sys
import signal
import subprocess
import logging

from wellbeing_app.gui.pages import (
  DashboardPage,
  JamahSettingsPage,
  EyeCareSettingsPage,
  PrayerSettingsPage,
  AdhanSettingsPage
)

logger = logging.getLogger(__name__)

NAV_ITEMS = [
  ('weather-clear-symbolic',        'Dashboard',     'dashboard'),
  ('preferences-system-symbolic',   'Prayer',        'prayer'),
  ('audio-volume-high-symbolic',    'Adhan',         'adhan'),
  ('object-select-symbolic',        'Jamah',         'jamah'),
  ('view-refresh-symbolic',         'Zikr',          'zikr'),
  ('list-add-symbolic',             'Overlays',      'overlays'),
  ('applications-system-symbolic',  'Widgets',       'widgets'),
  ('document-save-symbolic',        'Reminders',     'reminders'),
  ('media-playback-start-symbolic', 'Theme',         'theme'),
  ('document-open-symbolic',        'Audio',         'audio'),
  ('user-info-symbolic',            'Import/Export', 'import_export'),
  ('open-menu-symbolic',            'Plugins',       'plugins'),
  ('text-x-generic-symbolic',       'Logs',          'logs')
]

class MainWindow(Adw.ApplicationWindow):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.set_title("Wellbeing App")
    self.set_default_size(1100, 720)
    
    # Respect light/dark mode
    Adw.StyleManager.get_default()
    
    self._build_ui()
    
    # Update subtitle every 30 seconds
    self.update_header_subtitle()
    GLib.timeout_add_seconds(30, self.update_header_subtitle)
    
    # Update daemon status dot every 5 seconds
    self.update_daemon_status()
    GLib.timeout_add_seconds(5, self.update_daemon_status)

  def _build_ui(self):
    # Main split horizontal box
    self.main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    self.set_content(self.main_hbox)
    
    # 1. Left Sidebar Pane (Toolbar + HeaderBar)
    self.sidebar_toolbar = Adw.ToolbarView()
    self.sidebar_toolbar.add_css_class('sidebar-panel')
    self.sidebar_toolbar.set_size_request(200, -1)
    
    sidebar_header = Adw.HeaderBar()
    sidebar_header.set_show_start_title_buttons(False)
    sidebar_header.set_show_end_title_buttons(False)
    
    # Set blank center title widget to prevent duplicate automatic window title
    sidebar_header.set_title_widget(Gtk.Label(label=""))
    
    # Left search button
    search_icon = Gtk.Image.new_from_icon_name('system-search-symbolic')
    search_btn = Gtk.Button()
    search_btn.set_child(search_icon)
    search_btn.add_css_class('flat')
    sidebar_header.pack_start(search_btn)
    
    # Left-aligned Title
    sidebar_title = Gtk.Label(label='Wellbeing')
    sidebar_title.add_css_class('title-2')
    sidebar_title.add_css_class('bold')
    sidebar_title.set_margin_start(8)
    sidebar_header.pack_start(sidebar_title)
    
    # Sidebar Hide Button on the right of its header
    sidebar_toggle_icon = Gtk.Image.new_from_icon_name('sidebar-show-symbolic')
    sidebar_hide_btn = Gtk.Button()
    sidebar_hide_btn.set_child(sidebar_toggle_icon)
    sidebar_hide_btn.add_css_class('flat')
    sidebar_hide_btn.connect('clicked', self._on_sidebar_toggle_clicked)
    sidebar_header.pack_end(sidebar_hide_btn)
    
    self.sidebar_toolbar.add_top_bar(sidebar_header)
    
    # Sidebar vertical box contents
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sidebar.add_css_class('navigation-sidebar')
    sidebar.set_vexpand(True)
    
    # Navigation list
    self.nav_list = Gtk.ListBox()
    self.nav_list.add_css_class('navigation-sidebar')
    self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    self.nav_list.set_vexpand(True)
    self.nav_list.connect('row-selected', self._on_nav_selected)
    
    # Build list items
    for icon_name, label_text, _ in NAV_ITEMS:
      row = self.make_nav_row(icon_name, label_text)
      self.nav_list.append(row)
      
    # ScrolledWindow for sidebar list to prevent overflow
    sidebar_scroll = Gtk.ScrolledWindow()
    sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sidebar_scroll.set_child(self.nav_list)
    sidebar_scroll.set_vexpand(True)
    sidebar.append(sidebar_scroll)
    
    # Bottom Status Bar (Wrapped in an interactive Flat Button and Popover)
    status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    status_bar.set_margin_start(16)
    status_bar.set_margin_end(16)
    status_bar.set_margin_top(12)
    status_bar.set_margin_bottom(12)
    
    self.status_dot = Gtk.Label(label='●')
    self.status_dot.add_css_class('dim-label')
    
    self.status_lbl = Gtk.Label(label='Daemon stopped')
    self.status_lbl.add_css_class('caption')
    self.status_lbl.add_css_class('dim-label')
    
    status_bar.append(self.status_dot)
    status_bar.append(self.status_lbl)
    
    self.status_button = Gtk.Button()
    self.status_button.add_css_class('flat')
    self.status_button.set_child(status_bar)
    self.status_button.connect('clicked', self._on_status_clicked)
    
    # Setup interactive popover action menu
    self.status_popover = Gtk.Popover()
    self.status_popover.set_parent(self.status_button)
    self.status_popover.set_autohide(True)
    
    popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    popover_box.set_margin_start(8)
    popover_box.set_margin_end(8)
    popover_box.set_margin_top(8)
    popover_box.set_margin_bottom(8)
    
    self.popover_btn = Gtk.Button(label='Start Daemon')
    self.popover_btn.add_css_class('suggested-action')
    self.popover_btn.connect('clicked', self._on_popover_action)
    popover_box.append(self.popover_btn)
    
    self.status_popover.set_child(popover_box)
    sidebar.append(self.status_button)
    
    self.sidebar_toolbar.set_content(sidebar)
    self.main_hbox.append(self.sidebar_toolbar)
    
    # Vertical Separator separating compact sidebar from content
    sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    self.main_hbox.append(sep)
    
    # 2. Right Content Pane (Toolbar + HeaderBar)
    content_toolbar = Adw.ToolbarView()
    content_toolbar.set_hexpand(True)
    content_toolbar.set_vexpand(True)
    
    content_header = Adw.HeaderBar()
    content_header.set_show_start_title_buttons(False)
    content_header.set_show_end_title_buttons(True)
    
    # Sidebar Show Button on the left of content header (visible when sidebar is hidden)
    content_toggle_icon = Gtk.Image.new_from_icon_name('sidebar-show-symbolic')
    self.content_show_btn = Gtk.Button()
    self.content_show_btn.set_child(content_toggle_icon)
    self.content_show_btn.add_css_class('flat')
    self.content_show_btn.connect('clicked', self._on_sidebar_toggle_clicked)
    self.content_show_btn.set_visible(False)
    content_header.pack_start(self.content_show_btn)
    
    self.title_widget = Adw.WindowTitle(title='Dashboard', subtitle='')
    content_header.set_title_widget(self.title_widget)
    
    # End Menu Button
    menu_btn = Gtk.MenuButton()
    menu_btn.set_icon_name('open-menu-symbolic')
    content_header.pack_end(menu_btn)
    
    content_toolbar.add_top_bar(content_header)
    
    # Content vertical box container
    right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    right_box.set_hexpand(True)
    right_box.set_vexpand(True)
    
    self.banner = Adw.Banner()
    self.banner.set_title("Warning: Wellbeing background daemon is not running. Prayer alerts and overlays will not trigger.")
    self.banner.set_button_label("Start Daemon")
    self.banner.connect('button-clicked', self._on_start_daemon_clicked)
    self.banner.set_revealed(True)
    
    right_box.append(self.banner)
    
    self.content_stack = Gtk.Stack()
    self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    self.content_stack.set_transition_duration(200)
    self.content_stack.set_hexpand(True)
    self.content_stack.set_vexpand(True)
    
    right_box.append(self.content_stack)
    content_toolbar.set_content(right_box)
    self.main_hbox.append(content_toolbar)
    
    # Instantiate Pages
    self.dashboard_page = DashboardPage()
    self.prayer_page = PrayerSettingsPage(self.dashboard_page)
    self.adhan_page = AdhanSettingsPage()
    self.jamah_page = JamahSettingsPage()
    self.widgets_page = EyeCareSettingsPage() # Custom widgets configuration
    
    # Add named pages
    self.content_stack.add_named(self.dashboard_page, 'dashboard')
    self.content_stack.add_named(self.prayer_page, 'prayer')
    self.content_stack.add_named(self.adhan_page, 'adhan')
    self.content_stack.add_named(self.jamah_page, 'jamah')
    self.content_stack.add_named(self.widgets_page, 'widgets')
    
    # Add placeholders for the remaining options
    self.content_stack.add_named(self.make_placeholder('Zikr'), 'zikr')
    self.content_stack.add_named(self.make_placeholder('Overlays'), 'overlays')
    self.content_stack.add_named(self.make_placeholder('Reminders'), 'reminders')
    self.content_stack.add_named(self.make_placeholder('Theme'), 'theme')
    self.content_stack.add_named(self.make_placeholder('Audio'), 'audio')
    self.content_stack.add_named(self.make_placeholder('Import/Export'), 'import_export')
    self.content_stack.add_named(self.make_placeholder('Plugins'), 'plugins')
    self.content_stack.add_named(self.make_placeholder('Logs'), 'logs')
    
    # Select start page
    self.content_stack.set_visible_child_name('dashboard')
    self.nav_list.select_row(self.nav_list.get_row_at_index(0))

  def make_nav_row(self, icon_name: str, label_text: str) -> Gtk.ListBoxRow:
    row = Gtk.ListBoxRow()
    row.set_margin_start(4)
    row.set_margin_end(4)
    row.set_margin_top(2)
    row.set_margin_bottom(2)
    
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box.set_margin_start(8)
    box.set_margin_end(8)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    
    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.set_icon_size(Gtk.IconSize.NORMAL)
    icon.add_css_class('dim-label')
    
    label = Gtk.Label(label=label_text, xalign=0, hexpand=True)
    
    box.append(icon)
    box.append(label)
    row.set_child(box)
    return row

  def make_placeholder(self, name: str) -> Gtk.Label:
    label = Gtk.Label(label=f'{name} — coming in a later phase')
    label.add_css_class('dim-label')
    label.set_vexpand(True)
    label.set_valign(Gtk.Align.CENTER)
    return label

  def _on_nav_selected(self, listbox, row):
    if row is None:
      return
    idx = row.get_index()
    if 0 <= idx < len(NAV_ITEMS):
      _, _, stack_name = NAV_ITEMS[idx]
      self.content_stack.set_visible_child_name(stack_name)
      logger.info(f"Navigation selection changed to index {idx}: {stack_name}")

  def update_header_subtitle(self):
    try:
      next_p, next_t = self.dashboard_page.prayer_engine.get_next_prayer()
      time_str = next_t.strftime('%H:%M')
      self.title_widget.set_subtitle(f"Next: {next_p.capitalize()} {time_str}")
    except Exception as e:
      logger.warning(f"Failed to update Header subtitle: {e}")
      self.title_widget.set_subtitle("")
    return GLib.SOURCE_CONTINUE

  def update_daemon_status(self):
    # Check if daemon process is currently running by scanning /proc filesystem natively
    running = False
    try:
      my_pid = os.getpid()
      for pid_str in os.listdir('/proc'):
        if pid_str.isdigit():
          pid = int(pid_str)
          if pid == my_pid:
            continue
          try:
            with open(os.path.join('/proc', pid_str, 'cmdline'), 'r') as f:
              cmdline = f.read().replace('\0', ' ')
              if '--daemon' in cmdline and 'wellbeing' in cmdline:
                running = True
                break
          except Exception:
            pass
    except Exception:
      # Fallback to simple pgrep if /proc read fails
      try:
        res = subprocess.run(["pgrep", "-f", "--daemon"], capture_output=True)
        running = res.returncode == 0
      except Exception:
        running = False
      
    # Clean style classes
    self.status_dot.remove_css_class('success')
    self.status_dot.remove_css_class('error')
    
    if running:
      self.status_dot.add_css_class('success')
      self.status_lbl.set_text("Daemon running")
      self.banner.set_revealed(False)
    else:
      self.status_dot.add_css_class('error')
      self.status_lbl.set_text("Daemon stopped")
      self.banner.set_revealed(True)
      
    return GLib.SOURCE_CONTINUE

  def _on_start_daemon_clicked(self, banner):
    self.start_daemon()

  def _on_status_clicked(self, button):
    # Toggle popover based on current daemon status
    is_running = self.status_lbl.get_text() == "Daemon running"
    if is_running:
      self.popover_btn.set_label("Stop Daemon")
      self.popover_btn.remove_css_class('suggested-action')
      self.popover_btn.add_css_class('destructive-action')
    else:
      self.popover_btn.set_label("Start Daemon")
      self.popover_btn.remove_css_class('destructive-action')
      self.popover_btn.add_css_class('suggested-action')
    
    self.status_popover.popup()

  def _on_popover_action(self, btn):
    self.status_popover.popdown()
    is_running = self.status_lbl.get_text() == "Daemon running"
    if is_running:
      self.stop_daemon()
    else:
      self.start_daemon()

  def start_daemon(self):
    try:
      # Start detached daemon process
      subprocess.Popen(
        [sys.executable, "-m", "wellbeing_app.main", "--daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
      )
      # Trigger immediate status update check
      GLib.timeout_add(500, self.update_daemon_status)
    except Exception as e:
      logger.error(f"Failed to start daemon: {e}")

  def stop_daemon(self):
    try:
      my_pid = os.getpid()
      terminated = False
      for pid_str in os.listdir('/proc'):
        if pid_str.isdigit():
          pid = int(pid_str)
          if pid == my_pid:
            continue
          try:
            with open(os.path.join('/proc', pid_str, 'cmdline'), 'r') as f:
              cmdline = f.read().replace('\0', ' ')
              if '--daemon' in cmdline and 'wellbeing' in cmdline:
                os.kill(pid, signal.SIGTERM)
                terminated = True
          except Exception:
            pass
      if not terminated:
        subprocess.run(["pkill", "-f", "--daemon"])
      
      # Trigger immediate status update check
      GLib.timeout_add(500, self.update_daemon_status)
    except Exception as e:
      logger.error(f"Failed to stop daemon: {e}")

  def _on_sidebar_toggle_clicked(self, btn):
    is_visible = self.sidebar_toolbar.get_visible()
    self.sidebar_toolbar.set_visible(not is_visible)
    self.content_show_btn.set_visible(is_visible)
