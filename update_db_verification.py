# update_db_verification.py
import sqlite3
import os
from datetime import datetime

print("=" * 60)
print("🔄 به‌روزرسانی دیتابیس برای سیستم تأیید کاربران")
print("=" * 60)

# مسیر دیتابیس شما
db_path = r"F:\seraj\instance\seraj.db"

if not os.path.exists(db_path):
    print(f"❌ فایل دیتابیس پیدا نشد: {db_path}")
    # مسیرهای جایگزین را بررسی کن
    alt_paths = [
        r"F:\seraj\seraj.db",
        r"F:\seraj\app.db",
        r"F:\seraj\instance\app.db"
    ]
    for path in alt_paths:
        if os.path.exists(path):
            db_path = path
            print(f"✅ دیتابیس پیدا شد: {db_path}")
            break
    else:
        print("❌ هیچ فایل دیتابیسی پیدا نشد!")
        exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# بررسی وجود جدول users
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cursor.fetchone():
    print("❌ جدول users وجود ندارد!")
    exit(1)

# بررسی وجود ستون‌های جدید
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

new_columns = [
    ('is_verified', 'BOOLEAN DEFAULT 0'),
    ('verified_at', 'DATETIME'),
    ('verified_by', 'INTEGER'),
    ('verification_notes', 'TEXT')
]

print("\n📊 بررسی ستون‌ها...")
for col_name, col_type in new_columns:
    if col_name not in columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"   ✅ ستون {col_name} اضافه شد.")
        except Exception as e:
            print(f"   ❌ خطا در اضافه کردن {col_name}: {e}")
    else:
        print(f"   ⏺ ستون {col_name} از قبل وجود دارد.")

# ایجاد جدول verification_logs اگر وجود ندارد
cursor.execute("""
CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    performed_by INTEGER NOT NULL,
    reason TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(performed_by) REFERENCES users(id)
)
""")
print("   ✅ جدول verification_logs ایجاد شد.")

# به‌روزرسانی کاربران قدیمی
print("\n🔄 به‌روزرسانی وضعیت کاربران...")

# دانشجوها و ادمین‌ها خودکار تأیید می‌شوند
cursor.execute("UPDATE users SET is_verified = 1 WHERE user_type = 'student' OR user_type = 'admin' OR role = 'admin'")
student_count = cursor.rowcount
print(f"   ✅ {student_count} کاربر دانشجو و ادمین تأیید شدند.")

# اساتید و کارمندان نیاز به تأیید دارند
cursor.execute("UPDATE users SET is_verified = 0 WHERE user_type IN ('professor', 'staff')")
staff_count = cursor.rowcount
print(f"   ⏳ {staff_count} کاربر استاد و کارمند در انتظار تأیید قرار گرفتند.")

conn.commit()

# نمایش آمار نهایی
cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
verified_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 0")
unverified_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM users")
total_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='professor'")
professor_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='staff'")
staff_count_total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='student'")
student_count_total = cursor.fetchone()[0]

print("\n📊 آمار نهایی:")
print(f"   👤 کل کاربران: {total_count}")
print(f"   ✅ کاربران تأیید شده: {verified_count}")
print(f"   ⏳ کاربران در انتظار تأیید: {unverified_count}")
print(f"   └─ استاد: {professor_count}")
print(f"   └─ کارمند: {staff_count_total}")
print(f"   └─ دانشجو: {student_count_total}")

conn.close()

print("\n" + "=" * 60)
print("✅ عملیات با موفقیت انجام شد!")
print("=" * 60)
print("\n📝 حالا می‌توانید برنامه را اجرا کنید:")
print("   python app.py")