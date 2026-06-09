# build_data.py

import subprocess
import sys

scripts = [
    "data_collection.collect_basic_data",
    "data_collection.collect_moves",
    "data_collection.collect_type_chart",
    "data_collection.collect_natures",
]

for script in scripts:
    print(f"\nRunning {script}...")

    subprocess.run(
        [
            sys.executable,
            "-m",
            script,
        ],
        check=True,
    )

print("\nData generation complete.")