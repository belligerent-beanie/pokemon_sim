# build_data.py

import subprocess
import sys

scripts = [
    "pokemon_sim.data_collection.collect_basic_data",
    "pokemon_sim.data_collection.collect_moves",
    "pokemon_sim.data_collection.collect_type_chart",
    "pokemon_sim.data_collection.collect_natures",
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