#!/usr/bin/env python
"""Generate and export all schemas"""

import json
import os
from pathlib import Path
from schemas import SCHEMAS, print_schemas
from topics import print_topic_info


def main():
    print("\n" + "="*70)
    print("EVENT SCHEMAS - All Kafka Topics")
    print("="*70)

    # Print schemas
    print_schemas()

    # Print topic info
    print("\n" + "="*70)
    print("TOPIC CONFIGURATION")
    print("="*70)
    print_topic_info()

    # Export schemas to JSON files
    schema_dir = Path(__file__).parent / "schemas_json"
    schema_dir.mkdir(exist_ok=True)

    print(f"\n" + "="*70)
    print(f"EXPORTING SCHEMAS TO {schema_dir}")
    print("="*70)

    for topic, schema in SCHEMAS.items():
        filename = topic.replace(".", "_").replace("-", "_") + ".json"
        filepath = schema_dir / filename

        with open(filepath, "w") as f:
            json.dump(schema, f, indent=2)

        print(f"✓ {filename}")

    print(f"\nSchemas exported to: {schema_dir}")


if __name__ == "__main__":
    main()
