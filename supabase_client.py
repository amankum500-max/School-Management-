import os
import psycopg2
from psycopg2 import pool
import threading

# Global connection pool & Lock for thread safety
db_pool = None
_pool_lock = threading.Lock()

def init_pool():
    global db_pool
    # Thread lock taaki ek hi waqt mein do requests pool initialize na karein
    with _pool_lock:
        if db_pool is not None:
            return True
        try:
            db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20, # Thoda aur badha diya hai taaki requests block na hon
                dsn=os.getenv("DATABASE_URL"),
                sslmode="require",
                connect_timeout=10
            )
            print("Database connection pool initialized successfully.")
            return True
        except Exception as e:
            print(f"Error initializing connection pool: {e}")
            db_pool = None
            return False

# ==========================================
# MAGIC WRAPPER CLASS
# ==========================================
class SafeConnection:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self._is_closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._is_closed:
            try:
                # Transaction ko clear karo taaki next request ke liye connection clean rahe
                self._conn.rollback() 
                # Connection ko physical close karne ke bajaye wapas pool me daalo
                self._pool.putconn(self._conn)
            except Exception as e:
                print(f"Error while returning connection to pool: {e}")
            self._is_closed = True

    def __del__(self):
        self.close()

# ==========================================
# Naya get_conn() jo har haal mein safe rahega
# ==========================================
def get_conn():
    global db_pool
    
    # Agar pool nahi hai, toh initialize karo
    if db_pool is None:
        success = init_pool()
        if not success or db_pool is None:
            raise Exception("Database connection pool is not available. Please check DATABASE_URL and database status.")

    try:
        # Pool se connection nikalo
        raw_conn = db_pool.getconn()
        if not raw_conn:
            raise Exception("Could not get connection from pool.")
        return SafeConnection(raw_conn, db_pool)
    except pool.PoolError as e:
        # Agar pool exhaust ho gaya ho
        print(f"Connection pool exhausted: {e}")
        raise Exception("Server is busy. Please try again in a moment.")
    except Exception as e:
        print(f"Error getting connection: {e}")
        raise e

# Purane code support ke liye
def release_conn(conn):
    if hasattr(conn, 'close'):
        conn.close()
