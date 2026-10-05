#!/usr/bin/env python3
"""Convert config.yaml profile to JSON for Chrome extension import."""

import json
import yaml
from pathlib import Path


def main():
    config_path = Path(__file__).parent.parent / "config.yaml"

    if not config_path.exists():
        print(f"Error: {config_path} not found")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    profile = config.get("profile", {})

    # Output JSON file for import
    output_path = Path(__file__).parent / "profile.json"
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"Profile exported to: {output_path}")
    print("\nTo import into Chrome extension:")
    print("1. Open the extension options page")
    print("2. Click 'Import Profile'")
    print("3. Select the profile.json file")


if __name__ == "__main__":
    main()
