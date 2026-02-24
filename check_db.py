# check_db_complete.py
import sqlite3
import os
from datetime import datetime

print("=" * 60)
print("🔍 بررسی کامل دیتابیس سِراج - تمام جداول و ستون‌ها")
print("=" * 60)

# ============================================
# پیدا کردن دیتابیس
# ============================================
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
    print("📁 مسیرهای جستجو شده:")
    for path in db_paths:
        print(f"   - {path}")
    exit(1)

print(f"✅ دیتابیس پیدا شد: {db_found}")
print(f"📅 آخرین ویرایش: {datetime.fromtimestamp(os.path.getmtime(db_found)).strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

conn = sqlite3.connect(db_found)
cursor = conn.cursor()

# ============================================
# 1. بررسی جدول users
# ============================================
print("\n📋 جدول users:")
print("-" * 80)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    
    print(f"{'وضعیت':8} {'نام ستون':25} {'نوع':15} {'NOT NULL':10} {'پیش‌فرض':15}")
    print("-" * 80)
    
    # لیست ستون‌های مورد انتظار
    expected_columns = [
        'id', 'username', 'email', 'password_hash',
        'first_name', 'last_name', 'phone', 'landline', 'gender',
        'student_id', 'entrance_year', 'degree', 'field_of_study',
        'province', 'city', 'university', 'faculty',
        'role', 'is_active', 'created_at', 'last_login'
    ]
    
    found_columns = []
    for col in columns:
        col_name = col[1]
        found_columns.append(col_name)
        is_new = "🆕" if col_name in ['landline', 'gender', 'entrance_year', 'degree', 'field_of_study', 'province', 'city'] else "  "
        is_required = "🔴" if col_name in ['first_name', 'last_name', 'phone', 'student_id', 'university', 'faculty'] and col[3] == 1 else "  "
        status = f"{is_new}{is_required}" if is_new != "  " or is_required != "  " else "✅"
        not_null = "بله" if col[3] == 1 else "خیر"
        default = col[4] if col[4] else "-"
        print(f"{status:8} {col_name:25} {col[2]:15} {not_null:10} {default:15}")
    
    # بررسی ستون‌های جا افتاده
    print("\n📊 وضعیت ستون‌های مورد نیاز:")
    for col in expected_columns:
        if col in found_columns:
            print(f"   ✅ {col:25} موجود است")
        else:
            print(f"   ❌ {col:25} وجود ندارد!")
    
    # آمار کاربران
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()[0]
    
    print(f"\n📊 آمار کاربران:")
    print(f"   👤 کل کاربران: {users_count}")
    print(f"   ✅ کاربران فعال: {active_users}")
    print(f"   ❌ کاربران غیرفعال: {users_count - active_users}")
    
else:
    print("❌ جدول users وجود ندارد!")

# ============================================
# 2. بررسی جدول events
# ============================================
print("\n" + "=" * 60)
print("📋 جدول events:")
print("-" * 80)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(events)")
    columns = cursor.fetchall()
    
    print(f"{'وضعیت':8} {'نام ستون':25} {'نوع':15} {'NOT NULL':10} {'پیش‌فرض':15}")
    print("-" * 80)
    
    expected_event_columns = ['id', 'title', 'description', 'event_type', 'start_date', 'end_date', 'location', 'capacity', 'current_participants', 'image', 'is_active', 'created_by', 'created_at']
    
    has_image = False
    for col in columns:
        col_name = col[1]
        if col_name == 'image':
            has_image = True
            status = "🖼️"
        else:
            status = "✅"
        not_null = "بله" if col[3] == 1 else "خیر"
        default = col[4] if col[4] else "-"
        print(f"{status:8} {col_name:25} {col[2]:15} {not_null:10} {default:15}")
    
    print("\n📊 وضعیت ستون‌های ویژه:")
    if has_image:
        print("   ✅ ستون 'image' وجود دارد ✓")
    else:
        print("   ❌ ستون 'image' وجود ندارد ✗")
    
    # آمار رویدادها
    cursor.execute("SELECT COUNT(*) FROM events")
    events_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
    active_events = cursor.fetchone()[0]
    
    print(f"\n📊 آمار رویدادها:")
    print(f"   📅 کل رویدادها: {events_count}")
    print(f"   ✅ رویدادهای فعال: {active_events}")
    print(f"   ❌ رویدادهای غیرفعال: {events_count - active_events}")
    
else:
    print("❌ جدول events وجود ندارد!")

# ============================================
# 3. بررسی جدول registrations
# ============================================
print("\n" + "=" * 60)
print("📋 جدول registrations:")
print("-" * 80)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='registrations'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(registrations)")
    columns = cursor.fetchall()
    
    print(f"{'وضعیت':8} {'نام ستون':25} {'نوع':15} {'NOT NULL':10} {'پیش‌فرض':15}")
    print("-" * 80)
    
    has_attended = False
    for col in columns:
        col_name = col[1]
        if col_name == 'attended':
            has_attended = True
            status = "✓"
        elif col_name == 'attendance_confirmed':
            status = "⚠️"
        else:
            status = "✅"
        not_null = "بله" if col[3] == 1 else "خیر"
        default = col[4] if col[4] else "-"
        print(f"{status:8} {col_name:25} {col[2]:15} {not_null:10} {default:15}")
    
    print("\n📊 وضعیت ستون‌های ویژه:")
    if has_attended:
        print("   ✅ ستون 'attended' وجود دارد ✓")
    else:
        print("   ❌ ستون 'attended' وجود ندارد ✗")
    
    # آمار ثبت‌نام‌ها
    cursor.execute("SELECT COUNT(*) FROM registrations")
    reg_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM registrations WHERE attended = 1")
    attended_count = cursor.fetchone()[0] if has_attended else 0
    
    print(f"\n📊 آمار ثبت‌نام‌ها:")
    print(f"   📝 کل ثبت‌نام‌ها: {reg_count}")
    if has_attended:
        print(f"   ✅ حضور یافته: {attended_count}")
        print(f"   ⏳ در انتظار: {reg_count - attended_count}")
    
else:
    print("❌ جدول registrations وجود ندارد!")

# ============================================
# 4. بررسی سایر جداول
# ============================================
print("\n" + "=" * 60)
print("📋 سایر جداول:")
print("-" * 60)

other_tables = [
    ('notifications', 'اعلان‌ها'),
    ('ai_questions', 'سوالات هوش مصنوعی'),
    ('quran_verses', 'آیات قرآن'),
    ('password_reset_tokens', 'توکن‌های بازنشانی رمز')
]

for table, persian_name in other_tables:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if cursor.fetchone():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   ✅ {table:25} → {persian_name}: {count} رکورد")
        
        # نمایش چند ستون اول هر جدول
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        col_names = [col[1] for col in cols[:5]]
        print(f"      └─ ستون‌ها: {', '.join(col_names)}...")
    else:
        print(f"   ❌ {table:25} → {persian_name}: وجود ندارد")

# ============================================
# 5. خلاصه و جمع‌بندی
# ============================================
print("\n" + "=" * 60)
print("📊 خلاصه وضعیت دیتابیس:")
print("-" * 60)

issues = []

# بررسی users
if 'users' in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    print("✅ جدول users: موجود")
    # بررسی فیلدهای جدید
    for field in ['landline', 'gender', 'entrance_year', 'degree', 'field_of_study', 'province', 'city']:
        if field in found_columns:
            print(f"   ✅ {field}: موجود")
        else:
            print(f"   ❌ {field}: وجود ندارد")
            issues.append(f"فیلد {field} در جدول users وجود ندارد")
else:
    print("❌ جدول users: وجود ندارد")
    issues.append("جدول users وجود ندارد")

# بررسی events
if 'events' in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    if has_image:
        print("✅ جدول events: موجود (ستون image: ✅)")
    else:
        print("⚠️ جدول events: موجود (ستون image: ❌)")
        issues.append("ستون image در جدول events وجود ندارد")
else:
    print("❌ جدول events: وجود ندارد")
    issues.append("جدول events وجود ندارد")

# بررسی registrations
if 'registrations' in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    if has_attended:
        print("✅ جدول registrations: موجود (ستون attended: ✅)")
    else:
        print("⚠️ جدول registrations: موجود (ستون attended: ❌)")
        issues.append("ستون attended در جدول registrations وجود ندارد")
else:
    print("❌ جدول registrations: وجود ندارد")
    issues.append("جدول registrations وجود ندارد")

print("\n" + "=" * 60)
if issues:
    print("⚠️  مشکلات پیدا شده:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n🔧 راه‌حل:")
    print("   1. برای رفع مشکل ستون image در events:")
    print("      python fix_database_events.py")
    print("   2. برای رفع مشکل ستون attended در registrations:")
    print("      python fix_database_registrations.py")
    print("   3. برای اضافه کردن فیلدهای جدید به users:")
    print("      python fix_database_new_fields.py")
    print("   4. برای ریست کامل دیتابیس:")
    print("      python reset_db_complete.py")
else:
    print("✅ ✅ ✅ دیتابیس کامل و بدون مشکل است! ✅ ✅ ✅")
    print("   تمام جداول و ستون‌ها به درستی وجود دارند.")

print("=" * 60)

conn.close()