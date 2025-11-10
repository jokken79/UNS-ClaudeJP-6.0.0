"""
Analyze the photo mappings from the old project
"""
import json
from pathlib import Path

# Load the old photo mappings
old_project = Path("D:/UNS-ClaudeJP-4.2Ultimo/UNS-ClaudeJP-4.2")
photo_mappings_file = old_project / "access_photo_mappings.json"

print("Loading photo mappings...")
with open(photo_mappings_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\nMetadata:")
print(f"  Timestamp: {data.get('timestamp')}")
print(f"  Database: {data.get('access_database')}")
print(f"  Table: {data.get('table')}")
print(f"  Photo field: {data.get('photo_field')}")

print(f"\nStatistics:")
stats = data.get('statistics', {})
for key, value in stats.items():
    print(f"  {key}: {value}")

# Analyze mappings
mappings = data.get('mappings', {})
print(f"\nTotal mappings: {len(mappings)}")

# Show first few mappings
print(f"\nFirst 5 mappings:")
for idx, (key, value) in enumerate(list(mappings.items())[:5], 1):
    print(f"\n[{idx}] Rirekisho ID: {key}")
    if isinstance(value, dict):
        for k, v in value.items():
            if k == 'photo_data' and isinstance(v, str):
                print(f"  {k}: [Base64 data, length={len(v)}]")
            else:
                print(f"  {k}: {v}")
    else:
        print(f"  Type: {type(value)}")
        print(f"  Value: {str(value)[:100]}")

# Check if photos are stored as base64
first_mapping = list(mappings.values())[0]
if isinstance(first_mapping, dict) and 'photo_data' in first_mapping:
    photo_data = first_mapping['photo_data']
    if isinstance(photo_data, str) and photo_data.startswith('/9j/') or photo_data.startswith('iVBO'):
        print(f"\n✓ Photos are stored as Base64 in the mappings!")
        print(f"  Sample length: {len(photo_data)} characters")
