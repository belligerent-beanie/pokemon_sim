"""
Team Builder Flask app.
Run from pokemon_sim/: python app.py
Then open http://localhost:5168
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests as http
from flask import Flask, jsonify, render_template
from utils.constants import POKEMON_FILE, NATURES_FILE
from utils.data import load_json

app = Flask(__name__)

pokemon_db: dict = load_json(POKEMON_FILE)
nature_db: dict = load_json(NATURES_FILE)
ability_cache: dict = {}   # name → list[{name, hidden}]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/pokemon")
def get_all_pokemon():
    return jsonify(pokemon_db)


@app.route("/api/natures")
def get_natures():
    return jsonify(nature_db)


@app.route("/api/abilities/<name>")
def get_abilities(name: str):
    if name in ability_cache:
        return jsonify(ability_cache[name])
    try:
        data = http.get(
            f"https://pokeapi.co/api/v2/pokemon/{name}",
            timeout=6,
        ).json()
        abilities = [
            {"name": ab["ability"]["name"], "hidden": ab["is_hidden"]}
            for ab in data.get("abilities", [])
        ]
        ability_cache[name] = abilities
        return jsonify(abilities)
    except Exception:
        return jsonify([])


if __name__ == "__main__":
    print("Team Builder running at http://localhost:5168")
    app.run(debug=True, port=5168)
