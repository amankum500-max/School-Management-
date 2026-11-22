"""
School Management System — Database Layer (Complete, Merged & FIXED)
============================================================
Single-file consolidation of Phase 1 + Phase 2 + Phase 3.
• No duplicate functions (renamed class-section promote to promote_class_section)
• Fixed Dashboard Data Formats (Dict vs List)
• Removed recursive Bridge Functions
• Fixed SQL column errors (marks_obtained -> obtained)
"""
import os
import json as _json
import random as _random
import secrets
from datetime import datetime, date, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras

from supabase_client import get_conn   # ← ONLY DB connection source

# ============================================================
# CONSTANTS
# ============================================================
BACKUP_TABLES = ["settings","admins","students","fee_structure","fee_payments",
                 "attendance","exams","marks","notices","parents","enquiries",
                 "staff","whatsapp_templates","whatsapp_logs"]
ADMIN_ROLES = ["super_admin","admin","accountant","viewer"]
CERT_TYPES = ["Transfer Certificate","Bonafide Certificate","Character Certificate",
              "Study Certificate","Fee Clearance Certificate"]
CERT_TEMPLATES = {
    "Transfer Certificate": "This is to certify that {name}, son/daughter of {parent_name}, was a student of this school in Class {class_name}{section} (Roll No. {roll}) during the academic year {ay}. His/her conduct and character were found to be satisfactory. All dues have been cleared.",
    "Bonafide Certificate": "This is to certify that {name}, son/daughter of {parent_name}, is a bonafide student of this school, currently studying in Class {class_name}{section} (Roll No. {roll}) during AY {ay}.",
    "Character Certificate": "This is to certify that {name}, son/daughter of {parent_name}, was a student of this school in Class {class_name}{section}. His/her conduct was good and satisfactory.",
    "Study Certificate": "This is to certify that {name}, son/daughter of {parent_name}, is currently studying in Class {class_name}{section} (Roll No. {roll}) at this school during AY {ay}.",
    "Fee Clearance Certificate": "This is to certify that all fees and dues of {name}, son/daughter of {parent_name}, studying in Class {class_name}{section}, have been cleared up to the date of this certificate.",
}
EVENT_TYPES = ["holiday","exam","meeting","sports","cultural","other"]
BOOK_CATEGORIES = ["Textbook","Reference","Fiction","Non-fiction","Magazine","Comics","Biography","Other"]
LIBRARY_FINE_PER_DAY = 2
EXPENSE_CATEGORIES = ["Rent","Utilities","Maintenance","Stationery","Books","Transport",
                      "Food","Events","Marketing","Equipment","Other"]
CLASS_SEQUENCE = ["Nursery","LKG","UKG","1","2","3","4","5","6","7","8","9","10","11","12"]
BLOOD_GROUPS = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
ROOM_TYPES = ["single","double","triple","shared","dormitory"]
DISCOUNT_CATEGORIES = ["academic","sports","sibling","staff","other","merit","rte","need_based"]
VISITOR_PURPOSES = ["meeting","fee","enquiry","delivery","interview","event","other"]
ADVANCE_TYPES = ["advance","loan"]
DOC_TYPES = [("aadhaar","Aadhaar Card"),("birth_cert","Birth Certificate"),
             ("marksheet","Previous Marksheet"),("tc","Transfer Certificate"),
             ("caste","Caste Certificate"),("income","Income Certificate"),
             ("photo","Photo"),("other","Other")]

# ============================================================
# HELPERS
# ============================================================
def _json_safe(value):
    if value is None: return None
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, (list, tuple)): return [_json_safe(v) for v in value]
    if isinstance(value, dict): return {k: _json_safe(v) for k, v in value.items()}
    return value

def _academic_year_for_cert():
    now = datetime.now(); y = now.year
    return f"{y}-{str(y+1)[-2:]}" if now.month >= 4 else f"{y-1}-{str(y)[-2:]}"

def get_current_academic_year(): return _academic_year_for_cert()

def get_academic_year_options():
    today = date.today()
    current_start = today.year if today.month >= 4 else today.year - 1
    return [f"{y}-{str(y+1)[-2:]}" for y in range(current_start, current_start-5, -1)]

def _fy_range(fy_year): return date(fy_year,4,1), date(fy_year+1,3,31)
def _academic_year_range(year_label):
    p = year_label.split("-")
    return date(int(p[0]),4,1), date(int(p[0])+1,3,31)
def _to_bool(val, default=False):
    if val is None: return default
    if isinstance(val, bool): return val
    return str(val).strip().lower() in ("on","true","1","yes","y")

# ============================================================
# SECTION 1 — ADMIN & AUTH
# ============================================================
def create_admin(username, password, full_name=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s) RETURNING id;",
                    (username, generate_password_hash(password), full_name))
        uid = cur.fetchone()[0]; conn.commit(); return uid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_admin_by_username(username):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, password_hash, full_name, role, is_active FROM admins WHERE username=%s;", (username,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def verify_admin(username, password):
    row = get_admin_by_username(username)
    if not row or not row[5]: return None
    if check_password_hash(row[2], password):
        return {"id": row[0], "username": row[1], "full_name": row[3], "role": row[4] or "admin"}
    return None

def count_admins():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM admins;")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def get_all_admins():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, full_name, role, is_active, created_at FROM admins ORDER BY id;")
        rows = cur.fetchall()
        return [{"id": r[0], "username": r[1], "full_name": r[2], "role": r[3],
                 "is_active": r[4], "created_at": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_admin(admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, full_name, role, is_active, created_at FROM admins WHERE id=%s;", (admin_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "username": row[1], "full_name": row[2], "role": row[3],
                "is_active": row[4], "created_at": row[5]}
    finally:
        cur.close(); conn.close()

def get_admin_by_id(admin_id): return get_admin(admin_id)

def update_admin_profile(admin_id, full_name, username):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE admins SET full_name=%s, username=%s WHERE id=%s RETURNING id;",
                    (full_name, username, admin_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def change_admin_password(admin_id, old_password, new_password):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT password_hash FROM admins WHERE id=%s;", (admin_id,))
        row = cur.fetchone()
        if not row or not check_password_hash(row[0], old_password):
            return False
        cur.execute("UPDATE admins SET password_hash=%s WHERE id=%s;",
                    (generate_password_hash(new_password), admin_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_admin_last_login(admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE admins SET last_login=NOW() WHERE id=%s;", (admin_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def log_audit(admin_id, username, action, method=None, path=None, details=None, entity=None, ip=None, **kwargs):
    conn = None; cur = None
    try:
        conn = get_conn(); cur = conn.cursor()
        final_details = details or ""
        if entity:
            final_details += f" | Entity: {entity}"
        if ip:
            final_details += f" | IP: {ip}"

        cur.execute(
            "INSERT INTO audit_logs (admin_id, admin_username, action, method, path, details) VALUES (%s,%s,%s,%s,%s,%s);",
            (admin_id, username, action, method, path, final_details.strip())
        )
        conn.commit()
    except Exception:
        if conn:
            try: conn.rollback()
            except Exception: pass
    finally:
        if cur:
            try: cur.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

def get_audit_logs(limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, admin_id, admin_username, action, method, path, details, created_at FROM audit_logs ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "admin_id": r[1], "admin_username": r[2], "action": r[3],
                 "method": r[4], "path": r[5], "details": r[6], "created_at": r[7]} for r in rows]
    finally:
        cur.close(); conn.close()

def create_admin_user(username, password, full_name, role="admin"):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO admins (username, password_hash, full_name, role, is_active) VALUES (%s,%s,%s,%s,TRUE) RETURNING id;",
                    (username, generate_password_hash(password), full_name, role))
        uid = cur.fetchone()[0]; conn.commit(); return uid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_admin_user(admin_id, username, full_name, role):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE admins SET username=%s, full_name=%s, role=%s WHERE id=%s RETURNING id;",
                    (username, full_name, role, admin_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_admin_user(admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM admins WHERE id=%s;", (admin_id,)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def reset_admin_password(admin_id, new_password):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE admins SET password_hash=%s WHERE id=%s RETURNING id;",
                    (generate_password_hash(new_password), admin_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def toggle_admin_status(admin_id, is_active):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE admins SET is_active=%s WHERE id=%s;", (_to_bool(is_active), admin_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 2 — PASSWORD RESET (TOKEN FLOW)
# ============================================================
def create_password_reset_token(admin_id, token):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO password_resets (admin_id, token, expires_at) VALUES (%s, %s, NOW() + INTERVAL '1 hour') RETURNING id;",
                    (admin_id, token))
        rid = cur.fetchone()[0]; conn.commit(); return rid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def verify_reset_token(token):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT admin_id FROM password_resets WHERE token=%s AND expires_at > NOW() AND used=FALSE LIMIT 1;", (token,))
        row = cur.fetchone(); return row[0] if row else None
    finally:
        cur.close(); conn.close()

def update_password_by_token(token, new_password):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT admin_id FROM password_resets WHERE token=%s AND expires_at > NOW() AND used=FALSE LIMIT 1;", (token,))
        row = cur.fetchone()
        if not row: return False
        admin_id = row[0]
        cur.execute("UPDATE admins SET password_hash=%s WHERE id=%s;",
                    (generate_password_hash(new_password), admin_id))
        cur.execute("UPDATE password_resets SET used=TRUE WHERE token=%s;", (token,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 3 — STUDENTS
# ============================================================
def create_student(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO students (name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, address, admission_date, status, photo_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data.get("name"), data.get("roll_no"), data.get("class_name"), data.get("section"),
                     data.get("gender"), data.get("dob") or None, data.get("parent_name"),
                     data.get("parent_phone"), data.get("address"),
                     data.get("admission_date") or None, data.get("status") or "active",
                     data.get("photo_url") or None))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_students(search=None, class_name=None, status="active"):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, roll_no, class_name, section, parent_phone, status FROM students WHERE 1=1"
        params = []
        if status and status != "all":
            q += " AND status=%s"; params.append(status)
        if search:
            q += " AND (name ILIKE %s OR roll_no ILIKE %s OR parent_phone ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        if class_name:
            q += " AND class_name=%s"; params.append(class_name)
        q += " ORDER BY class_name, section, roll_no;"
        cur.execute(q, tuple(params))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def get_student(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, address, admission_date, status, created_at, photo_url FROM students WHERE id=%s;", (student_id,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def update_student(student_id, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE students SET name=%s, roll_no=%s, class_name=%s, section=%s, gender=%s, dob=%s, parent_name=%s, parent_phone=%s, address=%s, admission_date=%s, status=%s, photo_url=%s WHERE id=%s RETURNING id;",
                    (data.get("name"), data.get("roll_no"), data.get("class_name"), data.get("section"),
                     data.get("gender"), data.get("dob") or None, data.get("parent_name"),
                     data.get("parent_phone"), data.get("address"),
                     data.get("admission_date") or None, data.get("status") or "active",
                     data.get("photo_url") or None, student_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_student(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM students WHERE id=%s;", (student_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_students():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def get_classes_list():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT class_name FROM students WHERE class_name IS NOT NULL ORDER BY class_name;")
        return [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()

def get_students_full(class_name=None, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, address, admission_date, status, photo_url FROM students WHERE status='active'"
        params = []
        if class_name: q += " AND class_name=%s"; params.append(class_name)
        if section: q += " AND section=%s"; params.append(section)
        q += " ORDER BY class_name, section, roll_no, name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        keys = ["id","name","roll_no","class_name","section","gender","dob","parent_name",
                "parent_phone","address","admission_date","status","photo_url"]
        return [dict(zip(keys, r)) for r in rows]
    finally:
        cur.close(); conn.close()

def update_student_photo_url(student_id, photo_url):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE students SET photo_url=%s WHERE id=%s RETURNING id;", (photo_url, student_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_students_without_photos(class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, roll_no, class_name, section FROM students WHERE status='active' AND (photo_url IS NULL OR photo_url = '')"
        params = []
        if class_name: q += " AND class_name=%s"; params.append(class_name)
        q += " ORDER BY class_name, section, roll_no;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3], "section": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def count_students_with_photos():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE photo_url IS NOT NULL AND photo_url != ''), COUNT(*) FILTER (WHERE photo_url IS NULL OR photo_url = ''), COUNT(*) FROM students WHERE status='active';")
        r = cur.fetchone()
        return {"with_photo": r[0] or 0, "without_photo": r[1] or 0, "total": r[2] or 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 4 — FEES
# ============================================================
def create_fee_structure(class_name, fee_type, amount, frequency):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO fee_structure (class_name, fee_type, amount, frequency) VALUES (%s,%s,%s,%s) RETURNING id;",
                    (class_name, fee_type, amount, frequency))
        fid = cur.fetchone()[0]; conn.commit(); return fid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_fee_structures(class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if class_name:
            cur.execute("SELECT id, class_name, fee_type, amount, frequency FROM fee_structure WHERE class_name=%s ORDER BY fee_type;", (class_name,))
        else:
            cur.execute("SELECT id, class_name, fee_type, amount, frequency FROM fee_structure ORDER BY class_name, fee_type;")
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def delete_fee_structure(fid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM fee_structure WHERE id=%s;", (fid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def generate_receipt_no():
    return f"RCPT-{datetime.now().strftime('%Y%m%d')}-{_random.randint(1000,9999)}"

def create_fee_payment(student_id, fee_type, amount, month, mode, note, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        receipt_no = generate_receipt_no()
        for _ in range(5):
            cur.execute("SELECT 1 FROM fee_payments WHERE receipt_no=%s;", (receipt_no,))
            if not cur.fetchone(): break
            receipt_no = generate_receipt_no()
        cur.execute("INSERT INTO fee_payments (student_id, fee_type, amount, month, mode, receipt_no, note, recorded_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (student_id, fee_type, amount, month, mode, receipt_no, note, admin_id))
        pid = cur.fetchone()[0]; conn.commit()
        return {"id": pid, "receipt_no": receipt_no}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_payment(payment_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT p.id, p.student_id, p.fee_type, p.amount, p.month, p.mode, p.receipt_no, p.note, p.paid_at, s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE p.id=%s;", (payment_id,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def get_payments(student_id=None, month=None, limit=200):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT p.id, p.student_id, s.name, s.class_name, s.section, p.fee_type, p.amount, p.month, p.mode, p.receipt_no, p.paid_at FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE 1=1"
        params = []
        if student_id: q += " AND p.student_id=%s"; params.append(student_id)
        if month: q += " AND p.month=%s"; params.append(month)
        q += " ORDER BY p.paid_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def delete_payment(payment_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM fee_payments WHERE id=%s;", (payment_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def total_collected(month=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if month: cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE month=%s;", (month,))
        else: cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments;")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def pending_amount_for_student(student_id, month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT class_name FROM students WHERE id=%s;", (student_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return 0
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_structure WHERE class_name=%s;", (row[0],))
        due = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE student_id=%s AND month=%s;", (student_id, month))
        paid = cur.fetchone()[0]
        return max(due - paid, 0)
    finally:
        cur.close(); conn.close()

def get_defaulters(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT s.id, s.name, s.roll_no, s.class_name, s.section, s.parent_phone,
                              COALESCE(fs.total,0) AS due, COALESCE(fp.paid,0) AS paid
                       FROM students s
                       LEFT JOIN (SELECT class_name, SUM(amount) AS total FROM fee_structure GROUP BY class_name) fs
                           ON fs.class_name = s.class_name
                       LEFT JOIN (SELECT student_id, SUM(amount) AS paid FROM fee_payments WHERE month=%s GROUP BY student_id) fp
                           ON fp.student_id = s.id
                       WHERE s.status='active' AND COALESCE(fs.total,0) > COALESCE(fp.paid,0)
                       ORDER BY s.class_name, s.section, s.roll_no;""", (month,))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def get_receipts_for_bulk_print(month, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT p.id, p.receipt_no, p.paid_at, p.month, p.fee_type, p.amount, p.mode, p.note, s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE p.month=%s"
        params = [month]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        q += " ORDER BY s.class_name, s.section, s.roll_no, p.paid_at;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "receipt_no": r[1], "paid_at": r[2], "month": r[3],
                 "fee_type": r[4], "amount": float(r[5] or 0), "mode": r[6], "note": r[7],
                 "student_name": r[8], "roll": r[9], "class_name": r[10], "section": r[11],
                 "parent_name": r[12], "parent_phone": r[13]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_student_fee_dues(student_id):
    month = datetime.now().strftime("%Y-%m")
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT class_name FROM students WHERE id=%s;", (student_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return {"month": month, "due": 0, "paid": 0, "pending": 0}
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_structure WHERE class_name=%s;", (row[0],))
        due = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE student_id=%s AND month=%s;", (student_id, month))
        paid = float(cur.fetchone()[0] or 0)
        return {"month": month, "due": due, "paid": paid, "pending": max(due - paid, 0)}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 5 — ATTENDANCE & EXAMS
# ============================================================
def get_attendance_for_date(class_name, section, date_str):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT s.id, s.name, s.roll_no, s.class_name, s.section, a.status FROM students s LEFT JOIN attendance a ON a.student_id = s.id AND a.date=%s WHERE s.status='active' AND s.class_name=%s"
        params = [date_str, class_name]
        if section: q += " AND s.section=%s"; params.append(section)
        q += " ORDER BY s.roll_no, s.name;"
        cur.execute(q, tuple(params))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def mark_attendance(student_id, date_str, status, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO attendance (student_id, date, status, marked_by) VALUES (%s,%s,%s,%s) ON CONFLICT (student_id, date) DO UPDATE SET status=%s, marked_by=%s, marked_at=NOW();",
                    (student_id, date_str, status, admin_id, status, admin_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def bulk_mark_attendance(class_name, section, date_str, status, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "INSERT INTO attendance (student_id, date, status, marked_by) SELECT id, %s, %s, %s FROM students WHERE status='active' AND class_name=%s"
        params = [date_str, status, admin_id, class_name]
        if section: q += " AND section=%s"; params.append(section)
        q += " ON CONFLICT (student_id, date) DO UPDATE SET status=EXCLUDED.status, marked_by=EXCLUDED.marked_by, marked_at=NOW();"
        cur.execute(q, tuple(params)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_attendance_summary(student_id, month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status='absent'), COUNT(*) FILTER (WHERE status='late'), COUNT(*) FILTER (WHERE status='leave'), COUNT(*) FROM attendance WHERE student_id=%s AND TO_CHAR(date, 'YYYY-MM')=%s;", (student_id, month))
        row = cur.fetchone()
        if not row:
            return {"present":0,"absent":0,"late":0,"leave":0,"total":0,"percent":0}
        present, total = row[0] or 0, row[4] or 0
        percent = round(((present + (row[2] or 0) * 0.5) / total) * 100, 1) if total else 0
        return {"present": present, "absent": row[1] or 0, "late": row[2] or 0,
                "leave": row[3] or 0, "total": total, "percent": percent}
    finally:
        cur.close(); conn.close()

def get_attendance_calendar(student_id, month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT date, status FROM attendance WHERE student_id=%s AND TO_CHAR(date, 'YYYY-MM')=%s ORDER BY date;", (student_id, month))
        rows = cur.fetchall()
        return {r[0].strftime("%Y-%m-%d"): r[1] for r in rows}
    finally:
        cur.close(); conn.close()

def class_attendance_today(class_name, section, date_str):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT COUNT(*) FILTER (WHERE a.status='present'), COUNT(*) FILTER (WHERE a.status='absent'), COUNT(*) FILTER (WHERE a.status IS NULL), COUNT(s.id) FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.date=%s WHERE s.status='active' AND s.class_name=%s"
        params = [date_str, class_name]
        if section: q += " AND s.section=%s"; params.append(section)
        cur.execute(q, tuple(params)); row = cur.fetchone()
        return {"present": row[0] or 0, "absent": row[1] or 0, "unmarked": row[2] or 0, "total": row[3] or 0}
    finally:
        cur.close(); conn.close()

def today_attendance_percent(date_str):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status IN ('present','absent','late','leave')) FROM attendance WHERE date=%s;", (date_str,))
        row = cur.fetchone()
        if not row or not row[1]: return None
        return round((row[0] / row[1]) * 100, 1)
    finally:
        cur.close(); conn.close()

def create_exam(name, class_name, exam_date, subjects, max_marks=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO exams (name, class_name, exam_date, subjects, max_marks) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (name, class_name, exam_date or None, subjects, max_marks))
        eid = cur.fetchone()[0]; conn.commit(); return eid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_exams(class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if class_name:
            cur.execute("SELECT id, name, class_name, exam_date, subjects, max_marks FROM exams WHERE class_name=%s ORDER BY exam_date DESC NULLS LAST, id DESC;", (class_name,))
        else:
            cur.execute("SELECT id, name, class_name, exam_date, subjects, max_marks FROM exams ORDER BY exam_date DESC NULLS LAST, id DESC;")
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def get_exam(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, class_name, exam_date, subjects, max_marks FROM exams WHERE id=%s;", (exam_id,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def get_exam_details(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM exams WHERE id=%s;", (exam_id,))
        row = cur.fetchone()
        if not row: return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close(); conn.close()

def delete_exam(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM exams WHERE id=%s;", (exam_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_marks_grid(exam_id):
    exam = get_exam(exam_id)
    if not exam: return None, [], []
    subjects, class_name = exam[4] or [], exam[2]
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, roll_no, section FROM students WHERE status='active' AND class_name=%s ORDER BY section, roll_no, name;", (class_name,))
        students = [{"id": r[0], "name": r[1], "roll": r[2], "section": r[3]} for r in cur.fetchall()]
        cur.execute("SELECT student_id, subject, obtained FROM marks WHERE exam_id=%s;", (exam_id,))
        marks = {}
        for r in cur.fetchall(): marks.setdefault(r[0], {})[r[1]] = r[2]
        return {"id": exam[0], "name": exam[1], "class_name": exam[2], "exam_date": exam[3],
                "subjects": subjects, "max_marks": exam[5]}, students, marks
    finally:
        cur.close(); conn.close()

def save_mark(exam_id, student_id, subject, obtained):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO marks (exam_id, student_id, subject, obtained) VALUES (%s,%s,%s,%s) ON CONFLICT (exam_id, student_id, subject) DO UPDATE SET obtained=EXCLUDED.obtained;",
                    (exam_id, student_id, subject, obtained))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_student_marks_report(exam_id, student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT subject, obtained FROM marks WHERE exam_id=%s AND student_id=%s;", (exam_id, student_id))
        rows = cur.fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        cur.close(); conn.close()

def get_merit_list(exam_id):
    exam = get_exam(exam_id)
    if not exam: return []
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.roll_no, s.section, COALESCE(SUM(m.obtained), 0) AS total, COUNT(m.id) FROM students s LEFT JOIN marks m ON m.student_id = s.id AND m.exam_id=%s WHERE s.status='active' AND s.class_name=%s GROUP BY s.id, s.name, s.roll_no, s.section ORDER BY total DESC, s.name;",
                    (exam_id, exam[2]))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def get_exam_stats(exam_id):
    exam = get_exam(exam_id)
    if not exam: return None
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE total >= %s * 0.33), COUNT(*) FILTER (WHERE total < %s * 0.33), COALESCE(AVG(total), 0), COALESCE(MAX(total), 0) FROM (SELECT student_id, SUM(obtained) AS total FROM marks WHERE exam_id=%s GROUP BY student_id) t;",
                    (exam[5], exam[5], exam_id))
        row = cur.fetchone()
        return {"passed": row[0] or 0, "failed": row[1] or 0,
                "avg": round(float(row[2] or 0), 1), "top": row[3] or 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 6 — NOTICES
# ============================================================
def create_notice(data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO notices (title, content, category, priority, target_class, is_public, published, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["title"], data["content"], data.get("category") or "general",
                     data.get("priority") or "normal", data.get("target_class") or None,
                     _to_bool(data.get("is_public")), _to_bool(data.get("published")), admin_id))
        nid = cur.fetchone()[0]; conn.commit(); return nid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_notices(public_only=False, category=None, limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, title, content, category, priority, target_class, is_public, published, created_at FROM notices WHERE 1=1"
        params = []
        if public_only: q += " AND is_public=TRUE AND published=TRUE"
        if category: q += " AND category=%s"; params.append(category)
        q += " ORDER BY priority DESC, created_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def get_notice(notice_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, content, category, priority, target_class, is_public, published, created_at FROM notices WHERE id=%s;", (notice_id,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def update_notice(notice_id, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE notices SET title=%s, content=%s, category=%s, priority=%s, target_class=%s, is_public=%s, published=%s, updated_at=NOW() WHERE id=%s RETURNING id;",
                    (data["title"], data["content"], data.get("category") or "general",
                     data.get("priority") or "normal", data.get("target_class") or None,
                     _to_bool(data.get("is_public")), _to_bool(data.get("published")), notice_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_notice(notice_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM notices WHERE id=%s;", (notice_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_unread_notices(days=7):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM notices WHERE published=TRUE AND created_at > NOW() - INTERVAL '7 days';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def students_phone_list(class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT name, parent_phone, class_name, section FROM students WHERE status='active' AND parent_phone IS NOT NULL AND parent_phone != ''"
        params = []
        if class_name: q += " AND class_name=%s"; params.append(class_name)
        q += " ORDER BY class_name, section, name;"
        cur.execute(q, tuple(params))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 7 — PARENTS (AUTH) + CHILDREN
# ============================================================
def create_parent(phone, password, name=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO parents (phone, password_hash, name) VALUES (%s,%s,%s) RETURNING id;",
                    (phone, generate_password_hash(password), name))
        pid = cur.fetchone()[0]; conn.commit(); return pid
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def get_parent_by_phone(phone):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, phone, password_hash, name FROM parents WHERE phone=%s;", (phone,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def verify_parent(phone, password):
    row = get_parent_by_phone(phone)
    if not row: return None
    if check_password_hash(row[2], password):
        return {"id": row[0], "phone": row[1], "name": row[3]}
    return None

def phone_exists_in_students(phone):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM students WHERE parent_phone=%s LIMIT 1;", (phone,))
        return cur.fetchone() is not None
    finally:
        cur.close(); conn.close()

def get_children_for_parent(identifier):
    conn = get_conn(); cur = conn.cursor()
    try:
        try:
            cur.execute("SELECT id, name, roll_no, class_name, section, photo_url FROM students WHERE parent_id=%s AND status='active' ORDER BY name;", (identifier,))
            rows = cur.fetchall()
            if rows:
                return [{"id": r[0], "name": r[1], "roll": r[2], "roll_no": r[2],
                         "class_name": r[3], "section": r[4], "photo_url": r[5]} for r in rows]
        except Exception:
            conn.rollback()
        try:
            cur.execute("SELECT s.id, s.name, s.roll_no, s.class_name, s.section, s.photo_url FROM students s JOIN parents p ON s.parent_phone = p.phone WHERE p.id=%s AND s.status='active' ORDER BY s.name;", (identifier,))
            rows = cur.fetchall()
            if rows:
                return [{"id": r[0], "name": r[1], "roll": r[2], "roll_no": r[2],
                         "class_name": r[3], "section": r[4], "photo_url": r[5]} for r in rows]
        except Exception:
            conn.rollback()
        cur.execute("SELECT id, name, roll_no, class_name, section, photo_url FROM students WHERE parent_phone=%s AND status='active' ORDER BY name;", (str(identifier),))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll": r[2], "roll_no": r[2],
                 "class_name": r[3], "section": r[4], "photo_url": r[5]} for r in rows]
    except Exception:
        conn.rollback(); return []
    finally:
        cur.close(); conn.close()

def get_parent_info(parent_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, phone, name, email FROM parents WHERE id=%s;", (parent_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "phone": row[1], "name": row[2] or row[1], "email": row[3]}
    except Exception:
        conn.rollback()
        try:
            cur.execute("SELECT id, phone, name FROM parents WHERE id=%s;", (parent_id,))
            row = cur.fetchone()
            if not row: return None
            return {"id": row[0], "phone": row[1], "name": row[2] or row[1], "email": None}
        except Exception:
            return None
    finally:
        cur.close(); conn.close()

def get_exams_for_class(class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, exam_date, subjects, max_marks FROM exams WHERE class_name=%s ORDER BY exam_date DESC NULLS LAST, id DESC;", (class_name,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "exam_date": r[2], "subjects": r[3] or [], "max_marks": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_notices_for_class(class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, content, category, priority, target_class, created_at FROM notices WHERE published=TRUE AND (is_public=TRUE OR target_class=%s OR target_class IS NULL) ORDER BY priority DESC, created_at DESC LIMIT 50;", (class_name,))
        rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "category": r[3],
                 "priority": r[4], "target_class": r[5], "created_at": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 8 — SETTINGS
# ============================================================
def get_settings():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, school_name, tagline, address, phone, email, logo_url FROM settings WHERE id=1;")
        row = cur.fetchone()
        if not row:
            return {"school_name": "My School", "tagline": "", "address": "",
                    "phone": "", "email": "", "logo_url": ""}
        return {"school_name": row[1] or "My School", "tagline": row[2] or "",
                "address": row[3] or "", "phone": row[4] or "",
                "email": row[5] or "", "logo_url": row[6] or ""}
    finally:
        cur.close(); conn.close()

def update_settings(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE settings SET school_name=%s, tagline=%s, address=%s, phone=%s, email=%s, logo_url=%s, updated_at=NOW() WHERE id=1;",
                    (data.get("school_name") or "My School", data.get("tagline") or "",
                     data.get("address") or "", data.get("phone") or "",
                     data.get("email") or "", data.get("logo_url") or ""))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 9 — CHARTS & REPORTS
# ============================================================
def get_fees_monthly_trend(months=6):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT month, SUM(amount) AS total FROM fee_payments WHERE month IS NOT NULL AND month != '' GROUP BY month ORDER BY month DESC LIMIT %s;", (months,))
        rows = cur.fetchall()
        return [{"label": r[0], "value": float(r[1] or 0)} for r in reversed(rows)]
    finally:
        cur.close(); conn.close()

def get_attendance_trend(days=7):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT date, COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status IN ('present','absent','late','leave')) FROM attendance WHERE date >= CURRENT_DATE - INTERVAL '%s days' GROUP BY date ORDER BY date;", (int(days),))
        rows = cur.fetchall()
        out = []
        for r in rows:
            total = r[2] or 0
            pct = round((r[1] / total) * 100, 1) if total else 0
            out.append({"label": r[0].strftime("%d %b"), "value": pct})
        return out
    finally:
        cur.close(); conn.close()

def get_students_by_class():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(class_name, 'Unassigned'), COUNT(*) FROM students WHERE status='active' GROUP BY class_name ORDER BY class_name NULLS LAST;")
        rows = cur.fetchall()
        return [{"label": r[0], "value": r[1]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_fees_summary():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM fee_payments;")
        row = cur.fetchone()
        return {"total": float(row[0] or 0), "payments": row[1] or 0}
    finally:
        cur.close(); conn.close()

def get_fee_report(start_date, end_date, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT p.id, p.receipt_no, p.paid_at, p.month, p.fee_type, p.amount, p.mode, s.name, s.roll_no, s.class_name, s.section FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE DATE(p.paid_at) BETWEEN %s AND %s"
        params = [start_date, end_date]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        q += " ORDER BY p.paid_at DESC;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "receipt_no": r[1], "paid_at": r[2], "month": r[3],
                 "fee_type": r[4], "amount": float(r[5] or 0), "mode": r[6],
                 "student_name": r[7], "roll": r[8], "class_name": r[9], "section": r[10]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_fee_report_summary(start_date, end_date, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT COALESCE(SUM(p.amount),0), COUNT(p.id) FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE DATE(p.paid_at) BETWEEN %s AND %s"
        params = [start_date, end_date]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        cur.execute(q, tuple(params)); row = cur.fetchone()
        total, count = float(row[0] or 0), row[1] or 0
        q2 = "SELECT p.mode, COALESCE(SUM(p.amount),0) FROM fee_payments p JOIN students s ON s.id = p.student_id WHERE DATE(p.paid_at) BETWEEN %s AND %s"
        p2 = [start_date, end_date]
        if class_name: q2 += " AND s.class_name=%s"; p2.append(class_name)
        q2 += " GROUP BY p.mode ORDER BY 2 DESC;"
        cur.execute(q2, tuple(p2))
        modes = [{"mode": r[0], "amount": float(r[1] or 0)} for r in cur.fetchall()]
        return {"total": total, "count": count, "modes": modes}
    finally:
        cur.close(); conn.close()

def get_attendance_report(month, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT s.id, s.name, s.roll_no, s.class_name, s.section, COUNT(a.id) FILTER (WHERE a.status='present'), COUNT(a.id) FILTER (WHERE a.status='absent'), COUNT(a.id) FILTER (WHERE a.status='late'), COUNT(a.id) FILTER (WHERE a.status='leave'), COUNT(a.id) FROM students s LEFT JOIN attendance a ON a.student_id = s.id AND TO_CHAR(a.date, 'YYYY-MM') = %s WHERE s.status='active'"
        params = [month]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        q += " GROUP BY s.id, s.name, s.roll_no, s.class_name, s.section ORDER BY s.class_name, s.section, s.roll_no;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        out = []
        for r in rows:
            present, late, total = r[5] or 0, r[7] or 0, r[9] or 0
            pct = round(((present + late * 0.5) / total) * 100, 1) if total else 0
            out.append({"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3], "section": r[4],
                        "present": present, "absent": r[6] or 0, "late": late,
                        "leave": r[8] or 0, "total": total, "percent": pct})
        return out
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 10 — STAFF
# ============================================================
def create_staff(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO staff (name, role, phone, email, qualification, subjects, classes, salary, join_date, address, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["name"], data.get("role") or "teacher", data.get("phone") or None,
                     data.get("email") or None, data.get("qualification") or None,
                     data.get("subjects") or [], data.get("classes") or [],
                     float(data["salary"]) if data.get("salary") else None,
                     data.get("join_date") or None, data.get("address") or None,
                     data.get("status") or "active"))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_staff_list(search=None, role=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, role, phone, email, subjects, classes, status, join_date, salary FROM staff WHERE 1=1"
        params = []
        if search:
            q += " AND (name ILIKE %s OR phone ILIKE %s OR email ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        if role: q += " AND role=%s"; params.append(role)
        q += " ORDER BY role, name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "role": r[2], "phone": r[3], "email": r[4],
                 "subjects": r[5] or [], "classes": r[6] or [], "status": r[7],
                 "join_date": r[8], "salary": float(r[9]) if r[9] else 0} for r in rows]
    finally:
        cur.close(); conn.close()

def get_staff(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, role, phone, email, qualification, subjects, classes, salary, join_date, address, status, created_at FROM staff WHERE id=%s;", (staff_id,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","name","role","phone","email","qualification","subjects","classes",
                "salary","join_date","address","status","created_at"]
        d = dict(zip(keys, row)); d["salary"] = float(d["salary"] or 0); return d
    finally:
        cur.close(); conn.close()

def update_staff(staff_id, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE staff SET name=%s, role=%s, phone=%s, email=%s, qualification=%s, subjects=%s, classes=%s, salary=%s, join_date=%s, address=%s, status=%s WHERE id=%s RETURNING id;",
                    (data["name"], data.get("role") or "teacher", data.get("phone") or None,
                     data.get("email") or None, data.get("qualification") or None,
                     data.get("subjects") or [], data.get("classes") or [],
                     float(data["salary"]) if data.get("salary") else None,
                     data.get("join_date") or None, data.get("address") or None,
                     data.get("status") or "active", staff_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_staff(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM staff WHERE id=%s;", (staff_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_active_staff():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM staff WHERE status='active';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 11 — BULK STUDENTS
# ============================================================
def check_roll_no_exists(roll_no):
    if not roll_no: return False
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM students WHERE roll_no=%s LIMIT 1;", (roll_no,))
        return cur.fetchone() is not None
    finally:
        cur.close(); conn.close()

def get_existing_roll_nos(roll_nos):
    if not roll_nos: return set()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT roll_no FROM students WHERE roll_no = ANY(%s);", (list(roll_nos),))
        return {r[0] for r in cur.fetchall()}
    finally:
        cur.close(); conn.close()

def bulk_create_students(rows):
    if not rows: return 0, []
    conn = get_conn(); cur = conn.cursor()
    inserted, failed = 0, []
    try:
        for idx, r in enumerate(rows):
            try:
                cur.execute("SAVEPOINT sp_student_row;")
                cur.execute("INSERT INTO students (name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, address, admission_date, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                            (r["name"], r.get("roll_no") or None, r.get("class_name") or None,
                             r.get("section") or None, r.get("gender") or None,
                             r.get("dob") or None, r.get("parent_name") or None,
                             r.get("parent_phone") or None, r.get("address") or None,
                             r.get("admission_date") or None, "active"))
                cur.execute("RELEASE SAVEPOINT sp_student_row;")
                inserted += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_student_row;")
                failed.append({"row": idx+1, "name": r.get("name","?"), "error": str(e)[:120]})
        conn.commit(); return inserted, failed
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def check_duplicate_student(name, roll_no, parent_phone, exclude_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        conds, params = [], []
        if roll_no: conds.append("roll_no=%s"); params.append(roll_no)
        if parent_phone: conds.append("parent_phone=%s"); params.append(parent_phone)
        if name: conds.append("LOWER(name)=LOWER(%s)"); params.append(name.strip())
        if not conds: return []
        q = f"SELECT id, name, roll_no, class_name, section, parent_phone FROM students WHERE ({' OR '.join(conds)})"
        if exclude_id:
            q += " AND id != %s"; params.append(exclude_id)
        q += " LIMIT 10;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3],
                 "section": r[4], "parent_phone": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 12 — WHATSAPP
# ============================================================
def get_whatsapp_templates(category=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, category, body, created_at FROM whatsapp_templates"
        params = []
        if category: q += " WHERE category=%s"; params.append(category)
        q += " ORDER BY category, name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "category": r[2], "body": r[3], "created_at": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_whatsapp_template(tid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, category, body FROM whatsapp_templates WHERE id=%s;", (tid,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "name": row[1], "category": row[2], "body": row[3]}
    finally:
        cur.close(); conn.close()

def create_whatsapp_template(name, category, body):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO whatsapp_templates (name, category, body) VALUES (%s,%s,%s) RETURNING id;",
                    (name, category, body))
        tid = cur.fetchone()[0]; conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_whatsapp_template(tid, name, category, body):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE whatsapp_templates SET name=%s, category=%s, body=%s WHERE id=%s RETURNING id;",
                    (name, category, body, tid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_whatsapp_template(tid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM whatsapp_templates WHERE id=%s;", (tid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def log_whatsapp(student_id, template_id, phone, message, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO whatsapp_logs (student_id, template_id, phone, message, sent_by) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (student_id, template_id, phone, message, admin_id))
        lid = cur.fetchone()[0]; conn.commit(); return lid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_recent_whatsapp_logs(limit=50):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT wl.id, wl.sent_at, wl.phone, s.name, s.class_name, wt.name FROM whatsapp_logs wl LEFT JOIN students s ON s.id = wl.student_id LEFT JOIN whatsapp_templates wt ON wt.id = wl.template_id ORDER BY wl.sent_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "sent_at": r[1], "phone": r[2], "student_name": r[3],
                 "class_name": r[4], "template_name": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def was_sent_recently(student_id, template_id, days=7):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT sent_at FROM whatsapp_logs WHERE student_id=%s AND template_id=%s AND sent_at > NOW() - INTERVAL '%s days' ORDER BY sent_at DESC LIMIT 1;",
                    (student_id, template_id, int(days)))
        row = cur.fetchone(); return row[0] if row else None
    finally:
        cur.close(); conn.close()

def get_students_for_reminder(month, min_att_percent=None, only_defaulters=False, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT s.id, s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone,
                      COALESCE(fs.total,0) AS fee_due, COALESCE(fp.paid,0) AS fee_paid,
                      COALESCE(att.att_pct, NULL) AS att_pct
               FROM students s
               LEFT JOIN (SELECT class_name, SUM(amount) AS total FROM fee_structure GROUP BY class_name) fs
                   ON fs.class_name = s.class_name
               LEFT JOIN (SELECT student_id, SUM(amount) AS paid FROM fee_payments WHERE month=%s GROUP BY student_id) fp
                   ON fp.student_id = s.id
               LEFT JOIN (SELECT student_id, ROUND((COUNT(*) FILTER (WHERE status='present') * 100.0 / NULLIF(COUNT(*),0))::numeric, 1) AS att_pct
                          FROM attendance WHERE TO_CHAR(date, 'YYYY-MM') = %s GROUP BY student_id) att
                   ON att.student_id = s.id
               WHERE s.status='active' AND s.parent_phone IS NOT NULL AND s.parent_phone != ''"""
        params = [month, month]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        if only_defaulters: q += " AND COALESCE(fs.total,0) > COALESCE(fp.paid,0)"
        q += " ORDER BY s.class_name, s.section, s.roll_no;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        out = []
        for r in rows:
            due, paid = float(r[7] or 0), float(r[8] or 0)
            att = float(r[9]) if r[9] is not None else None
            if min_att_percent is not None and (att is None or att >= min_att_percent):
                continue
            out.append({"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3],
                        "section": r[4], "parent_name": r[5], "phone": r[6],
                        "pending_fees": max(due - paid, 0), "attendance_pct": att})
        return out
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 13 — BACKUP / RESTORE
# ============================================================
def backup_all_tables():
    conn = get_conn(); cur = conn.cursor()
    try:
        result = {"backup_at": datetime.now().isoformat(), "tables": {}}
        for table in BACKUP_TABLES:
            try:
                cur.execute(f'SELECT * FROM "{table}";')
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                result["tables"][table] = {
                    "columns": cols,
                    "rows": [{c: _json_safe(v) for c, v in zip(cols, row)} for row in rows],
                    "count": len(rows),
                }
            except Exception as e:
                conn.rollback()
                result["tables"][table] = {"error": str(e), "rows": [], "count": 0}
        return result
    finally:
        cur.close(); conn.close()

def restore_table(table, rows):
    if table not in BACKUP_TABLES: return 0, [f"Table '{table}' not allowed"]
    if not rows: return 0, []
    conn = get_conn(); cur = conn.cursor()
    inserted, errors = 0, []
    try:
        for idx, row in enumerate(rows):
            cols = list(row.keys())
            placeholders = ",".join(["%s"] * len(cols))
            col_names = ",".join([f'"{c}"' for c in cols])
            try:
                cur.execute("SAVEPOINT sp_restore_row;")
                cur.execute(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})',
                            [row[c] for c in cols])
                cur.execute("RELEASE SAVEPOINT sp_restore_row;")
                inserted += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_restore_row;")
                errors.append({"row": idx+1, "error": str(e)[:150]})
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
    try: _reset_sequence(table)
    except Exception: pass
    return inserted, errors

def _reset_sequence(table):
    if table not in BACKUP_TABLES: return
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM \"{table}\"), 1), true);")
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close(); conn.close()

def count_all_rows():
    conn = get_conn(); cur = conn.cursor()
    try:
        result = {}
        for table in BACKUP_TABLES:
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                result[table] = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                result[table] = "?"
        return result
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 14 — BILLS
# ============================================================
def generate_bills_for_class(class_name, month, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT fee_type, amount FROM fee_structure WHERE class_name=%s ORDER BY fee_type;", (class_name,))
        items = [{"fee_type": r[0], "amount": float(r[1])} for r in cur.fetchall()]
        if not items:
            return {"created": 0, "skipped": 0, "error": "Fee structure nahi hai"}
        base_total = sum(item["amount"] for item in items)
        items_json = _json.dumps(items)
        q = "SELECT id FROM students WHERE status='active' AND class_name=%s"
        params = [class_name]
        if section: q += " AND section=%s"; params.append(section)
        cur.execute(q, tuple(params))
        student_ids = [r[0] for r in cur.fetchall()]
        created, skipped, total_discounted, total_net_billed = 0, 0, 0.0, 0.0
        for sid in student_ids:
            try:
                cur.execute("SAVEPOINT sp_bill_row;")
                try:
                    discount_amount, discount_items = compute_student_discount(base_total, sid)
                except Exception:
                    discount_amount, discount_items = 0, []
                discount_amount = float(discount_amount or 0)
                final_total = max(base_total - discount_amount, 0.0)
                disc_json = _json.dumps(_json_safe(discount_items))
                cur.execute("INSERT INTO bills (student_id, month, total_amount, base_amount, discount_amount, discount_items, items, status) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,'pending');",
                            (sid, month, final_total, base_total, discount_amount, disc_json, items_json))
                cur.execute("RELEASE SAVEPOINT sp_bill_row;")
                created += 1
                total_discounted += discount_amount
                total_net_billed += final_total
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_bill_row;")
                skipped += 1
        conn.commit()
        return {"created": created, "skipped": skipped, "error": None,
                "total_students": len(student_ids), "total_amount": base_total,
                "total_discounted": total_discounted, "net_billed": total_net_billed}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_bills(month, status=None, class_name=None, search=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT b.id, b.student_id, b.month, b.total_amount, b.status, b.generated_at,
                      s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone,
                      COALESCE(p.paid, 0) AS paid_amount
               FROM bills b JOIN students s ON s.id = b.student_id
               LEFT JOIN (SELECT student_id, SUM(amount) AS paid FROM fee_payments WHERE month=%s GROUP BY student_id) p
                   ON p.student_id = b.student_id
               WHERE b.month=%s"""
        params = [month, month]
        if class_name: q += " AND s.class_name=%s"; params.append(class_name)
        if search:
            q += " AND (s.name ILIKE %s OR s.roll_no ILIKE %s)"
            like = f"%{search}%"; params += [like, like]
        q += " ORDER BY s.class_name, s.section, s.roll_no, s.name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        out = []
        for r in rows:
            total, paid = float(r[3] or 0), float(r[12] or 0)
            if paid >= total and total > 0: cstatus = "paid"
            elif paid > 0: cstatus = "partial"
            else: cstatus = "pending"
            if status and status != cstatus: continue
            out.append({"id": r[0], "student_id": r[1], "month": r[2], "total": total,
                        "status": cstatus, "generated_at": r[5], "student_name": r[6],
                        "roll": r[7], "class_name": r[8], "section": r[9],
                        "parent_name": r[10], "phone": r[11], "paid": paid,
                        "pending": max(total - paid, 0)})
        return out
    finally:
        cur.close(); conn.close()

def get_bill(bill_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT b.id, b.student_id, b.month, b.total_amount, b.base_amount, b.discount_amount, b.discount_items, b.items, b.generated_at, s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone, s.address, COALESCE((SELECT SUM(amount) FROM fee_payments WHERE student_id=b.student_id AND month=b.month), 0) AS paid FROM bills b JOIN students s ON s.id = b.student_id WHERE b.id=%s;", (bill_id,))
        row = cur.fetchone()
        if not row: return None
        items = _json.loads(row[7]) if isinstance(row[7], str) else row[7]
        discount_items = _json.loads(row[6]) if isinstance(row[6], str) else row[6]
        return {"id": row[0], "student_id": row[1], "month": row[2],
                "total": float(row[3] or 0), "base": float(row[4] or 0),
                "discount": float(row[5] or 0), "discount_items": discount_items or [],
                "items": items or [], "generated_at": row[8], "student_name": row[9],
                "roll": row[10], "class_name": row[11], "section": row[12],
                "parent_name": row[13], "phone": row[14], "address": row[15],
                "paid": float(row[16] or 0)}
    finally:
        cur.close(); conn.close()

def delete_bills_for_month(month, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if class_name:
            cur.execute("DELETE FROM bills WHERE month=%s AND student_id IN (SELECT id FROM students WHERE class_name=%s);", (month, class_name))
        else:
            cur.execute("DELETE FROM bills WHERE month=%s;", (month,))
        deleted = cur.rowcount; conn.commit(); return deleted
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_bills_summary(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(b.total_amount), 0) FROM bills b WHERE b.month=%s;", (month,))
        row = cur.fetchone(); total_bills, total_amount = row[0] or 0, float(row[1] or 0)
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM fee_payments WHERE month=%s;", (month,))
        collected = float(cur.fetchone()[0] or 0)
        return {"total_bills": total_bills, "total_amount": total_amount,
                "collected": collected, "pending": max(total_amount - collected, 0)}
    finally:
        cur.close(); conn.close()

def check_bills_exist(month, class_name=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if class_name:
            cur.execute("SELECT COUNT(*) FROM bills b JOIN students s ON s.id=b.student_id WHERE b.month=%s AND s.class_name=%s;", (month, class_name))
        else:
            cur.execute("SELECT COUNT(*) FROM bills WHERE month=%s;", (month,))
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

# ════════════════════════════════════════════════════════════
# ══════════════ PHASE 2 — OPERATIONS MODULES ════════════════
# ════════════════════════════════════════════════════════════

# ============================================================
# SECTION 15 — TIMETABLE
# ============================================================
def get_timetable_grid(class_name, section=''):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT t.day_of_week, t.period_no, t.subject, t.staff_id, s.name FROM timetable t LEFT JOIN staff s ON s.id = t.staff_id WHERE t.class_name=%s AND t.section=%s;",
                    (class_name, section or ''))
        rows = cur.fetchall()
        return {(r[0], r[1]): {"subject": r[2], "staff_id": r[3], "staff_name": r[4]} for r in rows}
    finally:
        cur.close(); conn.close()

def save_timetable_cell(class_name, section, day, period, subject, staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        section, subject = section or '', (subject or '').strip()
        if not subject:
            cur.execute("DELETE FROM timetable WHERE class_name=%s AND section=%s AND day_of_week=%s AND period_no=%s;",
                        (class_name, section, day, period))
        else:
            cur.execute("INSERT INTO timetable (class_name, section, day_of_week, period_no, subject, staff_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (class_name, section, day_of_week, period_no) DO UPDATE SET subject=EXCLUDED.subject, staff_id=EXCLUDED.staff_id, updated_at=NOW();",
                        (class_name, section, day, period, subject, staff_id or None))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_teacher_timetable(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT day_of_week, period_no, class_name, section, subject FROM timetable WHERE staff_id=%s ORDER BY day_of_week, period_no;", (staff_id,))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

# --- NAYA FUNCTION: Absent Teachers Fetch Karne Ke Liye ---
def get_absent_teachers(date_str):
    """Us specific date par absent teachers ki ID list return karta hai"""
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT teacher_id 
            FROM teacher_attendance 
            WHERE date = %s AND LOWER(status) = 'absent'
        """, (date_str,))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        conn.rollback()
        print(f"Error fetching absent teachers: {e}")
        return []
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 16 — SALARY
# ============================================================
def _gen_slip_no():
    return f"SAL-{datetime.now().strftime('%Y%m%d')}-{_random.randint(1000,9999)}"

def generate_salary_for_month(month, staff_ids=None):
    conn = get_conn(); cur = conn.cursor()
    created, skipped = 0, 0
    try:
        q = "SELECT id, salary FROM staff WHERE status='active' AND salary IS NOT NULL AND salary > 0"
        params = []
        if staff_ids: q += " AND id = ANY(%s)"; params.append(list(staff_ids))
        cur.execute(q, tuple(params)); staff_rows = cur.fetchall()
        for sid, base in staff_rows:
            try:
                cur.execute("SAVEPOINT sp_sal_row;")
                base_f = float(base)
                cur.execute("INSERT INTO salary_records (staff_id, month, base_salary, bonus, deductions, net_amount, status, note) VALUES (%s,%s,%s,0,%s,%s,'pending',%s);",
                            (sid, month, base_f, 0, base_f, None))
                cur.execute("RELEASE SAVEPOINT sp_sal_row;")
                created += 1
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_sal_row;")
                skipped += 1
        conn.commit()
        return {"created": created, "skipped": skipped, "total_staff": len(staff_rows)}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_salary_records(month, status=None, search=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT sr.id, sr.staff_id, sr.month, sr.base_salary, sr.bonus, sr.deductions, sr.net_amount, sr.status, sr.paid_at, sr.mode, sr.slip_no, s.name, s.role, s.phone FROM salary_records sr JOIN staff s ON s.id = sr.staff_id WHERE sr.month=%s"
        params = [month]
        if status: q += " AND sr.status=%s"; params.append(status)
        if search: q += " AND s.name ILIKE %s"; params.append(f"%{search}%")
        q += " ORDER BY s.role, s.name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "staff_id": r[1], "month": r[2], "base": float(r[3] or 0),
                 "bonus": float(r[4] or 0), "deductions": float(r[5] or 0),
                 "net": float(r[6] or 0), "status": r[7], "paid_at": r[8],
                 "mode": r[9], "slip_no": r[10], "name": r[11], "role": r[12],
                 "phone": r[13]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_salary_record(rid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT sr.id, sr.staff_id, sr.month, sr.base_salary, sr.bonus, sr.deductions, sr.net_amount, sr.status, sr.paid_at, sr.mode, sr.note, sr.slip_no, sr.created_at, s.name, s.role, s.phone, s.email, s.qualification FROM salary_records sr JOIN staff s ON s.id = sr.staff_id WHERE sr.id=%s;", (rid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","staff_id","month","base","bonus","deductions","net","status",
                "paid_at","mode","note","slip_no","created_at","name","role",
                "phone","email","qualification"]
        d = dict(zip(keys, row))
        for k in ["base","bonus","deductions","net"]: d[k] = float(d[k] or 0)
        return d
    finally:
        cur.close(); conn.close()

def update_salary_adjustments(rid, bonus, deductions):
    conn = get_conn(); cur = conn.cursor()
    try:
        b, d = float(bonus or 0), float(deductions or 0)
        cur.execute("UPDATE salary_records SET bonus=%s, deductions=%s, net_amount = base_salary + %s - %s WHERE id=%s AND status='pending' RETURNING id;",
                    (b, d, b, d, rid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def mark_salary_paid(rid, mode, note, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        slip_no = _gen_slip_no()
        for _ in range(5):
            cur.execute("SELECT 1 FROM salary_records WHERE slip_no=%s;", (slip_no,))
            if not cur.fetchone(): break
            slip_no = _gen_slip_no()
        cur.execute("UPDATE salary_records SET status='paid', paid_at=NOW(), mode=%s, note=%s, slip_no=%s, recorded_by=%s WHERE id=%s AND status='pending' RETURNING slip_no;",
                    (mode, note or "", slip_no, admin_id, rid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_salary_record(rid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM salary_records WHERE id=%s AND status='pending';", (rid,))
        n = cur.rowcount; conn.commit(); return n
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_salary_summary(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='paid'), COUNT(*) FILTER (WHERE status='pending'), COALESCE(SUM(net_amount) FILTER (WHERE status='paid'),0), COALESCE(SUM(net_amount) FILTER (WHERE status='pending'),0) FROM salary_records WHERE month=%s;", (month,))
        r = cur.fetchone()
        return {"total": r[0] or 0, "paid_count": r[1] or 0, "pending_count": r[2] or 0,
                "paid_amount": float(r[3] or 0), "pending_amount": float(r[4] or 0)}
    finally:
        cur.close(); conn.close()

def get_staff_salary_history(staff_id, limit=12):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, month, net_amount, status, paid_at, slip_no FROM salary_records WHERE staff_id=%s ORDER BY month DESC LIMIT %s;", (staff_id, limit))
        rows = cur.fetchall()
        return [{"id": r[0], "month": r[1], "net": float(r[2] or 0), "status": r[3],
                 "paid_at": r[4], "slip_no": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_staff_attendance_summary(staff_id, month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status='absent'), COUNT(*) FILTER (WHERE status='half_day'), COUNT(*) FILTER (WHERE status='leave'), COUNT(*) FILTER (WHERE status='holiday'), COUNT(*) FROM staff_attendance WHERE staff_id=%s AND TO_CHAR(date, 'YYYY-MM')=%s;",
                    (staff_id, month))
        r = cur.fetchone()
        if not r:
            return {"present":0,"absent":0,"half_day":0,"leave":0,"holiday":0,
                    "total_marked":0,"working_days":0,"percent":0}
        present, absent, half, leave_c = r[0] or 0, r[1] or 0, r[2] or 0, r[3] or 0
        total_working = present + absent + half + leave_c
        pct = round(((present + half * 0.5) / total_working) * 100, 1) if total_working > 0 else 0
        return {"present": present, "absent": absent, "half_day": half, "leave": leave_c,
                "holiday": r[4] or 0, "total_marked": r[5] or 0,
                "working_days": total_working, "percent": pct}
    finally:
        cur.close(); conn.close()

def get_staff_attendance_for_salary(staff_id, month):
    s = get_staff_attendance_summary(staff_id, month)
    return {"absent_days": s["absent"], "half_days": s["half_day"],
            "unpaid_leave": s["leave"],
            "total_deduction_days": s["absent"] + (s["half_day"] * 0.5) + s["leave"]}

# ============================================================
# SECTION 17 — HOMEWORK
# ============================================================
def create_homework(data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO homework (class_name, section, subject, title, description, due_date, attachment_url, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["class_name"], data.get("section") or '', data["subject"],
                     data["title"], data.get("description") or None,
                     data.get("due_date") or None, data.get("attachment_url") or None, admin_id))
        hid = cur.fetchone()[0]; conn.commit(); return hid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_homework_list(class_name=None, section=None, subject=None, search=None, limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, class_name, section, subject, title, description, due_date, attachment_url, created_at FROM homework WHERE 1=1"
        params = []
        if class_name: q += " AND class_name=%s"; params.append(class_name)
        if section is not None and section != '':
            q += " AND (section=%s OR section='')"; params.append(section)
        if subject: q += " AND subject ILIKE %s"; params.append(f"%{subject}%")
        if search:
            q += " AND (title ILIKE %s OR description ILIKE %s)"
            like = f"%{search}%"; params += [like, like]
        q += " ORDER BY COALESCE(due_date, created_at::date) DESC, created_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "class_name": r[1], "section": r[2] or '', "subject": r[3],
                 "title": r[4], "description": r[5], "due_date": r[6],
                 "attachment_url": r[7], "created_at": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_homework(hid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, class_name, section, subject, title, description, due_date, attachment_url, created_at, updated_at FROM homework WHERE id=%s;", (hid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","class_name","section","subject","title","description",
                "due_date","attachment_url","created_at","updated_at"]
        return dict(zip(keys, row))
    finally:
        cur.close(); conn.close()

def update_homework(hid, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE homework SET class_name=%s, section=%s, subject=%s, title=%s, description=%s, due_date=%s, attachment_url=%s, updated_at=NOW() WHERE id=%s RETURNING id;",
                    (data["class_name"], data.get("section") or '', data["subject"],
                     data["title"], data.get("description") or None,
                     data.get("due_date") or None, data.get("attachment_url") or None, hid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_homework(hid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM homework WHERE id=%s;", (hid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_homework_for_class(class_name, section='', limit=20):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, subject, title, description, due_date, attachment_url, created_at FROM homework WHERE class_name=%s AND (section=%s OR section='') ORDER BY COALESCE(due_date, created_at::date) DESC, created_at DESC LIMIT %s;",
                    (class_name, section or '', limit))
        rows = cur.fetchall()
        return [{"id": r[0], "subject": r[1], "title": r[2], "description": r[3],
                 "due_date": r[4], "attachment_url": r[5], "created_at": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def count_homework_this_week():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM homework WHERE created_at > NOW() - INTERVAL '7 days';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 18 — TRANSPORT
# ============================================================
def create_bus_route(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO bus_routes (name, driver_name, driver_phone, vehicle_no, capacity, fee_per_month, status) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["name"], data.get("driver_name") or None,
                     data.get("driver_phone") or None, data.get("vehicle_no") or None,
                     int(data.get("capacity") or 40),
                     float(data.get("fee_per_month") or 0),
                     data.get("status") or "active"))
        rid = cur.fetchone()[0]; conn.commit(); return rid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_bus_routes(search=None, status=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT r.id, r.name, r.driver_name, r.driver_phone, r.vehicle_no,
                      r.capacity, r.fee_per_month, r.status,
                      (SELECT COUNT(*) FROM bus_stops WHERE route_id=r.id) AS stop_count,
                      (SELECT COUNT(*) FROM student_transport WHERE route_id=r.id AND status='active') AS student_count
               FROM bus_routes r WHERE 1=1"""
        params = []
        if search:
            q += " AND (r.name ILIKE %s OR r.vehicle_no ILIKE %s OR r.driver_name ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        if status: q += " AND r.status=%s"; params.append(status)
        q += " ORDER BY r.name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "driver_name": r[2], "driver_phone": r[3],
                 "vehicle_no": r[4], "capacity": r[5], "fee_per_month": float(r[6] or 0),
                 "status": r[7], "stop_count": r[8], "student_count": r[9]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_bus_route(rid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, driver_name, driver_phone, vehicle_no, capacity, fee_per_month, status, created_at FROM bus_routes WHERE id=%s;", (rid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","name","driver_name","driver_phone","vehicle_no","capacity",
                "fee_per_month","status","created_at"]
        d = dict(zip(keys, row)); d["fee_per_month"] = float(d["fee_per_month"] or 0); return d
    finally:
        cur.close(); conn.close()

def update_bus_route(rid, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE bus_routes SET name=%s, driver_name=%s, driver_phone=%s, vehicle_no=%s, capacity=%s, fee_per_month=%s, status=%s WHERE id=%s RETURNING id;",
                    (data["name"], data.get("driver_name") or None,
                     data.get("driver_phone") or None, data.get("vehicle_no") or None,
                     int(data.get("capacity") or 40),
                     float(data.get("fee_per_month") or 0),
                     data.get("status") or "active", rid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_bus_route(rid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM bus_routes WHERE id=%s;", (rid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_bus_stops(route_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, route_id, name, pickup_time, drop_time, sequence FROM bus_stops WHERE route_id=%s ORDER BY sequence, name;", (route_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "route_id": r[1], "name": r[2], "pickup_time": r[3],
                 "drop_time": r[4], "sequence": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_bus_stop(sid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, route_id, name, pickup_time, drop_time, sequence FROM bus_stops WHERE id=%s;", (sid,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "route_id": row[1], "name": row[2],
                "pickup_time": row[3], "drop_time": row[4], "sequence": row[5]}
    finally:
        cur.close(); conn.close()

def create_bus_stop(route_id, name, pickup_time, drop_time, sequence):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO bus_stops (route_id, name, pickup_time, drop_time, sequence) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (route_id, name, pickup_time or None, drop_time or None, sequence or 1))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_bus_stop(sid, name, pickup_time, drop_time, sequence):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE bus_stops SET name=%s, pickup_time=%s, drop_time=%s, sequence=%s WHERE id=%s RETURNING id;",
                    (name, pickup_time or None, drop_time or None, sequence or 1, sid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_bus_stop(sid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM bus_stops WHERE id=%s;", (sid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def assign_student_transport(student_id, route_id, stop_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO student_transport (student_id, route_id, stop_id, status) VALUES (%s,%s,%s,'active') ON CONFLICT (student_id) DO UPDATE SET route_id=EXCLUDED.route_id, stop_id=EXCLUDED.stop_id, status='active';",
                    (student_id, route_id, stop_id or None))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def remove_student_transport(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM student_transport WHERE student_id=%s;", (student_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_students_on_route(route_id, search=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT st.id, st.student_id, st.stop_id, st.status, s.name, s.roll_no,
                      s.class_name, s.section, s.parent_phone, bs.name AS stop_name,
                      bs.pickup_time, bs.drop_time
               FROM student_transport st
               JOIN students s ON s.id = st.student_id
               LEFT JOIN bus_stops bs ON bs.id = st.stop_id
               WHERE st.route_id=%s"""
        params = [route_id]
        if search:
            q += " AND (s.name ILIKE %s OR s.roll_no ILIKE %s)"
            like = f"%{search}%"; params += [like, like]
        q += " ORDER BY bs.sequence NULLS LAST, s.class_name, s.section, s.roll_no;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "student_id": r[1], "stop_id": r[2], "status": r[3],
                 "name": r[4], "roll": r[5], "class_name": r[6], "section": r[7],
                 "phone": r[8], "stop_name": r[9], "pickup_time": r[10],
                 "drop_time": r[11]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_student_transport(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT st.id, st.route_id, st.stop_id, r.name, r.driver_name, r.driver_phone, r.vehicle_no, bs.name, bs.pickup_time, bs.drop_time FROM student_transport st LEFT JOIN bus_routes r ON r.id = st.route_id LEFT JOIN bus_stops bs ON bs.id = st.stop_id WHERE st.student_id=%s AND st.status='active';", (student_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "route_id": row[1], "stop_id": row[2], "route_name": row[3],
                "driver_name": row[4], "driver_phone": row[5], "vehicle_no": row[6],
                "stop_name": row[7], "pickup_time": row[8], "drop_time": row[9]}
    finally:
        cur.close(); conn.close()

def count_transport_students():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM student_transport WHERE status='active';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def get_all_routes_with_stops():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, driver_name, driver_phone, vehicle_no, capacity, fee_per_month, status FROM bus_routes WHERE status='active' ORDER BY name;")
        routes_raw = cur.fetchall()
        routes = []
        for r in routes_raw:
            cur.execute("SELECT id, route_id, name, pickup_time, drop_time, sequence FROM bus_stops WHERE route_id=%s ORDER BY sequence, name;", (r[0],))
            stops = [{"id": s[0], "route_id": s[1], "name": s[2], "pickup_time": s[3],
                      "drop_time": s[4], "sequence": s[5]} for s in cur.fetchall()]
            routes.append({"id": r[0], "name": r[1], "driver_name": r[2],
                           "driver_phone": r[3], "vehicle_no": r[4], "capacity": r[5],
                           "fee_per_month": float(r[6] or 0), "status": r[7], "stops": stops})
        return routes
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 19 — EXPENSES
# ============================================================
def create_expense(data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO expenses (category, description, amount, expense_date, vendor, payment_mode, receipt_no, note, recorded_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["category"], data.get("description") or None, float(data["amount"]),
                     data.get("expense_date") or None, data.get("vendor") or None,
                     data.get("payment_mode") or "cash", data.get("receipt_no") or None,
                     data.get("note") or None, admin_id))
        eid = cur.fetchone()[0]; conn.commit(); return eid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_expenses(month=None, category=None, search=None, limit=200):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, category, description, amount, expense_date, vendor, payment_mode, receipt_no, note, created_at FROM expenses WHERE 1=1"
        params = []
        if month: q += " AND TO_CHAR(expense_date, 'YYYY-MM')=%s"; params.append(month)
        if category: q += " AND category=%s"; params.append(category)
        if search:
            q += " AND (description ILIKE %s OR vendor ILIKE %s OR receipt_no ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        q += " ORDER BY expense_date DESC, id DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "category": r[1], "description": r[2], "amount": float(r[3] or 0),
                 "expense_date": r[4], "vendor": r[5], "payment_mode": r[6],
                 "receipt_no": r[7], "note": r[8], "created_at": r[9]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_expense(eid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, category, description, amount, expense_date, vendor, payment_mode, receipt_no, note, created_at FROM expenses WHERE id=%s;", (eid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","category","description","amount","expense_date","vendor",
                "payment_mode","receipt_no","note","created_at"]
        d = dict(zip(keys, row)); d["amount"] = float(d["amount"] or 0); return d
    finally:
        cur.close(); conn.close()

def update_expense(eid, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE expenses SET category=%s, description=%s, amount=%s, expense_date=%s, vendor=%s, payment_mode=%s, receipt_no=%s, note=%s WHERE id=%s RETURNING id;",
                    (data["category"], data.get("description") or None, float(data["amount"]),
                     data.get("expense_date") or None, data.get("vendor") or None,
                     data.get("payment_mode") or "cash", data.get("receipt_no") or None,
                     data.get("note") or None, eid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_expense(eid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM expenses WHERE id=%s;", (eid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_expense_summary(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT category, COUNT(*), SUM(amount) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY-MM')=%s GROUP BY category ORDER BY 3 DESC;", (month,))
        rows = cur.fetchall()
        cats = [{"category": r[0], "count": r[1], "total": float(r[2] or 0)} for r in rows]
        return {"categories": cats, "total": sum(c["total"] for c in cats), "count": len(cats)}
    finally:
        cur.close(); conn.close()

def get_pnl(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM fee_payments WHERE month=%s;", (month,))
        fee_row = cur.fetchone(); fees_collected, fee_count = float(fee_row[0] or 0), fee_row[1] or 0
        cur.execute("SELECT COALESCE(SUM(net_amount) FILTER (WHERE status='paid'), 0), COALESCE(SUM(net_amount) FILTER (WHERE status='pending'), 0), COUNT(*) FILTER (WHERE status='paid'), COUNT(*) FILTER (WHERE status='pending') FROM salary_records WHERE month=%s;", (month,))
        sal_row = cur.fetchone(); salary_paid, salary_pending = float(sal_row[0] or 0), float(sal_row[1] or 0)
        cur.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY-MM')=%s;", (month,))
        exp_row = cur.fetchone(); expenses_total, expenses_count = float(exp_row[0] or 0), exp_row[1] or 0
        cur.execute("SELECT category, SUM(amount) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY-MM')=%s GROUP BY category ORDER BY 2 DESC;", (month,))
        exp_cats = [{"category": r[0], "amount": float(r[1] or 0)} for r in cur.fetchall()]
        total_outflow = salary_paid + expenses_total; net = fees_collected - total_outflow
        return {"month": month, "fees_collected": fees_collected, "fee_count": fee_count,
                "salary_paid": salary_paid, "salary_pending": salary_pending,
                "salary_paid_count": sal_row[2] or 0, "salary_pending_count": sal_row[3] or 0,
                "expenses_total": expenses_total, "expenses_count": expenses_count,
                "expense_categories": exp_cats, "total_outflow": total_outflow,
                "net": net, "profit": net >= 0}
    finally:
        cur.close(); conn.close()

def get_expense_monthly_trend(months=6):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT TO_CHAR(expense_date, 'YYYY-MM'), SUM(amount) FROM expenses WHERE expense_date >= CURRENT_DATE - INTERVAL '%s months' GROUP BY 1 ORDER BY 1;", (int(months),))
        rows = cur.fetchall()
        return [{"label": r[0], "value": float(r[1] or 0)} for r in rows]
    finally:
        cur.close(); conn.close()

def count_expenses_this_month():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY-MM') = TO_CHAR(NOW(), 'YYYY-MM');")
        return float(cur.fetchone()[0] or 0)
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 20 — CERTIFICATES
# ============================================================
def _build_default_body(cert_type, student):
    tpl = CERT_TEMPLATES.get(cert_type, "")
    if not tpl: return ""
    return tpl.format(name=student.get("name",""),
        parent_name=student.get("parent_name") or "___",
        class_name=student.get("class_name") or "___",
        section=f"-{student.get('section')}" if student.get("section") else "",
        roll=student.get("roll_no") or "___",
        ay=_academic_year_for_cert())

def _generate_cert_no(cert_type):
    year = datetime.now().year
    prefix = "".join([w[0] for w in cert_type.split()[:2]]).upper() or "CERT"
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM certificates WHERE cert_type=%s AND EXTRACT(YEAR FROM created_at)=%s;", (cert_type, year))
        n = (cur.fetchone()[0] or 0) + 1
        return f"{prefix}-{year}-{n:04d}"
    finally:
        cur.close(); conn.close()

def create_certificate(student_id, cert_type, body, remarks, admin_id, issue_date=None):
    row = get_student(student_id)
    if not row: raise ValueError("Student nahi mila")
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date",
            "status","created_at","photo_url"]
    student = dict(zip(keys, row))
    if not body or not body.strip(): body = _build_default_body(cert_type, student)
    conn = get_conn(); cur = conn.cursor()
    try:
        cert_no = _generate_cert_no(cert_type)
        for attempt in range(6):
            try:
                cur.execute("SAVEPOINT sp_cert;")
                cur.execute("INSERT INTO certificates (student_id, cert_type, cert_no, issue_date, body, remarks, issued_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, cert_no;",
                            (student_id, cert_type, cert_no, issue_date or None, body, remarks or None, admin_id))
                res = cur.fetchone()
                cur.execute("RELEASE SAVEPOINT sp_cert;")
                conn.commit()
                return {"id": res[0], "cert_no": res[1]}
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_cert;")
                cert_no = f"{_generate_cert_no(cert_type)}-{_random.randint(10,99)}"
        raise RuntimeError("Certificate number generate nahi hua")
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_certificates(cert_type=None, search=None, limit=200):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT c.id, c.student_id, c.cert_type, c.cert_no, c.issue_date, c.created_at, s.name, s.roll_no, s.class_name, s.section FROM certificates c JOIN students s ON s.id = c.student_id WHERE 1=1"
        params = []
        if cert_type: q += " AND c.cert_type=%s"; params.append(cert_type)
        if search:
            q += " AND (s.name ILIKE %s OR c.cert_no ILIKE %s)"
            like = f"%{search}%"; params += [like, like]
        q += " ORDER BY c.created_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "student_id": r[1], "cert_type": r[2], "cert_no": r[3],
                 "issue_date": r[4], "created_at": r[5], "student_name": r[6],
                 "roll": r[7], "class_name": r[8], "section": r[9]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_certificate(cid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT c.id, c.student_id, c.cert_type, c.cert_no, c.issue_date, c.body, c.remarks, c.created_at, s.name, s.roll_no, s.class_name, s.section, s.parent_name, s.parent_phone, s.dob, s.admission_date FROM certificates c JOIN students s ON s.id = c.student_id WHERE c.id=%s;", (cid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","student_id","cert_type","cert_no","issue_date","body","remarks",
                "created_at","name","roll","class_name","section","parent_name",
                "parent_phone","dob","admission_date"]
        return dict(zip(keys, row))
    finally:
        cur.close(); conn.close()

def delete_certificate(cid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM certificates WHERE id=%s;", (cid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_certificates_this_month():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM certificates WHERE TO_CHAR(created_at, 'YYYY-MM') = TO_CHAR(NOW(), 'YYYY-MM');")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 21 — EVENTS
# ============================================================
def create_event(data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO events (title, description, event_type, start_date, end_date, start_time, end_time, venue, target_class, is_public, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["title"], data.get("description") or None,
                     data.get("event_type") or "other", data["start_date"],
                     data.get("end_date") or data["start_date"],
                     data.get("start_time") or None, data.get("end_time") or None,
                     data.get("venue") or None, data.get("target_class") or None,
                     _to_bool(data.get("is_public")), admin_id))
        eid = cur.fetchone()[0]; conn.commit(); return eid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_events(month=None, event_type=None, upcoming_only=False, limit=200):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, title, description, event_type, start_date, end_date, start_time, end_time, venue, target_class, is_public, created_at FROM events WHERE 1=1"
        params = []
        if month:
            q += " AND (TO_CHAR(start_date, 'YYYY-MM')=%s OR TO_CHAR(end_date, 'YYYY-MM')=%s)"
            params += [month, month]
        if event_type: q += " AND event_type=%s"; params.append(event_type)
        if upcoming_only: q += " AND (COALESCE(end_date, start_date) >= CURRENT_DATE)"
        q += " ORDER BY start_date ASC, start_time ASC NULLS FIRST LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "description": r[2], "event_type": r[3],
                 "start_date": r[4], "end_date": r[5], "start_time": r[6],
                 "end_time": r[7], "venue": r[8], "target_class": r[9],
                 "is_public": r[10], "created_at": r[11]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_event(eid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, description, event_type, start_date, end_date, start_time, end_time, venue, target_class, is_public, created_at FROM events WHERE id=%s;", (eid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","title","description","event_type","start_date","end_date",
                "start_time","end_time","venue","target_class","is_public","created_at"]
        return dict(zip(keys, row))
    finally:
        cur.close(); conn.close()

def update_event(eid, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE events SET title=%s, description=%s, event_type=%s, start_date=%s, end_date=%s, start_time=%s, end_time=%s, venue=%s, target_class=%s, is_public=%s WHERE id=%s RETURNING id;",
                    (data["title"], data.get("description") or None,
                     data.get("event_type") or "other", data["start_date"],
                     data.get("end_date") or data["start_date"],
                     data.get("start_time") or None, data.get("end_time") or None,
                     data.get("venue") or None, data.get("target_class") or None,
                     _to_bool(data.get("is_public")), eid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_event(eid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM events WHERE id=%s;", (eid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_events_for_month_grid(year, month):
    first_day = date(year, month, 1)
    last_day = (date(year+1,1,1) - timedelta(days=1)) if month == 12 else (date(year,month+1,1) - timedelta(days=1))
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, event_type, start_date, end_date, start_time, venue, target_class FROM events WHERE start_date <= %s AND COALESCE(end_date, start_date) >= %s ORDER BY start_date, start_time NULLS FIRST;",
                    (last_day, first_day))
        rows = cur.fetchall()
        grid = {}
        for r in rows:
            s, e = r[3], r[4] or r[3]
            current = max(s, first_day); end = min(e, last_day)
            while current <= end:
                grid.setdefault(current, []).append({
                    "id": r[0], "title": r[1], "type": r[2], "start_time": r[5],
                    "venue": r[6], "is_multiday": s != e, "target_class": r[7]})
                current += timedelta(days=1)
        return grid
    finally:
        cur.close(); conn.close()

def get_upcoming_events(days=30, class_name=None, limit=10):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, title, event_type, start_date, end_date, start_time, venue FROM events WHERE COALESCE(end_date, start_date) >= CURRENT_DATE AND start_date <= CURRENT_DATE + INTERVAL '%s days' AND is_public = TRUE"
        params = [int(days)]
        if class_name:
            q += " AND (target_class=%s OR target_class IS NULL OR target_class='')"
            params.append(class_name)
        q += " ORDER BY start_date, start_time NULLS FIRST LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "event_type": r[2], "start_date": r[3],
                 "end_date": r[4], "start_time": r[5], "venue": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def count_upcoming_events(days=7):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM events WHERE COALESCE(end_date, start_date) >= CURRENT_DATE AND start_date <= CURRENT_DATE + INTERVAL '%s days' AND is_public = TRUE;", (int(days),))
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 22 — LIBRARY
# ============================================================
def create_book(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        total = int(data.get("total_copies") or 1)
        cur.execute("INSERT INTO books (title, author, isbn, category, publisher, total_copies, available_copies, shelf_no) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["title"], data.get("author") or None, data.get("isbn") or None,
                     data.get("category") or None, data.get("publisher") or None,
                     total, total, data.get("shelf_no") or None))
        bid = cur.fetchone()[0]; conn.commit(); return bid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_books(search=None, category=None, only_available=False):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, title, author, isbn, category, publisher, total_copies, available_copies, shelf_no FROM books WHERE 1=1"
        params = []
        if search:
            q += " AND (title ILIKE %s OR author ILIKE %s OR isbn ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        if category: q += " AND category=%s"; params.append(category)
        if only_available: q += " AND available_copies > 0"
        q += " ORDER BY title;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "author": r[2], "isbn": r[3],
                 "category": r[4], "publisher": r[5], "total_copies": r[6],
                 "available_copies": r[7], "shelf_no": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_book(bid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, author, isbn, category, publisher, total_copies, available_copies, shelf_no, created_at FROM books WHERE id=%s;", (bid,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","title","author","isbn","category","publisher",
                "total_copies","available_copies","shelf_no","created_at"]
        return dict(zip(keys, row))
    finally:
        cur.close(); conn.close()

def update_book(bid, data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT total_copies, available_copies FROM books WHERE id=%s;", (bid,))
        row = cur.fetchone()
        if not row: return None
        old_total, old_avail = row
        new_total = int(data.get("total_copies") or old_total)
        new_available = max(new_total - (old_total - old_avail), 0)
        cur.execute("UPDATE books SET title=%s, author=%s, isbn=%s, category=%s, publisher=%s, total_copies=%s, available_copies=%s, shelf_no=%s WHERE id=%s RETURNING id;",
                    (data["title"], data.get("author") or None, data.get("isbn") or None,
                     data.get("category") or None, data.get("publisher") or None,
                     new_total, new_available, data.get("shelf_no") or None, bid))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_book(bid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM book_issues WHERE book_id=%s AND status='issued';", (bid,))
        if cur.fetchone()[0] > 0:
            return False
        cur.execute("DELETE FROM books WHERE id=%s;", (bid,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def create_book_issue(book_id, student_id, due_date, note, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT available_copies FROM books WHERE id=%s FOR UPDATE;", (book_id,))
        row = cur.fetchone()
        if not row or row[0] <= 0:
            raise ValueError("Book available nahi hai")
        cur.execute("SELECT 1 FROM book_issues WHERE book_id=%s AND student_id=%s AND status='issued' LIMIT 1;", (book_id, student_id))
        if cur.fetchone():
            raise ValueError("Ye student ye book already le chuka hai")
        cur.execute("INSERT INTO book_issues (book_id, student_id, due_date, note, issued_by, status) VALUES (%s,%s,%s,%s,%s,'issued') RETURNING id;",
                    (book_id, student_id, due_date, note, admin_id))
        iid = cur.fetchone()[0]
        cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id=%s;", (book_id,))
        conn.commit(); return iid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def return_book_issue(issue_id, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT book_id, due_date, status FROM book_issues WHERE id=%s FOR UPDATE;", (issue_id,))
        row = cur.fetchone()
        if not row or row[2] != 'issued':
            return None
        book_id, due_date, _ = row
        today = date.today()
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        fine = (today - due_date).days * LIBRARY_FINE_PER_DAY if due_date and today > due_date else 0
        cur.execute("UPDATE book_issues SET return_date=%s, fine=%s, status='returned', returned_by=%s WHERE id=%s RETURNING fine;",
                    (today, fine, admin_id, issue_id))
        returned_fine = cur.fetchone()[0]
        cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id=%s;", (book_id,))
        conn.commit()
        return {"fine": float(returned_fine or 0)}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_active_issues(search=None, only_overdue=False):
    today = date.today()
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT bi.id, bi.book_id, bi.student_id, bi.issue_date, bi.due_date, bi.status, b.title, b.author, s.name, s.roll_no, s.class_name, s.section, s.parent_phone FROM book_issues bi JOIN books b ON b.id = bi.book_id JOIN students s ON s.id = bi.student_id WHERE bi.status = 'issued'"
        params = []
        if search:
            q += " AND (b.title ILIKE %s OR s.name ILIKE %s)"
            like = f"%{search}%"; params += [like, like]
        if only_overdue: q += " AND bi.due_date < CURRENT_DATE"
        q += " ORDER BY bi.due_date;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        out = []
        for r in rows:
            due = r[4]
            due_d = due.date() if isinstance(due, datetime) else due
            days_overdue = (today - due_d).days if due_d and today > due_d else 0
            out.append({"id": r[0], "book_id": r[1], "student_id": r[2],
                        "issue_date": r[3], "due_date": due, "book_title": r[6],
                        "book_author": r[7], "student_name": r[8], "roll": r[9],
                        "class_name": r[10], "section": r[11], "phone": r[12],
                        "days_overdue": days_overdue,
                        "fine_est": days_overdue * LIBRARY_FINE_PER_DAY})
        return out
    finally:
        cur.close(); conn.close()

def get_issue_history(limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT bi.id, bi.issue_date, bi.due_date, bi.return_date, bi.fine, bi.status, b.title, s.name, s.class_name FROM book_issues bi JOIN books b ON b.id = bi.book_id JOIN students s ON s.id = bi.student_id WHERE bi.status='returned' ORDER BY bi.return_date DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "issue_date": r[1], "due_date": r[2], "return_date": r[3],
                 "fine": float(r[4] or 0), "status": r[5], "book_title": r[6],
                 "student_name": r[7], "class_name": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_student_library_history(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT bi.id, b.title, bi.issue_date, bi.due_date, bi.return_date, bi.fine, bi.status FROM book_issues bi JOIN books b ON b.id = bi.book_id WHERE bi.student_id=%s ORDER BY bi.issue_date DESC LIMIT 20;", (student_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "book_title": r[1], "issue_date": r[2], "due_date": r[3],
                 "return_date": r[4], "fine": float(r[5] or 0), "status": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_library_stats():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT (SELECT COUNT(*) FROM books), (SELECT COALESCE(SUM(total_copies),0) FROM books), (SELECT COUNT(*) FROM book_issues WHERE status='issued'), (SELECT COUNT(*) FROM book_issues WHERE status='issued' AND due_date < CURRENT_DATE), (SELECT COALESCE(SUM(fine),0) FROM book_issues WHERE status='returned');")
        r = cur.fetchone()
        return {"total_books": r[0] or 0, "total_copies": r[1] or 0,
                "issued_count": r[2] or 0, "overdue_count": r[3] or 0,
                "total_fine_collected": float(r[4] or 0)}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 23 — PROMOTION
# ============================================================
def get_next_class(current_class):
    if not current_class: return None
    c = str(current_class).strip()
    if c in CLASS_SEQUENCE:
        idx = CLASS_SEQUENCE.index(c)
        return CLASS_SEQUENCE[idx+1] if idx+1 < len(CLASS_SEQUENCE) else "ALUMNI"
    return None

def get_class_roster(class_name, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, roll_no, class_name, section, gender, parent_phone, status FROM students WHERE status='active' AND class_name=%s"
        params = [class_name]
        if section: q += " AND section=%s"; params.append(section)
        q += " ORDER BY section, roll_no, name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3],
                 "section": r[4], "gender": r[5], "phone": r[6], "status": r[7]} for r in rows]
    finally:
        cur.close(); conn.close()

def promote_students(student_ids, to_class, action, new_academic_year=None):
    if not student_ids: return {"updated": 0}
    conn = get_conn(); cur = conn.cursor()
    updated = 0
    try:
        ids_list = list(student_ids)
        if action == "promote":
            cur.execute("UPDATE students SET class_name=%s, status='active' WHERE id = ANY(%s);", (to_class, ids_list))
            updated = cur.rowcount
        elif action == "repeat":
            cur.execute("UPDATE students SET status='active' WHERE id = ANY(%s);", (ids_list,))
            updated = cur.rowcount
        elif action == "archive":
            cur.execute("UPDATE students SET status='inactive' WHERE id = ANY(%s);", (ids_list,))
            updated = cur.rowcount
        conn.commit()
        return {"updated": updated}
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def log_promotion(from_class, to_class, academic_year, total, promoted, repeated, archived, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO promotion_logs (from_class, to_class, academic_year, total_students, promoted, repeated, archived, performed_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (from_class, to_class, academic_year, total, promoted, repeated, archived, admin_id))
        lid = cur.fetchone()[0]; conn.commit(); return lid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_promotion_logs(limit=50):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, from_class, to_class, academic_year, total_students, promoted, repeated, archived, created_at FROM promotion_logs ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "from_class": r[1], "to_class": r[2], "academic_year": r[3],
                 "total": r[4], "promoted": r[5], "repeated": r[6], "archived": r[7],
                 "created_at": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_class_count_summary():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(class_name, 'Unassigned'), COUNT(*) FILTER (WHERE status='active'), COUNT(*) FILTER (WHERE status='inactive') FROM students GROUP BY class_name ORDER BY class_name NULLS LAST;")
        rows = cur.fetchall()
        return [{"class_name": r[0], "active": r[1], "inactive": r[2]} for r in rows]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 24 — TEACHERS
# ============================================================
def get_teacher_by_username(username):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT t.id, t.staff_id, t.username, t.password_hash, s.name, s.role, s.phone, s.email FROM teachers t JOIN staff s ON s.id = t.staff_id WHERE t.username=%s;", (username,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def verify_teacher(username, password):
    row = get_teacher_by_username(username)
    if not row or not check_password_hash(row[3], password): return None
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE teachers SET last_login=NOW() WHERE id=%s;", (row[0],))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
    return {"id": row[0], "staff_id": row[1], "username": row[2], "name": row[4], "role": row[5]}

def get_teacher_classes(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT class_name, section FROM timetable WHERE staff_id=%s ORDER BY class_name, section;", (staff_id,))
        rows = cur.fetchall()
        return [{"class_name": r[0], "section": r[1] or ''} for r in rows]
    finally:
        cur.close(); conn.close()

def get_teacher_today_schedule(staff_id):
    weekday = date.today().isoweekday()
    if weekday > 6: return []
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT period_no, class_name, section, subject FROM timetable WHERE staff_id=%s AND day_of_week=%s ORDER BY period_no;", (staff_id, weekday))
        rows = cur.fetchall()
        return [{"period_no": r[0], "class_name": r[1], "section": r[2] or '', "subject": r[3]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_teacher_homework(staff_id, limit=30):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT h.id, h.title, h.class_name, h.section, h.subject, h.due_date, h.created_at FROM homework h WHERE h.class_name IN (SELECT DISTINCT class_name FROM timetable WHERE staff_id=%s) ORDER BY h.created_at DESC LIMIT %s;",
                    (staff_id, limit))
        rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "class_name": r[2], "section": r[3] or '',
                 "subject": r[4], "due_date": r[5], "created_at": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def create_teacher(staff_id, username, password):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO teachers (staff_id, username, password_hash) VALUES (%s,%s,%s) RETURNING id;",
                    (staff_id, username, generate_password_hash(password)))
        tid = cur.fetchone()[0]; conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_all_teachers():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT t.id, t.username, t.last_login, s.id AS staff_id, s.name, s.role, s.phone FROM teachers t JOIN staff s ON s.id = t.staff_id ORDER BY s.name;")
        rows = cur.fetchall()
        return [{"id": r[0], "username": r[1], "last_login": r[2], "staff_id": r[3],
                 "name": r[4], "role": r[5], "phone": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def delete_teacher(teacher_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM teachers WHERE id=%s;", (teacher_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def reset_teacher_password(teacher_id, new_password):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE teachers SET password_hash=%s WHERE id=%s RETURNING id;",
                    (generate_password_hash(new_password), teacher_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 25 — MEDICAL
# ============================================================
def get_medical_record(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, student_id, blood_group, allergies, chronic_conditions, medications, emergency_contact_name, emergency_contact_phone, doctor_name, doctor_phone, insurance_info, notes, last_updated FROM medical_records WHERE student_id=%s;", (student_id,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","student_id","blood_group","allergies","chronic_conditions",
                "medications","emergency_contact_name","emergency_contact_phone",
                "doctor_name","doctor_phone","insurance_info","notes","last_updated"]
        return dict(zip(keys, row))
    finally:
        cur.close(); conn.close()

def save_medical_record(student_id, data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO medical_records (student_id, blood_group, allergies, chronic_conditions, medications, emergency_contact_name, emergency_contact_phone, doctor_name, doctor_phone, insurance_info, notes, updated_by)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (student_id) DO UPDATE SET
                         blood_group=EXCLUDED.blood_group, allergies=EXCLUDED.allergies,
                         chronic_conditions=EXCLUDED.chronic_conditions, medications=EXCLUDED.medications,
                         emergency_contact_name=EXCLUDED.emergency_contact_name,
                         emergency_contact_phone=EXCLUDED.emergency_contact_phone,
                         doctor_name=EXCLUDED.doctor_name, doctor_phone=EXCLUDED.doctor_phone,
                         insurance_info=EXCLUDED.insurance_info, notes=EXCLUDED.notes,
                         updated_by=EXCLUDED.updated_by, last_updated=NOW()
                       RETURNING id;""",
                    (student_id, data.get("blood_group") or None,
                     data.get("allergies") or None, data.get("chronic_conditions") or None,
                     data.get("medications") or None, data.get("emergency_contact_name") or None,
                     data.get("emergency_contact_phone") or None, data.get("doctor_name") or None,
                     data.get("doctor_phone") or None, data.get("insurance_info") or None,
                     data.get("notes") or None, admin_id))
        rid = cur.fetchone()[0]; conn.commit(); return rid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_medical_record(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM medical_records WHERE student_id=%s;", (student_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_vaccinations(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, vaccine_name, date_given, dose_no, notes, created_at FROM vaccinations WHERE student_id=%s ORDER BY date_given DESC;", (student_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "vaccine_name": r[1], "date_given": r[2], "dose_no": r[3],
                 "notes": r[4], "created_at": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def add_vaccination(student_id, vaccine_name, date_given, dose_no, notes):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO vaccinations (student_id, vaccine_name, date_given, dose_no, notes) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (student_id, vaccine_name, date_given, dose_no or None, notes or None))
        vid = cur.fetchone()[0]; conn.commit(); return vid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_vaccination(vid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM vaccinations WHERE id=%s;", (vid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_students_with_medical():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM medical_records;")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def get_students_missing_medical(limit=50):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.roll_no, s.class_name, s.section FROM students s LEFT JOIN medical_records m ON m.student_id = s.id WHERE s.status='active' AND m.id IS NULL ORDER BY s.class_name, s.section, s.roll_no LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3], "section": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_students_with_allergies():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.class_name, s.section, m.blood_group, m.allergies FROM medical_records m JOIN students s ON s.id = m.student_id WHERE s.status='active' AND m.allergies IS NOT NULL AND m.allergies != '' ORDER BY s.class_name, s.roll_no;")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "class_name": r[2], "section": r[3],
                 "blood_group": r[4], "allergies": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 26 — ALERTS
# ============================================================
def create_custom_alert(data, admin_id):
    if not data or not data.get("title"): raise ValueError("Alert title is required")
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO custom_alerts (title, message, alert_type, target, is_active, expires_at, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data["title"].strip(), (data.get("message") or "").strip() or None,
                     data.get("alert_type") or "info", data.get("target") or "admin",
                     _to_bool(data.get("is_active"), default=True),
                     data.get("expires_at") or None, admin_id))
        aid = cur.fetchone()[0]; conn.commit(); return aid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_custom_alerts(active_only=True, limit=20):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, title, message, alert_type, target, is_active, expires_at, created_at FROM custom_alerts"
        if active_only:
            q += " WHERE is_active=TRUE AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)"
        q += " ORDER BY created_at DESC LIMIT %s;"
        cur.execute(q, (limit,)); rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "message": r[2], "alert_type": r[3],
                 "target": r[4], "is_active": r[5], "expires_at": r[6],
                 "created_at": r[7]} for r in rows]
    finally:
        cur.close(); conn.close()

def toggle_custom_alert(aid, is_active):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE custom_alerts SET is_active=%s WHERE id=%s;", (_to_bool(is_active), aid))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_custom_alert(aid):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM custom_alerts WHERE id=%s;", (aid,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_computed_alerts():
    from flask import url_for
    conn = get_conn(); cur = conn.cursor()
    try:
        month = date.today().strftime("%Y-%m"); alerts = []
        def get_url(endpoint, **kwargs):
            try: return url_for(endpoint, **kwargs)
            except Exception: return "#"
        cur.execute("SELECT COUNT(*) FROM (SELECT s.id FROM students s LEFT JOIN (SELECT class_name, SUM(amount) AS total FROM fee_structure GROUP BY class_name) fs ON fs.class_name = s.class_name LEFT JOIN (SELECT student_id, SUM(amount) AS paid FROM fee_payments WHERE month=%s GROUP BY student_id) fp ON fp.student_id = s.id WHERE s.status='active' AND COALESCE(fs.total,0) > COALESCE(fp.paid,0)) t;", (month,))
        fd_count = cur.fetchone()[0] or 0
        if fd_count > 0:
            alerts.append({"type":"danger","icon":"💰","title":f"{fd_count} students ki fees pending",
                           "message":f"{month} ke liye fee defaulters hain",
                           "link":get_url("reports.defaulters", month=month),"count":fd_count})
        cur.execute("SELECT COUNT(*) FROM (SELECT student_id, ROUND((COUNT(*) FILTER (WHERE status='present') * 100.0 / NULLIF(COUNT(*),0))::numeric, 1) AS pct, COUNT(*) FROM attendance WHERE TO_CHAR(date, 'YYYY-MM')=%s GROUP BY student_id HAVING COUNT(*) >= 5 AND (COUNT(*) FILTER (WHERE status='present') * 100.0 / NULLIF(COUNT(*),0)) < 75) t;", (month,))
        att_count = cur.fetchone()[0] or 0
        if att_count > 0:
            alerts.append({"type":"warning","icon":"📊","title":f"{att_count} students ki attendance <75%",
                           "message":f"{month} mein low attendance wale students",
                           "link":get_url("reports.attendance", month=month),"count":att_count})
        cur.execute("SELECT COUNT(*) FROM book_issues WHERE status='issued' AND due_date < CURRENT_DATE;")
        lib_count = cur.fetchone()[0] or 0
        if lib_count > 0:
            alerts.append({"type":"danger","icon":"📚","title":f"{lib_count} overdue library books",
                           "message":"Books due date cross kar chuki hain",
                           "link":get_url("library.active_issues", overdue="1"),"count":lib_count})
        cur.execute("SELECT COUNT(*) FROM salary_records WHERE month=%s AND status='pending';", (month,))
        sal_count = cur.fetchone()[0] or 0
        if sal_count > 0:
            alerts.append({"type":"warning","icon":"💵","title":f"{sal_count} pending salaries",
                           "message":f"{month} ke salary records pending hain",
                           "link":get_url("salary.index", month=month),"count":sal_count})
        cur.execute("SELECT COUNT(*) FROM events WHERE COALESCE(end_date, start_date) >= CURRENT_DATE AND start_date <= CURRENT_DATE + INTERVAL '7 days' AND is_public = TRUE;")
        evt_count = cur.fetchone()[0] or 0
        if evt_count > 0:
            alerts.append({"type":"info","icon":"📅","title":f"{evt_count} events in next 7 days",
                           "message":"Upcoming school events",
                           "link":get_url("events.index"),"count":evt_count})
        cur.execute("SELECT COUNT(*) FROM homework WHERE created_at > NOW() - INTERVAL '3 days';")
        hw_count = cur.fetchone()[0] or 0
        if hw_count > 0:
            alerts.append({"type":"info","icon":"📝","title":f"{hw_count} homework assigned recently",
                           "message":"Last 3 days ka homework",
                           "link":get_url("homework.index"),"count":hw_count})
        return alerts
    finally:
        cur.close(); conn.close()

def count_active_alerts():
    total = 0
    try: total += len(get_computed_alerts())
    except Exception: pass
    try: total += len(get_custom_alerts(active_only=True, limit=100))
    except Exception: pass
    return total

# ============================================================
# SECTION 27 — HOSTEL
# ============================================================
def get_student_hostel(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT a.id, a.room_id, a.check_in, a.status, r.room_no, r.floor, r.room_type, r.monthly_fee, h.id AS hostel_id, h.name AS hostel_name, h.warden_name, h.warden_phone FROM hostel_allocations a LEFT JOIN hostel_rooms r ON r.id = a.room_id LEFT JOIN hostels h ON h.id = r.hostel_id WHERE a.student_id=%s AND a.status='active';", (student_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "room_id": row[1], "check_in": row[2], "room_no": row[4],
                "floor": row[5], "room_type": row[6], "monthly_fee": float(row[7] or 0),
                "hostel_id": row[8], "hostel_name": row[9], "warden_name": row[10],
                "warden_phone": row[11]}
    finally:
        cur.close(); conn.close()

def get_hostels():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, warden_name, warden_phone, capacity FROM hostels ORDER BY name;")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "warden_name": r[2],
                 "warden_phone": r[3], "capacity": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_hostel(hostel_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, warden_name, warden_phone, capacity FROM hostels WHERE id=%s;", (hostel_id,))
        row = cur.fetchone()
        return {"id": row[0], "name": row[1], "warden_name": row[2],
                "warden_phone": row[3], "capacity": row[4]} if row else None
    finally:
        cur.close(); conn.close()

def create_hostel(name, warden_name, warden_phone, capacity):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO hostels (name, warden_name, warden_phone, capacity) VALUES (%s,%s,%s,%s) RETURNING id;",
                    (name, warden_name, warden_phone, capacity))
        hid = cur.fetchone()[0]; conn.commit(); return hid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_hostel(hostel_id, name, warden_name, warden_phone, capacity):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE hostels SET name=%s, warden_name=%s, warden_phone=%s, capacity=%s WHERE id=%s RETURNING id;",
                    (name, warden_name, warden_phone, capacity, hostel_id))
        res = cur.fetchone(); conn.commit(); return res[0] if res else None
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_hostel(hostel_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM hostels WHERE id=%s;", (hostel_id,)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_hostel_rooms(hostel_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, hostel_id, room_no, floor, room_type, monthly_fee, capacity, occupied FROM hostel_rooms"
        params = []
        if hostel_id: q += " WHERE hostel_id=%s"; params.append(hostel_id)
        q += " ORDER BY room_no;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "hostel_id": r[1], "room_no": r[2], "floor": r[3],
                 "room_type": r[4], "monthly_fee": float(r[5] or 0),
                 "capacity": r[6], "occupied": r[7]} for r in rows]
    finally:
        cur.close(); conn.close()

def create_hostel_room(hostel_id, room_no, floor, room_type, monthly_fee, capacity):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO hostel_rooms (hostel_id, room_no, floor, room_type, monthly_fee, capacity, occupied) VALUES (%s,%s,%s,%s,%s,%s,0) RETURNING id;",
                    (hostel_id, room_no, floor, room_type, monthly_fee, capacity))
        rid = cur.fetchone()[0]; conn.commit(); return rid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_hostel_room(room_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, hostel_id, room_no, floor, room_type, monthly_fee, capacity, occupied FROM hostel_rooms WHERE id=%s;", (room_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "hostel_id": row[1], "room_no": row[2], "floor": row[3],
                "room_type": row[4], "monthly_fee": float(row[5] or 0),
                "capacity": row[6], "occupied": row[7]}
    finally:
        cur.close(); conn.close()

def delete_hostel_room(room_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM hostel_rooms WHERE id=%s;", (room_id,)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def allocate_room(student_id, room_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT capacity, occupied FROM hostel_rooms WHERE id=%s FOR UPDATE;", (room_id,))
        r_row = cur.fetchone()
        if r_row and (r_row[1] or 0) >= (r_row[0] or 0):
            return False
        cur.execute("INSERT INTO hostel_allocations (student_id, room_id, status) VALUES (%s,%s,'active');",
                    (student_id, room_id))
        cur.execute("UPDATE hostel_rooms SET occupied = occupied + 1 WHERE id=%s;", (room_id,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def allocate_hostel(student_id, room_id): return allocate_room(student_id, room_id)

def vacate_room(student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT room_id FROM hostel_allocations WHERE student_id=%s AND status='active' FOR UPDATE;", (student_id,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE hostel_allocations SET status='vacated' WHERE student_id=%s AND status='active';", (student_id,))
            cur.execute("UPDATE hostel_rooms SET occupied = GREATEST(occupied - 1, 0) WHERE id=%s;", (row[0],))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def vacate_hostel(student_id): return vacate_room(student_id)
def checkout_student(student_id): return vacate_room(student_id)

def get_room_inmates(room_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.roll_no, s.class_name, s.section, s.parent_phone, a.check_in FROM hostel_allocations a JOIN students s ON s.id = a.student_id WHERE a.room_id=%s AND a.status='active' ORDER BY s.name;", (room_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll_no": r[2], "class_name": r[3],
                 "section": r[4], "parent_phone": r[5], "check_in": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_hostel_inmates(hostel_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.roll_no, s.class_name, s.section, s.parent_phone, r.room_no FROM hostel_allocations a JOIN students s ON s.id = a.student_id JOIN hostel_rooms r ON r.id = a.room_id WHERE r.hostel_id = %s AND a.status='active' ORDER BY r.room_no, s.name;", (hostel_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll_no": r[2], "class_name": r[3],
                 "section": r[4], "parent_phone": r[5], "room_no": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_hostel_stats():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM hostels;")
        total_hostels = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*), COALESCE(SUM(capacity), 0), COALESCE(SUM(occupied), 0) FROM hostel_rooms;")
        row = cur.fetchone(); total_rooms, total_capacity, total_occupied = row[0] or 0, row[1] or 0, row[2] or 0
        cur.execute("SELECT COUNT(*) FROM hostel_allocations WHERE status='active';")
        total_students = cur.fetchone()[0] or 0
        return {"total_hostels": total_hostels, "total_rooms": total_rooms,
                "total_capacity": total_capacity, "total_occupied": total_occupied,
                "available_beds": total_capacity - total_occupied,
                "total_students": total_students}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 28 — DISCOUNTS
# ============================================================
def get_discount_types(active_only=True):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, category, discount_type, value, description, is_active FROM discount_types"
        if active_only: q += " WHERE is_active = TRUE"
        q += " ORDER BY name;"
        cur.execute(q); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "category": r[2], "discount_type": r[3],
                 "value": float(r[4] or 0), "description": r[5],
                 "is_active": r[6]} for r in rows]
    except Exception:
        conn.rollback()
        try:
            cur.execute("SELECT id, name, category, discount_type, value FROM discount_types ORDER BY name;")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "category": r[2], "discount_type": r[3],
                     "value": float(r[4] or 0), "description": None,
                     "is_active": True} for r in rows]
        except Exception:
            conn.rollback()
            return []
    finally:
        cur.close(); conn.close()

def create_discount_type(name, category, discount_type, value, description=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO discount_types (name, category, discount_type, value, description) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (name, category, discount_type, value, description))
        did = cur.fetchone()[0]; conn.commit(); return did
    except Exception:
        conn.rollback()
        try:
            cur.execute("INSERT INTO discount_types (name, category, discount_type, value) VALUES (%s,%s,%s,%s) RETURNING id;",
                        (name, category, discount_type, value))
            did = cur.fetchone()[0]; conn.commit(); return did
        except Exception:
            conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_discount_type(discount_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM discount_types WHERE id=%s;", (discount_id,))
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); print(f"Error deleting discount type: {e}"); return False
    finally:
        cur.close(); conn.close()

def get_student_discounts(student_id, active_only=True):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT sd.id, sd.student_id, sd.discount_type_id, sd.custom_value,
                      sd.from_date, sd.to_date, sd.reason, sd.is_active, sd.created_at,
                      dt.name, dt.category, dt.discount_type AS dtype, dt.value AS master_value
               FROM student_discounts sd
               JOIN discount_types dt ON dt.id = sd.discount_type_id
               WHERE sd.student_id=%s"""
        if active_only:
            q += " AND sd.is_active=TRUE AND (sd.to_date IS NULL OR sd.to_date >= CURRENT_DATE)"
        q += " ORDER BY sd.created_at DESC;"
        cur.execute(q, (student_id,)); rows = cur.fetchall()
        return [{"id": r[0], "student_id": r[1], "discount_type_id": r[2],
                 "custom_value": float(r[3]) if r[3] is not None else None,
                 "from_date": r[4], "to_date": r[5], "reason": r[6],
                 "is_active": r[7], "created_at": r[8], "name": r[9],
                 "category": r[10], "dtype": r[11], "master_value": float(r[12] or 0),
                 "effective_value": float(r[3]) if r[3] is not None else float(r[12] or 0)} for r in rows]
    except Exception:
        conn.rollback()
        try:
            q2 = """SELECT sd.id, sd.student_id, sd.discount_type_id, sd.custom_value,
                           sd.reason, sd.is_active, sd.created_at,
                           dt.name, dt.discount_type, dt.value
                    FROM student_discounts sd JOIN discount_types dt ON dt.id = sd.discount_type_id
                    WHERE sd.student_id=%s"""
            if active_only: q2 += " AND sd.is_active=TRUE"
            q2 += " ORDER BY sd.created_at DESC;"
            cur.execute(q2, (student_id,)); rows = cur.fetchall()
            return [{"id": r[0], "student_id": r[1], "discount_type_id": r[2],
                     "custom_value": float(r[3]) if r[3] is not None else None,
                     "from_date": None, "to_date": None, "reason": r[4],
                     "is_active": r[5], "created_at": r[6], "name": r[7],
                     "category": None, "dtype": r[8], "master_value": float(r[9] or 0),
                     "effective_value": float(r[3]) if r[3] is not None else float(r[9] or 0)} for r in rows]
        except Exception:
            conn.rollback()
            return []
    finally:
        cur.close(); conn.close()

def add_student_discount(student_id, discount_type_id, custom_value=None,
                         reason=None, from_date=None, to_date=None, admin_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO student_discounts (student_id, discount_type_id, custom_value, from_date, to_date, reason, is_active, created_by) VALUES (%s,%s,%s,%s,%s,%s,TRUE,%s) RETURNING id;",
                    (student_id, discount_type_id, custom_value, from_date, to_date, reason, admin_id))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    except Exception:
        conn.rollback()
        cur.execute("INSERT INTO student_discounts (student_id, discount_type_id, custom_value, reason, is_active) VALUES (%s,%s,%s,%s,TRUE) RETURNING id;",
                    (student_id, discount_type_id, custom_value, reason))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    finally:
        cur.close(); conn.close()

def apply_student_discount(student_id, discount_type_id, custom_value=None, reason=None):
    return add_student_discount(student_id, discount_type_id, custom_value, reason)

def delete_student_discount(student_discount_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM student_discounts WHERE id=%s;", (student_discount_id,))
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); print(f"Error deleting student discount: {e}"); return False
    finally:
        cur.close(); conn.close()

def compute_student_discount(base_fee, student_id):
    applied = get_student_discounts(student_id, active_only=True)
    total_discount_amount = 0.0; discount_items = []
    for d in applied:
        val = d['custom_value'] if d['custom_value'] is not None else d['master_value']
        amt = (float(base_fee) * float(val)) / 100.0 if d['dtype'] == 'percent' else float(val)
        total_discount_amount += amt
        discount_items.append({'name': d['name'], 'amount': amt, 'type': d['dtype'], 'value': val})
    return total_discount_amount, discount_items

def get_all_discount_summary():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT dt.name, COUNT(sd.id) as total_applied, SUM(dt.value) as total_value
                       FROM discount_types dt
                       LEFT JOIN student_discounts sd ON dt.id = sd.discount_type_id
                       GROUP BY dt.id, dt.name;""")
        rows = cur.fetchall()
        return [{"name": r[0], "total_applied": r[1], "total_value": float(r[2] or 0)} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_discounts_summary_for_class(class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT s.name as student_name, s.roll_no, dt.name as discount_name,
                              sd.custom_value, sd.from_date, sd.to_date
                       FROM student_discounts sd
                       JOIN students s ON sd.student_id = s.id
                       JOIN discount_types dt ON sd.discount_type_id = dt.id
                       WHERE s.class_name = %s;""", (class_name,))
        rows = cur.fetchall()
        return [{"student_name": r[0], "roll_no": r[1], "discount_name": r[2],
                 "custom_value": float(r[3]) if r[3] is not None else None,
                 "from_date": r[4], "to_date": r[5]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 29 — VISITORS
# ============================================================
def add_visitor(name, phone, purpose, person_to_meet, notes=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO visitors (name, phone, purpose, person_to_meet, notes, check_in, status) VALUES (%s,%s,%s,%s,%s,NOW(),'in') RETURNING id;",
                    (name, phone, purpose, person_to_meet, notes))
        vid = cur.fetchone()[0]; conn.commit(); return vid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def check_in_visitor(data, admin_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        badge_no = f"VIS-{datetime.now().strftime('%Y%m%d')}-{_random.randint(1000,9999)}"
        cur.execute("INSERT INTO visitors (name, phone, purpose, student_id, staff_id, notes, badge_no, admin_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (data.get('name'), data.get('phone'), data.get('purpose'),
                     data.get('student_id') or None, data.get('staff_id') or None,
                     data.get('notes'), badge_no, admin_id))
        vid = cur.fetchone()[0]; conn.commit()
        return {"id": vid, "badge_no": badge_no}
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def checkout_visitor(visitor_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE visitors SET check_out=NOW(), status='out' WHERE id=%s;", (visitor_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def check_out_visitor(visitor_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE visitors SET check_out=NOW() WHERE id=%s AND check_out IS NULL RETURNING id;", (visitor_id,))
        res = cur.fetchone(); conn.commit(); return bool(res)
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def get_visitor(visitor_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT v.id, v.name, v.phone, v.purpose, v.check_in, v.check_out,
                              v.badge_no, v.notes, s.name as student_name,
                              s.class_name, st.name as staff_name
                       FROM visitors v
                       LEFT JOIN students s ON v.student_id = s.id
                       LEFT JOIN staff st ON v.staff_id = st.id
                       WHERE v.id=%s;""", (visitor_id,))
        row = cur.fetchone()
        if not row: return None
        keys = ["id","name","phone","purpose","check_in","check_out","badge_no",
                "notes","student_name","class_name","staff_name"]
        return dict(zip(keys, row))
    except Exception:
        conn.rollback()
        return None
    finally:
        cur.close(); conn.close()

def get_visitors(date_str=None, status=None, search=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT v.id, v.name, v.phone, v.purpose, v.check_in, v.check_out,
                      v.badge_no, s.name as student_name, s.class_name,
                      st.name as staff_name
               FROM visitors v
               LEFT JOIN students s ON v.student_id = s.id
               LEFT JOIN staff st ON v.staff_id = st.id
               WHERE 1=1"""
        params = []
        if date_str: q += " AND DATE(v.check_in) = %s"; params.append(date_str)
        if status == 'active': q += " AND v.check_out IS NULL"
        elif status == 'checked_out': q += " AND v.check_out IS NOT NULL"
        if search:
            q += " AND (v.name ILIKE %s OR v.phone ILIKE %s OR v.badge_no ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like]
        q += " ORDER BY v.check_in DESC;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        keys = ["id","name","phone","purpose","check_in","check_out","badge_no",
                "student_name","class_name","staff_name"]
        return [dict(zip(keys, r)) for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_visitors_summary(date_str=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT COUNT(*) FROM visitors WHERE 1=1"; params = []
        if date_str: q += " AND DATE(check_in) = %s"; params.append(date_str)
        cur.execute(q, tuple(params)); total = cur.fetchone()[0]
        q_active = q + " AND check_out IS NULL"
        cur.execute(q_active, tuple(params)); active = cur.fetchone()[0]
        return {"total": total, "active": active, "checked_out": total - active}
    except Exception:
        conn.rollback()
        return {"total": 0, "active": 0, "checked_out": 0}
    finally:
        cur.close(); conn.close()

def get_active_visitors():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT v.id, v.name, v.phone, v.purpose, v.check_in, v.badge_no,
                              s.name as student_name
                       FROM visitors v
                       LEFT JOIN students s ON v.student_id = s.id
                       WHERE v.check_out IS NULL ORDER BY v.check_in DESC;""")
        rows = cur.fetchall()
        keys = ["id","name","phone","purpose","check_in","badge_no","student_name"]
        return [dict(zip(keys, r)) for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 30 — ONLINE PAYMENTS
# ============================================================
def get_online_payments_for_student(student_id, limit=10):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, amount, month, purpose, razorpay_payment_id, status, created_at, paid_at FROM online_payments WHERE student_id=%s AND status='paid' ORDER BY paid_at DESC LIMIT %s;",
                    (student_id, limit))
        rows = cur.fetchall()
        return [{"id": r[0], "amount": float(r[1] or 0), "month": r[2],
                 "purpose": r[3], "payment_id": r[4], "status": r[5],
                 "created_at": r[6], "paid_at": r[7]} for r in rows]
    finally:
        cur.close(); conn.close()

def create_online_payment(student_id, amount, month=None, purpose=None, razorpay_order_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO online_payments (student_id, amount, month, purpose, razorpay_order_id, status) VALUES (%s,%s,%s,%s,%s,'pending') RETURNING id;",
                    (student_id, amount, month, purpose, razorpay_order_id))
        pid = cur.fetchone()[0]; conn.commit(); return pid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def update_online_payment_status(payment_id, status, razorpay_payment_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if status == 'paid':
            cur.execute("UPDATE online_payments SET status=%s, razorpay_payment_id=%s, paid_at=NOW() WHERE id=%s;",
                        (status, razorpay_payment_id, payment_id))
        else:
            cur.execute("UPDATE online_payments SET status=%s WHERE id=%s;", (status, payment_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_online_payment_by_order(order_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, student_id, amount, month, purpose, razorpay_order_id, razorpay_payment_id, status, created_at, paid_at FROM online_payments WHERE razorpay_order_id=%s LIMIT 1;", (order_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "student_id": row[1], "amount": float(row[2] or 0),
                "month": row[3], "purpose": row[4], "order_id": row[5],
                "payment_id": row[6], "status": row[7], "created_at": row[8],
                "paid_at": row[9]}
    finally:
        cur.close(); conn.close()

def mark_online_payment_success(payment_id, razorpay_payment_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE online_payments SET status='paid', razorpay_payment_id=%s, paid_at=NOW() WHERE id=%s;",
                    (razorpay_payment_id, payment_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def mark_online_payment_failed(payment_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE online_payments SET status='failed' WHERE id=%s;", (payment_id,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_online_payments_summary():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='paid'), COALESCE(SUM(amount) FILTER (WHERE status='paid'), 0), COUNT(*) FILTER (WHERE status='pending'), COALESCE(SUM(amount) FILTER (WHERE status='pending'), 0), COUNT(*) FROM online_payments;")
        row = cur.fetchone()
        return {"paid_count": row[0] or 0, "total_paid": float(row[1] or 0),
                "pending_count": row[2] or 0, "total_pending": float(row[3] or 0),
                "total_transactions": row[4] or 0}
    except Exception:
        conn.rollback()
        return {"paid_count": 0, "total_paid": 0.0, "pending_count": 0,
                "total_pending": 0.0, "total_transactions": 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 31 — PUBLIC CONTENT
# ============================================================
def create_enquiry(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO enquiries (student_name, parent_name, phone, email, class_interested, message, status) VALUES (%s,%s,%s,%s,%s,%s,'new') RETURNING id;",
                    (data.get("student_name"), data.get("parent_name"), data.get("phone"),
                     data.get("email"), data.get("class_interested"), data.get("message")))
        eid = cur.fetchone()[0]; conn.commit(); return eid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_enquiries(status=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, student_name, parent_name, phone, email, class_interested, message, status, created_at FROM enquiries"
        params = []
        if status: q += " WHERE status=%s"; params.append(status)
        q += " ORDER BY created_at DESC;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "student_name": r[1], "parent_name": r[2], "phone": r[3],
                 "email": r[4], "class_interested": r[5], "message": r[6],
                 "status": r[7], "created_at": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_enquiry(enquiry_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, student_name, parent_name, phone, email, class_interested, message, status, created_at FROM enquiries WHERE id=%s;", (enquiry_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "student_name": row[1], "parent_name": row[2],
                "phone": row[3], "email": row[4], "class_interested": row[5],
                "message": row[6], "status": row[7], "created_at": row[8]}
    finally:
        cur.close(); conn.close()

def update_enquiry_status(enquiry_id, status):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE enquiries SET status=%s WHERE id=%s;", (status, enquiry_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_enquiry(enquiry_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM enquiries WHERE id=%s;", (enquiry_id,)); conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def count_new_enquiries():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM enquiries WHERE status='new';")
        return cur.fetchone()[0]
    finally:
        cur.close(); conn.close()

def get_testimonials(limit=10):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, role, message, rating, is_active, created_at FROM testimonials WHERE is_active = TRUE ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "role": r[2], "message": r[3],
                 "rating": r[4], "is_active": r[5], "created_at": r[6]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def create_testimonial(name, role, message, rating):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO testimonials (name, role, message, rating, is_active) VALUES (%s,%s,%s,%s,TRUE) RETURNING id;",
                    (name, role, message, rating))
        tid = cur.fetchone()[0]; conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_testimonial(testimonial_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM testimonials WHERE id=%s;", (testimonial_id,)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def toggle_testimonial_public(testimonial_id, is_active):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE testimonials SET is_active=%s WHERE id=%s;", (_to_bool(is_active), testimonial_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_gallery(limit=200):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, image_url, description, created_at FROM gallery ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "image_url": r[2],
                 "description": r[3], "created_at": r[4]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def add_gallery_item(title, image_url, description=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO gallery (title, image_url, description) VALUES (%s,%s,%s) RETURNING id;",
                    (title, image_url, description))
        gid = cur.fetchone()[0]; conn.commit(); return gid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def create_gallery_item(title, image_url, description="", category="General"):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO gallery (title, image_url, description, category) VALUES (%s,%s,%s,%s) RETURNING id;",
                    (title, image_url, description, category))
        gid = cur.fetchone()[0]; conn.commit(); return gid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_gallery_item(item_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM gallery WHERE id=%s;", (item_id,)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_gallery_categories():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT category FROM gallery WHERE category IS NOT NULL AND category != '';")
        rows = cur.fetchall()
        return [r[0] for r in rows]
    except Exception:
        conn.rollback()
        return ["Events","Sports","Academics","Campus","Other"]
    finally:
        cur.close(); conn.close()

def get_public_notices(limit=5):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, content, created_at FROM notices WHERE is_public = TRUE AND published = TRUE ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "created_at": r[3]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_public_events(limit=5):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, description, start_date, venue FROM events WHERE is_public = TRUE AND start_date >= CURRENT_DATE ORDER BY start_date ASC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "description": r[2],
                 "event_date": r[3], "venue": r[4]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def create_contact_message(data):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO contact_messages (name, email, phone, subject, message, status) VALUES (%s,%s,%s,%s,%s,'new') RETURNING id;",
                    (data.get("name"), data.get("email"), data.get("phone"),
                     data.get("subject"), data.get("message")))
        mid = cur.fetchone()[0]; conn.commit(); return mid
    except Exception:
        conn.rollback(); return True
    finally:
        cur.close(); conn.close()

def get_contact_messages(limit=50):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, email, phone, subject, message, status, created_at FROM contact_messages ORDER BY created_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "email": r[2], "phone": r[3],
                 "subject": r[4], "message": r[5], "status": r[6],
                 "created_at": r[7]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_public_stats():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
        total_students = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM staff WHERE status='active';")
        total_staff = cur.fetchone()[0] or 0
        return {"total_students": total_students, "total_staff": total_staff}
    except Exception:
        conn.rollback()
        return {"total_students": 0, "total_staff": 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 32 — QR ATTENDANCE
# ============================================================
def get_student_by_qr_data(qr_data):
    conn = get_conn(); cur = conn.cursor()
    try:
        qr_data = str(qr_data).strip()
        cur.execute("SELECT id, name, roll_no, class_name, section, parent_phone FROM students WHERE (id::text = %s OR roll_no = %s) AND status='active' LIMIT 1;",
                    (qr_data, qr_data))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "name": row[1], "roll_no": row[2],
                "class_name": row[3], "section": row[4], "parent_phone": row[5]}
    finally:
        cur.close(); conn.close()

def get_today_attendance_status(student_id, date_str=None):
    if not date_str: date_str = date.today().isoformat()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM attendance WHERE student_id=%s AND date=%s LIMIT 1;", (student_id, date_str))
        row = cur.fetchone(); return row[0] if row else None
    finally:
        cur.close(); conn.close()

def get_class_students_for_qr(class_name, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id, name, roll_no, class_name, section FROM students WHERE status='active' AND class_name=%s"
        params = [class_name]
        if section: q += " AND section=%s"; params.append(section)
        q += " ORDER BY section, roll_no, name;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll_no": r[2],
                 "class_name": r[3], "section": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_todays_attendance_summary(date_str=None):
    if not date_str: date_str = date.today().isoformat()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status='absent'), COUNT(*) FILTER (WHERE status='late'), COUNT(*) FILTER (WHERE status='leave'), COUNT(*) FROM attendance WHERE date=%s;", (date_str,))
        row = cur.fetchone()
        if not row:
            return {"present": 0, "absent": 0, "late": 0, "leave": 0, "total": 0}
        return {"present": row[0] or 0, "absent": row[1] or 0,
                "late": row[2] or 0, "leave": row[3] or 0, "total": row[4] or 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 33 — AUTOMATION
# ============================================================
def get_automation_jobs():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, job_name, job_type, target, message, schedule_time, status, last_run FROM automation_jobs ORDER BY created_at DESC;")
        rows = cur.fetchall()
        return [{"id": r[0], "job_name": r[1], "job_type": r[2], "target": r[3],
                 "message": r[4], "schedule_time": r[5], "status": r[6],
                 "last_run": r[7]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def add_automation_job(job_name, job_type, target, message, schedule_time):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO automation_jobs (job_name, job_type, target, message, schedule_time, status) VALUES (%s,%s,%s,%s,%s,'active') RETURNING id;",
                    (job_name, job_type, target, message, schedule_time))
        jid = cur.fetchone()[0]; conn.commit(); return jid
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def delete_automation_job(job_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM automation_jobs WHERE id=%s;", (job_id,)); conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def toggle_automation_job(job_id, status):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE automation_jobs SET status=%s WHERE id=%s;", (status, job_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def get_automation_settings():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT key, value FROM automation_settings;")
        rows = cur.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        conn.rollback()
        return {}
    finally:
        cur.close(); conn.close()

def update_automation_settings(key, value):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO automation_settings (key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;",
                    (key, value))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def get_sms_quota_remaining():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT value FROM automation_settings WHERE key = 'sms_quota_remaining';")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        conn.rollback()
        return 0
    finally:
        cur.close(); conn.close()

def start_automation_run(job_name, job_type="auto"):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO automation_runs (job_name, job_type, status, started_at) VALUES (%s,%s,'running',NOW()) RETURNING id;",
                    (job_name, job_type))
        run_id = cur.fetchone()[0]; conn.commit(); return run_id
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def complete_automation_run(run_id, status, details=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE automation_runs SET status=%s, details=%s, completed_at=NOW() WHERE id=%s;",
                    (status, details, run_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def update_last_run(job_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO automation_settings (key, value) VALUES (%s, NOW()::text) ON CONFLICT (key) DO UPDATE SET value = NOW()::text;",
                    (f"last_run_{job_name}",))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def get_automation_runs(limit=50):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, job_name, job_type, status, details, started_at, completed_at FROM automation_runs ORDER BY started_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "job_name": r[1], "job_type": r[2], "status": r[3],
                 "details": r[4], "started_at": r[5], "completed_at": r[6]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 34 — ANNUAL REPORTS
# ============================================================
def get_annual_report_data(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
        total_students = cur.fetchone()[0] or 0
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM fee_payments WHERE month LIKE %s;", (f"{year}%",))
        total_fees = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(net_amount), 0) FROM salary_records WHERE status='paid' AND month LIKE %s;", (f"{year}%",))
        total_salaries = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY') = %s;", (str(year),))
        total_expenses = float(cur.fetchone()[0] or 0)
        return {"total_students": total_students, "total_fees": total_fees,
                "total_salaries": total_salaries, "total_expenses": total_expenses,
                "net_profit": total_fees - (total_salaries + total_expenses)}
    except Exception:
        conn.rollback()
        return {"total_students": 0, "total_fees": 0, "total_salaries": 0,
                "total_expenses": 0, "net_profit": 0}
    finally:
        cur.close(); conn.close()

def get_annual_financial_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        year_str = str(year)
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM fee_payments WHERE month LIKE %s;", (f"{year_str}-%",))
        fees_collected = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(net_amount), 0) FROM salary_records WHERE status='paid' AND month LIKE %s;", (f"{year_str}-%",))
        salaries_paid = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY') = %s;", (year_str,))
        expenses_total = float(cur.fetchone()[0] or 0)
        total_outflow = salaries_paid + expenses_total; net_profit = fees_collected - total_outflow
        return {"year": year, "fees_collected": fees_collected,
                "salaries_paid": salaries_paid, "expenses_total": expenses_total,
                "total_outflow": total_outflow, "net_profit": net_profit,
                "profit": net_profit >= 0}
    finally:
        cur.close(); conn.close()

def get_annual_student_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        year_str = str(year)
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
        total_active = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM students WHERE TO_CHAR(admission_date, 'YYYY') = %s;", (year_str,))
        new_admissions = cur.fetchone()[0] or 0
        cur.execute("SELECT gender, COUNT(*) FROM students WHERE status='active' GROUP BY gender;")
        gender_counts = {row[0] or 'Unknown': row[1] for row in cur.fetchall()}
        return {"year": year, "total_active_students": total_active,
                "new_admissions": new_admissions, "gender_distribution": gender_counts}
    finally:
        cur.close(); conn.close()

def get_annual_academic_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        year_str = str(year)
        cur.execute("SELECT COUNT(*) FROM exams WHERE TO_CHAR(exam_date, 'YYYY') = %s;", (year_str,))
        total_exams = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status IN ('present','absent','late','leave')) FROM attendance WHERE TO_CHAR(date, 'YYYY') = %s;", (year_str,))
        row = cur.fetchone(); present, total_att = row[0] or 0, row[1] or 0
        att_percent = round((present / total_att * 100), 1) if total_att > 0 else 0
        cur.execute("SELECT COUNT(*) FROM marks m JOIN exams e ON e.id = m.exam_id WHERE TO_CHAR(e.exam_date, 'YYYY') = %s;", (year_str,))
        total_marks_entries = cur.fetchone()[0] or 0
        return {"year": year, "total_exams": total_exams,
                "overall_attendance_percent": att_percent,
                "total_marks_entries": total_marks_entries}
    finally:
        cur.close(); conn.close()

def get_annual_attendance_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        year_str = str(year)
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status='absent'), COUNT(*) FILTER (WHERE status='late'), COUNT(*) FILTER (WHERE status='leave'), COUNT(*) FROM attendance WHERE TO_CHAR(date, 'YYYY') = %s;", (year_str,))
        row = cur.fetchone()
        if not row or row[4] == 0:
            return {"year": year, "present": 0, "absent": 0, "late": 0,
                    "leave": 0, "total": 0, "percent": 0}
        present, late, total = row[0] or 0, row[2] or 0, row[4] or 0
        percent = round(((present + late * 0.5) / total) * 100, 1) if total > 0 else 0
        return {"year": year, "present": present, "absent": row[1] or 0,
                "late": late, "leave": row[3] or 0, "total": total, "percent": percent}
    finally:
        cur.close(); conn.close()

def get_annual_fee_defaulters_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        year_str = str(year)
        cur.execute("SELECT COUNT(*), COALESCE(SUM(pending), 0) FROM (SELECT b.student_id, MAX(b.total_amount) - COALESCE((SELECT SUM(amount) FROM fee_payments WHERE student_id=b.student_id AND month LIKE %s), 0) AS pending FROM bills b WHERE b.month LIKE %s GROUP BY b.student_id) t WHERE pending > 0;",
                    (f"{year_str}-%", f"{year_str}-%"))
        row = cur.fetchone()
        return {"year": year, "total_defaulters": row[0] or 0,
                "total_pending_amount": float(row[1] or 0)}
    finally:
        cur.close(); conn.close()

def get_annual_fee_collection_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM fee_payments WHERE month LIKE %s;", (f"{str(year)}-%",))
        row = cur.fetchone()
        return {"year": year, "total_collected": float(row[0] or 0),
                "total_transactions": row[1] or 0}
    finally:
        cur.close(); conn.close()

def get_annual_expense_summary(year):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT category, SUM(amount) FROM expenses WHERE TO_CHAR(expense_date, 'YYYY') = %s GROUP BY category ORDER BY 2 DESC;", (str(year),))
        rows = cur.fetchall()
        cats = [{"category": r[0], "amount": float(r[1] or 0)} for r in rows]
        return {"year": year, "total_expense": sum(c["amount"] for c in cats),
                "categories": cats}
    finally:
        cur.close(); conn.close()

# ════════════════════════════════════════════════════════════
# ══════════ PHASE 3 — LEAVE, ATTENDANCE, ADVANCES, ══════════
# ══════════ CHAT, EXAMS, HALL TICKET, REPORT CARDS, ═════════
# ══════════ PASSWORD OTP, SMS, SYSTEM ═══════════════════════
# ════════════════════════════════════════════════════════════

# ============================================================
# SECTION 35 — LEAVE MANAGEMENT
# ============================================================
def get_leave_types():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, max_days_per_year, is_paid FROM leave_types ORDER BY name;")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "max_days": r[2], "is_paid": r[3]} for r in rows]
    except Exception:
        conn.rollback()
        return [{"id": 1, "name": "Casual Leave", "max_days": 12, "is_paid": True},
                {"id": 2, "name": "Sick Leave", "max_days": 10, "is_paid": True}]
    finally:
        cur.close(); conn.close()

def count_working_days(start_date, end_date):
    if isinstance(start_date, str): start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str): end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    if isinstance(start_date, datetime): start_date = start_date.date()
    if isinstance(end_date, datetime): end_date = end_date.date()
    if start_date > end_date: return 0
    days = 0; current = start_date
    while current <= end_date:
        if current.weekday() != 6: days += 1
        current += timedelta(days=1)
    return days

def create_leave_application(staff_id, leave_type_id, start_date, end_date, reason):
    conn = get_conn(); cur = conn.cursor()
    try:
        if str(leave_type_id).isdigit():
            cur.execute("SELECT name FROM leave_types WHERE id=%s;", (int(leave_type_id),))
            lt_row = cur.fetchone()
            leave_type_name = lt_row[0] if lt_row else str(leave_type_id)
        else:
            leave_type_name = str(leave_type_id)
        days = count_working_days(start_date, end_date)
        cur.execute("INSERT INTO staff_leaves (staff_id, leave_type, start_date, end_date, reason, status) VALUES (%s,%s,%s,%s,%s,'pending') RETURNING id;",
                    (staff_id, leave_type_name, start_date, end_date, reason))
        lid = cur.fetchone()[0]; conn.commit()
        return {"id": lid, "days": days}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def apply_leave(staff_id, leave_type, start_date, end_date, reason):
    return create_leave_application(staff_id, leave_type, start_date, end_date, reason)

def get_leave_applications(staff_id=None, status=None, limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT l.id, l.staff_id, s.name, l.leave_type, l.start_date, l.end_date, l.reason, l.status, l.created_at FROM staff_leaves l JOIN staff s ON s.id = l.staff_id WHERE 1=1"
        params = []
        if staff_id: q += " AND l.staff_id=%s"; params.append(staff_id)
        if status: q += " AND l.status=%s"; params.append(status)
        q += " ORDER BY l.created_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "staff_id": r[1], "name": r[2], "leave_type": r[3],
                 "start_date": r[4], "end_date": r[5], "reason": r[6],
                 "status": r[7], "created_at": r[8]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_leaves(staff_id=None, status=None):
    return get_leave_applications(staff_id, status)

def get_leave_application(leave_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT l.id, l.staff_id, s.name, l.leave_type, l.start_date, l.end_date, l.reason, l.status, l.created_at FROM staff_leaves l JOIN staff s ON s.id = l.staff_id WHERE l.id = %s;", (leave_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "staff_id": row[1], "name": row[2], "leave_type": row[3],
                "start_date": row[4], "end_date": row[5], "reason": row[6],
                "status": row[7], "created_at": row[8]}
    except Exception:
        conn.rollback()
        return None
    finally:
        cur.close(); conn.close()

def approve_leave(leave_id, admin_id, note=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE staff_leaves SET status='approved', admin_note=%s WHERE id=%s AND status='pending' RETURNING staff_id, start_date, end_date;",
                    (note, leave_id))
        row = cur.fetchone()
        if not row: return {"ok": False, "error": "already reviewed"}
        staff_id, start_date, end_date = row
        cur.execute("""INSERT INTO staff_attendance (staff_id, date, status)
                       SELECT %s, date_val, 'leave' FROM generate_series(%s::date, %s::date, interval '1 day') AS date_val
                       WHERE EXTRACT(DOW FROM date_val) != 0
                       ON CONFLICT (staff_id, date) DO UPDATE SET status='leave';""",
                    (staff_id, start_date, end_date))
        conn.commit(); return {"ok": True}
    except Exception as e:
        conn.rollback(); return {"ok": False, "error": str(e)}
    finally:
        cur.close(); conn.close()

def reject_leave(leave_id, admin_id, note=""):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE staff_leaves SET status='rejected', admin_note=%s WHERE id=%s AND status='pending';",
                    (note, leave_id))
        conn.commit(); return cur.rowcount > 0
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def cancel_leave(leave_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE staff_leaves SET status='cancelled' WHERE id=%s AND status='pending';", (leave_id,))
        conn.commit(); return cur.rowcount > 0
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def update_leave_status(leave_id, status):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE staff_leaves SET status=%s WHERE id=%s;", (status, leave_id))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_leave(leave_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM staff_leaves WHERE id=%s;", (leave_id,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_pending_leave_count():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM staff_leaves WHERE status='pending';")
        return cur.fetchone()[0] or 0
    except Exception:
        conn.rollback()
        return 0
    finally:
        cur.close(); conn.close()

def get_staff_leave_summary(staff_id, year):
    try:
        balance = get_or_init_leave_balance(staff_id, year)
    except Exception:
        balance = {"total": 12, "used": 0, "remaining": 12}
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM staff_leaves WHERE staff_id=%s AND status='approved' AND EXTRACT(YEAR FROM start_date) = %s;",
                    (staff_id, year))
        approved_count = cur.fetchone()[0] or 0
        return {"total_allowed": balance.get("total", 12),
                "used": balance.get("used", 0) + approved_count,
                "remaining": balance.get("remaining", 12) - approved_count}
    except Exception:
        conn.rollback()
        return {"total_allowed": 12, "used": 0, "remaining": 12}
    finally:
        cur.close(); conn.close()

def get_leave_applications_for_staff(staff_id, limit=30):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, leave_type, start_date, end_date, reason, status, created_at FROM staff_leaves WHERE staff_id=%s ORDER BY created_at DESC LIMIT %s;",
                    (staff_id, limit))
        rows = cur.fetchall()
        return [{"id": r[0], "leave_type": r[1], "start_date": r[2],
                 "end_date": r[3], "reason": r[4], "status": r[5],
                 "created_at": r[6]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_or_init_leave_balance(staff_id, year=None):
    if not year: year = date.today().year
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, total_leaves, used_leaves FROM leave_balances WHERE staff_id=%s AND year=%s;", (staff_id, year))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "staff_id": staff_id, "year": year,
                    "total": row[1], "used": row[2], "remaining": row[1] - row[2]}
        cur.execute("INSERT INTO leave_balances (staff_id, year, total_leaves, used_leaves) VALUES (%s,%s,12,0) RETURNING id;",
                    (staff_id, year))
        new_id = cur.fetchone()[0]; conn.commit()
        return {"id": new_id, "staff_id": staff_id, "year": year,
                "total": 12, "used": 0, "remaining": 12}
    except Exception:
        conn.rollback()
        return {"staff_id": staff_id, "year": year, "total": 12, "used": 0, "remaining": 12}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 36 — STAFF ATTENDANCE (daily)
# ============================================================
def get_staff_attendance_for_date(date_str):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT s.id, s.name, s.role, sa.status, sa.check_in, sa.check_out FROM staff s LEFT JOIN staff_attendance sa ON sa.staff_id = s.id AND sa.date = %s WHERE s.status = 'active' ORDER BY s.role, s.name;", (date_str,))
        rows = cur.fetchall()
        return [{"staff_id": r[0], "name": r[1], "role": r[2],
                 "status": r[3] or "unmarked", "check_in": r[4],
                 "check_out": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def mark_staff_attendance(staff_id, date_str, status, check_in=None, check_out=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO staff_attendance (staff_id, date, status, check_in, check_out) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (staff_id, date) DO UPDATE SET status=EXCLUDED.status, check_in=EXCLUDED.check_in, check_out=EXCLUDED.check_out;",
                    (staff_id, date_str, status, check_in, check_out))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def bulk_mark_staff_attendance(date_str, status, staff_ids=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        if staff_ids:
            for sid in staff_ids:
                cur.execute("INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s,%s,%s) ON CONFLICT (staff_id, date) DO UPDATE SET status=EXCLUDED.status;",
                            (sid, date_str, status))
        else:
            cur.execute("INSERT INTO staff_attendance (staff_id, date, status) SELECT id, %s, %s FROM staff WHERE status='active' ON CONFLICT (staff_id, date) DO UPDATE SET status=EXCLUDED.status;",
                        (date_str, status))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_staff_attendance(staff_id, date_str):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM staff_attendance WHERE staff_id=%s AND date=%s;", (staff_id, date_str))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_staff_attendance_month_matrix(month):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, role FROM staff WHERE status='active' ORDER BY role, name;")
        staff_list = [{"id": r[0], "name": r[1], "role": r[2]} for r in cur.fetchall()]
        cur.execute("SELECT staff_id, TO_CHAR(date, 'YYYY-MM-DD'), status FROM staff_attendance WHERE TO_CHAR(date, 'YYYY-MM') = %s;", (month,))
        attendance_data = {}
        for r in cur.fetchall():
            attendance_data.setdefault(r[0], {})[r[1]] = r[2]
        return {"staff_list": staff_list, "attendance_data": attendance_data}
    except Exception:
        conn.rollback()
        return {"staff_list": [], "attendance_data": {}}
    finally:
        cur.close(); conn.close()

def get_staff_attendance_today_summary(date_str=None):
    if not date_str: date_str = date.today().isoformat()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FILTER (WHERE status='present'), COUNT(*) FILTER (WHERE status='absent'), COUNT(*) FILTER (WHERE status='half_day'), COUNT(*) FILTER (WHERE status='leave'), COUNT(*) FILTER (WHERE status='holiday'), COUNT(*) FROM staff_attendance WHERE date=%s;", (date_str,))
        row = cur.fetchone()
        if not row:
            return {"present": 0, "absent": 0, "half_day": 0,
                    "leave": 0, "holiday": 0, "total": 0}
        return {"present": row[0] or 0, "absent": row[1] or 0,
                "half_day": row[2] or 0, "leave": row[3] or 0,
                "holiday": row[4] or 0, "total": row[5] or 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 37 — ADVANCES (unified)
# ============================================================
def create_advance(staff_id, amount, reason="", advance_type="advance",
                   advance_date=None, status="active"):
    conn = get_conn(); cur = conn.cursor()
    try:
        try:
            cur.execute("SAVEPOINT sp_adv;")
            cur.execute("INSERT INTO advances (staff_id, amount, remaining_amount, reason, advance_type, status, advance_date) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                        (staff_id, amount, amount, reason, advance_type, status, advance_date))
            cur.execute("RELEASE SAVEPOINT sp_adv;")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_adv;")
            cur.execute("INSERT INTO advances (staff_id, amount, remaining_amount, reason, advance_type, status) VALUES (%s,%s,%s,%s,%s,'active') RETURNING id;",
                        (staff_id, amount, amount, reason, advance_type))
        aid = cur.fetchone()[0]; conn.commit(); return aid
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def get_advance(advance_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT a.id, a.staff_id, s.name, a.amount, a.remaining_amount, a.reason, a.advance_type, a.status, a.created_at FROM advances a JOIN staff s ON a.staff_id = s.id WHERE a.id = %s;", (advance_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "staff_id": row[1], "staff_name": row[2],
                "amount": float(row[3] or 0), "remaining_amount": float(row[4] or 0),
                "reason": row[5], "advance_type": row[6], "status": row[7],
                "created_at": row[8]}
    finally:
        cur.close(); conn.close()

def get_advances(status=None, staff_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT a.id, a.staff_id, s.name, a.amount, a.remaining_amount, a.reason, a.advance_type, a.status, a.created_at FROM advances a JOIN staff s ON a.staff_id = s.id WHERE 1=1"
        params = []
        if status and status != 'all': q += " AND a.status = %s"; params.append(status)
        if staff_id: q += " AND a.staff_id = %s"; params.append(staff_id)
        q += " ORDER BY a.created_at DESC;"
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "staff_id": r[1], "staff_name": r[2],
                 "amount": float(r[3] or 0), "remaining_amount": float(r[4] or 0),
                 "reason": r[5], "advance_type": r[6], "status": r[7],
                 "created_at": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_active_advance(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, staff_id, amount, remaining_amount, reason, advance_type, status FROM advances WHERE staff_id = %s AND status = 'active' AND remaining_amount > 0 ORDER BY created_at ASC;", (staff_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "staff_id": r[1], "amount": float(r[2] or 0),
                 "remaining": float(r[3] or 0), "reason": r[4],
                 "advance_type": r[5], "status": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_advance_repayments(advance_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, advance_id, amount, repayment_date, notes FROM advance_repayments WHERE advance_id = %s ORDER BY repayment_date DESC;", (advance_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "advance_id": r[1], "amount": float(r[2] or 0),
                 "repayment_date": r[3], "notes": r[4]} for r in rows]
    finally:
        cur.close(); conn.close()

def record_advance_repayment(advance_id, amount, notes="",
                              month=None, salary_record_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        try:
            cur.execute("SAVEPOINT sp_repay;")
            cur.execute("INSERT INTO advance_repayments (advance_id, amount, notes, repayment_date) VALUES (%s,%s,%s,CURRENT_DATE);",
                        (advance_id, amount, notes))
            cur.execute("RELEASE SAVEPOINT sp_repay;")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_repay;")
            cur.execute("INSERT INTO advance_repayments (advance_id, amount) VALUES (%s,%s);",
                        (advance_id, amount))
        cur.execute("UPDATE advances SET remaining_amount = GREATEST(remaining_amount - %s, 0) WHERE id = %s;",
                    (amount, advance_id))
        cur.execute("UPDATE advances SET status = 'completed' WHERE id = %s AND remaining_amount <= 0;",
                    (advance_id,))
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def cancel_advance(advance_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE advances SET status = 'cancelled' WHERE id = %s;", (advance_id,))
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()

def get_staff_advances_summary(staff_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(amount), 0), COALESCE(SUM(amount - remaining_amount), 0), COALESCE(SUM(remaining_amount), 0) FROM advances WHERE staff_id = %s AND status != 'cancelled';",
                    (staff_id,))
        row = cur.fetchone()
        return {"total_taken": float(row[0] or 0), "total_repaid": float(row[1] or 0),
                "total_outstanding": float(row[2] or 0)}
    finally:
        cur.close(); conn.close()

def get_total_advance_outstanding():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(remaining_amount), 0), COUNT(id) FROM advances WHERE status = 'active';")
        row = cur.fetchone()
        return {"outstanding": float(row[0] or 0), "active_count": int(row[1] or 0)}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 38 — CHAT ADMIN HELPERS
# ============================================================
def create_message_thread(parent_id, student_id, subject, first_message, parent_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO message_threads (parent_id, student_id, subject, last_message_by, unread_by_admin) VALUES (%s,%s,%s,'parent',1) RETURNING id;",
                    (parent_id, student_id, subject or "General"))
        tid = cur.fetchone()[0]
        cur.execute("INSERT INTO messages (thread_id, sender_type, sender_id, sender_name, body) VALUES (%s,'parent',%s,%s,%s);",
                    (tid, parent_id, parent_name, first_message))
        conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_thread(thread_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT t.id, t.parent_id, t.student_id, t.subject, t.status,
                              t.last_message_at, t.last_message_by,
                              t.unread_by_parent, t.unread_by_admin, t.created_at,
                              p.name AS parent_name, p.phone AS parent_phone,
                              s.name AS student_name, s.class_name, s.section
                       FROM message_threads t
                       LEFT JOIN parents p ON p.id = t.parent_id
                       LEFT JOIN students s ON s.id = t.student_id
                       WHERE t.id=%s;""", (thread_id,))
        row = cur.fetchone()
        if not row: return None
        return {"id": row[0], "parent_id": row[1], "student_id": row[2],
                "subject": row[3], "status": row[4], "last_message_at": row[5],
                "last_message_by": row[6], "unread_by_parent": row[7] or 0,
                "unread_by_admin": row[8] or 0, "created_at": row[9],
                "parent_name": row[10], "parent_phone": row[11],
                "student_name": row[12], "class_name": row[13], "section": row[14]}
    finally:
        cur.close(); conn.close()

def get_thread_messages(thread_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, sender_type, sender_id, sender_name, body, is_read, created_at FROM messages WHERE thread_id=%s ORDER BY created_at ASC;", (thread_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "sender_type": r[1], "sender_id": r[2],
                 "sender_name": r[3], "body": r[4], "is_read": r[5],
                 "created_at": r[6]} for r in rows]
    finally:
        cur.close(); conn.close()

def post_message(thread_id, sender_type, sender_id, sender_name, body):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO messages (thread_id, sender_type, sender_id, sender_name, body) VALUES (%s,%s,%s,%s,%s) RETURNING id;",
                    (thread_id, sender_type, sender_id, sender_name, body))
        mid = cur.fetchone()[0]
        if sender_type == "parent":
            cur.execute("UPDATE message_threads SET last_message_at=NOW(), last_message_by='parent', unread_by_admin = unread_by_admin + 1, status = CASE WHEN status='closed' THEN 'open' ELSE status END WHERE id=%s;", (thread_id,))
        else:
            cur.execute("UPDATE message_threads SET last_message_at=NOW(), last_message_by='admin', unread_by_parent = unread_by_parent + 1 WHERE id=%s;", (thread_id,))
        conn.commit(); return mid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def mark_thread_read(thread_id, viewer_type):
    conn = get_conn(); cur = conn.cursor()
    try:
        if viewer_type == "parent":
            cur.execute("UPDATE message_threads SET unread_by_parent=0 WHERE id=%s;", (thread_id,))
        else:
            cur.execute("UPDATE message_threads SET unread_by_admin=0 WHERE id=%s;", (thread_id,))
        cur.execute("UPDATE messages SET is_read=TRUE WHERE thread_id=%s AND sender_type != %s;",
                    (thread_id, "parent" if viewer_type == "parent" else "admin"))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def close_thread(thread_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE message_threads SET status='closed' WHERE id=%s;", (thread_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def reopen_thread(thread_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE message_threads SET status='open' WHERE id=%s;", (thread_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_threads_for_parent(parent_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT t.id, t.student_id, t.subject, t.status, t.last_message_at, t.last_message_by, t.unread_by_parent, s.name AS student_name, (SELECT body FROM messages WHERE thread_id=t.id ORDER BY created_at DESC LIMIT 1) AS last_msg FROM message_threads t LEFT JOIN students s ON s.id = t.student_id WHERE t.parent_id=%s ORDER BY t.last_message_at DESC;", (parent_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "student_id": r[1], "subject": r[2], "status": r[3],
                 "last_message_at": r[4], "last_message_by": r[5],
                 "unread": r[6] or 0, "student_name": r[7], "last_message": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_all_threads(status=None, search=None, limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = """SELECT t.id, t.parent_id, t.student_id, t.subject, t.status,
                      t.last_message_at, t.last_message_by, t.unread_by_admin,
                      p.name AS parent_name, p.phone AS parent_phone,
                      s.name AS student_name, s.class_name,
                      (SELECT body FROM messages WHERE thread_id=t.id ORDER BY created_at DESC LIMIT 1) AS last_msg
               FROM message_threads t
               LEFT JOIN parents p ON p.id = t.parent_id
               LEFT JOIN students s ON s.id = t.student_id
               WHERE 1=1"""
        params = []
        if status and status != 'all': q += " AND t.status=%s"; params.append(status)
        if search:
            q += " AND (p.name ILIKE %s OR p.phone ILIKE %s OR s.name ILIKE %s OR t.subject ILIKE %s)"
            like = f"%{search}%"; params += [like, like, like, like]
        q += " ORDER BY t.last_message_at DESC LIMIT %s;"; params.append(limit)
        cur.execute(q, tuple(params)); rows = cur.fetchall()
        return [{"id": r[0], "parent_id": r[1], "student_id": r[2], "subject": r[3],
                 "status": r[4], "last_message_at": r[5], "last_message_by": r[6],
                 "unread": r[7] or 0, "parent_name": r[8], "parent_phone": r[9],
                 "student_name": r[10], "class_name": r[11], "last_message": r[12]} for r in rows]
    finally:
        cur.close(); conn.close()

def count_unread_threads_admin():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM message_threads WHERE unread_by_admin > 0;")
        return cur.fetchone()[0] or 0
    except Exception:
        conn.rollback()
        return 0
    finally:
        cur.close(); conn.close()

def count_unread_threads_parent(parent_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(unread_by_parent), 0) FROM message_threads WHERE parent_id=%s;", (parent_id,))
        return cur.fetchone()[0] or 0
    except Exception:
        conn.rollback()
        return 0
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 39 — EXAMS (consolidated)
# ============================================================
def get_exam_schedule(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, exam_id, subject, exam_date, start_time, end_time, room_no, max_marks, pass_marks FROM exam_schedule WHERE exam_id=%s ORDER BY exam_date, start_time;", (exam_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "exam_id": r[1], "subject": r[2], "exam_date": r[3],
                 "start_time": r[4], "end_time": r[5], "room_no": r[6],
                 "max_marks": r[7], "pass_marks": r[8]} for r in rows]
    finally:
        cur.close(); conn.close()

def save_exam_schedule_row(exam_id, subject, exam_date, start_time=None,
                           end_time=None, room_no=None, max_marks=100, pass_marks=33):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO exam_schedule (exam_id, subject, exam_date, start_time, end_time, room_no, max_marks, pass_marks) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
                    (exam_id, subject, exam_date, start_time or None, end_time or None,
                     room_no or None, max_marks, pass_marks))
        sid = cur.fetchone()[0]; conn.commit(); return sid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def delete_exam_schedule_row(schedule_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM exam_schedule WHERE id=%s;", (schedule_id,))
        conn.commit(); return True
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_exam_subjects(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT subjects FROM exams WHERE id=%s;", (exam_id,))
        row = cur.fetchone()
        if row and row[0]: return list(row[0])
        cur.execute("SELECT DISTINCT subject FROM exam_schedule WHERE exam_id=%s;", (exam_id,))
        return [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()

def get_all_exams():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, class_name, exam_date, max_marks, subjects FROM exams ORDER BY exam_date DESC;")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "class_name": r[2], "exam_date": r[3],
                 "max_marks": r[4], "subjects": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def get_exam_by_id(exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, class_name, exam_date, max_marks, subjects FROM exams WHERE id=%s;", (exam_id,))
        r = cur.fetchone()
        if not r: return None
        return {"id": r[0], "name": r[1], "class_name": r[2], "exam_date": r[3],
                "max_marks": r[4], "subjects": r[5]}
    finally:
        cur.close(); conn.close()

def get_exams_by_class(class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, class_name, exam_date, max_marks, subjects FROM exams WHERE class_name=%s ORDER BY exam_date DESC;", (class_name,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "class_name": r[2], "exam_date": r[3],
                 "max_marks": r[4], "subjects": r[5]} for r in rows]
    finally:
        cur.close(); conn.close()

def promote_class_section(student_ids, from_class, to_class, from_section=None, to_section=None):
    if not student_ids: return 0
    conn = get_conn(); cur = conn.cursor()
    try:
        ids_list = list(student_ids)
        if to_section:
            cur.execute("UPDATE students SET class_name=%s, section=%s WHERE id = ANY(%s);",
                        (to_class, to_section, ids_list))
        else:
            cur.execute("UPDATE students SET class_name=%s WHERE id = ANY(%s);",
                        (to_class, ids_list))
        updated = cur.rowcount; conn.commit(); return updated
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def get_exam_results_for_class(exam_id, class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT s.id as student_id, s.name, s.roll_no, s.class_name, s.section,
                              COALESCE(SUM(m.obtained), 0) as total_marks
                       FROM students s
                       LEFT JOIN marks m ON s.id = m.student_id AND m.exam_id = %s
                       WHERE s.class_name = %s
                       GROUP BY s.id, s.name, s.roll_no, s.class_name, s.section
                       ORDER BY total_marks DESC, s.roll_no ASC;""", (exam_id, class_name))
        rows = cur.fetchall()
        return [{"student_id": r[0], "name": r[1], "roll_no": r[2],
                 "class_name": r[3], "section": r[4],
                 "total_marks": float(r[5] or 0)} for r in rows]
    finally:
        cur.close(); conn.close()

def get_top_performers(exam_id=None, limit=5):
    conn = get_conn(); cur = conn.cursor()
    try:
        if exam_id:
            cur.execute("""SELECT s.id, s.name, s.roll_no, s.class_name, s.section,
                                  COALESCE(SUM(m.obtained), 0) as total
                           FROM students s
                           JOIN marks m ON s.id = m.student_id
                           WHERE m.exam_id = %s
                           GROUP BY s.id, s.name, s.roll_no, s.class_name, s.section
                           ORDER BY total DESC LIMIT %s;""", (exam_id, limit))
        else:
            cur.execute("""SELECT s.id, s.name, s.roll_no, s.class_name, s.section,
                                  COALESCE(SUM(m.obtained), 0) as total
                           FROM students s
                           JOIN marks m ON s.id = m.student_id
                           GROUP BY s.id, s.name, s.roll_no, s.class_name, s.section
                           ORDER BY total DESC LIMIT %s;""", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "roll_no": r[2], "class_name": r[3],
                 "section": r[4], "total": float(r[5] or 0)} for r in rows]
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 40 — HALL TICKET
# ============================================================
def get_hall_ticket_data(exam_id, student_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, photo_url FROM students WHERE id=%s;", (student_id,))
        s_row = cur.fetchone()
        if not s_row: return None
        student = {"id": s_row[0], "name": s_row[1], "roll_no": s_row[2],
                   "class_name": s_row[3], "section": s_row[4], "gender": s_row[5],
                   "dob": s_row[6], "parent_name": s_row[7], "parent_phone": s_row[8],
                   "photo_url": s_row[9]}
        cur.execute("SELECT id, name, class_name, exam_date, max_marks, subjects FROM exams WHERE id=%s;", (exam_id,))
        e_row = cur.fetchone()
        if not e_row: return None
        exam = {"id": e_row[0], "name": e_row[1], "class_name": e_row[2],
                "exam_date": e_row[3], "max_marks": e_row[4], "subjects": e_row[5]}
        schedule = get_exam_schedule(exam_id)
        return {"student": student, "exam": exam, "schedule": schedule}
    finally:
        cur.close(); conn.close()

def get_bulk_hall_tickets(exam_id, class_name, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id FROM students WHERE status='active' AND class_name=%s"
        params = [class_name]
        if section: q += " AND section=%s"; params.append(section)
        q += " ORDER BY section, roll_no, name;"
        cur.execute(q, tuple(params))
        student_ids = [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()
    tickets = []
    for sid in student_ids:
        data = get_hall_ticket_data(exam_id, sid)
        if data: tickets.append(data)
    return tickets

def get_hall_ticket_stats(exam_id, class_name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active' AND class_name=%s;", (class_name,))
        total_students = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM exam_schedule WHERE exam_id=%s;", (exam_id,))
        scheduled_subjects = cur.fetchone()[0] or 0
        return {"total_students": total_students, "scheduled_subjects": scheduled_subjects,
                "ready": scheduled_subjects > 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 41 — REPORT CARDS
# ============================================================
def calculate_grade(percentage):
    if percentage >= 90: return "A+"
    elif percentage >= 80: return "A"
    elif percentage >= 70: return "B+"
    elif percentage >= 60: return "B"
    elif percentage >= 50: return "C"
    elif percentage >= 33: return "D"
    else: return "F"

def get_report_card_data(student_id, exam_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, roll_no, class_name, section, gender, dob, parent_name, parent_phone, photo_url FROM students WHERE id=%s;", (student_id,))
        s_row = cur.fetchone()
        if not s_row: return None
        student = {"id": s_row[0], "name": s_row[1], "roll_no": s_row[2],
                   "class_name": s_row[3], "section": s_row[4], "gender": s_row[5],
                   "dob": s_row[6], "parent_name": s_row[7], "parent_phone": s_row[8],
                   "photo_url": s_row[9]}
        cur.execute("SELECT id, name, class_name, exam_date, max_marks, subjects FROM exams WHERE id=%s;", (exam_id,))
        e_row = cur.fetchone()
        if not e_row: return None
        exam = {"id": e_row[0], "name": e_row[1], "class_name": e_row[2],
                "exam_date": e_row[3], "max_marks": e_row[4], "subjects": e_row[5]}
        cur.execute("SELECT subject, obtained FROM marks WHERE exam_id=%s AND student_id=%s;", (exam_id, student_id))
        marks_rows = cur.fetchall()
        marks_map = {r[0]: float(r[1] or 0) for r in marks_rows}
        subjects = exam["subjects"] if exam["subjects"] else list(marks_map.keys())
        max_per_subject = float(exam["max_marks"] or 100)
        subject_details = []
        total_obtained = 0.0
        for sub in subjects:
            obt = marks_map.get(sub, 0.0)
            total_obtained += obt
            pct = round((obt / max_per_subject) * 100, 1) if max_per_subject > 0 else 0
            subject_details.append({"subject": sub, "obtained": obt,
                                    "max_marks": max_per_subject,
                                    "percentage": pct, "grade": calculate_grade(pct)})
        total_max = max_per_subject * len(subjects) if subjects else max_per_subject
        overall_pct = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0
        overall_grade = calculate_grade(overall_pct)
        status = "PASS" if overall_pct >= 33 else "FAIL"
        return {"student": student, "exam": exam, "subjects": subject_details,
                "total_obtained": total_obtained, "total_max": total_max,
                "percentage": overall_pct, "grade": overall_grade, "status": status}
    finally:
        cur.close(); conn.close()

def get_class_report_cards(exam_id, class_name, section=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        q = "SELECT id FROM students WHERE status='active' AND class_name=%s"
        params = [class_name]
        if section: q += " AND section=%s"; params.append(section)
        q += " ORDER BY section, roll_no, name;"
        cur.execute(q, tuple(params))
        student_ids = [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()
    cards = []
    for sid in student_ids:
        card = get_report_card_data(sid, exam_id)
        if card: cards.append(card)
    cards.sort(key=lambda x: x["percentage"], reverse=True)
    for idx, c in enumerate(cards, start=1): c["rank"] = idx
    return cards

# ============================================================
# SECTION 42 — PASSWORD OTP
# ============================================================
def generate_otp_code(length=6):
    return "".join([str(_random.randint(0, 9)) for _ in range(length)])

def create_password_otp(user_type, identifier, otp_code=None):
    if not otp_code: otp_code = generate_otp_code(6)
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO password_otps (user_type, identifier, otp_code, expires_at, is_used) VALUES (%s,%s,%s,NOW() + INTERVAL '10 minutes',FALSE) RETURNING id;",
                    (user_type, identifier, otp_code))
        oid = cur.fetchone()[0]; conn.commit()
        return {"id": oid, "otp": otp_code}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

def verify_password_otp(user_type, identifier, otp_code):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM password_otps WHERE user_type=%s AND identifier=%s AND otp_code=%s AND expires_at > NOW() AND is_used=FALSE ORDER BY created_at DESC LIMIT 1;",
                    (user_type, identifier, otp_code))
        row = cur.fetchone()
        if not row: return False
        cur.execute("UPDATE password_otps SET is_used=TRUE WHERE id=%s;", (row[0],))
        conn.commit(); return True
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

def reset_password_by_identifier(user_type, identifier, new_password):
    hashed = generate_password_hash(new_password)
    conn = get_conn(); cur = conn.cursor()
    try:
        if user_type == "admin":
            cur.execute("UPDATE admins SET password_hash=%s WHERE username=%s OR email=%s;",
                        (hashed, identifier, identifier))
        elif user_type == "teacher":
            cur.execute("UPDATE teachers SET password_hash=%s WHERE username=%s;",
                        (hashed, identifier))
        elif user_type == "parent":
            cur.execute("UPDATE parents SET password_hash=%s WHERE phone=%s;",
                        (hashed, identifier))
        else:
            return False
        updated = cur.rowcount; conn.commit(); return updated > 0
    except Exception:
        conn.rollback(); return False
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 43 — SMS & GATEWAY
# ============================================================
def get_sms_logs(limit=100):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, phone, message, status, sent_at FROM sms_logs ORDER BY sent_at DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        return [{"id": r[0], "phone": r[1], "message": r[2],
                 "status": r[3], "sent_at": r[4]} for r in rows]
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def log_sms(phone, message, status="sent"):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO sms_logs (phone, message, status, sent_at) VALUES (%s,%s,%s,NOW()) RETURNING id;",
                    (phone, message, status))
        lid = cur.fetchone()[0]; conn.commit(); return lid
    except Exception:
        conn.rollback(); return None
    finally:
        cur.close(); conn.close()

def get_sms_stats():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='sent'), COUNT(*) FILTER (WHERE status='failed') FROM sms_logs;")
        row = cur.fetchone()
        return {"total": row[0] or 0, "sent": row[1] or 0, "failed": row[2] or 0}
    except Exception:
        conn.rollback()
        return {"total": 0, "sent": 0, "failed": 0}
    finally:
        cur.close(); conn.close()

# ============================================================
# SECTION 44 — SYSTEM HEALTH & METRICS
# ============================================================
def get_system_health():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT 1;"); cur.fetchone()
        return {"status": "healthy", "database": "connected",
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected",
                "error": str(e), "timestamp": datetime.now().isoformat()}
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def get_database_tables_info():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [r[0] for r in cur.fetchall()]
        info = []
        for t in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{t}";')
                cnt = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                cnt = -1
            info.append({"table_name": t, "row_count": cnt})
        return info
    except Exception:
        conn.rollback()
        return []
    finally:
        cur.close(); conn.close()

def get_app_metrics():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM students WHERE status='active';")
        students = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM staff WHERE status='active';")
        staff = cur.fetchone()[0] or 0
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM fee_payments;")
        fees = float(cur.fetchone()[0] or 0)
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses;")
        expenses = float(cur.fetchone()[0] or 0)
        return {"active_students": students, "active_staff": staff,
                "total_fees_collected": fees, "total_expenses": expenses,
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception:
        conn.rollback()
        return {"active_students": 0, "active_staff": 0,
                "total_fees_collected": 0.0, "total_expenses": 0.0,
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    finally:
        cur.close(); conn.close()
