# fix_user_type_enum.py
import sqlite3
import os

print("=" * 60)
print("🔄 رفع مشکل Enum UserType")
print("=" * 60)

# پیدا کردن دیتابیس
db_paths = [
    'instance/seraj.db',
    'seraj.db',
    'app.db',
    'instance/app.db'
]

db_found = None
for path in db_paths:
    if os.path.exists(path):
        db_found = path
        break

if not db_found:
    print("❌ فایل دیتابیس پیدا نشد!")
    exit(1)

print(f"✅ دیتابیس پیدا شد: {db_found}")

# اتصال به دیتابیس
conn = sqlite3.connect(db_found)
cursor = conn.cursor()

# نمایش مقادیر فعلی user_type
cursor.execute("SELECT id, username, user_type FROM users")
users = cursor.fetchall()

print("\n📊 مقادیر فعلی user_type:")
for user in users:
    print(f"   ID: {user[0]}, Username: {user[1]}, user_type: {user[2]}")

# به‌روزرسانی مقادیر
print("\n🔄 در حال به‌روزرسانی مقادیر...")

# اگر user_type وجود ندارد یا NULL است، مقدار پیش‌فرض 'student' را قرار بده
cursor.execute("UPDATE users SET user_type = 'student' WHERE user_type IS NULL OR user_type = ''")

# اگر کاربران با user_type='STUDENT' دارید، به 'student' تبدیل کنید
cursor.execute("UPDATE users SET user_type = 'student' WHERE user_type = 'STUDENT'")
cursor.execute("UPDATE users SET user_type = 'professor' WHERE user_type = 'PROFESSOR'")
cursor.execute("UPDATE users SET user_type = 'staff' WHERE user_type = 'STAFF'")

conn.commit()

# نمایش مقادیر جدید
cursor.execute("SELECT id, username, user_type FROM users")
users = cursor.fetchall()

print("\n📊 مقادیر جدید user_type:")
for user in users:
    print(f"   ID: {user[0]}, Username: {user[1]}, user_type: {user[2]}")

conn.close()

print("\n" + "=" * 60)
print("✅ عملیات با موفقیت انجام شد!")
print("=" * 60)