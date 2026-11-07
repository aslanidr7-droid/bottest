from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load(open(ROOT / "config" / "settings.yaml"))
