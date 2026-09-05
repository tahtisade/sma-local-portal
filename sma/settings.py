import os
import yaml


def load_settings(filename="settings.yaml"):
    if not os.path.exists(filename):
        return {}

    with open(filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
