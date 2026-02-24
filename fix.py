import sqlite3
import os
import shutil
from datetime import datetime

db_path = 'instance/seraj.db'

if not os.path.exists(db_path):
    print(f'❌ فایل پیدا نشد: {db_path}')
    exit(1)

# پشتیبان از کل دیتابیس
backup_path = f'instance/backup_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
shutil.copy2(db_path, backup_path)
print(f'✅ پشتیبان کامل: {backup_path}')

conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # اول ببینیم اصلاً کاربری وجود داره یا نه
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not c.fetchone():
        print("❌ جدول users وجود نداره!")
        exit(1)
    
    c.execute("SELECT COUNT(*) FROM users")
    count_before = c.fetchone()[0]
    print(f'📊 تعداد کاربران قبل از عملیات: {count_before}')
    
    if count_before == 0:
        print("⚠️  جدول users خالیه! احتمالاً مشکل جای دیگه‌ست.")
        
        # نمایش ساختار جدول
        c.execute("PRAGMA table_info(users)")
        columns = c.fetchall()
        print("\n📋 ساختار فعلی جدول users:")
        for col in columns:
            print(f"   - {col[1]}: {col[2]} (NULL: {col[3]}, PK: {col[5]})")
        
        # اگه جدول خالیه، فقط AUTOINCREMENT رو اضافه کنیم
        print("\n🔧 در حال اصلاح ساختار جدول...")
        
        # تغییر ساختار جدول
        c.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20) NOT NULL DEFAULT '',
                landline VARCHAR(20),
                gender VARCHAR(10) NOT NULL DEFAULT 'male',
                user_type VARCHAR(20) NOT NULL DEFAULT 'student',
                is_verified BOOLEAN DEFAULT 0,
                verified_at DATETIME,
                verified_by INTEGER,
                verification_notes TEXT,
                student_id VARCHAR(50),
                entrance_year VARCHAR(4),
                degree VARCHAR(50),
                field_of_study VARCHAR(150),
                academic_rank VARCHAR(50),
                specialization VARCHAR(200),
                resume_file VARCHAR(500),
                teaching_experience INTEGER,
                professor_code VARCHAR(50),
                office_hours VARCHAR(200),
                website VARCHAR(200),
                employee_id VARCHAR(50),
                department VARCHAR(100),
                position VARCHAR(100),
                office_phone VARCHAR(20),
                responsibility TEXT,
                province VARCHAR(100) NOT NULL DEFAULT '',
                city VARCHAR(100) NOT NULL DEFAULT '',
                university VARCHAR(150) NOT NULL DEFAULT '',
                faculty VARCHAR(150) NOT NULL DEFAULT '',
                address TEXT,
                role VARCHAR(50) DEFAULT 'STUDENT',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                last_login DATETIME,
                FOREIGN KEY(verified_by) REFERENCES users(id)
            )
        """)
        
        c.execute("DROP TABLE users")
        c.execute("ALTER TABLE users_new RENAME TO users")
        conn.commit()
        
        print("✅ ساختار جدول با موفقیت اصلاح شد!")
        
    else:
        # اگه داده داشت، روش قبلی رو با اصلاحات انجام بده
        print("\n🔧 در حال انتقال داده‌ها...")
        
        # حذف جدول پشتیبان اگه وجود داره
        c.execute('DROP TABLE IF EXISTS users_backup')
        
        # پشتیبان با همه داده‌ها
        c.execute('CREATE TABLE users_backup AS SELECT * FROM users')
        
        # ساخت جدول جدید
        c.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20) NOT NULL DEFAULT '',
                landline VARCHAR(20),
                gender VARCHAR(10) NOT NULL DEFAULT 'male',
                user_type VARCHAR(20) NOT NULL DEFAULT 'student',
                is_verified BOOLEAN DEFAULT 0,
                verified_at DATETIME,
                verified_by INTEGER,
                verification_notes TEXT,
                student_id VARCHAR(50),
                entrance_year VARCHAR(4),
                degree VARCHAR(50),
                field_of_study VARCHAR(150),
                academic_rank VARCHAR(50),
                specialization VARCHAR(200),
                resume_file VARCHAR(500),
                teaching_experience INTEGER,
                professor_code VARCHAR(50),
                office_hours VARCHAR(200),
                website VARCHAR(200),
                employee_id VARCHAR(50),
                department VARCHAR(100),
                position VARCHAR(100),
                office_phone VARCHAR(20),
                responsibility TEXT,
                province VARCHAR(100) NOT NULL DEFAULT '',
                city VARCHAR(100) NOT NULL DEFAULT '',
                university VARCHAR(150) NOT NULL DEFAULT '',
                faculty VARCHAR(150) NOT NULL DEFAULT '',
                address TEXT,
                role VARCHAR(50) DEFAULT 'STUDENT',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                last_login DATETIME,
                FOREIGN KEY(verified_by) REFERENCES users(id)
            )
        ''')
        
        # انتقال داده‌ها
        c.execute('''
            INSERT INTO users_new (
                id, username, email, password_hash, first_name, last_name, 
                phone, landline, gender, user_type, is_verified, 
                verified_at, verified_by, verification_notes,
                student_id, entrance_year, degree, field_of_study, 
                academic_rank, specialization, resume_file, teaching_experience, 
                professor_code, office_hours, website,
                employee_id, department, position, office_phone, responsibility, 
                province, city, university, faculty, address, 
                role, is_active, created_at, last_login
            )
            SELECT 
                id, username, email, password_hash, first_name, last_name, 
                COALESCE(phone, ''), landline, COALESCE(gender, 'male'), 
                COALESCE(user_type, 'student'), COALESCE(is_verified, 0),
                verified_at, verified_by, verification_notes,
                student_id, entrance_year, degree, field_of_study, 
                academic_rank, specialization, resume_file, teaching_experience, 
                professor_code, office_hours, website,
                employee_id, department, position, office_phone, responsibility, 
                COALESCE(province, ''), COALESCE(city, ''), 
                COALESCE(university, ''), COALESCE(faculty, ''), address,
                COALESCE(role, 'STUDENT'), COALESCE(is_active, 1), 
                COALESCE(created_at, CURRENT_TIMESTAMP), last_login
            FROM users_backup
        ''')
        
        # جایگزینی جدول جدید
        c.execute("DROP TABLE users")
        c.execute("ALTER TABLE users_new RENAME TO users")
        c.execute("DROP TABLE users_backup")
        conn.commit()
        
        print(f"✅ {count_before} کاربر با موفقیت منتقل شدند!")
    
    # بررسی نهایی
    c.execute("SELECT COUNT(*) FROM users")
    count_after = c.fetchone()[0]
    print(f'📊 تعداد کاربران بعد از عملیات: {count_after}')
    
    # نمایش ساختار نهایی
    c.execute("PRAGMA table_info(users)")
    columns = c.fetchall()
    print("\n📋 ساختار نهایی جدول users:")
    for col in columns:
        auto = " (AUTOINCREMENT)" if col[5] == 1 and col[2] == 'INTEGER' else ""
        print(f"   - {col[1]}: {col[2]}{auto}")
    
    print("\n✨ عملیات با موفقیت انجام شد!")
    print(f"📁 پشتیبان: {backup_path}")
    
except Exception as e:
    print(f'❌ خطا: {e}')
    conn.rollback()
    print('🔄 تغییرات برگردانده شد')
    
finally:
    conn.close()