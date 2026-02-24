import sqlite3

# مسیر صحیح دیتابیس
db_path = r"F:\seraj\instance\seraj.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# بررسی اینکه جدول users وجود دارد
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [table[0] for table in cursor.fetchall()]
print("Tables:", tables)

if "users" in tables:
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]

    if "fcm_token" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN fcm_token TEXT")
        print("ستون fcm_token اضافه شد ✅")
    else:
        print("ستون قبلاً وجود دارد ⚠️")
else:
    print("جدول users پیدا نشد ❌")

conn.commit()
conn.close()