import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk
import json
import logging

from wellbeing_app.storage.database import get_connection, db
from wellbeing_app.overlay_engine.overlay_manager import OverlayManager
from wellbeing_app.overlay_engine.overlay_window import OverlayConfig

logger = logging.getLogger(__name__)

class EyeCareSettingsPage(Gtk.ScrolledWindow):

  def __init__(self):
    super().__init__()
    self.set_propagate_natural_width(True)
    self.set_propagate_natural_height(False)
    
    self._load_settings()
    self._build_ui()

  def _load_settings(self):
    # Load interval, lock duration, and enable state from DB
    self.eyecare_enabled = True
    self.interval_minutes = 20
    self.lock_seconds = 20
    
    with get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT key, value FROM app_config")
      for key, val in cursor.fetchall():
        if key == 'eyecare_enabled':
          self.eyecare_enabled = val == '1'
        elif key == 'eyecare_interval_minutes':
          try:
            self.interval_minutes = int(val)
          except ValueError:
            pass
        elif key == 'eyecare_lock_seconds':
          try:
            self.lock_seconds = int(val)
          except ValueError:
            pass

  def _set_config_value(self, key: str, value: str):
    with get_connection() as conn:
      conn.execute("""
        INSERT OR REPLACE INTO app_config (key, value)
        VALUES (?, ?)
      """, (key, value))
      conn.commit()

  def _build_ui(self):
    self.inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    self.inner.set_margin_top(24)
    self.inner.set_margin_bottom(24)
    self.inner.set_margin_start(24)
    self.inner.set_margin_end(24)
    self.set_child(self.inner)
    
    # --- Group 1: General Settings ---
    general_group = Adw.PreferencesGroup(title='Eye-Care General Settings')
    
    # 1. Enable Toggle
    enable_row = Adw.ActionRow(title='Enable Eye-Care Scheduler')
    self.enable_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
    self.enable_switch.set_active(self.eyecare_enabled)
    self.enable_switch.connect('notify::active', self._on_enable_toggled)
    enable_row.add_suffix(self.enable_switch)
    general_group.add(enable_row)
    
    # 2. Interval SpinButton
    interval_row = Adw.ActionRow(
      title='Eye-care Interval (Minutes)',
      subtitle='Time between wellness breaks'
    )
    self.interval_spin = Gtk.SpinButton.new_with_range(1, 120, 1)
    self.interval_spin.set_value(self.interval_minutes)
    self.interval_spin.set_valign(Gtk.Align.CENTER)
    self.interval_spin.connect('value-changed', self._on_interval_changed)
    interval_row.add_suffix(self.interval_spin)
    general_group.add(interval_row)
    
    # 3. Lock Duration SpinButton
    lock_row = Adw.ActionRow(
      title='Lock Duration (Seconds)',
      subtitle='Breathing/wellness session length'
    )
    self.lock_spin = Gtk.SpinButton.new_with_range(5, 300, 5)
    self.lock_spin.set_value(self.lock_seconds)
    self.lock_spin.set_valign(Gtk.Align.CENTER)
    self.lock_spin.connect('value-changed', self._on_lock_changed)
    lock_row.add_suffix(self.lock_spin)
    general_group.add(lock_row)
    
    self.inner.append(general_group)
    
    # --- Group 2: Eye-Care Widgets ---
    self.eyecare_group = Adw.PreferencesGroup(
      title='Eye-Care Screen Widgets',
      description='Order of widgets displayed during focus break overlay'
    )
    self.eyecare_listbox = Gtk.ListBox()
    self.eyecare_listbox.add_css_class("boxed-list")
    self.eyecare_group.add(self.eyecare_listbox)
    
    # Add Widget Button
    add_ec_btn = Gtk.Button(label="Add Widget")
    add_ec_btn.set_halign(Gtk.Align.END)
    add_ec_btn.connect('clicked', self._on_add_widget_clicked, 'eyecare')
    self.eyecare_group.add(add_ec_btn)
    
    self.inner.append(self.eyecare_group)
    
    # --- Group 3: Zikr Widgets ---
    self.zikr_group = Adw.PreferencesGroup(
      title='Zikr Overlay Widgets',
      description='Order of widgets displayed in spiritual follow-up overlay'
    )
    self.zikr_listbox = Gtk.ListBox()
    self.zikr_listbox.add_css_class("boxed-list")
    self.zikr_group.add(self.zikr_listbox)
    
    # Add Widget Button
    add_zikr_btn = Gtk.Button(label="Add Widget")
    add_zikr_btn.set_halign(Gtk.Align.END)
    add_zikr_btn.connect('clicked', self._on_add_widget_clicked, 'zikr')
    self.zikr_group.add(add_zikr_btn)
    
    self.inner.append(self.zikr_group)
    
    # --- Group 4: Diagnostic Actions ---
    action_group = Adw.PreferencesGroup(title='Testing &amp; Troubleshooting')
    
    test_ec_btn = Gtk.Button(label="Test Eye-Care Overlay (5s)")
    test_ec_btn.connect('clicked', self._on_test_eyecare_clicked)
    action_group.add(test_ec_btn)
    
    test_zikr_btn = Gtk.Button(label="Test Zikr Overlay")
    test_zikr_btn.connect('clicked', self._on_test_zikr_clicked)
    action_group.add(test_zikr_btn)
    
    self.inner.append(action_group)
    
    # Render assigned list elements
    self._refresh_list('eyecare')
    self._refresh_list('zikr')

  def _refresh_list(self, slot: str):
    listbox = self.eyecare_listbox if slot == 'eyecare' else self.zikr_listbox
    
    # Clear current elements
    while True:
      row = listbox.get_row_at_index(0)
      if row is None:
        break
      listbox.remove(row)
      
    # Load from DB
    widgets = db.get_overlay_widgets(slot)
    
    for idx, w in enumerate(widgets):
      row = Adw.ActionRow(title=f"{w.widget_type.replace('_', ' ').title()}")
      row.set_subtitle(f"Order: {w.display_order}")
      
      # Directional controls (Up / Down)
      up_btn = Gtk.Button()
      up_btn.set_icon_name('pan-start-symbolic')
      up_btn.add_css_class('flat')
      up_btn.set_valign(Gtk.Align.CENTER)
      up_btn.set_sensitive(idx > 0)
      up_btn.connect('clicked', self._on_reorder_clicked, slot, idx, -1)
      
      down_btn = Gtk.Button()
      down_btn.set_icon_name('pan-down-symbolic')
      down_btn.add_css_class('flat')
      down_btn.set_valign(Gtk.Align.CENTER)
      down_btn.set_sensitive(idx < len(widgets) - 1)
      down_btn.connect('clicked', self._on_reorder_clicked, slot, idx, 1)
      
      # Delete Action
      delete_btn = Gtk.Button()
      delete_btn.set_icon_name('edit-delete-symbolic')
      delete_btn.add_css_class('flat')
      delete_btn.set_valign(Gtk.Align.CENTER)
      delete_btn.connect('clicked', self._on_delete_clicked, slot, w.template_id, w.display_order)
      
      row.add_suffix(up_btn)
      row.add_suffix(down_btn)
      row.add_suffix(delete_btn)
      
      listbox.append(row)

  def _on_enable_toggled(self, switch, pspec):
    active = switch.get_active()
    self._set_config_value('eyecare_enabled', '1' if active else '0')

  def _on_interval_changed(self, spin):
    val = int(spin.get_value())
    self._set_config_value('eyecare_interval_minutes', str(val))

  def _on_lock_changed(self, spin):
    val = int(spin.get_value())
    self._set_config_value('eyecare_lock_seconds', str(val))

  def _on_reorder_clicked(self, btn, slot: str, index: int, direction: int):
    # Fetch current assignments
    with get_connection() as conn:
      rows = conn.execute("""
        SELECT id, display_order FROM overlay_widget_assignments
        WHERE overlay_slot = ? AND enabled = 1
        ORDER BY display_order ASC
      """, (slot,)).fetchall()
      
      if not rows or index < 0 or index >= len(rows):
        return
        
      target_idx = index + direction
      if target_idx < 0 or target_idx >= len(rows):
        return
        
      id1, o1 = rows[index]
      id2, o2 = rows[target_idx]
      
      # Swap orders
      conn.execute("UPDATE overlay_widget_assignments SET display_order = ? WHERE id = ?", (o2, id1))
      conn.execute("UPDATE overlay_widget_assignments SET display_order = ? WHERE id = ?", (o1, id2))
      conn.commit()
      
    self._refresh_list(slot)

  def _on_delete_clicked(self, btn, slot: str, template_id: int, display_order: int):
    with get_connection() as conn:
      conn.execute("""
        DELETE FROM overlay_widget_assignments
        WHERE overlay_slot = ? AND widget_template_id = ? AND display_order = ?
      """, (slot, template_id, display_order))
      conn.commit()
      
    self._refresh_list(slot)

  def _on_add_widget_clicked(self, btn, slot: str):
    # Retrieve available templates
    templates = []
    with get_connection() as conn:
      templates = conn.execute("SELECT id, name, widget_type FROM widget_templates").fetchall()
      
    if not templates:
      return
      
    # Create simple picker dialog
    dialog = Gtk.Dialog(title="Select Widget Template")
    dialog.set_transient_for(self.get_root())
    dialog.set_modal(True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Add", Gtk.ResponseType.OK)
    
    content_area = dialog.get_content_area()
    content_area.set_spacing(12)
    content_area.set_margin_top(16)
    content_area.set_margin_bottom(16)
    content_area.set_margin_start(16)
    content_area.set_margin_end(16)
    
    label = Gtk.Label(label="Choose a widget template to insert:")
    content_area.append(label)
    
    dropdown = Gtk.DropDown()
    string_list = Gtk.StringList.new([f"{t[1]} ({t[2]})" for t in templates])
    dropdown.set_model(string_list)
    content_area.append(dropdown)
    
    def on_response(dialog, response_id):
      if response_id == Gtk.ResponseType.OK:
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(templates):
          t_id = templates[selected_index][0]
          
          # Insert assignment with max display order + 1
          with get_connection() as conn:
            max_order_row = conn.execute("""
              SELECT MAX(display_order) FROM overlay_widget_assignments
              WHERE overlay_slot = ?
            """, (slot,)).fetchone()
            max_order = (max_order_row[0] or 0) + 1
            
            conn.execute("""
              INSERT INTO overlay_widget_assignments (overlay_slot, widget_template_id, display_order, enabled)
              VALUES (?, ?, ?, 1)
            """, (slot, t_id, max_order))
            conn.commit()
            
          self._refresh_list(slot)
      dialog.destroy()
      
    dialog.connect('response', on_response)
    dialog.present()

  def _on_test_eyecare_clicked(self, btn):
    widgets = db.get_overlay_widgets('eyecare')
    config = OverlayConfig(
      mode='locked',
      duration_seconds=5,
      widgets=widgets,
      overlay_id='eyecare'
    )
    OverlayManager.get().show_overlay(config)

  def _on_test_zikr_clicked(self, btn):
    widgets = db.get_overlay_widgets('zikr')
    config = OverlayConfig(
      mode='unlocked',
      duration_seconds=0,
      widgets=widgets,
      overlay_id='zikr'
    )
    OverlayManager.get().show_overlay(config)
