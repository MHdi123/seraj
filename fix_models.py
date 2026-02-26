# fix_models.py
import sqlite3
import os

print("=" * 60)
print("🔄 رفع مشکلات مدل‌ها و به‌روزرسانی دیتابیس")
print("=" * 60)

db_path = r"F:\seraj\instance\seraj.db"

if not os.path.exists(db_path):
    print(f"❌ دیتابیس پیدا نشد: {db_path}")
    exit(1)

print(f"✅ دیتابیس پیدا شد: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# بررسی جداول موجود
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [table[0] for table in cursor.fetchall()]
print(f"\n📊 تعداد جداول موجود: {len(tables)}")

# لیست جداول مورد نیاز
required_tables = [
    'users', 'events', 'registrations', 'notifications', 'ai_questions',
    'quran_verses', 'password_reset_tokens', 'faculties', 'departments',
    'courses', 'academic_terms', 'classes', 'class_enrollments',
    'class_sessions', 'attendances', 'class_files', 'session_files',
    'quran_circles', 'circle_members', 'circle_sessions',
    'session_attendances', 'circle_files', 'circle_session_files',
    'user_fcm_tokens', 'verification_logs'
]

# بررسی جداول جا افتاده
missing_tables = []
for table in required_tables:
    if table not in tables:
        missing_tables.append(table)

if missing_tables:
    print("\n⚠️ جداول زیر وجود ندارند:")
    for table in missing_tables:
        print(f"   - {table}")
    print("\nلطفاً ابتدا update_db_professor.py را اجرا کنید.")
else:
    print("\n✅ همه جداول مورد نیاز وجود دارند.")

conn.close()

print("\n" + "=" * 60)
print("✅ بررسی کامل شد!")
print("=" * 60)
print("\nمراحل بعدی:")
print("1. python update_db_professor.py (اگر جداول کم دارید)")
print("2. python app.py")