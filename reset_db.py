# reset_db.py
import os
import sqlite3
from pathlib import Path

print("⚠️  هشدار: این برنامه تمام اطلاعات دیتابیس را پاک می‌کند!")
print("   آیا مطمئن هستید؟ (y/n): ", end="")

confirm = input()
if confirm.lower() != 'y':
    print("❌ عملیات لغو شد.")
    exit(0)

# پیدا کردن و حذف دیتابیس
db_paths = [
    'instance/seraj.db',
    'seraj.db',
    'app.db',
    'instance/app.db'
]

deleted = False
for path in db_paths:
    if os.path.exists(path):
        os.remove(path)
        print(f"✅ دیتابیس حذف شد: {path}")
        deleted = True

if not deleted:
    print("📁 فایل دیتابیس پیدا نشد!")

# حذف پوشه migrations اگر وجود دارد
if os.path.exists('migrations'):
    import shutil
    shutil.rmtree('migrations')
    print("✅ پوشه migrations حذف شد.")

print("\n🔄 در حال ساخت دیتابیس جدید...")

# ساخت دیتابیس جدید
try:
    from create_db import create_tables
    create_tables()
    print("✅ دیتابیس جدید با موفقیت ساخته شد!")
    print("   📂 مسیر: instance/seraj.db")
except Exception as e:
    print(f"❌ خطا در ساخت دیتابیس: {e}")

print("\n🚀 حالا می‌توانید برنامه را اجرا کنید:")
print("   python app.py")