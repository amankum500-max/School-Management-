import os
import psycopg2

def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )

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
