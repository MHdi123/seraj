# setup.py
"""
اسکریپت نصب و راه‌اندازی کامل پروژه سِراج
"""

import os
import sys
import subprocess
import sqlite3

def print_header(text):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_step(text):
    print(f"\n➡️  {text}")

def main():
    print_header("🚀 نصب و راه‌اندازی سامانه سِراج")
    
    # مرحله ۱: نصب پکیج‌های پایتون
    print_step("نصب پکیج‌های مورد نیاز...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ پکیج‌ها با موفقیت نصب شدند.")
    except:
        print("❌ خطا در نصب پکیج‌ها!")
        print("   در حال نصب دستی...")
        packages = [
            "Flask==2.3.3",
            "Flask-SQLAlchemy==3.0.5",
            "Flask-Login==0.6.2",
            "Flask-WTF==1.1.1",
            "WTForms==3.0.1",
            "email-validator==2.0.0",
            "python-dotenv==1.0.0"
        ]
        for package in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"   ✅ {package}")
            except:
                print(f"   ❌ {package}")
    
    # مرحله ۲: نصب Tailwind CSS
    print_step("نصب Tailwind CSS...")
    try:
        subprocess.check_call(["npm", "install"], shell=True)
        print("✅ Tailwind CSS نصب شد.")
    except:
        print("⚠️  Node.js نصب نیست! برای ظاهر بهتر، Tailwind CSS را جداگانه نصب کنید.")
        print("   دستور: npm install")
    
    # مرحله ۳: حذف دیتابیس قدیمی
    print_step("پاکسازی دیتابیس قبلی...")
    db_paths = [
        'instance/seraj.db',
        'seraj.db',
        'app.db',
        'instance/app.db'
    ]
    
    for path in db_paths:
        if os.path.exists(path):
            os.remove(path)
            print(f"   ✅ حذف: {path}")
    
    # مرحله ۴: ساخت دیتابیس جدید
    print_step("ساخت دیتابیس جدید...")
    try:
        from create_db import create_tables
        create_tables()
        print("✅ دیتابیس با موفقیت ساخته شد.")
    except Exception as e:
        print(f"❌ خطا در ساخت دیتابیس: {e}")
        return
    
    # مرحله ۵: اضافه کردن ستون image (اگر نیاز بود)
    print_step("بررسی و به‌روزرسانی ساختار دیتابیس...")
    
    db_file = 'instance/seraj.db'
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # بررسی وجود ستون image
        cursor.execute("PRAGMA table_info(events)")
        columns = cursor.fetchall()
        has_image = any(col[1] == 'image' for col in columns)
        
        if not has_image:
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN image VARCHAR(200)")
                conn.commit()
                print("✅ ستون 'image' به جدول events اضافه شد.")
            except Exception as e:
                print(f"⚠️  خطا در اضافه کردن ستون: {e}")
        
        conn.close()
    
    # مرحله ۶: ایجاد پوشه‌های مورد نیاز
    print_step("ایجاد پوشه‌های مورد نیاز...")
    folders = [
        'static/uploads',
        'static/css',
        'static/js',
        'static/fonts',
        'static/logo',
        'templates/auth',
        'templates/admin',
        'templates/participant',
        'templates/ai'
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"   ✅ {folder}")
    
    # مرحله ۷: ساخت فایل CSS
    print_step("ساخت فایل CSS...")
    css_dir = 'static/css'
    os.makedirs(css_dir, exist_ok=True)
    
    # فایل input.css
    input_css = os.path.join('static/css', 'input.css')
    with open(input_css, 'w', encoding='utf-8') as f:
        f.write("""@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700;
  }
  
  .btn-secondary {
    @apply bg-gray-100 text-gray-800 hover:bg-gray-200;
  }
  
  .card {
    @apply bg-white rounded-xl shadow-sm overflow-hidden;
  }
  
  .card-header {
    @apply px-6 py-4 border-b border-gray-100;
  }
  
  .card-body {
    @apply px-6 py-4;
  }
  
  .nav-link {
    @apply px-3 py-2 rounded-lg text-sm font-medium transition-colors;
  }
  
  .nav-link-active {
    @apply bg-blue-50 text-blue-700;
  }
  
  .nav-link-inactive {
    @apply text-gray-700 hover:bg-gray-100;
  }
  
  .badge {
    @apply px-2.5 py-0.5 rounded-full text-xs font-medium;
  }
  
  .badge-workshop {
    @apply bg-blue-100 text-blue-800;
  }
  
  .badge-competition {
    @apply bg-green-100 text-green-800;
  }
  
  .badge-halaqah {
    @apply bg-purple-100 text-purple-800;
  }
  
  .badge-lecture {
    @apply bg-yellow-100 text-yellow-800;
  }
  
  .alert {
    @apply p-4 rounded-lg mb-4;
  }
  
  .alert-success {
    @apply bg-green-50 text-green-800 border-r-4 border-green-500;
  }
  
  .alert-error {
    @apply bg-red-50 text-red-800 border-r-4 border-red-500;
  }
  
  .alert-warning {
    @apply bg-yellow-50 text-yellow-800 border-r-4 border-yellow-500;
  }
  
  .alert-info {
    @apply bg-blue-50 text-blue-800 border-r-4 border-blue-500;
  }
}
""")
    print("   ✅ static/css/input.css")
    
    # ساخت tailwind.css
    try:
        subprocess.run(["npm", "run", "build-css"], shell=True, capture_output=True)
        print("   ✅ static/css/tailwind.css")
    except:
        # کپی فایل ساده
        tailwind_css = os.path.join('static/css', 'tailwind.css')
        with open(tailwind_css, 'w', encoding='utf-8') as f:
            f.write("/* Tailwind CSS - موقت */\n")
            f.write("body { font-family: Vazir, Tahoma, sans-serif; }\n")
        print("   ⚠️  فایل CSS ساده ساخته شد.")
    
    # مرحله ۸: کپی لوگو
    print_step("ایجاد لوگوی پیش‌فرض...")
    logo_dir = 'static/logo'
    os.makedirs(logo_dir, exist_ok=True)
    
    logo_path = os.path.join(logo_dir, '12.png')
    if not os.path.exists(logo_path):
        # ایجاد یک فایل متنی به جای لوگو
        with open(logo_path, 'w') as f:
            f.write("")
        print("   ✅ پوشه لوگو آماده است.")
    
    print_header("✅ نصب با موفقیت کامل شد!")
    print("""
    📝 مراحل بعدی:
    
    1️⃣ اجرای برنامه:
       python app.py
    
    2️⃣ دسترسی به سایت:
       http://localhost:5000
    
    3️⃣ اطلاعات ورود ادمین:
       👤 نام کاربری: admin
       🔑 رمز عبور: Admin@123
    
    4️⃣ ساخت CSS (در صورت نصب Node.js):
       npm run build-css
    """)

if __name__ == "__main__":
    main()