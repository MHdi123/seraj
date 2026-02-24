# init_db.py
import os
import sys
from app import app, db
from models import User, UserRole, Event, EventType, QuranVerse
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def init_database():
    """ایجاد دیتابیس و جداول از صفر"""
    
    print("🚀 شروع فرآیند ایجاد دیتابیس...")
    print("=" * 50)
    
    with app.app_context():
        
        # پاک کردن دیتابیس قدیمی
        db_path = 'instance/seraj.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ دیتابیس قدیمی حذف شد: {db_path}")
        
        # ایجاد پوشه instance اگر وجود نداره
        os.makedirs('instance', exist_ok=True)
        
        # ایجاد همه جداول
        print("📦 در حال ایجاد جداول...")
        db.create_all()
        print("✅ همه جداول با موفقیت ایجاد شدند!")
        
        # ========== ایجاد کاربر ادمین ==========
        print("\n👤 در حال ایجاد کاربر ادمین...")
        admin = User(
            username='admin',
            email='admin@seraj.ir',
            password_hash=generate_password_hash('Admin@123'),
            first_name='مدیر',
            last_name='سیستم',
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        print(f"   ✅ کاربر ادمین ایجاد شد:")
        print(f"      👤 نام کاربری: admin")
        print(f"      🔑 رمز عبور: Admin@123")
        
        # ========== ایجاد رویدادهای نمونه ==========
        print("\n📅 در حال ایجاد رویدادهای نمونه...")
        
        events_data = [
            {
                'title': 'مسابقه بزرگ قرآن کریم',
                'description': 'مسابقه قرآن کریم ویژه دانشجویان دانشگاه‌های تهران\n\nبخش‌های مسابقه:\n- حفظ قرآن\n- قرائت تحقیق\n- مفاهیم قرآن\n\nجوایز:\nنفر اول: ۵,۰۰۰,۰۰۰ تومان\nنفر دوم: ۳,۰۰۰,۰۰۰ تومان\nنفر سوم: ۲,۰۰۰,۰۰۰ تومان',
                'event_type': EventType.COMPETITION,
                'start_date': datetime.now() + timedelta(days=7),
                'end_date': datetime.now() + timedelta(days=7, hours=5),
                'location': 'دانشگاه تهران، دانشکده الهیات، سالن شهید مطهری',
                'capacity': 100,
                'current_participants': 34,
                'is_active': True
            },
            {
                'title': 'کارگاه آموزشی تجوید مقدماتی',
                'description': 'آموزش قواعد تجوید قرآن کریم از سطح مقدماتی\n\nسرفصل‌ها:\n- مخارج حروف\n- صفات حروف\n- قواعد نون ساکنه\n- قواعد مد\n\nمدرس: استاد احمدی',
                'event_type': EventType.WORKSHOP,
                'start_date': datetime.now() + timedelta(days=5, hours=14),
                'end_date': datetime.now() + timedelta(days=5, hours=18),
                'location': 'دانشگاه صنعتی شریف، ساختمان کلاس‌ها، کلاس ۳۰۱',
                'capacity': 40,
                'current_participants': 28,
                'is_active': True
            },
            {
                'title': 'حلقه تلاوت و تدبر در قرآن',
                'description': 'جلسات هفتگی تلاوت و تدبر در قرآن کریم\n\nبرنامه:\n- تلاوت آیات منتخب\n- ترجمه و مفاهیم\n- بحث و گفتگو\n- پرسش و پاسخ\n\nمختص دانشجویان علاقه‌مند به انس با قرآن',
                'event_type': EventType.HALAQAH,
                'start_date': datetime.now() + timedelta(days=3, hours=16),
                'end_date': datetime.now() + timedelta(days=3, hours=18),
                'location': 'مسجد دانشگاه تربیت مدرس',
                'capacity': 30,
                'current_participants': 18,
                'is_active': True
            },
            {
                'title': 'سخنرانی: قرآن و سبک زندگی',
                'description': 'بررسی نقش قرآن در سبک زندگی اسلامی\n\nسخنران: حجت‌الاسلام دکتر رضایی\n\nموضوعات:\n- قرآن و خانواده\n- قرآن و اخلاق اجتماعی\n- قرآن و سلامت روان\n- قرآن و موفقیت',
                'event_type': EventType.LECTURE,
                'start_date': datetime.now() + timedelta(days=10, hours=10),
                'end_date': datetime.now() + timedelta(days=10, hours=12),
                'location': 'دانشگاه علامه طباطبائی، سالن آمفی‌تئاتر',
                'capacity': 200,
                'current_participants': 87,
                'is_active': True
            },
            {
                'title': 'کارگاه حفظ قرآن (روش‌های نوین)',
                'description': 'آموزش روش‌های نوین و تخصصی حفظ قرآن کریم\n\nسرفصل‌ها:\n- تکنیک‌های تقویت حافظه\n- روش‌های مرور مؤثر\n- برنامه‌ریزی روزانه حفظ\n- مدیریت زمان در حفظ\n\nمدرس: استاد کریمی',
                'event_type': EventType.WORKSHOP,
                'start_date': datetime.now() + timedelta(days=12, hours=9),
                'end_date': datetime.now() + timedelta(days=12, hours=13),
                'location': 'دانشگاه شهید بهشتی، دانشکده علوم قرآنی',
                'capacity': 35,
                'current_participants': 22,
                'is_active': True
            },
            {
                'title': 'مسابقه حفظ سوره یس',
                'description': 'مسابقه حفظ سوره مبارکه یس ویژه دانشجویان\n\nشرایط:\n- حفظ کامل سوره یس\n- تلاوت صحیح و روان\n- شرکت برای تمام دانشجویان آزاد\n\nجوایز نقدی و فرهنگی',
                'event_type': EventType.COMPETITION,
                'start_date': datetime.now() + timedelta(days=15, hours=15),
                'end_date': datetime.now() + timedelta(days=15, hours=18),
                'location': 'دانشگاه الزهرا، تالار حضرت مریم(س)',
                'capacity': 60,
                'current_participants': 41,
                'is_active': True
            }
        ]
        
        for event_data in events_data:
            event = Event(
                **event_data,
                created_by=admin.id,
                created_at=datetime.utcnow()
            )
            db.session.add(event)
        
        db.session.commit()
        print(f"   ✅ {len(events_data)} رویداد نمونه ایجاد شد!")
        
        # ========== ایجاد آیات قرآن ==========
        print("\n📖 در حال ایجاد آیات قرآن...")
        
        verses_data = [
            {
                'verse_arabic': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
                'verse_persian': 'به نام خداوند بخشنده مهربان',
                'surah_name': 'الفاتحة',
                'verse_number': 1,
                'title': 'بسم الله',
                'is_active': True
            },
            {
                'verse_arabic': 'الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ',
                'verse_persian': 'ستایش مخصوص خداوندی است که پروردگار جهانیان است',
                'surah_name': 'الفاتحة',
                'verse_number': 2,
                'title': 'حمد',
                'is_active': True
            },
            {
                'verse_arabic': 'الرَّحْمَٰنِ الرَّحِيمِ',
                'verse_persian': 'بخشنده مهربان',
                'surah_name': 'الفاتحة',
                'verse_number': 3,
                'title': 'رحمان و رحیم',
                'is_active': True
            },
            {
                'verse_arabic': 'مَالِكِ يَوْمِ الدِّينِ',
                'verse_persian': 'مالک روز جزا',
                'surah_name': 'الفاتحة',
                'verse_number': 4,
                'title': 'مالک یوم الدین',
                'is_active': True
            },
            {
                'verse_arabic': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ',
                'verse_persian': 'تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم',
                'surah_name': 'الفاتحة',
                'verse_number': 5,
                'title': 'عبادت و استعانت',
                'is_active': True
            },
            {
                'verse_arabic': 'اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ',
                'verse_persian': 'ما را به راه راست هدایت کن',
                'surah_name': 'الفاتحة',
                'verse_number': 6,
                'title': 'هدایت به صراط مستقیم',
                'is_active': True
            },
            {
                'verse_arabic': 'صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ',
                'verse_persian': 'راه کسانی که به آنها نعمت دادی، نه راه مغضوبان و نه گمراهان',
                'surah_name': 'الفاتحة',
                'verse_number': 7,
                'title': 'صراط مستقیم',
                'is_active': True
            },
            {
                'verse_arabic': 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ',
                'verse_persian': 'خداوند، که معبودی جز او نیست، زنده و برپا دارنده است',
                'surah_name': 'البقرة',
                'verse_number': 255,
                'title': 'آیه الکرسی',
                'is_active': True
            },
            {
                'verse_arabic': 'لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا',
                'verse_persian': 'خداوند هیچ کس را جز به اندازه توانش تکلیف نمی‌کند',
                'surah_name': 'البقرة',
                'verse_number': 286,
                'title': 'تکلیف به قدر وسع',
                'is_active': True
            },
            {
                'verse_arabic': 'فَإِنَّ مَعَ الْعُسْرِ يُسْرًا',
                'verse_persian': 'پس بی‌گمان با دشواری، آسانی است',
                'surah_name': 'الشَّرْح',
                'verse_number': 5,
                'title': 'آسانی بعد از سختی',
                'is_active': True
            },
            {
                'verse_arabic': 'إِنَّ هَٰذَا الْقُرْآنَ يَهْدِي لِلَّتِي هِيَ أَقْوَمُ',
                'verse_persian': 'همانا این قرآن به استوارترین راه هدایت می‌کند',
                'surah_name': 'الإسراء',
                'verse_number': 9,
                'title': 'هدایتگری قرآن',
                'is_active': True
            },
            {
                'verse_arabic': 'وَنُنَزِّلُ مِنَ الْقُرْآنِ مَا هُوَ شِفَاءٌ وَرَحْمَةٌ لِّلْمُؤْمِنِينَ',
                'verse_persian': 'و از قرآن آنچه شفا و رحمت برای مؤمنان است نازل می‌کنیم',
                'surah_name': 'الإسراء',
                'verse_number': 82,
                'title': 'قرآن شفاست',
                'is_active': True
            }
        ]
        
        for verse_data in verses_data:
            verse = QuranVerse(**verse_data)
            db.session.add(verse)
        
        db.session.commit()
        print(f"   ✅ {len(verses_data)} آیه قرآن ایجاد شد!")
        
        # ========== آمار نهایی ==========
        print("\n" + "=" * 50)
        print("📊 آمار نهایی دیتابیس:")
        print("=" * 50)
        
        users_count = User.query.count()
        events_count = Event.query.count()
        verses_count = QuranVerse.query.count()
        
        print(f"👤 کاربران: {users_count}")
        print(f"📅 رویدادها: {events_count}")
        print(f"📖 آیات قرآن: {verses_count}")
        print(f"✅ وضعیت: فعال")
        
        print("\n" + "=" * 50)
        print("🎉 دیتابیس با موفقیت ایجاد شد!")
        print("=" * 50)
        print("\n🚀 برای اجرای برنامه:")
        print("   python app.py")
        print("\n🌐 آدرس برنامه:")
        print("   http://localhost:5000")
        print("\n👤 اطلاعات ورود ادمین:")
        print("   نام کاربری: admin")
        print("   رمز عبور: Admin@123")

if __name__ == '__main__':
    init_database()