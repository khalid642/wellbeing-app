import sys
import argparse
from wellbeing_app.storage.database import init_db
from wellbeing_app.gui.application import WellbeingApplication
from wellbeing_app.daemon.service import run_daemon

def main():
    parser = argparse.ArgumentParser(description="Wellbeing App")
    parser.add_argument('--daemon', action='store_true', help="Run the background daemon")
    args, remaining = parser.parse_known_args()

    init_db()

    if args.daemon:
        run_daemon()
    else:
        app = WellbeingApplication()
        sys.exit(app.run([sys.argv[0]] + remaining))

if __name__ == "__main__":
    main()
