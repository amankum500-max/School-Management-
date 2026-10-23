import os
import psycopg2

def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )

# ---------- Users ----------
def create_user(name, email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id;",
        (name, email)
    )
    uid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return uid

def get_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users WHERE id=%s;", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def update_user(user_id, name, email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET name=%s, email=%s WHERE id=%s RETURNING id;",
        (name, email, user_id)
    )
    res = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return res[0] if res else None

def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

# ---------- Todos ----------
def create_todo(user_id, title):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO todos (user_id, title, done) VALUES (%s, %s, FALSE) RETURNING id;",
        (user_id, title)
    )
    tid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return tid

def get_todos(user_id=None, done=None):
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT id, user_id, title, done FROM todos WHERE 1=1"
    params = []
    if user_id:
        query += " AND user_id=%s"
        params.append(user_id)
    if done is not None:
        query += " AND done=%s"
        params.append(done)
    query += " ORDER BY id;"
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_todo(todo_id, title):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE todos SET title=%s WHERE id=%s RETURNING id;",
        (title, todo_id)
    )
    res = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return res[0] if res else None

def toggle_todo(todo_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE todos SET done = NOT done WHERE id=%s RETURNING done;",
        (todo_id,)
    )
    res = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return res[0] if res else None

def delete_todo(todo_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id=%s;", (todo_id,))
    conn.commit()
    cur.close()
    conn.close()
