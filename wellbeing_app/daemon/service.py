import time
import logging
from wellbeing_app.constants import LOGS_DIR

def run_daemon():
    log_file = LOGS_DIR / "daemon.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("WellbeingDaemon")
    logger.info("Daemon started")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Daemon stopped")
