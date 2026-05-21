import os
import json
import random
from pathlib import Path

class AdhanLibrary:

  def __init__(self, custom_dir: str = None, bundled_dir: str = None):
    self.custom_dir = Path(custom_dir or os.path.expanduser('~/.config/wellbeing-app/audio/adhan'))
    self.bundled_dir = Path(bundled_dir or os.path.abspath('data/audio/adhan'))
    self.SUPPORTED_EXTENSIONS = {'.mp3', '.ogg', '.wav', '.opus', '.m4a', '.flac'}

  def list_available_adhans(self) -> list[dict]:
    adhans = []
    
    # 1. Scan bundled dir
    if self.bundled_dir.exists():
      try:
        for entry in self.bundled_dir.iterdir():
          if entry.is_file() and entry.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            adhans.append({
              'name': entry.stem,
              'file_path': str(entry.absolute()),
              'is_custom': False
            })
      except Exception:
        pass
        
    # 2. Scan custom dir
    if self.custom_dir.exists():
      try:
        for entry in self.custom_dir.iterdir():
          if entry.is_file() and entry.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            if not any(a['file_path'] == str(entry.absolute()) for a in adhans):
              adhans.append({
                'name': entry.stem,
                'file_path': str(entry.absolute()),
                'is_custom': True
              })
      except Exception:
        pass
        
    return adhans

  def get_adhan_for_prayer(self, prayer_name: str, config) -> str:
    def get_val(obj, key, default=None):
      if isinstance(obj, dict):
        return obj.get(key, default)
      try:
        return obj[key]
      except Exception:
        pass
      try:
        return getattr(obj, key, default)
      except Exception:
        return default

    audio_file = get_val(config, 'audio_file')
    audio_file_list_raw = get_val(config, 'audio_file_list')
    random_selection = bool(get_val(config, 'random_selection', 0))
    
    selected_path = None
    
    # 1. Try random selection if requested
    if random_selection and audio_file_list_raw:
      try:
        if isinstance(audio_file_list_raw, str):
          paths = json.loads(audio_file_list_raw)
        elif isinstance(audio_file_list_raw, list):
          paths = audio_file_list_raw
        else:
          paths = []
          
        if paths:
          selected_path = random.choice(paths)
      except Exception:
        pass
        
    # 2. Fall back to direct audio_file if no random path was selected
    if not selected_path:
      selected_path = audio_file
      
    # 3. Check if the path actually exists on disk (or is special "sine" identifier)
    # If not, fall back to first available bundled adhan, custom adhan, or "sine"
    if not selected_path or (selected_path != "sine" and not os.path.exists(selected_path)):
      available = self.list_available_adhans()
      bundled = [a for a in available if not a['is_custom']]
      if bundled:
        selected_path = bundled[0]['file_path']
      elif available:
        selected_path = available[0]['file_path']
      else:
        selected_path = "sine"
        
    return selected_path
