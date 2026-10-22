from flask import Flask, request, jsonify
from db import create_user, get_users

app = Flask(__name__)

@app.route("/")
def home():
    return "App chal raha hai"

@app.route("/users", methods=["GET"])
def list_users():
    rows = get_users()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])

@app.route("/users", methods=["POST"])
def add_user():
    data = request.json
    uid = create_user(data["name"], data["email"])
    return jsonify({"id": uid}), 201

if __name__ == "__main__":
    app.run()
