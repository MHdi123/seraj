# fix_all_columns.py
import sqlite3
import os

print("=" * 60)
print("🔄 رفع کامل عدم تطابق ستون‌های دیتابیس")
print("=" * 60)

# مسیر دیتابیس
db_path = r"F:\seraj\instance\seraj.db"
if not os.path.exists(db_path):
    db_path = r"F:\seraj\seraj.db"
    if not os.path.exists(db_path):
        print("❌ فایل دیتابیس پیدا نشد!")
        exit(1)

print(f"✅ دیتابیس پیدا شد: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# دریافت ستون‌های موجود
cursor.execute("PRAGMA table_info(users)")
existing_columns = [col[1] for col in cursor.fetchall()]
print(f"\n📊 ستون‌های موجود ({len(existing_columns)} عدد):")
print(f"   {', '.join(existing_columns)}")

# لیست کامل ستون‌های مورد نیاز بر اساس models.py
required_columns = {
    'fcm_token': 'VARCHAR(500)',
    'is_verified': 'BOOLEAN DEFAULT 0',
    'verified_at': 'DATETIME',
    'verified_by': 'INTEGER',
    'verification_notes': 'TEXT',
    'landline': 'VARCHAR(20)',
    'office_phone': 'VARCHAR(20)',
    'teaching_experience': 'INTEGER',
    'professor_code': 'VARCHAR(50)',
    'office_hours': 'VARCHAR(200)',
    'website': 'VARCHAR(200)',
    'employee_id': 'VARCHAR(50)',
    'department': 'VARCHAR(100)',
    'position': 'VARCHAR(100)',
    'responsibility': 'TEXT',
    'resume_file': 'VARCHAR(500)'
}

# اضافه کردن ستون‌های جا افتاده
added_columns = []
for col_name, col_type in required_columns.items():
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            added_columns.append(col_name)
            print(f"   ✅ ستون {col_name} اضافه شد.")
        except Exception as e:
            print(f"   ❌ خطا در اضافه کردن {col_name}: {e}")

if added_columns:
    conn.commit()
    print(f"\n🎉 {len(added_columns)} ستون جدید با موفقیت اضافه شدند:")
    for col in added_columns:
        print(f"   - {col}")
else:
    print("\n✅ همه ستون‌ها از قبل وجود دارند.")

# نمایش آمار نهایی
cursor.execute("PRAGMA table_info(users)")
final_columns = [col[1] for col in cursor.fetchall()]
print(f"\n📊 تعداد کل ستون‌ها بعد از تغییر: {len(final_columns)}")

conn.close()

print("\n" + "=" * 60)
print("✅ عملیات با موفقیت انجام شد!")
print("=" * 60)
print("\n📝 حالا برنامه را اجرا کنید:")
print("   python app.py")