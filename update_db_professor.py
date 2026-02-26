# update_db_professor.py
import sqlite3
import os
from datetime import datetime

print("=" * 60)
print("🔄 به‌روزرسانی دیتابیس برای پنل اساتید")
print("=" * 60)

# مسیر دیتابیس
db_path = r"F:\seraj\instance\seraj.db"

if not os.path.exists(db_path):
    # مسیرهای جایگزین
    alt_paths = [
        r"F:\seraj\seraj.db",
        r"F:\seraj\app.db",
        r"F:\seraj\instance\app.db"
    ]
    for path in alt_paths:
        if os.path.exists(path):
            db_path = path
            break
    else:
        print("❌ فایل دیتابیس پیدا نشد!")
        exit(1)

print(f"✅ دیتابیس پیدا شد: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ============================================
# 1. اضافه کردن فیلدهای جدید به جدول users
# ============================================
print("\n📊 بررسی و اضافه کردن فیلدهای جدید به جدول users...")

cursor.execute("PRAGMA table_info(users)")
existing_columns = [col[1] for col in cursor.fetchall()]

new_user_columns = [
    ('office_location', 'VARCHAR(200)'),
    ('last_seen', 'DATETIME'),
    ('department', 'VARCHAR(100)')
]

for col_name, col_type in new_user_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"   ✅ ستون {col_name} اضافه شد.")
        except Exception as e:
            print(f"   ❌ خطا در اضافه کردن {col_name}: {e}")
    else:
        print(f"   ⏺ ستون {col_name} از قبل وجود دارد.")

# ============================================
# 2. ایجاد جدول faculties (دانشکده‌ها)
# ============================================
print("\n📊 ایجاد جدول faculties...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS faculties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    university VARCHAR(200) NOT NULL,
    dean VARCHAR(200),
    description TEXT,
    established_year INTEGER,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("   ✅ جدول faculties ایجاد شد.")

# ============================================
# 3. ایجاد جدول departments (گروه‌های آموزشی)
# ============================================
print("\n📊 ایجاد جدول departments...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    faculty_id INTEGER,
    head VARCHAR(200),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(faculty_id) REFERENCES faculties(id)
)
""")
print("   ✅ جدول departments ایجاد شد.")

# ============================================
# 4. ایجاد جدول courses (دروس)
# ============================================
print("\n📊 ایجاد جدول courses...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    credits INTEGER DEFAULT 3,
    department_id INTEGER,
    description TEXT,
    prerequisites VARCHAR(500),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(department_id) REFERENCES departments(id)
)
""")
print("   ✅ جدول courses ایجاد شد.")

# ============================================
# 5. ایجاد جدول academic_terms (ترم‌های تحصیلی)
# ============================================
print("\n📊 ایجاد جدول academic_terms...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS academic_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("   ✅ جدول academic_terms ایجاد شد.")

# ============================================
# 6. ایجاد جدول classes (کلاس‌های درس)
# ============================================
print("\n📊 ایجاد جدول classes...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    instructor_id INTEGER,
    faculty_id INTEGER,
    course_id INTEGER,
    academic_term VARCHAR(50),
    start_date DATE,
    end_date DATE,
    schedule VARCHAR(500),
    location VARCHAR(200),
    capacity INTEGER DEFAULT 30,
    credits INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(instructor_id) REFERENCES users(id),
    FOREIGN KEY(faculty_id) REFERENCES faculties(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
)
""")
print("   ✅ جدول classes ایجاد شد.")

# ============================================
# 7. ایجاد جدول class_enrollments (ثبت‌نام در کلاس)
# ============================================
print("\n📊 ایجاد جدول class_enrollments...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS class_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    enrollment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    grade FLOAT,
    notes TEXT,
    FOREIGN KEY(class_id) REFERENCES classes(id),
    FOREIGN KEY(student_id) REFERENCES users(id),
    UNIQUE(class_id, student_id)
)
""")
print("   ✅ جدول class_enrollments ایجاد شد.")

# ============================================
# 8. ایجاد جدول class_sessions (جلسات کلاس)
# ============================================
print("\n📊 ایجاد جدول class_sessions...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS class_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    title VARCHAR(200),
    session_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    location VARCHAR(200),
    topic TEXT,
    materials TEXT,
    status VARCHAR(20) DEFAULT 'scheduled',
    is_cancelled BOOLEAN DEFAULT 0,
    cancel_reason VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(class_id) REFERENCES classes(id)
)
""")
print("   ✅ جدول class_sessions ایجاد شد.")

# ============================================
# 9. ایجاد جدول attendances (حضور و غیاب)
# ============================================
print("\n📊 ایجاد جدول attendances...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'present',
    late_minutes INTEGER DEFAULT 0,
    excuse TEXT,
    marked_by INTEGER,
    marked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES class_sessions(id),
    FOREIGN KEY(student_id) REFERENCES users(id),
    FOREIGN KEY(marked_by) REFERENCES users(id),
    UNIQUE(session_id, student_id)
)
""")
print("   ✅ جدول attendances ایجاد شد.")

# ============================================
# 10. ایجاد جدول class_files (فایل‌های کلاس)
# ============================================
print("\n📊 ایجاد جدول class_files...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS class_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by INTEGER,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    FOREIGN KEY(class_id) REFERENCES classes(id),
    FOREIGN KEY(uploaded_by) REFERENCES users(id)
)
""")
print("   ✅ جدول class_files ایجاد شد.")

# ============================================
# 11. ایجاد جدول session_files (فایل‌های جلسات)
# ============================================
print("\n📊 ایجاد جدول session_files...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS session_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by INTEGER,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES class_sessions(id),
    FOREIGN KEY(uploaded_by) REFERENCES users(id)
)
""")
print("   ✅ جدول session_files ایجاد شد.")

# ============================================
# 12. ایجاد جدول circle_session_files (فایل‌های جلسات حلقه)
# ============================================
print("\n📊 ایجاد جدول circle_session_files...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS circle_session_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by INTEGER,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES circle_sessions(id),
    FOREIGN KEY(uploaded_by) REFERENCES users(id)
)
""")
print("   ✅ جدول circle_session_files ایجاد شد.")

# ============================================
# 13. به‌روزرسانی مقادیر پیش‌فرض
# ============================================
print("\n📊 به‌روزرسانی مقادیر پیش‌فرض...")

# تنظیم last_seen برای کاربران موجود
cursor.execute("UPDATE users SET last_seen = created_at WHERE last_seen IS NULL")
print("   ✅ last_seen برای کاربران به‌روزرسانی شد.")

# تنظیم is_verified برای اساتید و دانشجویان موجود
cursor.execute("UPDATE users SET is_verified = 1 WHERE user_type IN ('student', 'professor') AND is_verified IS NULL")
print("   ✅ is_verified برای اساتید و دانشجویان تنظیم شد.")

# ============================================
# 14. ایجاد ترم جاری پیش‌فرض
# ============================================
print("\n📊 ایجاد ترم جاری پیش‌فرض...")

from datetime import date, timedelta
import jdatetime

try:
    # تاریخ شمسی فعلی
    today = jdatetime.date.today()
    
    # تعریف ترم جاری (نیمسال اول یا دوم)
    if today.month <= 6:
        term_name = f"نیمسال اول {today.year}-{today.year+1}"
        start_date = jdatetime.date(today.year, 7, 1).togregorian()
        end_date = jdatetime.date(today.year+1, 1, 1).togregorian()
    else:
        term_name = f"نیمسال دوم {today.year}-{today.year+1}"
        start_date = jdatetime.date(today.year, 10, 1).togregorian()
        end_date = jdatetime.date(today.year+1, 2, 1).togregorian()
    
    cursor.execute("""
        INSERT OR IGNORE INTO academic_terms (name, start_date, end_date, is_current)
        VALUES (?, ?, ?, 1)
    """, (term_name, start_date.isoformat(), end_date.isoformat()))
    
    print(f"   ✅ ترم جاری ایجاد شد: {term_name}")
except Exception as e:
    print(f"   ⚠️ خطا در ایجاد ترم جاری: {e}")

# ============================================
# 15. نمایش آمار نهایی
# ============================================
print("\n" + "=" * 60)
print("📊 آمار نهایی:")
print("=" * 60)

# تعداد جداول
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
tables_count = cursor.fetchone()[0]
print(f"📋 تعداد کل جداول: {tables_count}")

# تعداد کاربران
cursor.execute("SELECT COUNT(*) FROM users")
users_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='professor'")
professors_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='student'")
students_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='staff'")
staff_count = cursor.fetchone()[0]

print(f"👤 کل کاربران: {users_count}")
print(f"   ├─ استاد: {professors_count}")
print(f"   ├─ دانشجو: {students_count}")
print(f"   └─ کارمند: {staff_count}")

# آمار کلاس‌ها
cursor.execute("SELECT COUNT(*) FROM classes")
classes_count = cursor.fetchone()[0]
print(f"📚 کلاس‌های درس: {classes_count}")

# آمار دانشکده‌ها
cursor.execute("SELECT COUNT(*) FROM faculties")
faculties_count = cursor.fetchone()[0]
print(f"🏛 دانشکده‌ها: {faculties_count}")

# آمار دروس
cursor.execute("SELECT COUNT(*) FROM courses")
courses_count = cursor.fetchone()[0]
print(f"📖 دروس: {courses_count}")

# آمار جلسات
cursor.execute("SELECT COUNT(*) FROM class_sessions")
sessions_count = cursor.fetchone()[0]
print(f"📅 جلسات کلاس: {sessions_count}")

# آمار ثبت‌نام‌ها
cursor.execute("SELECT COUNT(*) FROM class_enrollments")
enrollments_count = cursor.fetchone()[0]
print(f"📝 ثبت‌نام‌های کلاس: {enrollments_count}")

# آمار حضور و غیاب
cursor.execute("SELECT COUNT(*) FROM attendances")
attendance_count = cursor.fetchone()[0]
print(f"✅ حضور و غیاب ثبت شده: {attendance_count}")

# آمار فایل‌ها
cursor.execute("SELECT COUNT(*) FROM class_files")
class_files_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM session_files")
session_files_count = cursor.fetchone()[0]
print(f"📁 فایل‌های کلاس: {class_files_count}")
print(f"📁 فایل‌های جلسات: {session_files_count}")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ به‌روزرسانی دیتابیس با موفقیت انجام شد!")
print("=" * 60)
print("\n📝 حالا می‌توانید برنامه را اجرا کنید:")
print("   python app.py")
print("\n🔍 برای دسترسی به پنل استاد:")
print("   /professor/dashboard")