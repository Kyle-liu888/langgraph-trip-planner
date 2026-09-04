"""Check staged patches against private local credentials without printing their values."""
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
config = Path.home() / "dev/config"
diff = subprocess.check_output(["git", "diff", "--cached", "--no-ext-diff"], cwd=root, text=True)
files = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=root, text=True).splitlines()
for path in files:
    name = Path(path).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example") or \
            name.endswith((".dump", ".vhdx", ".sqlite", ".db")):
        raise SystemExit(f"Private/local state file is staged: {path}")
values = []
for file in config.glob("*"):
    if not file.is_file():
        continue
    if file.suffix == ".env":
        for line in file.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            if re.search(r"KEY|SECRET|PASSWORD|DATABASE_URL", key, re.I):
                value = value.strip().strip('"').strip("'")
                if len(value) >= 12 and not value.startswith("your"):
                    values.append(value)
    elif file.name.startswith("db-") and file.suffix == ".json":
        values.append(json.loads(file.read_text())["password"])
    elif file.name == "postgres-admin-password":
        values.append(file.read_text().strip())
if any(secret in diff for secret in values if secret):
    raise SystemExit("A private credential was found in staged content. Nothing printed; do not commit.")
print(f"Staged secret scan passed ({len(files)} files; credential values never printed).")
