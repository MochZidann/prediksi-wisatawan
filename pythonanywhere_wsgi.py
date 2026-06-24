import sys
from pathlib import Path

project_home = Path.home() / "visitor_pulse_uas_ready"
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from app import app as application
