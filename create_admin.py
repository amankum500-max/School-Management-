# create_admin.py
from database import create_admin_user

try:
    # function call kar rahe hain
    admin_id = create_admin_user(
        username="admin",
        password="Admin@123",
        full_name="Super Admin",
        role="admin"
    )
    print(f"✅ Admin successfully ban gaya! (ID: {admin_id})")
    print("👉 Login ID: admin")
    print("👉 Password: Admin@123")
except Exception as e:
    print(f"❌ Error aaya: {e}")
