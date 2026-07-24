
import json
from datetime import datetime, timezone
from pathlib import Path

result = {
    "schemaVersion": 1,
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "status": "GitHub Actions test successful",
    "current": None,
    "upcoming": None
}

output_file = Path("docs/result.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with output_file.open("w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(f"Created: {output_file}")
