# check_db_final.py
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
# تابع بررسی جدول و ستون‌ها
# ============================================
def check_table(table_name, expected_columns=None, special_columns=None):
    print(f"\n📋 جدول {table_name}:")
    print("-" * 80)
    
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if not cursor.fetchone():
        print(f"❌ جدول {table_name} وجود ندارد!")
        return None, None
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print(f"{'وضعیت':8} {'نام ستون':25} {'نوع':15} {'NOT NULL':10} {'پیش‌فرض':15}")
    print("-" * 80)
    
    found_columns = []
    special_status = {}
    
    for col in columns:
        col_name = col[1]
        found_columns.append(col_name)
        
        # ستون ویژه
        if special_columns and col_name in special_columns:
            status = special_columns[col_name]
            special_status[col_name] = True
        else:
            status = "✅"
        
        not_null = "بله" if col[3] == 1 else "خیر"
        default = col[4] if col[4] else "-"
        print(f"{status:8} {col_name:25} {col[2]:15} {not_null:10} {default:15}")
    
    # بررسی ستون‌های مورد انتظار
    if expected_columns:
        print("\n📊 وضعیت ستون‌های مورد نیاز:")
        for col in expected_columns:
            if col in found_columns:
                print(f"   ✅ {col:25} موجود است")
            else:
                print(f"   ❌ {col:25} وجود ندارد!")
    
    return columns, found_columns

# ============================================
# بررسی جدول users
# ============================================
users_expected = [
    'id', 'username', 'email', 'password_hash',
    'first_name', 'last_name', 'phone', 'landline', 'gender',
    'student_id', 'entrance_year', 'degree', 'field_of_study',
    'province', 'city', 'university', 'faculty',
    'role', 'is_active', 'created_at', 'last_login'
]
users_special = {
    'landline': "🆕", 'gender': "🆕", 'entrance_year': "🆕", 'degree': "🆕", 
    'field_of_study': "🆕", 'province': "🆕", 'city': "🆕",
    'first_name': "🔴", 'last_name': "🔴", 'phone': "🔴", 'student_id': "🔴", 'university': "🔴", 'faculty': "🔴"
}
_, user_columns = check_table("users", users_expected, users_special)

# آمار کاربران
cursor.execute("SELECT COUNT(*) FROM users")
users_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
active_users = cursor.fetchone()[0]
print(f"\n📊 آمار کاربران:")
print(f"   👤 کل کاربران: {users_count}")
print(f"   ✅ کاربران فعال: {active_users}")
print(f"   ❌ کاربران غیرفعال: {users_count - active_users}")

# ============================================
# بررسی جدول events
# ============================================
events_expected = ['id', 'title', 'description', 'event_type', 'start_date', 'end_date', 'location',
                   'capacity', 'current_participants', 'image', 'is_active', 'created_by', 'created_at']
events_special = {'image': "🖼️"}
_, event_columns = check_table("events", events_expected, events_special)

# آمار رویدادها
cursor.execute("SELECT COUNT(*) FROM events")
events_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM events WHERE is_active = 1")
active_events = cursor.fetchone()[0]
print(f"\n📊 آمار رویدادها:")
print(f"   📅 کل رویدادها: {events_count}")
print(f"   ✅ رویدادهای فعال: {active_events}")
print(f"   ❌ رویدادهای غیرفعال: {events_count - active_events}")

# ============================================
# بررسی جدول registrations
# ============================================
regs_expected = ['id', 'user_id', 'event_id', 'registration_date', 'status', 'attended']
regs_special = {'attended': "✓"}
_, reg_columns = check_table("registrations", regs_expected, regs_special)

# آمار ثبت‌نام‌ها
cursor.execute("SELECT COUNT(*) FROM registrations")
reg_count = cursor.fetchone()[0]
attended_count = cursor.execute("SELECT COUNT(*) FROM registrations WHERE attended = 1").fetchone()[0] if 'attended' in reg_columns else 0
print(f"\n📊 آمار ثبت‌نام‌ها:")
print(f"   📝 کل ثبت‌نام‌ها: {reg_count}")
if 'attended' in reg_columns:
    print(f"   ✅ حضور یافته: {attended_count}")
    print(f"   ⏳ در انتظار: {reg_count - attended_count}")

# ============================================
# بررسی سایر جداول
# ============================================
other_tables = [
    ('notifications', 'اعلان‌ها'),
    ('ai_questions', 'سوالات هوش مصنوعی'),
    ('quran_verses', 'آیات قرآن'),
    ('password_reset_tokens', 'توکن‌های بازنشانی رمز'),
    ('quran_circles', 'حلقه‌های تلاوت'),
    ('circle_members', 'اعضای حلقه'),
    ('circle_sessions', 'جلسات حلقه'),
    ('session_attendances', 'حضور و غیاب'),
    ('circle_files', 'فایل‌های حلقه'),
    ('session_files', 'فایل‌های جلسات'),
    ('user_fcm_tokens', 'توکن‌های نوتیفیکیشن'),
    ('verification_logs', 'لاگ تأیید کاربران')
]

print("\n" + "="*60)
print("📋 سایر جداول:")
print("-"*60)
for table, persian_name in other_tables:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if cursor.fetchone():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   ✅ {table:25} → {persian_name}: {count} رکورد")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        col_names = [col[1] for col in cols[:5]]
        print(f"      └─ ستون‌ها: {', '.join(col_names)}...")
    else:
        print(f"   ❌ {table:25} → {persian_name}: وجود ندارد")

# ============================================
# جمع‌بندی و بررسی مشکلات
# ============================================
print("\n" + "="*60)
print("📊 جمع‌بندی وضعیت دیتابیس:")
issues = []

# users
for field in ['landline', 'gender', 'entrance_year', 'degree', 'field_of_study', 'province', 'city']:
    if user_columns and field not in user_columns:
        issues.append(f"فیلد {field} در جدول users وجود ندارد")

# events
if event_columns and 'image' not in event_columns:
    issues.append("ستون image در جدول events وجود ندارد")

# registrations
if reg_columns and 'attended' not in reg_columns:
    issues.append("ستون attended در جدول registrations وجود ندارد")

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

print("="*60)
conn.close()