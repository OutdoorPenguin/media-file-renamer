# views.py
# Saves and loads favorite filter views

import json
from pathlib import Path

VIEWS_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/saved_views.json")

def save_view(name, filters):
    """Saves a named filter view."""
    views = load_all_views()
    views[name] = filters
    with open(VIEWS_FILE, "w") as f:
        json.dump(views, f, indent=2)

def load_all_views():
    """Loads all saved views."""
    if not VIEWS_FILE.exists():
        return {}
    with open(VIEWS_FILE, "r") as f:
        return json.load(f)

def delete_view(name):
    """Deletes a saved view by name."""
    views = load_all_views()
    if name in views:
        del views[name]
        with open(VIEWS_FILE, "w") as f:
            json.dump(views, f, indent=2)