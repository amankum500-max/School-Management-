import os
import psycopg2
from psycopg2 import pool

# Global connection pool
db_pool = None

def init_pool():
    global db_pool
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=15, # Thoda badha diya hai safety ke liye
            dsn=os.getenv("DATABASE_URL"),
            sslmode="require",
            connect_timeout=10
        )
        print("Database connection pool initialized successfully.")
    except Exception as e:
        print(f"Error initializing connection pool: {e}")

# ==========================================
# MAGIC WRAPPER CLASS (Isko change mat karna)
# ==========================================
class SafeConnection:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self._is_closed = False

    # Ye line ensure karti hai ki conn.cursor() waise hi kaam kare jaise pehle karta tha
    def __getattr__(self, name):
        return getattr(self._conn, name)

    # Jab aapka purana code 'conn.close()' call karega, toh ye function chalega
    def close(self):
        if not self._is_closed:
            try:
                # Transaction ko clear karo taaki next request ke liye connection clean rahe
                self._conn.rollback() 
                # Connection ko physical close karne ke bajaye wapas pool me daalo
                self._pool.putconn(self._conn)
            except Exception:
                pass
            self._is_closed = True

    # Safety net: Agar kisi function me error ki wajah se close() nahi chala, toh ye garbage collector se wapas pool me daal dega
    def __del__(self):
        self.close()

# ==========================================
# Naya get_conn() jo wrapper return karega
# ==========================================
def get_conn():
    global db_pool
    if db_pool is None:
        init_pool()
    raw_conn = db_pool.getconn()
    return SafeConnection(raw_conn, db_pool)

# Purane code support ke liye (agar kahin release_conn use hua ho)
def release_conn(conn):
    if hasattr(conn, 'close'):
        conn.close()
