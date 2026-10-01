from pathlib import Path

ROOT = Path.cwd()

directories = [
    "src/ingestion",
    "src/storage",
    "src/retrieval",
    "src/agents",
    "src/models",
    "src/common",
    "tests",
    "scripts",
    "configs",
    "data/raw",
    "data/processed",
]

files = [
    "src/__init__.py",
    "src/ingestion/__init__.py",
    "src/storage/__init__.py",
    "src/retrieval/__init__.py",
    "src/agents/__init__.py",
    "src/models/__init__.py",
    "src/common/__init__.py",
    "tests/__init__.py",
]

for directory in directories:
    (ROOT / directory).mkdir(parents=True, exist_ok=True)

for file in files:
    path = ROOT / file
    path.touch(exist_ok=True)

print("Repository structure created.")