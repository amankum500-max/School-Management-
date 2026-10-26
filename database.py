"""
School Management System — Complete Database Layer
====================================================
All 51 phases combined into single database.py

Structure:
    - Imports & Helpers
    - Phase 1: Admin
    - Phase 2: Students
    - Phase 3: Fees
    - Phase 4: Attendance
    - Phase 5: Exams & Marks
    - Phase 6: Notices
    - Phase 7: Parents
    - Phase 8: Settings & Charts
    - Phase 9: Reports
    - Phase 13: Bulk Import
    - Phase 14: WhatsApp
    - Phase 15: Backup
    - Phase 16: Bills
    - Phase 18: Timetable
    - Phase 19: Salary
    - Phase 20: Homework
    - Phase 21: Transport
    - Phase 22: Expenses & P&L
    - Phase 23: Certificates
    - Phase 24: Events
    - Phase 25: Library
    - Phase 26: Promotion
    - Phase 27: Teachers
    - Phase 28: Medical
    - Phase 29: Alerts
    - Phase 30: Multi-Admin & Audit
    - Phase 31: Hostel
    - Phase 32: QR Attendance
    - Phase 34: Annual Reports
    - Phase 36: Public Content
    - Phase 37: Online Payments
    - Phase 38: Dashboard V2
    - Phase 39: Staff Attendance
    - Phase 40: Leave
    - Phase 41: Discounts
    - Phase 42: SMS
    - Phase 43: Visitors
    - Phase 44: Advances
    - Phase 45: Chat
    - Phase 46: Online Exams
    - Phase 47: Automation
    - Phase 48: Hall Tickets
    - Phase 49: Photos & Documents
    - Phase 50: Report Cards
    - Phase 51: Password Reset, Duplicate Detection
"""

# ============================================================
# IMPORTS & CONSTANTS
# ============================================================
import os
import json as _json
import random as _random
import secrets
from datetime import datetime, date, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from supabase_client import get_conn


# ---- Global Constants ----
BACKUP_TABLES = [
    "settings", "admins", "students", "fee_structure",
    "fee_payments", "attendance", "exams", "marks",
    "notices", "parents", "enquiries", "staff",
    "whatsapp_templates", "whatsapp_logs",
]

ADMIN_ROLES = ["super_admin", "admin", "accountant", "viewer"]

CERT_TYPES = [
    "Transfer Certificate",
    "Bonafide Certificate",
    "Character Certificate",
    "Study Certificate",
    "Fee Clearance Certificate",
]

CERT_TEMPLATES = {
    "Transfer Certificate": (
        "This is to certify that {name}, son/daughter of {parent_name}, "
        "was a student of this school in Class {class_name}{section} "
        "(Roll No. {roll}) during the academic year {ay}. "
        "His/her conduct and character were found to be satisfactory. "
        "All dues have been cleared."
    ),
    "Bonafide Certificate": (
        "This is to certify that {name}, son/daughter of {parent_name}, "
        "is a bonafide student of this school, currently studying in "
        "Class {class_name}{section} (Roll No. {roll}) during AY {ay}."
    ),
    "Character Certificate": (
        "This is to certify that {name}, son/daughter of {parent_name}, "
        "was a student of this school in Class {class_name}{section}. "
        "His/her conduct was good and satisfactory."
    ),
    "Study Certificate": (
        "This is to certify that {name}, son/daughter of {parent_name}, "
        "is currently studying in Class {class_name}{section} "
        "(Roll No. {roll}) at this school during AY {ay}."
    ),
    "Fee Clearance Certificate": (
        "This is to certify that all fees and dues of {name}, son/daughter "
        "of {parent_name}, studying in Class {class_name}{section}, have "
        "been cleared up to the date of this certificate."
    ),
}

EVENT_TYPES = ["holiday", "exam", "meeting", "sports", "cultural", "other"]
BOOK_CATEGORIES = ["Textbook", "Reference", "Fiction", "Non-fiction",
                   "Magazine", "Comics", "Biography", "Other"]
LIBRARY_FINE_PER_DAY = 2

EXPENSE_CATEGORIES = [
    "Rent", "Utilities", "Maintenance", "Stationery", "Books",
    "Transport", "Food", "Events", "Marketing", "Equipment", "Other",
]

CLASS_SEQUENCE = [
    "Nursery", "LKG", "UKG",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

ROOM_TYPES = ["single", "double", "triple", "shared", "dormitory"]

DISCOUNT_CATEGORIES = ["sibling", "staff", "merit", "sports",
                       "rte", "need_based", "other"]

VISITOR_PURPOSES = ["meeting", "fee", "enquiry", "delivery",
                    "interview", "event", "other"]

ADVANCE_TYPES = ["advance", "loan"]

DOC_TYPES = [
    ("aadhaar", "Aadhaar Card"),
    ("birth_cert", "Birth Certificate"),
    ("marksheet", "Previous Marksheet"),
    ("tc", "Transfer Certificate"),
    ("caste", "Caste Certificate"),
    ("income", "Income Certificate"),
    ("photo", "Photo"),
    ("other", "Other"),
]


# ============================================================
# HELPERS
# ============================================================
def _json_safe(value):
    """Convert datetime/Decimal/list/dict to JSON-safe"""
    from datetime import date as _d, datetime as _dt
    from decimal import Decimal
    if value is None:
        return None
    if isinstance(value, (_dt, _d)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _academic_year_for_cert():
    """Current academic year like '2024-25'"""
    now = datetime.now()
    y = now.year
    if now.month >= 4:
        return f"{y}-{str(y + 1)[-2:]}"
    return f"{y - 1}-{str(y)[-2:]}"


def get_current_academic_year():
    return _academic_year_for_cert()


def get_academic_year_options():
    today = date.today()
    current_start = today.year if today.month >= 4 else today.year - 1
    return [f"{y}-{str(y + 1)[-2:]}" for y in range(current_start, current_start - 5, -1)]


def _fy_range(fy_year):
    """2024 → (2024-04-01, 2025-03-31)"""
    return date(fy_year, 4, 1), date(fy_year + 1, 3, 31)


def _academic_year_range(year_label):
    """'2024-25' → (date, date)"""
    parts = year_label.split("-")
    start_year = int(parts[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


# ============================================================
# PHASE 1 — ADMIN
# ============================================================
def create_admin(username, password, full_name=""):
    conn = get_conn()
    cur = conn.cursor()
    pwd_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO admins (username, password_hash, full_name) "
        "VALUES (%s, %s, %s) RETURNING id;",
        (username, pwd_hash, full_name)
    )
    uid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return uid


def get_admin_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, password_hash, full_name, role, is_active
        FROM admins WHERE username=%s;
    """, (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def verify_admin(username, password):
    row = get_admin_by_username(username)
    if not row:
        return None
    if not row[5]:
        return None
    if check_password_hash(row[2], password):
        return {"id": row[0], "username": row[1],
                "full_name": row[3], "role": row[4] or "admin"}
    return None


def count_admins():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM admins;")
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def get_admin(admin_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, full_name, role, is_active, created_at
        FROM admins WHERE id=%s;
    """, (admin_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "full_name": row[2],
            "role": row[3], "is_active": row[4], "created_at": row[5]}


def update_admin_profile(admin_id, full_name, username):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE admins SET full_name=%s, username=%s
            WHERE id=%s RETURNING id;
        """, (full_name, username, admin_id))
        res = cur.fetchone()
        conn.commit()
        return res[0] if res else None
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def change_admin_password(admin_id, old_password, new_password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM admins WHERE id=%s;", (admin_id,))
    row = cur.fetchone()
    if not row or not check_password_hash(row[0], old_password):
        cur.close()
        conn.close()
        return False
    new_hash = generate_password_hash(new_password)
    cur.execute("UPDATE admins SET password_hash=%s WHERE id=%s;",
                (new_hash, admin_id))
    conn.commit()
    cur.close()
    conn.close()
    return True


# ============================================================
# PHASE 2 — STUDENTS
# ============================================================
def create_student(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO students
        (name, roll_no, class_name, section, gender, dob,
         parent_name, parent_phone, address, admission_date, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """, (
        data.get("name"), data.get("roll_no"), data.get("class_name"),
        data.get("section"), data.get("gender"), data.get("dob") or None,
        data.get("parent_name"), data.get("parent_phone"),
        data.get("address"), data.get("admission_date") or None,
        data.get("status") or "active"
    ))
    sid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return sid


def get_students(search=None, class_name=None, status="active"):
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT id, name, roll_no, class_name, section, parent_phone, status FROM students WHERE 1=1"
    params = []
    if status and status != "all":
        q += " AND status=%s"
        params.append(status)
    if search:
        q += " AND (name ILIKE %s OR roll_no ILIKE %s OR parent_phone ILIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]
    if class_name:
        q += " AND class_name=%s"
        params.append(class_name)
    q += " ORDER BY class_name, section, roll_no;"
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_student(student_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, roll_no, class_name, section, gender, dob,
               parent_name, parent_phone, address, admission_date, status, created_at
        FROM students WHERE id=%s;
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def update_student(student_id, data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE students SET
            name=%s, roll_no=%s, class_name=%s, section=%s, gender=%s,
            dob=%s, parent_name=%s, parent_phone=%s, address=%s,
            admission_date=%s, status=%s
        WHERE id=%s RETURNING id;
    """, (
        data.get("name"), data.get("roll_no"), data.get("class_name"),
        data.get("section"), data.get("gender"), data.get("dob") or None,
        data.get("parent_name"), data.get("parent_phone"),
        data.get("address"), data.get("admission_date") or None,
        data.get("status") or "active", student_id
    ))
    res = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return res[0] if res else None


def delete_student(student_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s;", (student_id,))
    conn.commit()
    cur.close()
    conn.close()


def count_students():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def get_classes_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT class_name FROM students WHERE class_name IS NOT NULL ORDER BY class_name;")
    rows = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def get_students_full(class_name=None, section=None):
    """Full student records — used by ID cards, hall tickets"""
    conn = get_conn()
    cur = conn.cursor()
    q = """
        SELECT id, name, roll_no, class_name, section, gender, dob,
               parent_name, parent_phone, address, admission_date, status,
               photo_url
        FROM students WHERE status='active'
    """
    params = []
    if class_name:
        q += " AND class_name=%s"
        params.append(class_name)
    if section:
        q += " AND section=%s"
        params.append(section)
    q += " ORDER BY class_name, section, roll_no, name;"
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","photo_url"]
    return [dict(zip(keys, r)) for r in rows]


def update_student_photo_url(student_id, photo_url):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE students SET photo_url=%s WHERE id=%s RETURNING id;",
                (photo_url, student_id))
    res = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return res[0] if res else None


def get_students_without_photos(class_name=None):
    conn = get_conn()
    cur = conn.cursor()
    q = """
        SELECT id, name, roll_no, class_name, section
        FROM students
        WHERE status='active' AND (photo_url IS NULL OR photo_url = '')
    """
    params = []
    if class_name:
        q += " AND class_name=%s"
        params.append(class_name)
    q += " ORDER BY class_name, section, roll_no;"
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1], "roll": r[2],
             "class_name": r[3], "section": r[4]} for r in rows]


def count_students_with_photos():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE photo_url IS NOT NULL AND photo_url != '') AS with_photo,
            COUNT(*) FILTER (WHERE photo_url IS NULL OR photo_url = '') AS without_photo,
            COUNT(*) AS total
        FROM students WHERE status='active';
    """)
    r = cur.fetchone()
    cur.close()
    conn.close()
    return {"with_photo": r[0] or 0, "without_photo": r[1] or 0,
            "total": r[2] or 0}


# ============================================================
# PHASE 3 — FEES
# ============================================================
def create_fee_structure(class_name, fee_type, amount, frequency):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fee_structure (class_name, fee_type, amount, frequency)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """, (class_name, fee_type, amount, frequency))
        fid = cur.fetchone()[0]
        conn.commit()
        return fid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_fee_structures(class_name=None):
    conn = get_conn()
    cur = conn.cursor()
    if class_name:
        cur.execute("""
            SELECT id, class_name, fee_type, amount, frequency
            FROM fee_structure WHERE class_name=%s ORDER BY fee_type;
        """, (class_name,))
    else:
        cur.execute("""
            SELECT id, class_name, fee_type, amount, frequency
            FROM fee_structure ORDER BY class_name, fee_type;
        """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_fee_structure(fid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM fee_structure WHERE id=%s;", (fid,))
    conn.commit()
    cur.close()
    conn.close()


def generate_receipt_no():
    today = datetime.now().strftime("%Y%m%d")
    rand = _random.randint(1000, 9999)
    return f"RCPT-{today}-{rand}"


def create_fee_payment(student_id, fee_type, amount, month, mode, note, admin_id):
    conn = get_conn()
    cur = conn.cursor()
    receipt_no = generate_receipt_no()
    for _ in range(5):
        cur.execute("SELECT 1 FROM fee_payments WHERE receipt_no=%s;", (receipt_no,))
        if not cur.fetchone():
            break
        receipt_no = generate_receipt_no()

    cur.execute("""
        INSERT INTO fee_payments
        (student_id, fee_type, amount, month, mode, receipt_no, note, recorded_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
    """, (student_id, fee_type, amount, month, mode, receipt_no, note, admin_id))
    pid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": pid, "receipt_no": receipt_no}


def get_payment(payment_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.student_id, p.fee_type, p.amount, p.month, p.mode,
               p.receipt_no, p.note, p.paid_at,
               s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone
        FROM fee_payments p
        JOIN students s ON s.id = p.student_id
        WHERE p.id=%s;
    """, (payment_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_payments(student_id=None, month=None, limit=200):
    conn = get_conn()
    cur = conn.cursor()
    q = """
        SELECT p.id, p.student_id, s.name, s.class_name, s.section,
               p.fee_type, p.amount, p.month, p.mode, p.receipt_no, p.paid_at
        FROM fee_payments p
        JOIN students s ON s.id = p.student_id
        WHERE 1=1
    """
    params = []
    if student_id:
        q += " AND p.student_id=%s"
        params.append(student_id)
    if month:
        q += " AND p.month=%s"
        params.append(month)
    q += " ORDER BY p.paid_at DESC LIMIT %s;"
    params.append(limit)
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_payment(payment_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM fee_payments WHERE id=%s;", (payment_id,))
    conn.commit()
    cur.close()
    conn.close()


def total_collected(month=None):
    conn = get_conn()
    cur = conn.cursor()
    if month:
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE month=%s;", (month,))
    else:
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments;")
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def pending_amount_for_student(student_id, month):
    conn = get_conn()
    cur = qconn.cursor()
    cur.execute("SELECT class_name FROM students WHERE id=%s;", (student_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        cur.close()
        conn.close()
        return 0
    class_name = row[0]

    cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_structure WHERE class_name=%s;",
                (class_name,))
    due = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE student_id=%s AND month=%s;",
                (student_id, month))
    paid = cur.fetchone()[0]
    cur.close()cç 
    conn.close()
    return max(due - paid, 0)


def get_defaulters(month):
    conn = get_conn()
    cur = co
