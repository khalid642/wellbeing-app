import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
  log_dir = os.path.expanduser('~/.local/state/wellbeing-app')
  os.makedirs(log_dir, exist_ok=True)
  log_file = os.path.join(log_dir, 'daemon.log')
  
  logger = logging.getLogger('wellbeing_app.daemon')
  logger.setLevel(logging.INFO)
  
  if not logger.handlers:
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s DAEMON: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also add a stream handler for stdout/stderr console visibility
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
  return logger
