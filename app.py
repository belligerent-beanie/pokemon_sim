"""
Team Builder Flask app.
Run from pokemon_sim/: python app.py
Then open http://localhost:5168
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, render_template
from utils.constants import POKEMON_FILE, MOVE_DATA_FILE, NATURES_FILE, TYPE_CHART_FILE
from utils.data import load_json

app = Flask(__name__)

pokemon_db: dict = load_json(POKEMON_FILE)
nature_db: dict = load_json(NATURES_FILE)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/pokemon")
def get_all_pokemon():
    return jsonify(pokemon_db)


@app.route("/api/natures")
def get_natures():
    return jsonify(nature_db)


if __name__ == "__main__":
    print("Team Builder running at http://localhost:5168")
    app.run(debug=True, port=5168)
