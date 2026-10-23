from flask import Flask, request, jsonify
from db import (
    create_user, get_users, get_user, update_user, delete_user,
    create_todo, get_todos, update_todo, toggle_todo, delete_todo
)

app = Flask(__name__)

@app.route("/")
def home():
    return "Todo API chal raha hai"

# ---------- Users ----------
@app.route("/users", methods=["GET"])
def list_users():
    rows = get_users()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])

@app.route("/users", methods=["POST"])
def add_user():
    data = request.json
    uid = create_user(data["name"], data["email"])
    return jsonify({"id": uid}), 201

@app.route("/users/<int:user_id>", methods=["GET"])
def get_one_user(user_id):
    row = get_user(user_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": row[0], "name": row[1], "email": row[2]})

@app.route("/users/<int:user_id>", methods=["PUT"])
def edit_user(user_id):
    data = request.json
    res = update_user(user_id, data["name"], data["email"])
    if not res:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": res})

@app.route("/users/<int:user_id>", methods=["DELETE"])
def remove_user(user_id):
    delete_user(user_id)
    return jsonify({"deleted": user_id})

# ---------- Todos ----------
@app.route("/todos", methods=["GET"])
def list_todos():
    user_id = request.args.get("user_id")
    done_param = request.args.get("done")
    done = None
    if done_param is not None:
        done = done_param.lower() == "true"
    rows = get_todos(user_id, done)
    return jsonify([
        {"id": r[0], "user_id": r[1], "title": r[2], "done": r[3]}
        for r in rows
    ])

@app.route("/todos", methods=["POST"])
def add_todo():
    data = request.json
    tid = create_todo(data["user_id"], data["title"])
    return jsonify({"id": tid}), 201

@app.route("/todos/<int:todo_id>", methods=["PUT"])
def edit_todo(todo_id):
    data = request.json
    res = update_todo(todo_id, data["title"])
    if not res:
        return jsonify({"error": "not found"}), 404
    return jsonify({"updated": res})

@app.route("/todos/<int:todo_id>/toggle", methods=["PATCH"])
def toggle(todo_id):
    done = toggle_todo(todo_id)
    if done is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"done": done})

@app.route("/todos/<int:todo_id>", methods=["DELETE"])
def remove(todo_id):
    delete_todo(todo_id)
    return jsonify({"deleted": todo_id})

if __name__ == "__main__":
    app.run()
