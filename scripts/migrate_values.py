"""
OBSOLETE: The Value model was removed in migration 0094. Topic no longer has
a "parents" M2M (removed in 0106). This script cannot run.

To restore value topics:
  1. Prepare a CSV with columns: name [, slug, description]
  2. Run: python manage.py load_values path/to/values.csv

See narratives/management/commands/load_values.py
"""
import sys

if __name__ == "__main__":
    print(__doc__)
    sys.exit(1)
