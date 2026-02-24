import sqlite3

# ====== اتصال به دیتابیس SQLite ======
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# ====== ایجاد جدول کاربران ======
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT ''
)
""")
conn.commit()

# ====== تابع ثبت نام کاربر ======
def register_user(username, first_name='', last_name=''):
    cursor.execute("""
        INSERT INTO users (username, first_name, last_name)
        VALUES (?, ?, ?)
    """, (username, first_name, last_name))
    conn.commit()

    # پیام خوش‌آمدگویی
    if first_name or last_name:
        display_name = f"{first_name} {last_name}"
    else:
        display_name = username

    print(f"\nبه سِراج خوش آمدید!\nکاربر گرامی {display_name}، ثبت‌نام شما با موفقیت انجام شد.\n")


# ====== تابع نمایش همه کاربران ======
def show_users():
    cursor.execute("SELECT username, first_name, last_name FROM users")
    rows = cursor.fetchall()
    if not rows:
        print("هیچ کاربری ثبت نشده است.")
        return
    print("===== لیست کاربران =====")
    for row in rows:
        username, first_name, last_name = row
        first_name = first_name or ''
        last_name = last_name or ''
        if first_name or last_name:
            display_name = f"{first_name} {last_name}"
        else:
            display_name = username
        print(f"Username: {username} | Name: {display_name}")
    print("=========================\n")


# ====== مثال استفاده ======
if __name__ == "__main__":
    # ثبت چند کاربر
    register_user("mahdi")  # فقط username
    register_user("ali", "Ali", "Ahmadi")  # username + نام + نام خانوادگی

    # نمایش همه کاربران
    show_users()

# ====== بستن اتصال ======
conn.close()
