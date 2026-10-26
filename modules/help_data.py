"""
In-app help content. Har topic ka structure:
{
    "title": str,
    "icon": emoji,
    "category": str,
    "summary": short str,
    "steps": [str, ...],
    "tips": [str, ...],   # optional
    "related": [slug, ...],  # optional
}
"""

HELP_CATEGORIES = [
    {"id": "start", "label": "🚀 Getting Started"},
    {"id": "core", "label": "🎓 Daily Operations"},
    {"id": "finance", "label": "💰 Finance"},
    {"id": "people", "label": "👥 People & Access"},
    {"id": "extras", "label": "🧩 Additional Modules"},
    {"id": "advanced", "label": "⚙️ Advanced"},
]

HELP_TOPICS = {
    # ---------- Getting Started ----------
    "getting-started": {
        "title": "School Setup Shuru Karo",
        "icon": "🚀",
        "category": "start",
        "summary": "Pehli baar login karne ke baad ye steps follow karo — 30 minute mein school ready.",
        "steps": [
            "Settings → School Name, logo, phone, address bhardo",
            "Staff → apne teachers aur staff add karo",
            "Classes → classes/subjects set karo (ya students add karte waqt automatic)",
            "Fee Structure → har class ki fees define karo (Tuition, Transport, etc.)",
            "Students → ek-ek karke ya Bulk Import se students add karo",
            "Timetable → har class ka weekly timetable banao",
            "Admin Users → accountant, principal ke login banao (role ke saath)",
        ],
        "tips": [
            "Pehla admin automatically super_admin hota hai",
            "Bulk Import template download karke CSV banao — 100+ students ek saath",
            "Sab kuch karne ke baad Backup zaroor lo",
        ],
        "related": ["students", "fees", "staff"],
    },

    # ---------- Core Operations ----------
    "students": {
        "title": "Students Manage Karo",
        "icon": "🎓",
        "category": "core",
        "summary": "Add, edit, search, aur student profiles manage karo. Class-wise filter karo.",
        "steps": [
            "Students → + Add Student → form bharo (name zaroori, baaki optional)",
            "Bulk import ke liye → 📥 Template download karo → fill karo → 📤 Upload",
            "Search bar se naam/roll/phone filter karo",
            "Class dropdown + Status (Active/Inactive) filter",
            "Student pe click → 360° profile (fees, attendance, marks, medical, hostel, transport)",
        ],
        "tips": [
            "Roll No unique hona chahiye",
            "Inactive students list mein nahi dikhte — status filter se dekho",
            "Student profile se ID Card, Certificate, Medical, Library history sab accessible",
        ],
        "related": ["fees", "attendance", "medical"],
    },
    "fees": {
        "title": "Fees Collect Karo",
        "icon": "💰",
        "category": "finance",
        "summary": "Fee structure set karo, monthly bills generate karo, aur payments record karo.",
        "steps": [
            "Fees → Fee Structure → class-wise fees add karo (Tuition 1500/month etc.)",
            "Bills → + Generate Bills → class + month select → sab active students ke bills ban jayenge",
            "Fees → + Collect Fee → student, amount, mode (cash/upi/cheque) select → record",
            "Auto receipt milta hai — print kar sakte ho",
            "Defaulters page → pending fees wale students dekho → WhatsApp reminder bhejo",
        ],
        "tips": [
            "Bill = student ko dena hai, Payment = student ne diya — dono auto-reconcile hote hain",
            "Fee structure badalne se purane bills nahi badalte (snapshot safe hai)",
            "WhatsApp Reminder se ek tap mein fee reminder bhejo",
        ],
        "related": ["finance", "reports"],
    },
    "attendance": {
        "title": "Attendance Mark Karo",
        "icon": "📋",
        "category": "core",
        "summary": "Manual attendance ya QR scan se attendance mark karo.",
        "steps": [
            "Manual: Attendance → class select → date → P/A/L/Lv buttons per student",
            "Bulk: 'All Present' ya 'All Absent' button",
            "QR: 📷 QR Attendance → camera auto-start → student ka QR card scan karo",
            "Parent portal → attendance % aur calendar view automatically dikhta hai",
            "Reports → Attendance Report → month-wise %, 75% se neeche wale highlight",
        ],
        "tips": [
            "QR Cards print karo: QR Attendance → Print QR Cards → laminate karo",
            "Same student dobara scan karne pe status update hota hai (safe)",
            "Late marking se 50% weight in percentage calculation",
        ],
        "related": ["qr-attendance", "reports"],
    },
    "exams": {
        "title": "Exams & Marks",
        "icon": "📝",
        "category": "core",
        "summary": "Exam banao, marks enter karo, report card aur merit list nikalo.",
        "steps": [
            "Exams → + New Exam → class, exam name, subjects (comma separated) → create",
            "Marks entry grid khulega → har student ka har subject marks daalo → save",
            "Merit button → ranking table with total marks",
            "Report Card button → printable per-student card with grades",
            "Parent portal mein marks automatically dikhte hain",
        ],
        "tips": [
            "Grade: 90+ = A+, 80-89 = A, 70-79 = B, 60-69 = C, 33-59 = D, <33 = F",
            "Teachers apne assigned classes ke marks Teacher Portal se bhi enter kar sakte hain",
            "Marks save hone ke baad Report Card / Merit turant ready",
        ],
        "related": ["reports", "teacher-portal"],
    },
    "communication": {
        "title": "Notices aur Events",
        "icon": "📢",
        "category": "core",
        "summary": "Parents tak announcements pahunchao — notices + calendar events.",
        "steps": [
            "Notices → + New Notice → title, content, priority → public mark karo",
            "Event: Events → + Add Event → type (holiday/exam/meeting), date, venue",
            "WhatsApp: Notice ke detail page pe 📲 WhatsApp button → parents list with send links",
            "Public site: Notices public board pe automatically dikhte hain",
            "Parent portal mein sirf relevant notices dikhte hain (target_class filter)",
        ],
        "tips": [
            "Priority: 'urgent' red, 'high' yellow, 'normal' blue",
            "Events calendar view → monthly grid with color-coded types",
            "Public events bina login ke /site pe dikhte hain",
        ],
        "related": ["whatsapp"],
    },
    "homework": {
        "title": "Homework Post Karo",
        "icon": "📚",
        "category": "core",
        "summary": "Class-wise homework assign karo, parents ko automatic dikhta hai.",
        "steps": [
            "Homework → + New Homework → class, subject, title, description, due date",
            "Attachment URL daal sakte ho (Drive link, image, etc.)",
            "Status auto: upcoming (blue), due today (yellow), overdue (red)",
            "Parent portal → child's class ka homework automatically visible",
        ],
        "tips": [
            "Teachers bhi Teacher Portal se homework post kar sakte hain",
            "Due date optional hai — khaali chhodo toh 'no due date' status",
        ],
        "related": ["teacher-portal"],
    },

    # ---------- People & Access ----------
    "staff": {
        "title": "Staff & Teacher Logins",
        "icon": "👥",
        "category": "people",
        "summary": "Staff directory banao, teachers ke logins create karo.",
        "steps": [
            "Staff → + Add Staff → name, role, phone, subjects, salary set karo",
            "Teacher Logins → + Create Login → staff member select karo → username/password",
            "Teacher Portal: /teacher/login → teacher apna dashboard, attendance, homework, marks manage karta hai",
            "Timetable mein teacher assign karo → uski classes determine hoti hain",
        ],
        "tips": [
            "Teacher login sirf apni assigned classes ka access rakhta hai",
            "Staff salary records automatic Salary module mein use hote hain",
            "Driver, helper, accountant ke bhi staff records banao",
        ],
        "related": ["teacher-portal"],
    },
    "multi-admin": {
        "title": "Multi-Admin + Roles",
        "icon": "👤",
        "category": "people",
        "summary": "Multiple admin users banao alag roles ke saath.",
        "steps": [
            "Admin Users → + Create Admin User → username, password, role select",
            "Roles: super_admin (all), admin (no user manage), accountant (finance), viewer (read)",
            "Har admin ka alag login, audit log mein separate track",
            "Password reset, deactivate, delete — sab available",
        ],
        "tips": [
            "Apne aap ko delete ya edit nahi kar sakte (safety)",
            "Inactive user turant login nahi kar sakta",
            "Audit Logs → kis admin ne kya kiya, kab",
        ],
        "related": ["settings"],
    },

    # ---------- Parent/Teacher ----------
    "parent-portal": {
        "title": "Parent Portal",
        "icon": "👨‍👩‍👧",
        "category": "people",
        "summary": "Parents apne bachche ka data dekhte hain — fees, attendance, marks, homework.",
        "steps": [
            "Parent register karta hai /parent/register → phone (jo students mein hai) + password",
            "Login → dashboard pe bachche ka summary",
            "Child card click → detailed view (fees, attendance, exam results)",
            "Notices, homework, events — sab filtered by child's class",
        ],
        "tips": [
            "Parent phone exactly match karna chahiye students.parent_phone se",
            "Multiple children ho sakte hain — tabs se switch",
            "Ek parent = ek login, multiple children track",
        ],
        "related": ["students"],
    },
    "teacher-portal": {
        "title": "Teacher Portal",
        "icon": "👨‍🏫",
        "category": "people",
        "summary": "Teachers apna login karke attendance, homework, marks manage karte hain.",
        "steps": [
            "Admin pehle teacher login banata hai (Teacher Logins page)",
            "Teacher /teacher/login pe login karta hai",
            "Dashboard: aaj ke periods, assigned classes, recent homework",
            "Attendance: sirf apni classes ka mark kar sakta hai",
            "Homework: apni classes ke liye post kar sakta hai",
            "Marks: apni classes ke exams ke marks enter kar sakta hai",
        ],
        "tips": [
            "Access control automatic hai — unauthorized classes block",
            "Teacher summary dashboard se turant pata chalta hai kaunsa period",
            "Attendance/Homework/Marks sab parent portal mein reflect hote hain",
        ],
        "related": ["staff", "attendance", "exams"],
    },

    # ---------- Extras ----------
    "medical": {
        "title": "Medical Records",
        "icon": "🩺",
        "category": "extras",
        "summary": "Har student ka health record — allergies, emergency contacts, vaccinations.",
        "steps": [
            "Medical → missing students list → student pe click",
            "Blood group, allergies, chronic conditions, emergency contact bhardo",
            "Vaccinations section → vaccine add karo (name, date, dose)",
            "Student profile pe summary card automatic dikhta hai",
        ],
        "tips": [
            "Allergy wale students Medical index pe red alert mein dikhte hain",
            "Emergency phone tel: link hai — direct call",
            "Missing records wale students ko reminder ki tarah dekh sakte ho",
        ],
    },
    "library": {
        "title": "Library",
        "icon": "📚",
        "category": "extras",
        "summary": "Books catalog banao, issue/return track karo, fine calculate karo.",
        "steps": [
            "Library → + Add Book → title, author, copies, shelf",
            "Issue Book → book + student + due date select",
            "Active Issues → overdue highlight, fine estimation (₹2/day)",
            "Return button → fine auto-calculate + book available ho jata hai",
            "Student profile pe library history dikhti hai",
        ],
        "tips": [
            "Ek student ek book ki ek hi copy le sakta hai",
            "Book delete blocked jab active issues hain",
            "Fine per day customize karne ke liye database.py mein LIBRARY_FINE_PER_DAY",
        ],
    },
    "transport": {
        "title": "Bus Routes",
        "icon": "🚌",
        "category": "extras",
        "summary": "Bus routes banao, stops define karo, students assign karo.",
        "steps": [
            "Transport → + Add Route → name, driver, phone, vehicle, capacity",
            "Route view → + Add Stop → 3-4 stops with pickup/drop times",
            "Route → + Assign Student → student + stop select",
            "Student profile mein transport card auto dikhta hai",
        ],
        "tips": [
            "Ek student ek route pe ho sakta hai (reassign automatic)",
            "Driver phone tel: link hai",
            "Capacity exceed pe visual warning but block nahi",
        ],
    },
    "hostel": {
        "title": "Hostel",
        "icon": "🏠",
        "category": "extras",
        "summary": "Hostels, rooms, bed allocation, inmates, fees track karo.",
        "steps": [
            "Hostel → + Add Hostel → name, warden details",
            "Hostel view → + Add Room → room no, type, capacity, monthly fee",
            "Allocate Student → student + room select → capacity check hoti hai",
            "Checkout → room seat free ho jati hai",
            "Room card click → inmates detail view",
        ],
        "tips": [
            "Room full hote hi dropdown mein nahi aata",
            "Active inmates wale room delete nahi ho sakte",
            "Hostel delete → rooms delete, students unallocated",
        ],
    },
    "certificates": {
        "title": "Certificates",
        "icon": "📜",
        "category": "extras",
        "summary": "TC, Bonafide, Character Certificates generate karo — auto-filled + printable.",
        "steps": [
            "Certificates → + New Certificate",
            "Student select karo → type (TC/Bonafide/Character/Study/Fee Clearance) → body auto-fill",
            "Body edit kar sakte ho → Generate",
            "Auto cert number (BC-2025-0001 type)",
            "Print / Save as PDF",
        ],
        "tips": [
            "Certificate number per type, per year counter",
            "Student profile se 📜 Certificate button shortcut",
            "Letterhead, seal placeholder, principal signature — sab included",
        ],
    },
    "promotion": {
        "title": "Year-End Promotion",
        "icon": "🎓",
        "category": "extras",
        "summary": "Saal ke end pe bulk promote students to next class.",
        "steps": [
            "Promotion → class card pe click",
            "Preview mein har student ka action choose karo — Promote / Repeat / Archive",
            "Bulk buttons: All Promote / All Repeat",
            "Confirm with count → execute",
            "Class 12 promote → automatically alumni (inactive)",
        ],
        "tips": [
            "⚠️ Irreversible — pehle Backup zaroor lo",
            "Archive students inactive ho jate hain, delete nahi",
            "Section same rehta hai promotion ke baad",
        ],
        "related": ["backup"],
    },
    "qr-attendance": {
        "title": "QR Code Attendance",
        "icon": "📷",
        "category": "core",
        "summary": "Camera se student ka QR scan karo — 2 second mein attendance mark.",
        "steps": [
            "QR Attendance sidebar → camera auto-start",
            "Pehle QR Cards print karo: QR Attendance → Print QR Cards → class select → print",
            "Student card ka QR camera ke saamne rakho",
            "Green overlay: mark ho gaya, list mein add",
            "Manual entry fallback bhi available (ID type karo)",
        ],
        "tips": [
            "Print + laminate + distribute to students",
            "Status dropdown: Present / Late / Leave / Absent — pehle select karo",
            "Duplicate scan → 2s debounce + status update message",
            "HTTPS zaroori — Render pe automatic",
        ],
        "related": ["attendance", "qr-attendance"],
    },

    # ---------- Finance ----------
    "finance": {
        "title": "Salaries & Expenses",
        "icon": "💵",
        "category": "finance",
        "summary": "Staff salaries track karo, school expenses log karo, P&L dekho.",
        "steps": [
            "Salary → + Generate Salary → month select → sab active staff ke records ban jate hain",
            "Adjust → bonus/deductions add karo before paying",
            "Mark Paid → mode select → slip auto-generate",
            "Expenses → + Add Expense → category (Rent/Utilities), amount, vendor",
            "Expenses → P&L → monthly profit/loss view",
        ],
        "tips": [
            "Salary double entry mat karo expenses mein — separately track hota hai",
            "P&L = Fees Collected - (Salary Paid + Other Expenses)",
            "Pending salary P&L mein count nahi hoti",
        ],
        "related": ["reports"],
    },
    "reports": {
        "title": "Reports",
        "icon": "📊",
        "category": "finance",
        "summary": "Fee, attendance, defaulters, annual — sab reports CSV export ke saath.",
        "steps": [
            "Reports → Fee Collection → date range + class filter → CSV export",
            "Reports → Attendance → month + class → 75% below highlighted",
            "Reports → Defaulters → month → WhatsApp links per parent",
            "Annual Report → FY select → print-ready full report",
        ],
        "tips": [
            "CSV Excel/Google Sheets mein khulta hai",
            "Annual report board meeting ke liye print-friendly",
            "Defaulters report mein WhatsApp link → direct message",
        ],
        "related": ["finance", "fees"],
    },
    "whatsapp": {
        "title": "WhatsApp Reminders",
        "icon": "📲",
        "category": "finance",
        "summary": "Fee defaulters, low attendance parents ko bulk WhatsApp links.",
        "steps": [
            "WhatsApp Reminder sidebar → mode select (Defaulters/Low Attendance/All)",
            "Month + class filter → template auto-select",
            "Preview mein message dikhega",
            "Har student ke saamne Send button → WhatsApp opens with pre-filled message",
            "Send click ke baad '✓ Sent' chip aa jata hai (log auto-save)",
        ],
        "tips": [
            "Template edit: ⚙️ Templates page",
            "Placeholders: {name}, {parent}, {amount}, {month}, {school}",
            "7 din mein same template → '✓ Sent' yellow warning (spam avoid)",
            "Free WhatsApp API nahi hai — semi-auto, click per parent",
        ],
    },

    # ---------- Advanced ----------
    "settings": {
        "title": "Settings & Profile",
        "icon": "⚙️",
        "category": "advanced",
        "summary": "School branding, admin profile, password change.",
        "steps": [
            "Settings → school name, logo URL, phone, email, address",
            "My Profile → apna name/username change karo",
            "Change password with old password verification",
            "PWA install instructions bhi yahan",
        ],
        "tips": [
            "School name sidebar, receipts, report cards, certificates — sab jagah use hota hai",
            "Logo URL public hone chahiye (Supabase Storage / Cloudinary)",
        ],
    },
    "backup": {
        "title": "Backup & Restore",
        "icon": "💾",
        "category": "advanced",
        "summary": "Full JSON backup, per-table CSV, restore.",
        "steps": [
            "Backup → ⬇️ Download Backup → timestamped JSON file",
            "Backup weekly/monthly lo — Google Drive / email pe save karo",
            "Per-table CSV download bhi possible (sirf students, fees, etc.)",
            "Restore → JSON upload → preview → confirm",
        ],
        "tips": [
            "Restore existing data delete nahi karta — sirf add karta hai",
            "Best: fresh database pe restore karo",
            "Restore se pehle current data ka backup lo",
            "School year-end pe backup essential — permanent record",
        ],
    },
    "alerts": {
        "title": "Alerts & Notifications",
        "icon": "🔔",
        "category": "advanced",
        "summary": "Live system alerts + custom announcements.",
        "steps": [
            "Alerts sidebar → computed alerts (fee defaulters, low attendance, overdue books)",
            "Click any alert → relevant page pe jump",
            "Custom Alert: Alerts → + New Custom Alert → title, message, type, expiry",
            "Active/inactive toggle, delete",
        ],
        "tips": [
            "Sidebar badge pe total alert count",
            "Dashboard pe bhi top alerts dikhte hain",
            "Custom alerts expiry date ke baad automatic hide",
        ],
    },
}
