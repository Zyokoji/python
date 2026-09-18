import sys
from pathlib import Path

# Make the project root importable (config, database, utils, db_session)
# regardless of where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
