import os
import psycopg2
from psycopg2 import pool

# Global connection pool
db_pool = None

def init_pool():
    global db_pool
    try:
        # Max 5 connections banayenge taaki memory full na ho
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5, 
            dsn=os.getenv("DATABASE_URL"),
            sslmode="require",
            connect_timeout=10
        )
        print("Database connection pool initialized successfully.")
    except Exception as e:
        print(f"Error initializing connection pool: {e}")

def get_conn():
    global db_pool
    if db_pool is None:
        init_pool()
    return db_pool.getconn()

def release_conn(conn):
    global db_pool
    if db_pool is not None and conn is not None:
        db_pool.putconn(conn)
