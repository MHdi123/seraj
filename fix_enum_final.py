# fix_enum_final.py
from app import app, db
from models import User, UserType
from sqlalchemy import text

print("=" * 60)
print("🔄 رفع نهایی مشکل Enum")
print("=" * 60)

with app.app_context():
    # 1. اول ببینیم چه مقادیری در دیتابیس هست
    result = db.session.execute(text("SELECT id, username, user_type FROM users"))
    users = result.fetchall()
    
    print("\n📊 مقادیر فعلی در دیتابیس:")
    for user in users:
        print(f"   ID: {user[0]}, {user[1]}: user_type='{user[2]}'")
    
    # 2. اصلاح مقادیر با SQL مستقیم
    print("\n🔄 در حال اصلاح مقادیر...")
    
    # تبدیل همه مقادیر به lowercase
    db.session.execute(text("UPDATE users SET user_type = LOWER(user_type)"))
    
    # اطمینان از مقادیر صحیح
    db.session.execute(text("UPDATE users SET user_type = 'student' WHERE user_type = 'student'"))
    db.session.execute(text("UPDATE users SET user_type = 'professor' WHERE user_type = 'professor'"))
    db.session.execute(text("UPDATE users SET user_type = 'staff' WHERE user_type = 'staff'"))
    
    db.session.commit()
    
    # 3. حالا با استفاده از ORM، کاربران را واکشی کنیم تا ببینیم مشکل حل شده؟
    print("\n📊 واکشی با ORM:")
    all_users = User.query.all()
    for user in all_users:
        print(f"   ID: {user.id}, {user.username}: user_type={user.user_type}, display={user.get_user_type_display()}")
    
    # 4. تست کاربر ادمین
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"\n✅ کاربر ادمین: {admin.username}")
        print(f"   user_type: {admin.user_type}")
        print(f"   نمایش: {admin.get_user_type_display()}")
    else:
        print("\n⚠️ کاربر ادمین پیدا نشد!")

print("\n" + "=" * 60)
print("✅ عملیات با موفقیت انجام شد!")
print("=" * 60)