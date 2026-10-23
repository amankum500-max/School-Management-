import sqlite3

def get_db():
    conn = sqlite3.connect('database.db')
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# ---------- Users ----------
def create_user(name, email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    uid = cursor.lastrowid
    cursor.close()
    conn.close()
    return uid

def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def update_user(user_id, name, email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (name, email, user_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return user_id if updated else None

def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

# ---------- Todos ----------
def create_todo(user_id, title):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (user_id, title, done) VALUES (?, ?, 0)", (user_id, title))
    conn.commit()
    tid = cursor.lastrowid
    cursor.close()
    conn.close()
    return tid

def get_todos(user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT id, user_id, title, done FROM todos WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT id, user_id, title, done FROM todos")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def toggle_todo(todo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT done FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return None
    new_done = 0 if row[0] else 1
    cursor.execute("UPDATE todos SET done = ? WHERE id = ?", (new_done, todo_id))
    conn.commit()
    cursor.close()
    conn.close()
    return new_done

def delete_todo(todo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    cursor.close()
    conn.close()
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

# Database initialize karein
init_db()
