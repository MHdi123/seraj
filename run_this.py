# check_endpoints.py
import sys
import os

# اضافه کردن مسیر پروژه
sys.path.insert(0, 'F:/seraj')

try:
    # سعی در import کردن اپلیکیشن
    from app import app
except ImportError:
    try:
        from main import app
    except ImportError:
        try:
            from run import app
        except ImportError:
            print("لطفاً نام فایل اصلی برنامه خود را وارد کنید:")
            print("فایل‌های موجود در پوشه:")
            for f in os.listdir('F:/seraj'):
                if f.endswith('.py'):
                    print(f"  - {f}")
            exit()

with app.app_context():
    print("\n" + "="*60)
    print("لیست تمام endpointهای ثبت شده:")
    print("="*60)
    
    found_index = False
    
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
        # نمایش endpointهای مهم
        if rule.rule == '/' or 'index' in rule.endpoint.lower() or 'home' in rule.endpoint.lower():
            print(f"\n📍 مسیر: {rule.rule}")
            print(f"   نام endpoint: {rule.endpoint}")
            print(f"   متدها: {[m for m in rule.methods if m != 'HEAD']}")
            found_index = True
    
    if not found_index:
        print("\n⚠️ هیچ endpoint با نام index یا مسیر '/' پیدا نشد!")
        print("\nنمایش همه endpointها:")
        for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
            if not rule.rule.startswith('/static'):
                print(f"  {rule.rule} → {rule.endpoint}")