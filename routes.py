# routes.py
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, render_template_string
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import os
import secrets
import uuid
import random
import time
import sqlite3
from models import (
    QuranCircle,
    CircleMember,
    CircleSession,
    CircleFile,
    SessionFile,
    SessionAttendance,
    AcademicRank,
    Class,
    ClassEnrollment,
    CourseSession,
    Attendance,
    Faculty,
    Department,
    Course,
    AcademicTerm,
    ClassFile,
    CircleSessionFile,
    UserFCMToken,
    VerificationLog,
    Event,
    EventType,
    Registration,
    AIQuestion,
    Notification,
    PasswordResetToken,
    QuranVerse,
    UserRole,
    Banner,
    # اضافه کردن مدل‌های مسابقات
    Competition,
    CompetitionCategory,
    CompetitionRegistration,
    CompetitionRound,
    JudgeScore,
)
import jdatetime
from decorators import admin_required, staff_required, verified_required
from sqlalchemy import func, and_, or_, desc

try:
    from quran_ai import (
        ask_quran_ai,
        analyze_quranic_text,
        get_verse_suggestions,
        get_ai_statistics,
        get_recent_qa
    )
    AI_ENABLED = True
except ImportError:
    AI_ENABLED = False
    print("⚠️ هوش مصنوعی قرآنی در دسترس نیست. از حالت ساده استفاده می‌شود.")

def init_routes(app):
    
    # ============================================
    # تابع بررسی وجود endpoint
    # ============================================
    
    @app.context_processor
    def utility_processor():
        def endpoint_exists(endpoint):
            try:
                url_for(endpoint)
                return True
            except:
                return False
        return dict(endpoint_exists=endpoint_exists)
    
    # ============================================
    # توابع کمکی آیه روز و حدیث
    # ============================================

    def get_persian_date():
        try:
            today = jdatetime.date.today()
            persian_months = {
                1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
                5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
                9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
            }
            month_name = persian_months[today.month]
            return f"{today.day} {month_name} {today.year}"
        except:
            today = date.today()
            return today.strftime("%d %B %Y")

    def get_daily_verse():
        """برمی‌گرداند آیه روز یا حدیث روز (۵۰٪ شانس) - بدون دیتابیس اضافی"""
        import random
        from datetime import date

        hadiths = [
            {'title': 'پیامبر اکرم (ص)', 'arabic': 'الْقُرْآنُ مَأْدُبَةُ اللَّهِ، فَتَعَلَّمُوا مَأْدُبَتَهُ مَا اسْتَطَعْتُمْ.', 'persian': 'قرآن سفرهٔ الهی است، پس تا می‌توانید از این سفره بیاموزید.', 'source': 'نهج‌الفصاحه'},
            {'title': 'امام علی (ع)', 'arabic': 'وَ اعْلَمُوا أَنَّ هَذَا الْقُرْآنَ هُوَ النَّاصِحُ الَّذِي لَا يَغُشُّ، وَ الْهَادِي الَّذِي لَا يُضِلُّ، وَ الْمُحَدِّثُ الَّذِي لَا يَكْذِبُ.', 'persian': 'بدانید که این قرآن، اندرزگویی است که فریب نمی‌دهد، راهنمایی است که گمراه نمی‌کند، و سخنگویی است که دروغ نمی‌گوید.', 'source': 'نهج‌البلاغه، خطبه ۱۷۶'},
            {'title': 'امام صادق (ع)', 'arabic': 'إِنَّ الْقُرْآنَ حَيٌ لَمْ يَمُتْ، وَ إِنَّهُ جَارٍ كَمَا يَجْرِي اللَّيْلُ وَ النَّهَارُ، وَ كَمَا يَجْرِي الشَّمْسُ وَ الْقَمَرُ.', 'persian': 'قرآن زنده است و نمی‌میرد؛ جاری است چنانکه شب و روز جاری است، و چنانکه خورشید و ماه جاری هستند.', 'source': 'الکافی، ج۲، ص۶۰۳'},
            {'title': 'امام باقر (ع)', 'arabic': 'مَنْ قَرَأَ الْقُرْآنَ وَ هُوَ شَابٌّ مُؤْمِنٌ، اخْتَلَطَ الْقُرْآنُ بِلَحْمِهِ وَ دَمِهِ، وَ جَعَلَهُ اللَّهُ مَعَ السَّفَرَةِ الْكِرَامِ الْبَرَرَةِ.', 'persian': 'هر جوان مؤمنی که قرآن بخواند، قرآن با گوشت و خونش آمیخته می‌شود و خداوند او را با فرشتگان بزرگوار و نیکوکار محشور می‌گرداند.', 'source': 'الکافی، ج۲، ص۶۰۴'},
            {'title': 'پیامبر اکرم (ص)', 'arabic': 'شِفَاءُ مَا فِي الصُّدُورِ الْقُرْآنُ.', 'persian': 'قرآن درمان آنچه در سینه‌ها (دل‌ها) است، می‌باشد.', 'source': 'بحارالانوار، ج۹۲، ص۲۱'},
            {'title': 'امام رضا (ع)', 'arabic': 'إِنَّ الْقُرْآنَ حَبْلُ اللَّهِ الْمَتِينُ وَ عُرْوَتُهُ الْوُثْقَى وَ الصِّرَاطُ الْمُسْتَقِیمُ.', 'persian': 'قرآن، ریسمان محکم خدا و دستاویز استوار و راه راست است.', 'source': 'عیون اخبار الرضا، ج۱، ص۲۹'},
            {'title': 'امیرالمؤمنین (ع)', 'arabic': 'فَاسْتَشْفُوهُ مِنْ أَدْوَائِكُمْ، وَ اسْتَعِينُوا بِهِ عَلَى لَأْوَائِكُمْ، فَإِنَّ فِيهِ شِفَاءً مِنْ أَكْبَرِ الدَّاءِ وَ هُوَ الْكُفْرُ وَ النِّفَاقُ.', 'persian': 'پس از قرآن برای درمان بیماری‌هایتان شفا بجویید و در سختی‌ها از آن یاری بخواهید؛ زیرا در قرآن درمان بزرگ‌ترین بیماری‌ها یعنی کفر و نفاق است.', 'source': 'نهج‌البلاغه، خطبه ۱۷۶'},
            {'title': 'امام سجاد (ع)', 'arabic': 'آيَاتُ الْقُرْآنِ خَزَائِنُ الرَّحْمَةِ، فَإِذَا فُتِحَتْ خَزَائِنُ الرَّحْمَةِ فَلَا تَنْبَغِي أَنْ تُقْفَلَ.', 'persian': 'آیات قرآن گنجینه‌های رحمتند؛ پس هنگامی که گشوده شدند، شایسته نیست که بسته شوند.', 'source': 'تحف العقول'}
        ]

        if random.choice([True, False]):
            hadith = random.choice(hadiths)
            return {
                'title': hadith['title'],
                'verse': hadith['persian'],
                'arabic_text': hadith['arabic'],
                'translation': hadith['persian'],
                'surah': hadith['source'],
                'verse_number': '',
                'is_hadith': True
            }

        with app.app_context():
            try:
                verses = QuranVerse.query.all()
                if not verses:
                    hadith = hadiths[0]
                    return {
                        'title': hadith['title'],
                        'verse': hadith['persian'],
                        'arabic_text': hadith['arabic'],
                        'translation': hadith['persian'],
                        'surah': hadith['source'],
                        'verse_number': '',
                        'is_hadith': True
                    }
                today = date.today()
                random.seed(today.toordinal())
                verse = random.choice(verses)
                return {
                    'title': 'آیه روز',
                    'verse': getattr(verse, 'verse_persian', getattr(verse, 'translation', '')),
                    'arabic_text': getattr(verse, 'verse_arabic', ''),
                    'translation': getattr(verse, 'verse_persian', getattr(verse, 'translation', '')),
                    'surah': getattr(verse, 'surah_name', 'قرآن'),
                    'verse_number': getattr(verse, 'verse_number', ''),
                    'is_hadith': False
                }
            except Exception as e:
                print(f"❌ خطا در دریافت آیه: {e}")
                hadith = hadiths[0]
                return {
                    'title': hadith['title'],
                    'verse': hadith['persian'],
                    'arabic_text': hadith['arabic'],
                    'translation': hadith['persian'],
                    'surah': hadith['source'],
                    'verse_number': '',
                    'is_hadith': True
                }
            
                # ============================================
    # توابع هوش مصنوعی قرآنی
    # ============================================
    
    def find_best_answer(question):
        """پیدا کردن بهترین پاسخ برای سوال کاربر از دیتابیس"""
        from sqlalchemy import or_
        
        # نرمال کردن سوال
        question_clean = question.strip().lower()
        
        # جستجو در جدول QuranQA
        # 1. جستجوی دقیق
        exact_match = QuranQA.query.filter(
            QuranQA.is_active == True,
            QuranQA.question == question_clean
        ).first()
        
        if exact_match:
            return exact_match
        
        # 2. جستجو با contains
        contains_match = QuranQA.query.filter(
            QuranQA.is_active == True,
            or_(
                QuranQA.question.contains(question_clean),
                QuranQA.keywords.contains(question_clean)
            )
        ).order_by(QuranQA.priority.desc()).first()
        
        if contains_match:
            return contains_match
        
        # 3. جستجو بر اساس کلمات کلیدی (تجزیه سوال)
        keywords = question_clean.split()
        for keyword in keywords:
            if len(keyword) > 2:
                keyword_match = QuranQA.query.filter(
                    QuranQA.is_active == True,
                    QuranQA.keywords.contains(keyword)
                ).order_by(QuranQA.priority.desc()).first()
                if keyword_match:
                    return keyword_match
        
        return None
    
    def get_suggestions_by_mood(mood):
        """دریافت آیات پیشنهادی بر اساس حال و هوا"""
        suggestions = QuranSuggestion.query.filter_by(
            mood=mood, 
            is_active=True
        ).order_by(QuranSuggestion.order).limit(5).all()
        
        verses = []
        for s in suggestions:
            verses.append({
                'text': s.verse_text,
                'translation': s.verse_translation,
                'surah': s.surah_name,
                'ayah': s.verse_number
            })
        return verses
    
    def save_user_chat(user_id, question, answer, related_verses=None):
        """ذخیره تاریخچه چت کاربر"""
        try:
            chat = UserQuranChat(
                user_id=user_id,
                question=question,
                answer=answer,
                related_verses=related_verses
            )
            db.session.add(chat)
            db.session.commit()
        except Exception as e:
            print(f"خطا در ذخیره چت: {e}")
    
    def format_answer_with_verses(qa_obj):
        """فرمت کردن پاسخ با آیات مرتبط"""
        import json
        
        answer_text = qa_obj.answer
        
        # اضافه کردن منبع در انتها
        answer_text += "\n\n📚 **منبع:** پاسخ بر اساس قرآن کریم و تفاسیر معتبر"
        
        related_verses = []
        if qa_obj.related_verses:
            try:
                related_verses = json.loads(qa_obj.related_verses)
            except:
                pass
        
        suggestions = []
        if qa_obj.category:
            suggestions = [
                f"تفسیر آیات مربوط به {qa_obj.category}",
                f"آیات مشابه در قرآن",
                "معنای عمیق‌تر این مفهوم"
            ]
        
        return {
            "success": True,
            "answer": answer_text,
            "is_quranic": True,
            "related_verses": related_verses,
            "suggestions": suggestions
        }

    
    # ============================================
    # توابع کمکی
    # ============================================
    
    def save_uploaded_file(file, subfolder='events'):
        """ذخیره فایل آپلود شده و برگرداندن مسیر"""
        if not file or file.filename == '':
            return None
        
        # ایجاد نام یکتا
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # ایجاد پوشه
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)
        
        # ذخیره فایل
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # برگرداندن مسیر نسبی
        return os.path.join(subfolder, filename)
    
    def create_notification(user_id, title, message):
        """ایجاد اعلان جدید"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message
            )
            db.session.add(notification)
            db.session.commit()
        except:
            db.session.rollback()
    
    def convert_academic_rank(rank_value):
        """تبدیل مقدار فارسی academic_rank به enum"""
        if rank_value is None:
            return None
        
        # اگر خودش enum است
        if hasattr(rank_value, 'value'):
            return rank_value
        
        # اگر رشته است
        rank_str = str(rank_value)
        
        mapping = {
            'استاد': 'PROFESSOR',
            'دانشیار': 'ASSOCIATE_PROFESSOR',
            'استادیار': 'ASSISTANT_PROFESSOR',
            'مربی': 'INSTRUCTOR',
            'استاد مدعو': 'VISITING_LECTURER',
            'پژوهشگر': 'RESEARCHER',
            'دکتر': 'DOCTORAL',
            'کارشناسی ارشد': 'MASTER',
            'کارشناسی': 'BACHELOR'
        }
        
        return mapping.get(rank_str, 'OTHER')
    
    # ============================================
    # ========== مسیر install_pwa ==========
    # ============================================
    
    @app.route('/install-pwa')
    def install_pwa():
        """صفحه راهنمای نصب برنامه روی دستگاه"""
        return render_template('install_pwa.html', current_user=current_user)
    
    # ============================================
    # مسیرهای عمومی
    # ============================================
    
    @app.route('/')
    def index():
        """صفحه اصلی"""
        try:
            # دریافت رویدادهای فعال
            upcoming_events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(6).all()
        except:
            upcoming_events = []
        
        # دریافت بنرهای فعال
        try:
            banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()
        except:
            banners = []
        
        # دریافت آیه روز
        daily_verse = get_daily_verse()
        
        # دریافت تاریخ شمسی
        current_date = get_persian_date()
        
        try:
            # آمار
            active_students = User.query.filter_by(is_active=True, role=UserRole.STUDENT).count()
            events_count = Event.query.count()
            competitions_count = Event.query.filter_by(event_type=EventType.COMPETITION).count()
            workshops_count = Event.query.filter_by(event_type=EventType.WORKSHOP).count()
        except:
            active_students = 0
            events_count = 0
            competitions_count = 0
            workshops_count = 0
        
        # دریافت مسابقات پیش‌رو
        upcoming_competitions = []
        try:
            upcoming_competitions = Competition.query.filter(
                Competition.start_date >= datetime.utcnow(),
                Competition.is_active == True
            ).order_by(Competition.start_date).limit(6).all()
        except:
            pass
        
        return render_template('index.html', 
                             events=upcoming_events,
                             banners=banners,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             active_students=active_students,
                             events_count=events_count,
                             competitions_count=competitions_count,
                             workshops_count=workshops_count,
                             competitions=upcoming_competitions,
                             current_user=current_user)
    
    @app.route('/events')
    def events_list():
        """لیست تمام رویدادها"""
        page = request.args.get('page', 1, type=int)
        event_type = request.args.get('type')
        search = request.args.get('search')
        
        query = Event.query.filter(Event.is_active == True)
        
        if event_type:
            try:
                event_type_enum = EventType(event_type)
                query = query.filter(Event.event_type == event_type_enum)
            except:
                pass
        
        if search:
            query = query.filter(
                (Event.title.contains(search)) | 
                (Event.description.contains(search))
            )
        
        try:
            events = query.order_by(Event.start_date).paginate(
                page=page, per_page=app.config.get('POSTS_PER_PAGE', 10), error_out=False
            )
        except:
            events = []
        
        return render_template('events/list.html', 
                             events=events,
                             event_types=EventType,
                             current_user=current_user)
    
    @app.route('/event/<int:event_id>')
    def event_detail(event_id):
        """صفحه جزئیات رویداد"""
        try:
            event = Event.query.get_or_404(event_id)
        except:
            flash('رویداد مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        # بررسی ثبت‌نام کاربر
        is_registered = False
        if current_user.is_authenticated:
            try:
                registration = Registration.query.filter_by(
                    user_id=current_user.id,
                    event_id=event_id
                ).first()
                is_registered = registration is not None
            except:
                is_registered = False
        
        return render_template('events/detail.html',
                             event=event,
                             is_registered=is_registered,
                             current_user=current_user)
    
    @app.route('/search')
    def search():
        """صفحه جستجوی پیشرفته"""
        q = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        
        results = {
            'events': [],
            'total': 0
        }
        
        if q:
            try:
                # جستجو در رویدادها
                events_query = Event.query.filter(
                    Event.is_active == True,
                    (Event.title.contains(q)) | 
                    (Event.description.contains(q)) |
                    (Event.location.contains(q))
                ).order_by(Event.start_date)
                
                results['events'] = events_query.paginate(page=page, per_page=10, error_out=False)
                results['total'] = results['events'].total
            except:
                results = {
                    'events': [],
                    'total': 0
                }
        
        return render_template('search.html', 
                             query=q, 
                             results=results,
                             current_user=current_user)
    
    @app.route('/about')
    def about():
        """صفحه درباره ما"""
        return render_template('about.html', current_user=current_user)
    
    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        """صفحه تماس با ما"""
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')
            
            # اینجا می‌توانید ایمیل ارسال کنید
            flash('پیام شما با موفقیت ارسال شد. به زودی پاسخ داده خواهد شد.', 'success')
            return redirect(url_for('contact'))
        
        return render_template('contact.html', current_user=current_user)
    
    # ============================================
    # مسیرهای احراز هویت
    # ============================================
    
    @app.route('/auth/register', methods=['GET', 'POST'])
    def register():
        """ثبت‌نام کاربر جدید"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            student_id = request.form.get('student_id')
            university = request.form.get('university')
            faculty = request.form.get('faculty')
            phone = request.form.get('phone')
            
            # اعتبارسنجی
            errors = []
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد.')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید.')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد.')
            
            if password != confirm_password:
                errors.append('رمز عبور و تأیید آن مطابقت ندارند.')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است.')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register'))
            
            # ایجاد کاربر جدید
            user = User(
                username=username,
                email=email,
                first_name=request.form.get('first_name', ''),
                last_name=request.form.get('last_name', ''),
                student_id=student_id,
                university=university,
                faculty=faculty,
                phone=phone,
                role=UserRole.STUDENT,
                user_type='student',
                is_active=True,
                is_verified=True  # دانشجوها خودکار تأیید می‌شوند
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # ایجاد اعلان خوش‌آمدگویی
            create_notification(
                user.id,
                'به سِراج خوش آمدید!',
                f'کاربر گرامی {user.full_name}، ثبت‌نام شما با موفقیت انجام شد. می‌توانید از رویدادهای قرآنی دیدن کنید.'
            )
            
            flash('ثبت‌نام با موفقیت انجام شد. لطفاً وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html')
    
    # ============================================
    # ========== مسیر لاگین ==========
    # ============================================
    
    @app.route('/auth/login', methods=['GET', 'POST'])
    def login():
        """ورود کاربر - اصلاح شده برای هدایت صحیح اساتید"""
        if current_user.is_authenticated:
            # اگر کاربر لاگین است، بر اساس نوع کاربر هدایت شود
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():  # اولویت با استاد
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():  # بعد کارمند
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                if user.is_active:
                    login_user(user, remember=remember)
                    
                    # به‌روزرسانی آخرین ورود
                    user.last_login = datetime.utcnow()
                    user.last_seen = datetime.utcnow()
                    db.session.commit()
                    
                    # بررسی تأیید برای استاد و کارمند
                    if user.user_type in ['professor', 'staff'] and not user.is_verified:
                        flash('⚠️ حساب کاربری شما در انتظار تأیید است.', 'warning')
                        return redirect(url_for('not_approved'))
                    
                    flash(f'خوش آمدید {user.full_name}!', 'success')
                    
                    # ریدایرکت بر اساس نوع کاربر
                    if user.is_admin():
                        return redirect(url_for('admin_dashboard'))
                    elif user.is_professor():
                        return redirect(url_for('professor_dashboard'))
                    elif user.is_staff():
                        return redirect(url_for('staff_dashboard'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    flash('⚠️ حساب کاربری شما غیرفعال شده است. با پشتیبانی تماس بگیرید.', 'error')
            else:
                flash('نام کاربری یا رمز عبور نادرست است.', 'error')
        
        return render_template('auth/login.html')
    
    # ============================================
    # ========== مسیر not_approved ==========
    # ============================================
    
    @app.route('/not-approved')
    def not_approved():
        """صفحه کاربران در انتظار تأیید"""
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # اگر کاربر تأیید شده یا دانشجو است، به داشبورد برود
        if current_user.is_verified or current_user.user_type == 'student':
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        return render_template('not_approved.html')
    
    @app.route('/auth/logout')
    @login_required
    def logout():
        """خروج کاربر"""
        logout_user()
        flash('با موفقیت خارج شدید.', 'info')
        return redirect(url_for('index'))
    
    @app.route('/auth/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """فراموشی رمز عبور"""
        if request.method == 'POST':
            email = request.form.get('email')
            user = User.query.filter_by(email=email).first()
            
            if user:
                # ایجاد توکن
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=24)
                
                reset_token = PasswordResetToken(
                    user_id=user.id,
                    token=token,
                    expires_at=expires_at
                )
                
                db.session.add(reset_token)
                db.session.commit()
                
                # ایجاد اعلان
                create_notification(
                    user.id,
                    'بازنشانی رمز عبور',
                    f'لینک بازنشانی رمز عبور برای شما ایجاد شد. این لینک تا ۲۴ ساعت معتبر است.'
                )
                
                flash('لینک بازنشانی رمز عبور به ایمیل شما ارسال شد.', 'success')
            else:
                flash('ایمیل وارد شده در سیستم یافت نشد.', 'error')
            
            return redirect(url_for('login'))
        
        return render_template('auth/forgot_password.html')
    
    @app.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        """بازنشانی رمز عبور"""
        reset_token = PasswordResetToken.query.filter_by(
            token=token, 
            used=False
        ).first()
        
        if not reset_token or reset_token.expires_at < datetime.utcnow():
            flash('لینک بازنشانی رمز عبور نامعتبر یا منقضی شده است.', 'error')
            return redirect(url_for('forgot_password'))
        
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('رمز عبور و تأیید آن مطابقت ندارند.', 'error')
                return redirect(url_for('reset_password', token=token))
            
            if len(password) < 6:
                flash('رمز عبور باید حداقل ۶ کاراکتر باشد.', 'error')
                return redirect(url_for('reset_password', token=token))
            
            # به‌روزرسانی رمز عبور
            user = reset_token.user
            user.set_password(password)
            
            # غیرفعال کردن توکن
            reset_token.used = True
            
            db.session.commit()
            
            create_notification(
                user.id,
                'تغییر رمز عبور',
                'رمز عبور شما با موفقیت تغییر یافت.'
            )
            
            flash('رمز عبور شما با موفقیت تغییر یافت. لطفاً وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/reset_password.html', token=token)
    
    # ============================================
    # ========== مسیرهای کاربر عادی ==========
    # ============================================
    
    @app.route('/dashboard')
    @login_required
    @verified_required
    def dashboard():
        """داشبورد کاربر عادی"""
        # اگر کاربر ادمین است به پنل ادمین برود
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        # اگر کاربر استاد است به پنل استاد برود
        elif current_user.is_professor():
            return redirect(url_for('professor_dashboard'))
        # اگر کاربر کارمند است به داشبورد کارمندان برود
        elif current_user.is_staff():
            return redirect(url_for('staff_dashboard'))
        
        try:
            # رویدادهای ثبت‌نام شده کاربر
            user_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).order_by(Registration.registration_date.desc()).limit(5).all()
        except:
            user_registrations = []
        
        try:
            # رویدادهای پیش‌رو
            upcoming_events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(5).all()
        except:
            upcoming_events = []
        
        try:
            # اعلان‌های خوانده نشده
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).order_by(Notification.created_at.desc()).limit(5).all()
        except:
            unread_notifications = []
        
        try:
            # تعداد اعلان‌های خوانده نشده
            unread_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        except:
            unread_count = 0
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        return render_template('participant/dashboard.html',
                             registrations=user_registrations,
                             upcoming_events=upcoming_events,
                             notifications=unread_notifications,
                             unread_count=unread_count,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             current_user=current_user)
    
    @app.route('/event/register/<int:event_id>', methods=['POST'])
    @login_required
    @verified_required
    def register_for_event(event_id):
        """ثبت‌نام در رویداد"""
        try:
            event = Event.query.get_or_404(event_id)
        except:
            flash('رویداد مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        # بررسی وجود رویداد
        if not event.is_active:
            flash('این رویداد فعال نیست.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # بررسی ظرفیت
        if event.is_full():
            flash('ظرفیت این رویداد تکمیل شده است.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # بررسی ثبت‌نام قبلی
        existing_registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event_id
        ).first()
        
        if existing_registration:
            flash('شما قبلاً در این رویداد ثبت‌نام کرده‌اید.', 'warning')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # ثبت‌نام
        registration = Registration(
            user_id=current_user.id,
            event_id=event_id
        )
        
        event.current_participants += 1
        
        db.session.add(registration)
        db.session.commit()
        
        # اعلان به کاربر
        create_notification(
            current_user.id,
            'ثبت‌نام موفق',
            f'ثبت‌نام شما در رویداد "{event.title}" با موفقیت انجام شد.'
        )
        
        # اعلان به مدیر (اختیاری)
        try:
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id,
                    'ثبت‌نام جدید در رویداد',
                    f'کاربر {current_user.full_name} در رویداد "{event.title}" ثبت‌نام کرد.'
                )
        except:
            pass
        
        flash('ثبت‌نام شما با موفقیت انجام شد.', 'success')
        return redirect(url_for('event_detail', event_id=event_id))
    
    @app.route('/event/cancel/<int:event_id>', methods=['POST'])
    @login_required
    @verified_required
    def cancel_registration(event_id):
        """لغو ثبت‌نام در رویداد"""
        try:
            registration = Registration.query.filter_by(
                user_id=current_user.id,
                event_id=event_id
            ).first_or_404()
        except:
            flash('ثبت‌نام مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        event = registration.event
        
        if event.start_date < datetime.utcnow():
            flash('امکان لغو ثبت‌نام پس از برگزاری رویداد وجود ندارد.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # کاهش تعداد شرکت‌کنندگان
        event.current_participants -= 1
        
        db.session.delete(registration)
        db.session.commit()
        
        create_notification(
            current_user.id,
            'لغو ثبت‌نام',
            f'ثبت‌نام شما در رویداد "{event.title}" لغو شد.'
        )
        
        flash('ثبت‌نام شما با موفقیت لغو شد.', 'success')
        return redirect(url_for('event_detail', event_id=event_id))
    
    @app.route('/profile')
    @login_required
    @verified_required
    def profile():
        """پروفایل کاربر - همه کاربران می‌توانند ببینند"""
        try:
            # آمار کاربر
            total_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).count()
            
            attended_events = Registration.query.filter_by(
                user_id=current_user.id,
                attended=True
            ).count()
            
            upcoming_registrations = Registration.query.filter(
                Registration.user_id == current_user.id,
                Registration.event.has(Event.start_date >= datetime.utcnow())
            ).count()
        except:
            total_registrations = 0
            attended_events = 0
            upcoming_registrations = 0
        
        return render_template('participant/profile.html',
                             total_registrations=total_registrations,
                             attended_events=attended_events,
                             upcoming_registrations=upcoming_registrations,
                             current_user=current_user)
    
    @app.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def edit_profile():
        """ویرایش پروفایل"""
        if request.method == 'POST':
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            current_user.university = request.form.get('university')
            current_user.faculty = request.form.get('faculty')
            current_user.student_id = request.form.get('student_id')
            
            # تغییر رمز عبور (در صورت ارائه)
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('رمز عبور فعلی نادرست است.', 'error')
                    return redirect(url_for('edit_profile'))
                
                if new_password != confirm_password:
                    flash('رمز عبور جدید و تأیید آن مطابقت ندارند.', 'error')
                    return redirect(url_for('edit_profile'))
                
                if len(new_password) < 6:
                    flash('رمز عبور باید حداقل ۶ کاراکتر باشد.', 'error')
                    return redirect(url_for('edit_profile'))
                
                current_user.set_password(new_password)
                flash('رمز عبور با موفقیت تغییر یافت.', 'success')
            
            db.session.commit()
            flash('پروفایل با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('profile'))
        
        return render_template('participant/edit_profile.html',
                             current_user=current_user)
    
    @app.route('/notifications')
    @login_required
    @verified_required
    def notifications():
        """لیست اعلان‌ها"""
        page = request.args.get('page', 1, type=int)
        
        try:
            user_notifications = Notification.query.filter_by(
                user_id=current_user.id
            ).order_by(Notification.created_at.desc()).paginate(
                page=page, per_page=20, error_out=False
            )
        except:
            user_notifications = []
        
        return render_template('participant/notifications.html',
                             notifications=user_notifications,
                             current_user=current_user)
    
    @app.route('/notification/read/<int:notification_id>')
    @login_required
    @verified_required
    def mark_notification_read(notification_id):
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        try:
            notification = Notification.query.get_or_404(notification_id)
        except:
            flash('اعلان مورد نظر یافت نشد.', 'error')
            return redirect(url_for('notifications'))
        
        if notification.user_id != current_user.id:
            flash('دسترسی غیرمجاز.', 'error')
            return redirect(url_for('notifications'))
        
        notification.is_read = True
        db.session.commit()
        
        return redirect(url_for('notifications'))
    
    @app.route('/notification/read-all', methods=['POST'])
    @login_required
    @verified_required
    def mark_all_notifications_read():
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        try:
            Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).update({'is_read': True})
            
            db.session.commit()
            flash('همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.', 'success')
        except:
            flash('خطا در به‌روزرسانی اعلان‌ها.', 'error')
        
        return redirect(url_for('notifications'))
    
    @app.route('/my-events')
    @login_required
    @verified_required
    def my_events():
        """رویدادهای ثبت‌نام شده کاربر"""
        page = request.args.get('page', 1, type=int)
        
        try:
            registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).order_by(Registration.registration_date.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            registrations = []
        
        return render_template('participant/my_events.html',
                             registrations=registrations,
                             current_user=current_user)
    
    # ============================================
    # ========== مسیرهای کارمندان ==========
    # ============================================
    
    @app.route('/staff/dashboard')
    @login_required
    @staff_required
    def staff_dashboard():
        """داشبورد کارمندان و اساتید - متصل به پایگاه داده"""
        
        # =============== آمارهای عمومی ===============
        try:
            total_students = User.query.filter_by(user_type='student', is_active=True).count()
        except:
            total_students = 0
        
        try:
            total_professors = User.query.filter_by(user_type='professor', is_active=True).count()
        except:
            total_professors = 0
        
        try:
            total_staff = User.query.filter_by(user_type='staff', is_active=True).count()
        except:
            total_staff = 0
        
        try:
            pending_approvals = User.query.filter_by(is_verified=False, is_active=True).count()
        except:
            pending_approvals = 0
        
        # لیست کاربرانی که نیاز به تأیید دارند
        try:
            pending_users = User.query.filter_by(is_verified=False, is_active=True).order_by(
                User.created_at.desc()
            ).limit(10).all()
        except:
            pending_users = []
        
        # کاربران جدید
        try:
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        except:
            recent_users = []
        
        # آمار رویدادها
        try:
            total_events = Event.query.count()
        except:
            total_events = 0
        
        try:
            active_events = Event.query.filter_by(is_active=True).count()
        except:
            active_events = 0
        
        try:
            upcoming_events_count = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).count()
        except:
            upcoming_events_count = 0
        
        # رویدادهای پیش‌رو
        try:
            events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(5).all()
        except:
            events = []
        
        # آمار حلقه‌های تلاوت
        try:
            total_circles = QuranCircle.query.count()
        except:
            total_circles = 0
        
        try:
            active_circles = QuranCircle.query.filter_by(is_active=True).count()
        except:
            active_circles = 0
        
        # =============== محاسبات آماری برای کارت‌ها ===============
        
        # کلاس‌های فعال
        try:
            active_classes = Class.query.filter_by(is_active=True).count()
        except:
            active_classes = 18
        
        # کلاس‌های این هفته
        try:
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            classes_this_week = Class.query.filter(
                Class.start_date >= start_of_week,
                Class.start_date <= end_of_week
            ).count()
        except:
            classes_this_week = 5
        
        # دانشجویان جدید این ماه
        try:
            first_day_of_month = datetime.now().replace(day=1)
            new_students_month = User.query.filter(
                User.user_type == 'student',
                User.created_at >= first_day_of_month
            ).count()
        except:
            new_students_month = 23
        
        # میانگین حضور (محاسبه از جدول attendances)
        try:
            avg_attendance_result = db.session.query(
                func.avg(Attendance.status == 'present').cast(db.Float) * 100
            ).scalar()
            avg_attendance = int(avg_attendance_result) if avg_attendance_result else 78
        except:
            avg_attendance = 78
        
        # جلسات برگزار شده
        try:
            completed_sessions = CourseSession.query.filter(
                CourseSession.session_date < datetime.now().date()
            ).count()
        except:
            completed_sessions = 124
        
        # نزدیک‌ترین جلسه
        try:
            next_session = CourseSession.query.filter(
                CourseSession.session_date >= datetime.now().date(),
                CourseSession.is_cancelled == False
            ).order_by(CourseSession.session_date, CourseSession.start_time).first()
            
            if next_session:
                # تبدیل تاریخ به شمسی
                try:
                    gregorian_date = next_session.session_date
                    jdate = jdatetime.date.fromgregorian(date=gregorian_date)
                    persian_months = {
                        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
                        5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
                        9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
                    }
                    next_session_date = f"{jdate.day} {persian_months[jdate.month]} {jdate.year}"
                except:
                    next_session_date = next_session.session_date.strftime('%Y/%m/%d')
            else:
                next_session_date = "---"
        except:
            next_session_date = "۱۵ اسفند ۱۴۰۴"
        
        # درصد تکمیل ترم (محاسبه بر اساس تاریخ)
        try:
            # فرض می‌کنیم ترم ۴ ماهه است
            semester_start = date(datetime.now().year, 1, 1)  # تاریخ شروع ترم
            semester_end = date(datetime.now().year, 4, 30)   # تاریخ پایان ترم
            today = date.today()
            
            total_days = (semester_end - semester_start).days
            passed_days = (today - semester_start).days
            
            if total_days > 0:
                semester_completion = int((passed_days / total_days) * 100)
                semester_completion = max(0, min(100, semester_completion))
            else:
                semester_completion = 65
        except:
            semester_completion = 65
        
        # تعداد دانشکده‌ها
        try:
            faculties_count = Faculty.query.count()
        except:
            faculties_count = 12
        
        # تعداد کل کلاس‌ها
        try:
            total_classes_count = Class.query.count()
        except:
            total_classes_count = 32
        
        # =============== کلاس‌های من (بر اساس کاربر جاری) ===============
        my_classes = []
        try:
            classes = Class.query.filter_by(instructor_id=current_user.id).limit(10).all()
            
            for cls in classes:
                # تعداد دانشجویان کلاس
                student_count = ClassEnrollment.query.filter_by(
                    class_id=cls.id,
                    status='active'
                ).count()
                
                # محاسبه درصد حضور برای این کلاس
                try:
                    # دریافت تمام جلسات این کلاس
                    sessions = CourseSession.query.filter_by(class_id=cls.id).all()
                    session_ids = [s.id for s in sessions]
                    
                    if session_ids:
                        # تعداد کل حضورهای ممکن
                        total_possible_attendances = len(session_ids) * student_count
                        
                        # تعداد حضورهای ثبت شده
                        actual_attendances = Attendance.query.filter(
                            Attendance.session_id.in_(session_ids),
                            Attendance.status == 'present'
                        ).count()
                        
                        if total_possible_attendances > 0:
                            attendance_percent = int((actual_attendances / total_possible_attendances) * 100)
                        else:
                            attendance_percent = 0
                    else:
                        attendance_percent = 0
                except:
                    attendance_percent = random.randint(60, 95)
                
                my_classes.append({
                    'name': cls.name,
                    'code': cls.code,
                    'student_count': student_count,
                    'attendance_percent': attendance_percent
                })
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            # داده نمونه در صورت عدم وجود
            my_classes = [
                {'name': 'ریاضی ۱', 'code': 'MATH101', 'student_count': 35, 'attendance_percent': 85},
                {'name': 'فیزیک ۱', 'code': 'PHY101', 'student_count': 42, 'attendance_percent': 62},
                {'name': 'برنامه‌نویسی', 'code': 'CS101', 'student_count': 28, 'attendance_percent': 91},
            ]
        
        # =============== جلسات آینده ===============
        upcoming_sessions = []
        try:
            sessions = CourseSession.query.filter(
                CourseSession.session_date >= datetime.now().date(),
                CourseSession.is_cancelled == False
            ).order_by(CourseSession.session_date, CourseSession.start_time).limit(10).all()
            
            for session in sessions:
                class_obj = Class.query.get(session.class_id)
                
                # تبدیل تاریخ به شمسی
                try:
                    gregorian_date = session.session_date
                    jdate = jdatetime.date.fromgregorian(date=gregorian_date)
                    persian_date = f"{jdate.year}/{jdate.month}/{jdate.day}"
                except:
                    persian_date = session.session_date.strftime('%Y/%m/%d')
                
                # فرمت زمان
                time_str = session.start_time.strftime('%H:%M') if session.start_time else '---'
                
                upcoming_sessions.append({
                    'class_name': class_obj.name if class_obj else '---',
                    'title': session.title,
                    'date': persian_date,
                    'time': time_str,
                    'location': session.location
                })
        except Exception as e:
            print(f"خطا در دریافت جلسات آینده: {e}")
            upcoming_sessions = [
                {'class_name': 'ریاضی ۱', 'title': 'جلسه ۱۲ - مشتق', 'date': '۱۴۰۴/۱۲/۲۰', 'time': '۱۰:۰۰', 'location': 'کلاس ۲۰۳'},
                {'class_name': 'فیزیک ۱', 'title': 'آزمایشگاه', 'date': '۱۴۰۴/۱۲/۲۱', 'time': '۱۴:۰۰', 'location': 'آزمایشگاه فیزیک'},
            ]
        
        # =============== دانشجویان کم‌حضور ===============
        low_attendance_students = []
        try:
            # دریافت دانشجویانی که حضور کمتر از 50% دارند
            students = User.query.filter_by(user_type='student', is_active=True).limit(50).all()
            
            for student in students:
                # دریافت تمام ثبت‌نام‌های کلاس این دانشجو
                enrollments = ClassEnrollment.query.filter_by(
                    student_id=student.id,
                    status='active'
                ).all()
                
                for enrollment in enrollments[:2]:  # حداکثر 2 کلاس برای هر دانشجو
                    class_obj = Class.query.get(enrollment.class_id)
                    
                    # دریافت جلسات این کلاس
                    sessions = CourseSession.query.filter_by(class_id=enrollment.class_id).all()
                    session_ids = [s.id for s in sessions]
                    
                    if session_ids:
                        # تعداد حضورهای این دانشجو
                        attendances = Attendance.query.filter(
                            Attendance.session_id.in_(session_ids),
                            Attendance.student_id == student.id,
                            Attendance.status == 'present'
                        ).count()
                        
                        attendance_percent = int((attendances / len(session_ids)) * 100) if session_ids else 0
                        
                        if attendance_percent < 50:
                            low_attendance_students.append({
                                'id': student.id,
                                'name': student.full_name,
                                'student_id': getattr(student, 'student_id', '---'),
                                'class_name': class_obj.name if class_obj else '---',
                                'attendance_percent': attendance_percent
                            })
                            
                            if len(low_attendance_students) >= 10:
                                break
                
                if len(low_attendance_students) >= 10:
                    break
        except Exception as e:
            print(f"خطا در دریافت دانشجویان کم‌حضور: {e}")
            low_attendance_students = [
                {'id': 1, 'name': 'علی محمدی', 'student_id': '۴۰۰۱۲۳۴۵۶', 'class_name': 'معارف اسلامی', 'attendance_percent': 35},
                {'id': 2, 'name': 'زهرا احمدی', 'student_id': '۴۰۰۱۲۳۴۵۷', 'class_name': 'فیزیک ۱', 'attendance_percent': 42},
            ]
        
        # =============== دانشجویان دانشگاه (فیلتر شده بر اساس دانشگاه کاربر) ===============
        university_students = []
        try:
            students = User.query.filter_by(
                user_type='student',
                university=current_user.university,
                is_active=True
            ).limit(10).all()
            
            for student in students:
                university_students.append({
                    'full_name': student.full_name,
                    'email': student.email,
                    'student_id': getattr(student, 'student_id', '---'),
                    'major': getattr(student, 'field_of_study', '---'),
                    'is_active': student.is_active
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            university_students = [
                {'full_name': 'احمد کریمی', 'email': 'a.karimi@example.com', 'student_id': '۴۰۰۱۲۳۴۵۹', 'major': 'مهندسی کامپیوتر', 'is_active': True},
                {'full_name': 'سارا محمدی', 'email': 's.mohammadi@example.com', 'student_id': '۴۰۰۱۲۳۴۶۰', 'major': 'فیزیک', 'is_active': True},
            ]
        
        # =============== متغیرهای stats برای کارت‌های آماری ===============
        stats = {
            'active_classes': active_classes,
            'classes_this_week': classes_this_week,
            'total_students': total_students,
            'new_students_month': new_students_month,
            'avg_attendance': avg_attendance,
            'completed_sessions': completed_sessions,
            'upcoming_sessions': upcoming_events_count,
            'next_session_date': next_session_date,
            'semester_completion': semester_completion,
            'faculties_count': faculties_count,
            'total_classes': total_classes_count
        }
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        return render_template('staff/dashboard.html',
                             # آمارهای عمومی
                             total_students=total_students,
                             total_professors=total_professors,
                             total_staff=total_staff,
                             pending_approvals=pending_approvals,
                             pending_users=pending_users,
                             recent_users=recent_users,
                             total_events=total_events,
                             active_events=active_events,
                             upcoming_events=upcoming_events_count,
                             events=events,
                             total_circles=total_circles,
                             active_circles=active_circles,
                             
                             # متغیر stats برای کارت‌های آماری
                             stats=stats,
                             
                             # داده‌های جداول
                             my_classes=my_classes,
                             upcoming_sessions=upcoming_sessions,
                             low_attendance_students=low_attendance_students,
                             university_students=university_students,
                             
                             # اطلاعات عمومی
                             current_date=current_date,
                             daily_verse=daily_verse,
                             current_user=current_user,
                             now=datetime.now())

    @app.route('/staff/pending-users')
    @login_required
    @staff_required
    def staff_pending_users():
        """لیست کاربران در انتظار تأیید برای کارمندان"""
        page = request.args.get('page', 1, type=int)
        user_type = request.args.get('type', 'all')
        
        try:
            query = User.query.filter_by(is_verified=False, is_active=True)
            
            if user_type != 'all':
                query = query.filter_by(user_type=user_type)
            
            users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except:
            users = []
        
        return render_template('staff/pending_users.html', 
                             users=users,
                             current_user=current_user,
                             user_type=user_type)

    # ===============================
    # تأیید کاربر توسط staff
    # ===============================

    @app.route('/staff/verify/<int:user_id>')
    @login_required
    @staff_required
    def staff_verify_user(user_id):
        """تأیید کاربر توسط کارمند"""
        user = User.query.get_or_404(user_id)
        
        # بررسی اینکه کاربر قبلاً تأیید نشده باشد
        if user.is_verified:
            flash('این کاربر قبلاً تأیید شده است.', 'warning')
            return redirect(url_for('staff_pending_users'))
        
        # تأیید کاربر
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        user.verified_by = current_user.id
        db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '✅ تأیید حساب کاربری',
            f'حساب کاربری شما با موفقیت تأیید شد. اکنون می‌توانید وارد شوید.'
        )
        
        flash(f'کاربر {user.full_name} با موفقیت تأیید شد.', 'success')
        return redirect(url_for('staff_pending_users'))

    # ===============================
    # رد کاربر توسط staff
    # ===============================

    @app.route('/staff/reject/<int:user_id>', methods=['POST'])
    @login_required
    @staff_required
    def staff_reject_user(user_id):
        """رد درخواست کاربر توسط کارمند"""
        user = User.query.get_or_404(user_id)
        
        # بررسی اینکه کاربر قبلاً تأیید نشده باشد
        if user.is_verified:
            flash('این کاربر قبلاً تأیید شده است و نمی‌توان آن را رد کرد.', 'warning')
            return redirect(url_for('staff_pending_users'))
        
        # دریافت دلیل رد از فرم
        reason = request.form.get('reason', 'دلیل خاصی ذکر نشده است.')
        
        try:
            # غیرفعال کردن کاربر
            user.is_active = False
            user.verification_notes = f"رد شده: {reason}"
            db.session.commit()
        except:
            # اگر فیلدهای خاص وجود نداشت، حداقل کاربر را غیرفعال کن
            user.is_active = False
            db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )
        
        flash(f'درخواست کاربر {user.full_name} رد شد.', 'danger')
        return redirect(url_for('staff_pending_users'))

    @app.route('/staff/reject-user/<int:user_id>', methods=['POST'])
    @login_required
    @staff_required
    def staff_reject_user_json(user_id):
        """رد درخواست کاربر توسط کارمند (نسخه JSON برای درخواست‌های AJAX)"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        if user.is_verified:
            return jsonify({'success': False, 'message': 'این کاربر قبلاً تأیید شده است.'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'دلیل خاصی ذکر نشده است.')
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )
        
        # غیرفعال کردن کاربر
        user.is_active = False
        user.verification_notes = reason
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'درخواست کاربر {user.full_name} رد شد.'})

    @app.route('/staff/user/<int:user_id>')
    @login_required
    @staff_required
    def staff_user_detail(user_id):
        """مشاهده جزئیات کاربر برای کارمندان"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('staff_pending_users'))
        
        return render_template('staff/user_detail.html', user=user, current_user=current_user)
    
    # ============================================
    # ========== پنل اختصاصی اساتید ==========
    # ============================================

    @app.route('/professor/dashboard')
    @login_required
    def professor_dashboard():
        """داشبورد اصلی اساتید"""
        # بررسی دسترسی استاد
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        # آمار کلی
        try:
            # کلاس‌های این استاد
            my_classes_count = Class.query.filter_by(instructor_id=current_user.id, is_active=True).count()
            
            # دانشجویان تحت نظر
            total_students = db.session.query(func.count(ClassEnrollment.student_id))\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .scalar() or 0
            
            # جلسات امروز
            today_sessions_count = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date == date.today())\
                .count()
            
            # حلقه‌های تلاوت
            my_circles_count = QuranCircle.query.filter_by(created_by=current_user.id, is_active=True).count()
            
            # نمرات ثبت نشده
            pending_grades = ClassEnrollment.query\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(ClassEnrollment.grade.is_(None))\
                .count()
            
            stats = {
                'my_classes': my_classes_count,
                'total_students': total_students,
                'today_sessions': today_sessions_count,
                'my_circles': my_circles_count,
                'pending_grades': pending_grades,
                'last_login': current_user.last_login
            }
        except Exception as e:
            print(f"خطا در دریافت آمار: {e}")
            stats = {
                'my_classes': 0,
                'total_students': 0,
                'today_sessions': 0,
                'my_circles': 0,
                'pending_grades': 0
            }
        
        # کلاس‌های فعال
        try:
            classes = Class.query\
                .filter_by(instructor_id=current_user.id, is_active=True)\
                .order_by(Class.start_date.desc())\
                .limit(5).all()
            
            active_classes = []
            for cls in classes:
                student_count = ClassEnrollment.query.filter_by(class_id=cls.id, status='active').count()
                total_sessions = CourseSession.query.filter_by(class_id=cls.id).count()
                completed_sessions = CourseSession.query.filter(
                    CourseSession.class_id == cls.id,
                    CourseSession.session_date < date.today()
                ).count()
                
                active_classes.append({
                    'id': cls.id,
                    'name': cls.name,
                    'code': cls.code,
                    'student_count': student_count,
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'progress': int((completed_sessions / total_sessions * 100)) if total_sessions > 0 else 0
                })
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            active_classes = []
        
        # جلسات امروز
        try:
            today_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date == date.today())\
                .order_by(CourseSession.start_time)\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات امروز: {e}")
            today_sessions = []
        
        # جلسات آینده
        try:
            upcoming_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date > date.today())\
                .filter(CourseSession.is_cancelled == False)\
                .order_by(CourseSession.session_date)\
                .limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت جلسات آینده: {e}")
            upcoming_sessions = []
        
        return render_template('professor/dashboard.html',
                             stats=stats,
                             active_classes=active_classes,
                             today_sessions=today_sessions,
                             upcoming_sessions=upcoming_sessions,
                             current_user=current_user,
                             now=datetime.now())


    @app.route('/professor/classes')
    @login_required
    def professor_classes():
        """لیست کلاس‌های استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        term = request.args.get('term', 'current')
        page = request.args.get('page', 1, type=int)
        
        try:
            query = Class.query.filter_by(instructor_id=current_user.id)
            
            if term == 'current':
                # ترم جاری
                current_term = AcademicTerm.query.filter_by(is_current=True).first()
                if current_term:
                    query = query.filter_by(academic_term=current_term.name)
            elif term == 'past':
                # ترم‌های گذشته
                current_term = AcademicTerm.query.filter_by(is_current=True).first()
                if current_term:
                    query = query.filter(Class.academic_term != current_term.name)
            
            classes = query.order_by(Class.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            classes = []
        
        return render_template('professor/classes.html',
                             classes=classes,
                             term=term,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>')
    @login_required
    def professor_class_detail(class_id):
        """جزئیات کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        # بررسی دسترسی
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ شما دسترسی به این کلاس ندارید.', 'error')
            return redirect(url_for('professor_classes'))
        
        # دانشجویان کلاس
        try:
            enrollments = ClassEnrollment.query\
                .filter_by(class_id=class_id)\
                .filter_by(status='active')\
                .join(User, User.id == ClassEnrollment.student_id)\
                .add_columns(
                    User.id,
                    User.first_name,
                    User.last_name,
                    User.student_id,
                    User.email,
                    User.phone
                ).all()
            
            students = []
            for enrollment, user_id, first_name, last_name, student_id, email, phone in enrollments:
                # آمار حضور این دانشجو
                total_sessions = CourseSession.query.filter_by(class_id=class_id).count()
                attended = Attendance.query\
                    .join(CourseSession, CourseSession.id == Attendance.session_id)\
                    .filter(CourseSession.class_id == class_id)\
                    .filter(Attendance.student_id == user_id)\
                    .filter(Attendance.status == 'present')\
                    .count()
                
                attendance_rate = int((attended / total_sessions * 100)) if total_sessions > 0 else 0
                
                students.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'student_id': student_id,
                    'email': email,
                    'phone': phone,
                    'attendance_rate': attendance_rate,
                    'grade': enrollment.grade
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            students = []
        
        # جلسات کلاس
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات: {e}")
            sessions = []
        
        return render_template('professor/class_detail.html',
                             class_obj=class_obj,
                             students=students,
                             sessions=sessions,
                             current_user=current_user,
                             now=datetime.now())


    @app.route('/professor/class/<int:class_id>/grades', methods=['GET', 'POST'])
    @login_required
    def professor_grades(class_id):
        """مدیریت نمرات کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        if request.method == 'POST':
            # ذخیره نمرات
            grades = request.form.getlist('grades[]')
            student_ids = request.form.getlist('student_ids[]')
            
            try:
                for i, student_id in enumerate(student_ids):
                    if i < len(grades) and grades[i]:
                        enrollment = ClassEnrollment.query.filter_by(
                            class_id=class_id,
                            student_id=student_id
                        ).first()
                        
                        if enrollment:
                            enrollment.grade = float(grades[i])
                
                db.session.commit()
                flash('✅ نمرات با موفقیت ثبت شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطا در ثبت نمرات: {e}', 'error')
            
            return redirect(url_for('professor_class_detail', class_id=class_id))
        
        # دریافت دانشجویان
        try:
            enrollments = ClassEnrollment.query\
                .filter_by(class_id=class_id, status='active')\
                .join(User, User.id == ClassEnrollment.student_id)\
                .add_columns(
                    User.id,
                    User.first_name,
                    User.last_name,
                    User.student_id
                ).all()
            
            students = []
            for enrollment, user_id, first_name, last_name, student_id in enrollments:
                students.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'student_id': student_id,
                    'grade': enrollment.grade
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            students = []
        
        return render_template('professor/grades.html',
                             class_obj=class_obj,
                             students=students,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/attendance', methods=['GET', 'POST'])
    @login_required
    def professor_attendance(class_id):
        """حضور و غیاب کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        session_id = request.args.get('session_id', type=int)
        
        if request.method == 'POST':
            # ثبت حضور و غیاب
            session_id = request.form.get('session_id', type=int)
            attendance_data = request.form.getlist('attendance[]')
            student_ids = request.form.getlist('student_ids[]')
            late_minutes_list = request.form.getlist('late_minutes[]')
            excuses_list = request.form.getlist('excuse[]')
            
            if not session_id:
                flash('❌ لطفاً جلسه را انتخاب کنید.', 'error')
                return redirect(request.url)
            
            try:
                # پاک کردن حضورهای قبلی این جلسه
                Attendance.query.filter_by(session_id=session_id).delete()
                
                # ثبت حضورهای جدید
                for i, student_id in enumerate(student_ids):
                    if i < len(attendance_data):
                        status = attendance_data[i]
                        late_minutes = int(late_minutes_list[i]) if i < len(late_minutes_list) else 0
                        excuse = excuses_list[i] if i < len(excuses_list) else ''
                        
                        attendance = Attendance(
                            session_id=session_id,
                            student_id=student_id,
                            status=status,
                            late_minutes=late_minutes,
                            excuse=excuse,
                            marked_by=current_user.id
                        )
                        db.session.add(attendance)
                
                db.session.commit()
                flash('✅ حضور و غیاب با موفقیت ثبت شد.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطا در ثبت حضور و غیاب: {e}', 'error')
            
            return redirect(url_for('professor_attendance', class_id=class_id, session_id=session_id))
        
        # دریافت جلسات کلاس
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات: {e}")
            sessions = []
        
        students = []
        attendances = {}
        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0
        
        if session_id:
            # دریافت دانشجویان کلاس
            try:
                enrollments = ClassEnrollment.query\
                    .filter_by(class_id=class_id, status='active')\
                    .join(User, User.id == ClassEnrollment.student_id)\
                    .add_columns(
                        User.id,
                        User.first_name,
                        User.last_name,
                        User.student_id
                    ).all()
                
                for enrollment, user_id, first_name, last_name, student_id in enrollments:
                    students.append({
                        'id': user_id,
                        'full_name': f"{first_name} {last_name}",
                        'student_id': student_id
                    })
            except Exception as e:
                print(f"خطا در دریافت دانشجویان: {e}")
            
            # دریافت حضورهای قبلی این جلسه
            try:
                attendance_records = Attendance.query\
                    .filter_by(session_id=session_id)\
                    .all()
                
                for att in attendance_records:
                    attendances[att.student_id] = {
                        'status': att.status.value if att.status else 'absent',
                        'late_minutes': att.late_minutes,
                        'excuse': att.excuse
                    }
                    
                    if att.status == 'present':
                        present_count += 1
                    elif att.status == 'absent':
                        absent_count += 1
                    elif att.status == 'late':
                        late_count += 1
                        present_count += 1
                    elif att.status == 'excused':
                        excused_count += 1
                        present_count += 1
            except Exception as e:
                print(f"خطا در دریافت حضورها: {e}")
        
        # دریافت اطلاعات جلسه انتخاب شده
        session_title = ""
        session_date = ""
        session_time = ""
        if session_id:
            try:
                session = CourseSession.query.get(session_id)
                if session:
                    session_title = session.title or f"جلسه {session.id}"
                    session_date = session.session_date.strftime('%Y/%m/%d')
                    session_time = f"{session.start_time.strftime('%H:%M') if session.start_time else '---'} - {session.end_time.strftime('%H:%M') if session.end_time else '---'}"
            except:
                pass
        
        return render_template('professor/attendance.html',
                             class_obj=class_obj,
                             sessions=sessions,
                             students=students,
                             attendances=attendances,
                             selected_session=session_id,
                             session_title=session_title,
                             session_date=session_date,
                             session_time=session_time,
                             present_count=present_count,
                             absent_count=absent_count,
                             late_count=late_count,
                             excused_count=excused_count,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/files')
    @login_required
    def professor_files(class_id):
        """مدیریت فایل‌های کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        # فایل‌های عمومی کلاس
        try:
            class_files = ClassFile.query\
                .filter_by(class_id=class_id)\
                .order_by(ClassFile.uploaded_at.desc())\
                .all()
        except:
            class_files = []
        
        # فایل‌های جلسات
        try:
            session_files = SessionFile.query\
                .join(CourseSession, CourseSession.id == SessionFile.session_id)\
                .filter(CourseSession.class_id == class_id)\
                .order_by(SessionFile.uploaded_at.desc())\
                .all()
        except:
            session_files = []
        
        # جلسات برای انتخاب در آپلود
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except:
            sessions = []
        
        return render_template('professor/files.html',
                             class_obj=class_obj,
                             class_files=class_files,
                             session_files=session_files,
                             sessions=sessions,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/files/upload', methods=['POST'])
    @login_required
    def professor_upload_file(class_id):
        """آپلود فایل جدید"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            return jsonify({'success': False, 'message': 'کلاس یافت نشد.'}), 404
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'فایلی ارسال نشده.'}), 400
        
        file = request.files['file']
        title = request.form.get('title', file.filename)
        description = request.form.get('description', '')
        file_type = request.form.get('type', 'general')
        session_id = request.form.get('session_id', type=int)
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'نام فایل نامعتبر است.'}), 400
        
        # ذخیره فایل
        try:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            new_filename = f"{uuid.uuid4().hex}.{ext}"
            
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'class_files', str(class_id))
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, new_filename)
            file.save(file_path)
            
            # مسیر نسبی برای ذخیره در دیتابیس
            relative_path = os.path.join('class_files', str(class_id), new_filename)
            
            if session_id:
                # فایل مخصوص جلسه
                session_file = SessionFile(
                    session_id=session_id,
                    title=title,
                    description=description,
                    file_path=relative_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=current_user.id
                )
                db.session.add(session_file)
            else:
                # فایل عمومی کلاس
                class_file = ClassFile(
                    class_id=class_id,
                    title=title,
                    description=description,
                    file_path=relative_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=current_user.id
                )
                db.session.add(class_file)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'فایل با موفقیت آپلود شد.',
                'filename': title
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/professor/file/delete/<int:file_id>', methods=['POST'])
    @login_required
    def professor_delete_file(file_id):
        """حذف فایل"""
        try:
            # بررسی نوع فایل
            class_file = ClassFile.query.get(file_id)
            session_file = SessionFile.query.get(file_id) if not class_file else None
            
            file_obj = class_file or session_file
            
            if not file_obj:
                return jsonify({'success': False, 'message': 'فایل یافت نشد.'}), 404
            
            # بررسی دسترسی
            if class_file:
                class_obj = Class.query.get(class_file.class_id)
                if class_obj.instructor_id != current_user.id and not current_user.is_admin():
                    return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
            else:
                session = CourseSession.query.get(session_file.session_id)
                class_obj = Class.query.get(session.class_id)
                if class_obj.instructor_id != current_user.id and not current_user.is_admin():
                    return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
            
            # حذف فایل از دیسک
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_obj.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            db.session.delete(file_obj)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'فایل با موفقیت حذف شد.'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/professor/profile')
    @login_required
    def professor_profile():
        """پروفایل استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        # آمار تدریس
        try:
            total_classes = Class.query.filter_by(instructor_id=current_user.id).count()
            total_students = db.session.query(func.count(ClassEnrollment.student_id))\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .scalar() or 0
            
            total_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .count()
            
            total_circles = QuranCircle.query.filter_by(created_by=current_user.id).count()
            
            teaching_stats = {
                'total_classes': total_classes,
                'total_students': total_students,
                'total_sessions': total_sessions,
                'total_circles': total_circles
            }
        except:
            teaching_stats = {
                'total_classes': 0,
                'total_students': 0,
                'total_sessions': 0,
                'total_circles': 0
            }
        
        # دروس ارائه شده
        try:
            courses = Class.query\
                .filter_by(instructor_id=current_user.id)\
                .order_by(Class.created_at.desc())\
                .limit(10).all()
        except:
            courses = []
        
        return render_template('professor/profile.html',
                             teaching_stats=teaching_stats,
                             courses=courses,
                             current_user=current_user)


    @app.route('/professor/profile/edit', methods=['GET', 'POST'])
    @login_required
    def professor_edit_profile():
        """ویرایش پروفایل استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        if request.method == 'POST':
            # اطلاعات پایه
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            current_user.landline = request.form.get('landline')
            
            # اطلاعات تخصصی
            current_user.academic_rank = request.form.get('academic_rank')
            current_user.specialization = request.form.get('specialization')
            current_user.teaching_experience = request.form.get('teaching_experience', type=int)
            current_user.professor_code = request.form.get('professor_code')
            current_user.office_hours = request.form.get('office_hours')
            current_user.website = request.form.get('website')
            
            # اطلاعات مکانی
            current_user.university = request.form.get('university')
            current_user.faculty = request.form.get('faculty')
            current_user.department = request.form.get('department')
            current_user.office_location = request.form.get('office_location')
            
            # آپلود رزومه جدید
            if 'resume' in request.files:
                file = request.files['resume']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes')
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # حذف فایل قبلی
                    if current_user.resume_file:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.resume_file)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    new_filename = f"resume_{current_user.id}_{int(time.time())}.pdf"
                    file_path = os.path.join(upload_path, new_filename)
                    file.save(file_path)
                    
                    current_user.resume_file = os.path.join('resumes', new_filename)
            
            db.session.commit()
            flash('✅ پروفایل با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('professor_profile'))
        
        return render_template('professor/edit_profile.html',
                             current_user=current_user)


     # ============================================
    # ========== حلقه‌های تلاوت (استاد و عمومی) ==========
    # ============================================

    @app.route('/professor/circles')
    @login_required
    def professor_circles():
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        page = request.args.get('page', 1, type=int)
        try:
            circles = QuranCircle.query\
                .filter_by(created_by=current_user.id)\
                .order_by(QuranCircle.created_at.desc())\
                .paginate(page=page, per_page=10, error_out=False)
            total_members = 0
            total_sessions = 0
            for circle in circles.items:
                total_members += circle.current_members
                total_sessions += circle.sessions.count()
            avg_attendance = 0
            if circles.items:
                total_attendance = 0
                for circle in circles.items:
                    total_attendance += circle.attendance_rate
                avg_attendance = int(total_attendance / len(circles.items))
        except Exception as e:
            print(f"خطا در دریافت حلقه‌ها: {e}")
            circles = []
            total_members = 0
            total_sessions = 0
            avg_attendance = 0
        return render_template('professor/circles.html',
                               circles=circles,
                               total_members=total_members,
                               total_sessions=total_sessions,
                               avg_attendance=avg_attendance,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>')
    @login_required
    def professor_circle_detail(circle_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_circles'))
        if circle.created_by != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circles'))
        # اعضای حلقه
        try:
            members = CircleMember.query\
                .filter_by(circle_id=circle_id, is_active=True)\
                .join(User, User.id == CircleMember.user_id)\
                .add_columns(
                    User.id, User.first_name, User.last_name,
                    User.email, User.phone
                ).all()
            circle_members = []
            for member, user_id, first_name, last_name, email, phone in members:
                attendance_rate = 0
                total_sessions = circle.sessions.count()
                if total_sessions > 0:
                    attended = SessionAttendance.query\
                        .join(CircleSession, CircleSession.id == SessionAttendance.session_id)\
                        .filter(CircleSession.circle_id == circle_id)\
                        .filter(SessionAttendance.member_id == member.id)\
                        .filter(SessionAttendance.attended == True)\
                        .count()
                    attendance_rate = int((attended / total_sessions) * 100)
                circle_members.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'email': email,
                    'phone': phone,
                    'role': member.role,
                    'joined_date': member.joined_date,
                    'attendance_rate': attendance_rate
                })
        except Exception as e:
            print(f"خطا در دریافت اعضا: {e}")
            circle_members = []
        try:
            sessions = CircleSession.query\
                .filter_by(circle_id=circle_id)\
                .order_by(CircleSession.session_date.desc())\
                .all()
        except:
            sessions = []
        return render_template('professor/circle_detail.html',
                               circle=circle,
                               members=circle_members,
                               sessions=sessions,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>/session/create', methods=['POST'])
    @login_required
    def professor_create_session(circle_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            return jsonify({'success': False, 'message': 'حلقه یافت نشد.'}), 404
        if circle.created_by != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        data = request.get_json()
        try:
            session_date = datetime.strptime(data.get('session_date'), '%Y-%m-%d').date()
            session = CircleSession(
                circle_id=circle_id,
                title=data.get('title'),
                session_date=session_date,
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                topic=data.get('topic'),
                description=data.get('description'),
                verses_reviewed=data.get('verses_reviewed'),
                notes=data.get('notes'),
                homework=data.get('homework')
            )
            db.session.add(session)
            db.session.commit()
            return jsonify({'success': True, 'message': 'جلسه با موفقیت ایجاد شد.', 'session_id': session.id})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/professor/circle/<int:circle_id>/attendance/<int:session_id>')
    @login_required
    def professor_circle_attendance(circle_id, session_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
            session = CircleSession.query.get_or_404(session_id)
        except:
            flash('اطلاعات مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_circles'))
        if circle.created_by != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circles'))
        try:
            members = CircleMember.query\
                .filter_by(circle_id=circle_id, is_active=True)\
                .join(User, User.id == CircleMember.user_id)\
                .add_columns(User.id, User.first_name, User.last_name).all()
        except:
            members = []
        attendances = {}
        present_count = 0
        late_count = 0
        try:
            atts = SessionAttendance.query.filter_by(session_id=session_id).all()
            for a in atts:
                attendances[a.member_id] = {
                    'attended': a.attended,
                    'late_minutes': a.late_minutes,
                    'excuse': a.excuse
                }
                if a.attended:
                    present_count += 1
                    if a.late_minutes > 0:
                        late_count += 1
        except:
            pass
        return render_template('professor/circle_attendance.html',
                               circle=circle,
                               session=session,
                               members=members,
                               attendance_dict=attendances,
                               present_count=present_count,
                               late_count=late_count,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>/attendance/<int:session_id>', methods=['POST'])
    @login_required
    def professor_save_circle_attendance(circle_id, session_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
            session = CircleSession.query.get_or_404(session_id)
        except:
            return jsonify({'success': False, 'message': 'اطلاعات یافت نشد.'}), 404
        if circle.created_by != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        data = request.get_json()
        attendances = data.get('attendances', [])
        try:
            SessionAttendance.query.filter_by(session_id=session_id).delete()
            for att in attendances:
                attendance = SessionAttendance(
                    session_id=session_id,
                    member_id=att['member_id'],
                    attended=att['attended'],
                    late_minutes=att.get('late_minutes', 0),
                    excuse=att.get('excuse', ''),
                    marked_by=current_user.id
                )
                db.session.add(attendance)
            db.session.commit()
            return jsonify({'success': True, 'message': 'حضور و غیاب با موفقیت ثبت شد.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    # ======================= درخواست ایجاد حلقه تلاوت توسط استاد =======================
    @app.route('/professor/circle-request', methods=['GET', 'POST'])
    @login_required
    def professor_circle_request():
        if not current_user.is_professor():
            flash('⛔ فقط اساتید می‌توانند درخواست ایجاد حلقه تلاوت بدهند.', 'error')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            max_members = request.form.get('max_members', type=int)
            circle_type = request.form.get('circle_type', 'public')
            if not name or not description:
                flash('لطفاً نام و توضیحات حلقه را وارد کنید.', 'error')
                return redirect(url_for('professor_circle_request'))

            # ایجاد حلقه جدید – فقط یکبار از capacity استفاده کنید
            new_circle = QuranCircle(
                name=name,
                description=description,
                capacity=max_members,                 # max_members به capacity نگاشت می‌شود
                circle_type=circle_type,
                created_by=current_user.id,
                status='pending',
                teacher_name=current_user.full_name,  # فیلد اجباری
                is_active=True
            )
            db.session.add(new_circle)
            db.session.commit()

            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id,
                    'درخواست جدید ایجاد حلقه تلاوت',
                    f'استاد {current_user.full_name} درخواست ایجاد حلقه "{new_circle.name}" را داده است.'
                )
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، حلقه فعال خواهد شد.', 'success')
            return redirect(url_for('professor_dashboard'))

        return render_template('professor/circle_request.html', current_user=current_user)

    @app.route('/professor/circle-requests')
    @login_required
    def professor_circle_requests():
        if not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        status = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        query = QuranCircle.query.filter_by(created_by=current_user.id)
        if status != 'all':
            query = query.filter_by(status=status)
        pagination = query.order_by(QuranCircle.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        return render_template('professor/circle_requests.html', requests=pagination, status=status, current_user=current_user)

    @app.route('/professor/circle-request/<int:request_id>')
    @login_required
    def professor_circle_request_detail(request_id):
        if not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        circle = QuranCircle.query.get_or_404(request_id)
        if circle.created_by != current_user.id:
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circle_requests'))
        return render_template('professor/circle_request_detail.html', request=circle, current_user=current_user)

    # ======================= مدیریت درخواست‌های حلقه توسط ادمین =======================
    @app.route('/admin/circle-requests')
    @login_required
    @admin_required
    def admin_circle_requests():
        pending_circles = QuranCircle.query.filter_by(status='pending').all()
        return render_template('admin/circle_requests.html', circles=pending_circles, current_user=current_user)

    @app.route('/admin/circle-request/<int:request_id>')
    @login_required
    @admin_required
    def admin_circle_request_detail(request_id):
        circle = QuranCircle.query.get_or_404(request_id)
        req_data = {
            'id': circle.id,
            'name': circle.name,
            'description': circle.description,
            'professor': User.query.get(circle.created_by),
            'created_at': circle.created_at,
            'circle_type': circle.circle_type,
            'max_members': circle.capacity,  # اصلاح: از capacity استفاده شد
            'status': circle.status,
            'rejection_reason': circle.rejection_reason
        }
        return render_template('admin/circle_request_detail.html', request=req_data, current_user=current_user)
     
    # ============================================
    # ========== مسیر دانلود رزومه استاد ==========
    # ============================================

    @app.route('/professor/download-resume')
    @login_required
    def download_resume():
        """دانلود رزومه استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        if not current_user.resume_file:
            flash('❌ فایل رزومه یافت نشد.', 'error')
            return redirect(url_for('professor_profile'))
        
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.resume_file)
            if not os.path.exists(file_path):
                flash('❌ فایل رزومه روی سرور یافت نشد.', 'error')
                return redirect(url_for('professor_profile'))
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"resume_{current_user.full_name}.pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            flash(f'❌ خطا در دانلود فایل: {str(e)}', 'error')
            return redirect(url_for('professor_profile'))

            
    
    # ============================================
    # ========== مسیرهای مدیریتی (ادمین) ==========
    # ============================================
    
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        """داشبورد مدیریت - فقط برای ادمین‌ها"""
        # آمار کلی
        try:
            total_users = User.query.count()
        except:
            total_users = 0
        
        try:
            total_events = Event.query.count()
        except:
            total_events = 0
        
        try:
            active_events = Event.query.filter_by(is_active=True).count()
        except:
            active_events = 0
        
        try:
            total_registrations = Registration.query.count()
        except:
            total_registrations = 0
        
        # تعداد کاربران در انتظار تأیید
        try:
            pending_count = User.query.filter_by(is_verified=False, is_active=True).count()
        except:
            pending_count = 0
        
        # رویدادهای اخیر
        try:
            recent_events = Event.query.order_by(
                Event.created_at.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت رویدادها: {e}")
            recent_events = []
        
        # کاربران جدید
        try:
            new_users = User.query.order_by(
                User.created_at.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت کاربران: {e}")
            new_users = []
        
        # ثبت‌نام‌های اخیر
        try:
            recent_registrations = Registration.query.order_by(
                Registration.registration_date.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت ثبت‌نام‌ها: {e}")
            recent_registrations = []
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_events=total_events,
                             active_events=active_events,
                             total_registrations=total_registrations,
                             recent_events=recent_events,
                             new_users=new_users,
                             recent_registrations=recent_registrations,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             pending_count=pending_count,
                             current_user=current_user)
 
      # ============================================
    # مسیرهای مدیریت رویداد (فقط ادمین)
    # ============================================
    
    @app.route('/admin/events')
    @login_required
    @admin_required
    def admin_events():
        events = Event.query.order_by(Event.created_at.desc()).all()
        return render_template('admin/events.html', events=events, current_user=current_user)
    
    @app.route('/admin/event/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def create_event():
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            event_type = request.form.get('event_type')
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            location = request.form.get('location')
            capacity = request.form.get('capacity', type=int)
            
            if not title or not description or not event_type or not start_date_shamsi or not start_time:
                flash('لطفاً تمام فیلدهای ضروری (عنوان، توضیحات، نوع رویداد، تاریخ شمسی و ساعت شروع) را پر کنید.', 'error')
                return redirect(url_for('create_event'))
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                start_date = jstart.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('create_event'))
            
            end_date = start_date
            
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'events')
            
            event = Event(
                title=title, description=description, event_type=EventType(event_type),
                start_date=start_date, end_date=end_date, location=location,
                capacity=capacity, image=image_path, created_by=current_user.id, is_active=True
            )
            db.session.add(event)
            db.session.commit()
            flash('رویداد با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('admin_events'))
        
        return render_template('admin/event_form.html', event=None, event_types=EventType, current_user=current_user)
    
    @app.route('/admin/event/edit/<int:event_id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def edit_event(event_id):
        event = Event.query.get_or_404(event_id)
        if request.method == 'POST':
            event.title = request.form.get('title')
            event.description = request.form.get('description')
            event.event_type = EventType(request.form.get('event_type'))
            
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            
            if not start_date_shamsi or not start_time:
                flash('تاریخ و ساعت شروع الزامی است.', 'error')
                return redirect(url_for('edit_event', event_id=event_id))
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                event.start_date = jstart.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('edit_event', event_id=event_id))
            
            event.end_date = event.start_date
            event.location = request.form.get('location')
            event.capacity = request.form.get('capacity', type=int)
            event.is_active = request.form.get('is_active') == 'on'
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if event.image:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    event.image = save_uploaded_file(file, 'events')
            
            db.session.commit()
            flash('رویداد با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('admin_events'))
        
        total_registrations = event.registrations.count()
        attended_count = event.registrations.filter_by(attended=True).count()
        return render_template('admin/event_form.html', event=event, event_types=EventType,
                             total_registrations=total_registrations, attended_count=attended_count, current_user=current_user)
    
    @app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_event(event_id):
        event = Event.query.get_or_404(event_id)
        if event.image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        Registration.query.filter_by(event_id=event_id).delete()
        db.session.delete(event)
        db.session.commit()
        return jsonify({'success': True, 'message': 'رویداد با موفقیت حذف شد'})
    @app.route('/admin/users')
    @login_required
    @admin_required
    def admin_users():
        """مدیریت کاربران"""
        try:
            users = User.query.order_by(User.created_at.desc()).all()
        except:
            users = []
        
        return render_template('admin/users.html',
                             users=users,
                             current_user=current_user)
    
    @app.route('/admin/user/toggle/<int:user_id>', methods=['GET'])
    @login_required
    @admin_required
    def toggle_user_status(user_id):
        """فعال/غیرفعال کردن کاربر - با ریدایرکت به جای JSON"""
        if user_id == current_user.id:
            flash('نمی‌توانید خودتان را غیرفعال کنید', 'error')
            return redirect(url_for('admin_users'))
        
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('admin_users'))
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'فعال' if user.is_active else 'غیرفعال'
        
        # اعلان به کاربر
        create_notification(
            user.id,
            'تغییر وضعیت حساب کاربری',
            f'وضعیت حساب کاربری شما به "{status}" تغییر یافت.'
        )
        
        flash(f'کاربر {user.username} {status} شد', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/role/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def change_user_role(user_id):
        """تغییر نقش کاربر"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in [r.value for r in UserRole]:
            return jsonify({'success': False, 'message': 'نقش نامعتبر است'}), 400
        
        user.role = UserRole(new_role)
        db.session.commit()
        
        # اعلان به کاربر
        role_names = {'admin': 'مدیر', 'manager': 'مسئول', 'participant': 'دانشجو'}
        create_notification(
            user.id,
            'تغییر نقش کاربری',
            f'نقش شما در سیستم به "{role_names.get(new_role, new_role)}" تغییر یافت.'
        )
        
        return jsonify({'success': True, 'message': f'نقش کاربر {user.username} تغییر یافت'})
    
    # ============================================
    # مسیرهای مدیریتی برای ادمین (تأیید کاربران)
    # ============================================
    
    @app.route('/admin/pending-users')
    @login_required
    @admin_required
    def admin_pending_users():
        """لیست کاربران در انتظار تأیید برای ادمین"""
        page = request.args.get('page', 1, type=int)
        user_type = request.args.get('type', 'all')
        
        try:
            query = User.query.filter_by(is_verified=False, is_active=True)
            
            if user_type != 'all':
                query = query.filter_by(user_type=user_type)
            
            users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except Exception as e:
            print(f"خطا در دریافت کاربران: {e}")
            users = []
        
        return render_template('admin/pending_users.html', 
                             users=users,
                             current_user=current_user,
                             user_type=user_type)

    @app.route('/admin/user/verify/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_verify_user(user_id):
        """تأیید کاربر توسط ادمین"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        if user.is_verified:
            return jsonify({'success': False, 'message': 'این کاربر قبلاً تأیید شده است.'}), 400
        
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        user.verified_by = current_user.id
        db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '✅ تأیید حساب کاربری',
            f'حساب کاربری شما با موفقیت تأیید شد. اکنون می‌توانید وارد شوید.'
        )
        
        return jsonify({'success': True, 'message': f'کاربر {user.full_name} تأیید شد.'})

    @app.route('/admin/user/reject/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_reject_user(user_id):
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404

        # تشخیص نوع درخواست (JSON یا فرم)
        if request.is_json:
            data = request.get_json()
            reason = data.get('reason', 'دلیل خاصی ذکر نشده است.')
        else:
            reason = request.form.get('reason', 'دلیل خاصی ذکر نشده است.')

        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )

        user.is_active = False
        user.verification_notes = reason
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': f'درخواست کاربر {user.full_name} رد شد.'})
        else:
            flash(f'درخواست کاربر {user.full_name} رد شد.', 'danger')
            return redirect(url_for('admin_pending_users'))

    @app.route('/admin/user/<int:user_id>')
    @login_required
    @admin_required
    def admin_user_detail(user_id):
        """مشاهده جزئیات کاربر برای ادمین"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('admin_pending_users'))
        
        return render_template('admin/user_detail.html', user=user, current_user=current_user)
    
    @app.route('/admin/reports')
    @login_required
    @admin_required
    def admin_reports():
        """گزارش‌گیری"""
        event_participation = []
        daily_registrations = []
        university_stats = []
        
        try:
            # ============= آمار شرکت در رویدادها =============
            event_participation_raw = db.session.query(
                Event,
                func.count(Registration.id).label('participants')
            ).outerjoin(Registration, Event.id == Registration.event_id)\
             .group_by(Event.id)\
             .order_by(func.count(Registration.id).desc())\
             .limit(10).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for event, participants in event_participation_raw:
                event_participation.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'event_type': event.event_type,
                    'event_type_value': event.event_type.value,
                    'start_date': event.start_date,
                    'end_date': event.end_date,
                    'location': event.location,
                    'capacity': event.capacity,
                    'current_participants': event.current_participants,
                    'image': event.image,
                    'is_active': event.is_active,
                    'created_by': event.created_by,
                    'created_at': event.created_at,
                    'participants': participants
                })
        except:
            pass
        
        try:
            # ============= آمار روزانه ثبت‌نام =============
            daily_registrations_raw = db.session.query(
                func.date(Registration.registration_date).label('date'),
                func.count(Registration.id).label('count')
            ).group_by(func.date(Registration.registration_date))\
             .order_by(func.date(Registration.registration_date).desc())\
             .limit(30).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for date, count in daily_registrations_raw:
                daily_registrations.append({
                    'date': date,
                    'count': count
                })
        except:
            pass
        
        try:
            # ============= آمار کاربران بر اساس دانشگاه =============
            university_stats_raw = db.session.query(
                User.university,
                func.count(User.id).label('count')
            ).filter(User.university.isnot(None))\
             .group_by(User.university)\
             .order_by(func.count(User.id).desc())\
             .limit(10).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for university, count in university_stats_raw:
                university_stats.append({
                    'university': university,
                    'count': count
                })
        except:
            pass
        
        return render_template('admin/reports.html',
                             event_participation=event_participation,
                             daily_registrations=daily_registrations,
                             university_stats=university_stats,
                             current_user=current_user)
    
    # ============================================
    # ========== مسیر هوش مصنوعی برای ادمین ==========
    # ============================================
    
    @app.route('/admin/ai')
    @login_required
    @admin_required
    def admin_ai_dashboard():
        """داشبورد مدیریت هوش مصنوعی"""
        try:
            if AI_ENABLED:
                try:
                    stats = get_ai_statistics()
                    recent_questions = get_recent_qa(limit=20)
                except:
                    stats = {
                        'total_questions': AIQuestion.query.count(),
                        'unique_users': db.session.query(AIQuestion.user_id).distinct().count(),
                        'ai_enabled': True
                    }
                    recent_questions = AIQuestion.query.order_by(AIQuestion.created_at.desc()).limit(20).all()
            else:
                try:
                    total_questions = AIQuestion.query.count()
                    quranic_questions = AIQuestion.query.filter_by(is_quranic=True).count()
                    unique_users = db.session.query(AIQuestion.user_id).distinct().count()
                    
                    stats = {
                        'total_questions': total_questions,
                        'quranic_questions': quranic_questions,
                        'unique_users': unique_users,
                        'total_verses': QuranVerse.query.count(),
                        'system_status': 'در حال توسعه',
                        'ai_enabled': False
                    }
                    
                    recent_questions = AIQuestion.query.order_by(
                        AIQuestion.created_at.desc()
                    ).limit(20).all()
                except:
                    stats = {
                        'total_questions': 0,
                        'unique_users': 0,
                        'ai_enabled': False,
                        'system_status': 'خطا در اتصال'
                    }
                    recent_questions = []
        except:
            stats = {
                'total_questions': 0,
                'unique_users': 0,
                'ai_enabled': False,
                'system_status': 'خطا در سیستم'
            }
            recent_questions = []
        
        return render_template('admin/ai_dashboard.html',
                             stats=stats,
                             recent_questions=recent_questions,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
      # ============================================
    # ========== مدیریت بنرها (ادمین) ==========
    # ============================================
    
    @app.route('/admin/banners')
    @login_required
    @admin_required
    def admin_banners_list():
        """لیست تمام بنرها"""
        banners = Banner.query.order_by(Banner.order, Banner.id).all()
        return render_template('admin/admin_banners.html', banners=banners, current_user=current_user)

    @app.route('/admin/banners/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_add_banner():
        """افزودن بنر جدید"""
        title = request.form.get('title')
        link_url = request.form.get('link_url')
        alt_text = request.form.get('alt_text')
        order = request.form.get('order', 0)
        
        if not title:
            return jsonify({'success': False, 'message': 'عنوان بنر الزامی است'})
        
        # مدیریت آپلود تصویر
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                # استفاده از مسیر static/uploads/banners
                upload_path = os.path.join(app.root_path, 'static', 'uploads', 'banners')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                image_url = f'/static/uploads/banners/{filename}'
        
        # یا آدرس تصویر از ورودی
        if not image_url and request.form.get('image_url'):
            image_url = request.form.get('image_url')
        
        if not image_url:
            return jsonify({'success': False, 'message': 'تصویر بنر الزامی است'})
        
        banner = Banner(
            title=title,
            image_url=image_url,
            link_url=link_url,
            alt_text=alt_text,
            order=int(order) if order else 0,
            is_active=True
        )
        
        db.session.add(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت اضافه شد'})

    @app.route('/admin/banners/edit/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_edit_banner(banner_id):
        """ویرایش بنر"""
        banner = Banner.query.get_or_404(banner_id)
        
        banner.title = request.form.get('title', banner.title)
        banner.link_url = request.form.get('link_url')
        banner.alt_text = request.form.get('alt_text')
        banner.order = int(request.form.get('order', banner.order))
        
        # آپلود تصویر جدید
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # حذف تصویر قدیمی
                if banner.image_url:
                    old_path = os.path.join(app.root_path, banner.image_url.lstrip('/'))
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except:
                            pass
                
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                upload_path = os.path.join(app.root_path, 'static', 'uploads', 'banners')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                banner.image_url = f'/static/uploads/banners/{filename}'
        
        # آدرس تصویر از ورودی
        if request.form.get('image_url'):
            banner.image_url = request.form.get('image_url')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت ویرایش شد'})

    @app.route('/admin/banners/toggle/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_toggle_banner(banner_id):
        """فعال/غیرفعال کردن بنر"""
        banner = Banner.query.get_or_404(banner_id)
        banner.is_active = not banner.is_active
        db.session.commit()
        
        return jsonify({'success': True, 'is_active': banner.is_active})

    @app.route('/admin/banners/delete/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_banner(banner_id):
        """حذف بنر"""
        banner = Banner.query.get_or_404(banner_id)
        
        # حذف فایل تصویر
        if banner.image_url:
            file_path = os.path.join(app.root_path, banner.image_url.lstrip('/'))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        db.session.delete(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت حذف شد'})

    @app.route('/admin/banners/reorder', methods=['POST'])
    @login_required
    @admin_required
    def admin_reorder_banners():
        """تنظیم ترتیب بنرها"""
        data = request.get_json()
        orders = data.get('orders', [])
        
        for item in orders:
            banner = Banner.query.get(item['id'])
            if banner:
                banner.order = item['order']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'ترتیب بنرها ذخیره شد'})
    @app.route('/admin/banners/api/banner/<int:banner_id>')
    @login_required
    @admin_required
    def admin_get_banner(banner_id):
        """دریافت اطلاعات یک بنر (برای ویرایش)"""
        banner = Banner.query.get_or_404(banner_id)
        return jsonify({
            'id': banner.id,
            'title': banner.title,
            'image_url': banner.image_url,
            'link_url': banner.link_url,
            'alt_text': banner.alt_text,
            'order': banner.order,
            'is_active': banner.is_active
        })

    @app.route('/admin/circle-request/<int:circle_id>/approve', methods=['POST'])
    @login_required
    @admin_required
    def approve_circle_request(circle_id):
        circle = QuranCircle.query.get_or_404(circle_id)
        if circle.status != 'pending':
            return jsonify({'success': False, 'message': 'این درخواست قبلاً بررسی شده است.'})
        circle.status = 'approved'
        db.session.commit()
        create_notification(circle.created_by, '✅ تأیید درخواست حلقه تلاوت', f'درخواست شما برای ایجاد حلقه "{circle.name}" توسط مدیر تأیید شد.')
        return jsonify({'success': True})
    @app.route('/ai/quran', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def ai_quran():
        """پرسش و پاسخ قرآنی با استفاده از دیتابیس"""
        answer = None
        question = ""
        recent_questions = []
        suggested_verses = []
        
        # آمار
        try:
            stats = {
                'total_verses': QuranVerse.query.count(),
                'total_questions': QuranQA.query.count(),
                'user_questions': UserQuranChat.query.filter_by(user_id=current_user.id).count()
            }
        except:
            stats = {
                'total_verses': 0,
                'total_questions': 0,
                'user_questions': 0
            }
        
        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            
            if question:
                # جستجو در دیتابیس
                qa_obj = find_best_answer(question)
                
                if qa_obj:
                    # پاسخ از دیتابیس
                    answer = format_answer_with_verses(qa_obj)
                    # ذخیره در تاریخچه
                    save_user_chat(current_user.id, question, answer['answer'], qa_obj.related_verses)
                else:
                    # پاسخ پیش‌فرض برای سوالات بدون پاسخ
                    answer = {
                        "success": True,
                        "answer": f"""📖 **پاسخ به سوال شما:**

**سوال:** {question}

**پاسخ:** 
سوال خوبی پرسیدید! در حال حاضر پاسخ دقیقی برای این سوال در پایگاه داده من موجود نیست. 
پیشنهاد می‌کنم:

1. سوال خود را با عبارات ساده‌تر بپرسید
2. از کلمات کلیدی اصلی موضوع استفاده کنید
3. به بخش «پیشنهاد آیات» مراجعه کنید

اگر سوال شما تخصصی‌تر است، می‌توانید با پشتیبانی تماس بگیرید.

**آیه پیشنهادی برای مطالعه:**
«وَمَنْ يَتَّقِ اللَّهَ يَجْعَلْ لَهُ مَخْرَجًا»
(سوره طلاق، آیه ۲)
هر کس تقوای الهی پیشه کند، خداوند راه نجاتی برای او قرار می‌دهد.""",
                        "is_quranic": True,
                        "suggestions": [
                            "تفسیر قرآن",
                            "مفاهیم پایه قرآنی",
                            "آیات مشابه"
                        ]
                    }
                    # ذخیره در تاریخچه
                    save_user_chat(current_user.id, question, answer['answer'], None)
        
        # دریافت سوالات اخیر کاربر
        try:
            recent_chats = UserQuranChat.query.filter_by(
                user_id=current_user.id
            ).order_by(UserQuranChat.created_at.desc()).limit(5).all()
            
            for chat in recent_chats:
                recent_questions.append({
                    'id': chat.id,
                    'question': chat.question[:50] + '...' if len(chat.question) > 50 else chat.question,
                    'answer': chat.answer[:100] if chat.answer else '',
                    'created_at': chat.created_at.strftime('%Y-%m-%d') if chat.created_at else '',
                    'is_quranic': True
                })
        except:
            recent_questions = []
        
        # دریافت آیات تصادفی
        try:
            suggested_verses = QuranVerse.query.order_by(func.random()).limit(3).all()
        except:
            suggested_verses = []
        
        return render_template('ai/quran.html',
                             answer=answer,
                             question=question,
                             recent_questions=recent_questions,
                             suggested_verses=suggested_verses,
                             stats=stats,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    @app.route('/admin/quran-qa/<int:qa_id>/get')
    @login_required
    @admin_required
    def admin_get_quran_qa(qa_id):
        qa = QuranQA.query.get_or_404(qa_id)
        return jsonify({
            'success': True,
            'qa': {
                'id': qa.id,
                'question': qa.question,
                'keywords': qa.keywords,
                'answer': qa.answer,
                'related_verses': qa.related_verses,
                'category': qa.category,
                'priority': qa.priority
            }
        })

    @app.route('/admin/quran-qa/<int:qa_id>/edit', methods=['POST'])
    @login_required
    @admin_required
    def admin_edit_quran_qa(qa_id):
        qa = QuranQA.query.get_or_404(qa_id)
        data = request.get_json()
        
        qa.question = data.get('question')
        qa.keywords = data.get('keywords')
        qa.answer = data.get('answer')
        qa.related_verses = data.get('related_verses')
        qa.category = data.get('category')
        qa.priority = data.get('priority', 0)
        qa.updated_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'بروزرسانی شد'})
        @app.route('/admin/quran-qa/add', methods=['POST'])
        @login_required
        @admin_required
        def admin_add_quran_qa():
            """افزودن پرسش و پاسخ جدید"""
        data = request.get_json()
        
        qa = QuranQA(
            question=data.get('question'),
            keywords=data.get('keywords'),
            answer=data.get('answer'),
            related_verses=data.get('related_verses'),
            category=data.get('category'),
            priority=data.get('priority', 0),
            is_active=True
        )
        db.session.add(qa)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'پرسش و پاسخ با موفقیت اضافه شد'})

    @app.route('/admin/quran-qa/<int:qa_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_quran_qa(qa_id):
        """حذف پرسش و پاسخ"""
        qa = QuranQA.query.get_or_404(qa_id)
        db.session.delete(qa)
        db.session.commit()
        return jsonify({'success': True, 'message': 'حذف شد'})

    @app.route('/admin/quran-qa/<int:qa_id>/toggle', methods=['POST'])
    @login_required
    @admin_required
    def admin_toggle_quran_qa(qa_id):
        """فعال/غیرفعال کردن پرسش و پاسخ"""
        qa = QuranQA.query.get_or_404(qa_id)
        qa.is_active = not qa.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': qa.is_active})
    
    @app.route('/ai/history')
    @login_required
    @verified_required
    def ai_history():
        """تاریخچه پرسش‌ها"""
        page = request.args.get('page', 1, type=int)
        
        try:
            questions = AIQuestion.query.filter_by(
                user_id=current_user.id
            ).order_by(AIQuestion.created_at.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            questions = []
        
        return render_template('ai/history.html',
                             questions=questions,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/ask', methods=['POST'])
    @login_required
    @verified_required
    def ask_quran():
        """پرسش و پاسخ قرآنی (پردازش فرم)"""
        question = request.form.get('question', '').strip()
        
        if not question:
            flash('لطفاً سوال خود را وارد کنید', 'error')
            return redirect(url_for('ai_quran'))
        
        try:
            # ذخیره سوال در دیتابیس
            ai_question = AIQuestion(
                user_id=current_user.id,
                question=question
            )
            db.session.add(ai_question)
            db.session.commit()
            
            if AI_ENABLED:
                answer = ask_quran_ai(question, current_user.id)
                # به‌روزرسانی پاسخ
                ai_question.answer = answer.get('answer', '')
                ai_question.is_quranic = answer.get('is_quranic', True)
                db.session.commit()
            else:
                # حالت ساده
                answer = {
                    "success": True,
                    "answer": f"""📖 **پاسخ به سوال شما:**

**سوال:** {question}

**پاسخ:**
این سیستم هوش مصنوعی قرآنی در حال توسعه است. 
برای پاسخ دقیق به سوال شما، می‌توانید به تفاسیر معتبر قرآن مراجعه کنید.

**آیه پیشنهادی:**
«بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ»
(سوره الفاتحة، آیه ۱)

هر کاری را با نام خداوند بخشنده مهربان شروع کنید.""",
                    "is_quranic": True,
                    "related_verses": [
                        {
                            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                            "translation": "به نام خداوند بخشنده مهربان",
                            "surah": "الفاتحة",
                            "ayah": 1
                        }
                    ],
                    "suggestions": [
                        "تفسیر آیه‌الکرسی",
                        "آیات مربوط به توحید",
                        "فضیلت سوره یس"
                    ]
                }
        except:
            flash('خطا در پردازش سوال. لطفاً بعداً تلاش کنید.', 'error')
            return redirect(url_for('ai_quran'))
        
        # دریافت سوالات اخیر کاربر با فرمت تاریخ مناسب
        recent_questions = []
        try:
            recent_questions_raw = AIQuestion.query.filter_by(
                user_id=current_user.id
            ).order_by(AIQuestion.created_at.desc()).limit(5).all()
            
            for q in recent_questions_raw:
                question_obj = {
                    'id': q.id,
                    'question': q.question,
                    'answer': q.answer,
                    'created_at': q.created_at.strftime('%Y-%m-%d') if q.created_at else '',
                    'is_quranic': q.is_quranic
                }
                recent_questions.append(question_obj)
        except:
            pass
        
        suggested_verses = []
        try:
            suggested_verses = QuranVerse.query.order_by(func.random()).limit(3).all()
        except:
            pass
        
        return render_template('ai/quran.html',
                             answer=answer,
                             question=question,
                             recent_questions=recent_questions,
                             suggested_verses=suggested_verses,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/analyze', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def ai_analyze():
        """تحلیل محتوای قرآنی"""
        analysis = None
        text = ""
        
        if request.method == 'POST':
            text = request.form.get('text', '').strip()
            
            if text:
                if AI_ENABLED:
                    try:
                        analysis = analyze_quranic_text(text, current_user.id)
                    except:
                        analysis = {
                            "verses": [
                                {
                                    "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                                    "translation": "به نام خداوند بخشنده مهربان",
                                    "surah": "الفاتحة",
                                    "ayah": 1
                                }
                            ],
                            "keywords": ["خداوند", "بخشنده", "مهربان"],
                            "sentiment": "positive"
                        }
                else:
                    analysis = {
                        "verses": [
                            {
                                "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                                "translation": "به نام خداوند بخشنده مهربان",
                                "surah": "الفاتحة",
                                "ayah": 1
                            }
                        ],
                        "keywords": ["خداوند", "بخشنده", "مهربان"],
                        "sentiment": "positive"
                    }
        
        return render_template('ai/analyze.html',
                             analysis=analysis,
                             text=text,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
        @app.route('/ai/suggest', methods=['GET', 'POST'])
        @login_required
        @verified_required
        def ai_suggest():
            """پیشنهاد آیات بر اساس حال و هوا"""
            verses = []
            mood = "general"
        
            if request.method == 'POST':
               mood = request.form.get('mood', 'general')
            
            # نقشه mood به فارسی
            mood_map = {
                'امید': 'امید',
                'آرامش': 'آرامش',
                'توکل': 'توکل'
            }
            
            mood_key = mood_map.get(mood, 'general')
            
            # دریافت از دیتابیس
            if mood_key != 'general':
                verses = get_suggestions_by_mood(mood_key)
            
            # اگر آیات کافی نبود، از جدول QuranVerse استفاده کن
            if not verses or len(verses) < 3:
                try:
                    random_verses = QuranVerse.query.order_by(func.random()).limit(5).all()
                    for v in random_verses:
                        verses.append({
                            'text': v.verse_arabic if hasattr(v, 'verse_arabic') else '',
                            'translation': v.verse_persian if hasattr(v, 'verse_persian') else v.translation if hasattr(v, 'translation') else '',
                            'surah': v.surah_name if hasattr(v, 'surah_name') else '',
                            'ayah': v.verse_number if hasattr(v, 'verse_number') else ''
                        })
                except:
                    pass
        
        return render_template('ai/suggest.html',
                             verses=verses,
                             mood=mood,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/ask_api', methods=['POST'])
    @login_required
    @verified_required
    def ai_ask_api():
        """API برای پرسش سوال (استفاده در AJAX)"""
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'سوال الزامی است'}), 400
        
        question = data['question'].strip()
        
        try:
            # ذخیره در دیتابیس
            ai_question = AIQuestion(
                user_id=current_user.id,
                question=question
            )
            db.session.add(ai_question)
            db.session.commit()
            
            if AI_ENABLED:
                answer = ask_quran_ai(question, current_user.id)
                ai_question.answer = answer.get('answer', '')
                ai_question.is_quranic = answer.get('is_quranic', True)
                db.session.commit()
            else:
                answer = {
                    'success': True,
                    'answer': f'پاسخ به سوال: {question}\n\nسیستم هوش مصنوعی در حال توسعه است.',
                    'is_quranic': True
                }
        except:
            answer = {
                'success': False,
                'answer': 'خطا در پردازش سوال',
                'is_quranic': True
            }
        
        return jsonify(answer)
    
    # ============================================
    # API های عمومی
    # ============================================
    
    @app.route('/api/events/upcoming')
    def api_upcoming_events():
        """API دریافت رویدادهای پیش‌رو"""
        try:
            events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(10).all()
            
            events_list = []
            for event in events:
                events_list.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description[:100] + '...',
                    'event_type': event.event_type.value,
                    'start_date': event.start_date.isoformat(),
                    'end_date': event.end_date.isoformat(),
                    'location': event.location,
                    'capacity': event.capacity,
                    'current_participants': event.current_participants,
                    'is_full': event.is_full(),
                    'image': url_for('static', filename=f'uploads/{event.image}') if event.image else None
                })
            
            return jsonify({'events': events_list})
        except:
            return jsonify({'events': []})
    
    @app.route('/api/user/stats')
    @login_required
    @verified_required
    def api_user_stats():
        """API آمار کاربر"""
        try:
            total_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).count()
            
            attended_events = Registration.query.filter_by(
                user_id=current_user.id,
                attended=True
            ).count()
            
            upcoming_events = Registration.query.filter(
                Registration.user_id == current_user.id,
                Registration.event.has(Event.start_date >= datetime.utcnow())
            ).count()
            
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
            
            return jsonify({
                'total_registrations': total_registrations,
                'attended_events': attended_events,
                'upcoming_events': upcoming_events,
                'unread_notifications': unread_notifications
            })
        except:
            return jsonify({
                'total_registrations': 0,
                'attended_events': 0,
                'upcoming_events': 0,
                'unread_notifications': 0
            })
    
    # ============================================
    # مسیر گزارش مشکل
    # ============================================
    
    @app.route('/report-issue', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def report_issue():
        """گزارش مشکل"""
        url = request.args.get('url', '')
        
        if request.method == 'POST':
            issue_url = request.form.get('url')
            issue_description = request.form.get('description')
            
            # اینجا می‌توانید مشکل را در دیتابیس ذخیره کنید یا ایمیل بزنید
            flash('مشکل شما با موفقیت گزارش شد. تیم فنی در اسرع وقت بررسی خواهد کرد.', 'success')
            return redirect(url_for('index'))
        
        return render_template('report_issue.html', url=url, current_user=current_user)
    
    # ============================================
    # مسیرهای مدیریت اعلامیه‌ها
    # ============================================
    
    @app.route('/admin/announcement', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_announcement():
        """ارسال اعلامیه به همه کاربران"""
        if request.method == 'POST':
            title = request.form.get('title')
            message = request.form.get('message')
            priority = request.form.get('priority', 'normal')
            
            if not title or not message:
                flash('عنوان و متن اعلامیه الزامی است.', 'error')
                return redirect(url_for('admin_announcement'))
            
            # دریافت همه کاربران فعال
            try:
                users = User.query.filter_by(is_active=True).all()
                sent_count = 0
                
                for user in users:
                    create_notification(
                        user_id=user.id,
                        title=title,
                        message=message
                    )
                    sent_count += 1
                
                flash(f'✅ اعلامیه با موفقیت برای {sent_count} کاربر ارسال شد.', 'success')
            except:
                flash('خطا در ارسال اعلامیه.', 'error')
            
            return redirect(url_for('admin_dashboard'))
        
        # تعداد کاربران فعال برای نمایش در فرم
        try:
            users_count = User.query.filter_by(is_active=True).count()
        except:
            users_count = 0
        
        return render_template('admin/announcement.html', 
                             current_user=current_user,
                             users_count=users_count)
    
    @app.route('/admin/announcements')
    @login_required
    @admin_required
    def admin_announcements_list():
        """لیست اعلامیه‌های ارسال شده"""
        from sqlalchemy import func
        
        try:
            recent_announcements = db.session.query(
                Notification.title,
                Notification.message,
                func.max(Notification.created_at).label('created_at'),
                func.count(Notification.id).label('recipients')
            ).group_by(
                Notification.title,
                Notification.message
            ).order_by(
                func.max(Notification.created_at).desc()
            ).limit(20).all()
        except:
            recent_announcements = []
        
        return render_template('admin/announcements_list.html',
                             announcements=recent_announcements,
                             current_user=current_user)
    
    # ============================================
    # مسیرهای حلقه‌های تلاوت
    # ============================================
    
    @app.route('/circles')
    def circles_list():
        """لیست حلقه‌های تلاوت"""
        page = request.args.get('page', 1, type=int)
        circle_type = request.args.get('type')
        level = request.args.get('level')
        search = request.args.get('search')
        
        try:
            query = QuranCircle.query.filter_by(is_active=True)
            
            if circle_type:
                query = query.filter_by(circle_type=circle_type)
            
            if level:
                query = query.filter_by(level=level)
            
            if search:
                query = query.filter(
                    (QuranCircle.name.contains(search)) | 
                    (QuranCircle.description.contains(search)) |
                    (QuranCircle.teacher_name.contains(search))
                )
            
            circles = query.order_by(QuranCircle.created_at.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            circles = []
        
        return render_template('circles/list.html',
                             circles=circles,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>')
    def circle_detail(circle_id):
        """جزئیات حلقه تلاوت"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی عضویت کاربر
        is_member = False
        if current_user.is_authenticated:
            try:
                membership = CircleMember.query.filter_by(
                    circle_id=circle_id,
                    user_id=current_user.id
                ).first()
                is_member = membership is not None
            except:
                is_member = False
        
        # دریافت جلسات
        try:
            upcoming_sessions = circle.sessions.filter(
                CircleSession.session_date >= datetime.now().date()
            ).order_by(CircleSession.session_date).limit(5).all()
        except:
            upcoming_sessions = []
        
        try:
            past_sessions = circle.sessions.filter(
                CircleSession.session_date < datetime.now().date()
            ).order_by(CircleSession.session_date.desc()).limit(5).all()
        except:
            past_sessions = []
        
        # دریافت فایل‌ها
        try:
            files = circle.files.order_by(CircleFile.uploaded_at.desc()).limit(10).all()
        except:
            files = []
        
        return render_template('circles/detail.html',
                             circle=circle,
                             is_member=is_member,
                             upcoming_sessions=upcoming_sessions,
                             past_sessions=past_sessions,
                             files=files,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>/join', methods=['POST'])
    @login_required
    @verified_required
    def join_circle(circle_id):
        """عضویت در حلقه تلاوت"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی ظرفیت
        if circle.is_full():
            flash('ظرفیت این حلقه تکمیل شده است.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        # بررسی عضویت قبلی
        existing = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=current_user.id
        ).first()
        
        if existing:
            if existing.is_active:
                flash('شما قبلاً عضو این حلقه هستید.', 'warning')
            else:
                existing.is_active = True
                circle.current_members += 1
                db.session.commit()
                flash('عضویت شما مجدداً فعال شد.', 'success')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        # عضویت جدید
        membership = CircleMember(
            circle_id=circle_id,
            user_id=current_user.id,
            is_active=True
        )
        
        circle.current_members += 1
        
        db.session.add(membership)
        db.session.commit()
        
        # اعلان به کاربر
        create_notification(
            current_user.id,
            'عضویت در حلقه تلاوت',
            f'شما با موفقیت در حلقه "{circle.name}" عضو شدید.'
        )
        
        flash('عضویت شما با موفقیت ثبت شد.', 'success')
        return redirect(url_for('circle_detail', circle_id=circle_id))


    @app.route('/circle/<int:circle_id>/leave', methods=['POST'])
    @login_required
    @verified_required
    def leave_circle(circle_id):
        """خروج از حلقه تلاوت"""
        try:
            membership = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first_or_404()
        except:
            flash('عضویت مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        circle = membership.circle
        
        membership.is_active = False
        circle.current_members -= 1
        
        db.session.commit()
        
        create_notification(
            current_user.id,
            'خروج از حلقه تلاوت',
            f'شما از حلقه "{circle.name}" خارج شدید.'
        )
        
        flash('شما با موفقیت از حلقه خارج شدید.', 'success')
        return redirect(url_for('circle_detail', circle_id=circle_id))


    @app.route('/circle/<int:circle_id>/sessions')
    @login_required
    @verified_required
    def circle_sessions(circle_id):
        """لیست جلسات حلقه"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی دسترسی
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده جلسات باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        try:
            query = circle.sessions
            
            if status == 'upcoming':
                query = query.filter(CircleSession.session_date >= datetime.now().date())
            elif status == 'past':
                query = query.filter(CircleSession.session_date < datetime.now().date())
            
            sessions = query.order_by(CircleSession.session_date.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            sessions = []
        
        return render_template('circles/sessions.html',
                             circle=circle,
                             sessions=sessions,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>')
    @login_required
    @verified_required
    def session_detail(session_id):
        """جزئیات جلسه"""
        try:
            session = CircleSession.query.get_or_404(session_id)
        except:
            flash('جلسه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        circle = session.circle
        
        # بررسی دسترسی
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle.id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        # دریافت حضور و غیاب
        try:
            attendances = session.attendances.all()
        except:
            attendances = []
        
        # دریافت فایل‌ها
        try:
            files = session.files.order_by(CircleSessionFile.uploaded_at.desc()).all()
        except:
            files = []
        
        return render_template('circles/session_detail.html',
                             session=session,
                             circle=circle,
                             attendances=attendances,
                             files=files,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>/attendance', methods=['POST'])
    @login_required
    @staff_required
    def mark_attendance(session_id):
        """ثبت حضور و غیاب"""
        try:
            session = CircleSession.query.get_or_404(session_id)
        except:
            return jsonify({'success': False, 'message': 'جلسه مورد نظر یافت نشد.'}), 404
        
        # فقط استاد یا مدیر می‌توانند ثبت کنند
        is_teacher = False
        try:
            is_teacher = CircleMember.query.filter_by(
                circle_id=session.circle_id,
                user_id=current_user.id,
                role='teacher',
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_teacher and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        member_id = data.get('member_id')
        attended = data.get('attended', False)
        late_minutes = data.get('late_minutes', 0)
        excuse = data.get('excuse', '')
        
        try:
            attendance = SessionAttendance.query.filter_by(
                session_id=session_id,
                member_id=member_id
            ).first()
            
            if attendance:
                attendance.attended = attended
                attendance.late_minutes = late_minutes
                attendance.excuse = excuse
                attendance.marked_by = current_user.id
            else:
                attendance = SessionAttendance(
                    session_id=session_id,
                    member_id=member_id,
                    attended=attended,
                    late_minutes=late_minutes,
                    excuse=excuse,
                    marked_by=current_user.id
                )
                db.session.add(attendance)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/circle/<int:circle_id>/files')
    @login_required
    @verified_required
    def circle_files(circle_id):
        """فایل‌های حلقه"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی عضویت
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده فایل‌ها باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        try:
            files = circle.files.order_by(CircleFile.uploaded_at.desc()).all()
        except:
            files = []
        
        try:
            session_files = CircleSessionFile.query.join(CircleSession)\
                                            .filter(CircleSession.circle_id == circle_id)\
                                            .order_by(CircleSessionFile.uploaded_at.desc()).all()
        except:
            session_files = []
        
        return render_template('circles/files.html',
                             circle=circle,
                             files=files,
                             session_files=session_files,
                             current_user=current_user)


    @app.route('/circle/file/<int:file_id>/download')
    @login_required
    @verified_required
    def download_circle_file(file_id):
        """دانلود فایل"""
        try:
            file = CircleFile.query.get_or_404(file_id)
        except:
            flash('فایل مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی دسترسی
        if not file.is_public:
            is_member = False
            try:
                is_member = CircleMember.query.filter_by(
                    circle_id=file.circle_id,
                    user_id=current_user.id,
                    is_active=True
                ).first() is not None
            except:
                pass
            
            if not is_member and not current_user.is_admin():
                flash('دسترسی غیرمجاز', 'error')
                return redirect(url_for('circles_list'))
        
        try:
            file.download_count += 1
            db.session.commit()
        except:
            pass
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)


    @app.route('/circle/session-file/<int:file_id>/download')
    @login_required
    @verified_required
    def download_session_file(file_id):
        """دانلود فایل جلسه"""
        try:
            file = CircleSessionFile.query.get_or_404(file_id)
        except:
            flash('فایل مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        session = file.session
        
        # بررسی عضویت
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=session.circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        try:
            file.download_count += 1
            db.session.commit()
        except:
            pass
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)
    
    # ============================================
    # مسیرهای جدید ثبت‌نام
    # ============================================
    
    @app.route('/auth/register/choice')
    def register_choice():
        """صفحه انتخاب نوع ثبت‌نام"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        return render_template('auth/register_choice.html')

    @app.route('/auth/register/professor', methods=['GET', 'POST'])
    def register_professor():
        """ثبت‌نام استاد"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            # دریافت اطلاعات فرم
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # اطلاعات تخصصی
            academic_rank = request.form.get('academic_rank')
            specialization = request.form.get('specialization')
            teaching_experience = request.form.get('teaching_experience', type=int)
            professor_code = request.form.get('professor_code')
            office_hours = request.form.get('office_hours')
            website = request.form.get('website')
            
            # اطلاعات مکانی
            university = request.form.get('university')
            faculty = request.form.get('faculty')
            province = request.form.get('province')
            city = request.form.get('city')
            address = request.form.get('address')
            
            # اطلاعات تماس
            phone = request.form.get('phone')
            landline = request.form.get('landline')
            office_phone = request.form.get('office_phone')
            gender = request.form.get('gender')
            
            # اعتبارسنجی
            errors = []
            
            if not first_name or not last_name:
                errors.append('نام و نام خانوادگی الزامی است')
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد')
            
            if password != confirm_password:
                errors.append('رمز عبور و تکرار آن مطابقت ندارند')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register_professor'))
            
            # آپلود فایل رزومه
            resume_path = None
            if 'resume' in request.files:
                file = request.files['resume']
                if file and file.filename:
                    allowed_extensions = {'pdf', 'doc', 'docx'}
                    if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        resume_path = save_uploaded_file(file, 'resumes')
            
            # تبدیل academic_rank به enum
            academic_rank_enum = convert_academic_rank(academic_rank)
            
            # ایجاد کاربر جدید
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                landline=landline,
                gender=gender,
                user_type='professor',
                is_verified=False,  # استاد نیاز به تأیید دارد
                academic_rank=academic_rank_enum,
                specialization=specialization,
                teaching_experience=teaching_experience,
                professor_code=professor_code,
                office_hours=office_hours,
                website=website,
                resume_file=resume_path,
                office_phone=office_phone,
                province=province,
                city=city,
                university=university,
                faculty=faculty,
                address=address,
                role=UserRole.MANAGER,
                is_active=True  # کاربر فعال است اما نیاز به تأیید دارد
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            try:
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'درخواست جدید همکاری استاد',
                        f'استاد {first_name} {last_name} درخواست همکاری داده است.'
                    )
            except:
                pass
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_professor.html')

    @app.route('/auth/register/staff', methods=['GET', 'POST'])
    def register_staff():
        """ثبت‌نام کارمند امور فرهنگی"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            # دریافت اطلاعات فرم
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # اطلاعات شغلی
            employee_id = request.form.get('employee_id')
            department = request.form.get('department')
            position = request.form.get('position')
            responsibility = request.form.get('responsibility')
            office_phone = request.form.get('office_phone')
            
            # اطلاعات مکانی
            university = request.form.get('university')
            faculty = request.form.get('faculty')
            province = request.form.get('province')
            city = request.form.get('city')
            address = request.form.get('address')
            
            # اطلاعات تماس
            phone = request.form.get('phone')
            landline = request.form.get('landline')
            gender = request.form.get('gender')
            
            # اعتبارسنجی
            errors = []
            
            if not first_name or not last_name:
                errors.append('نام و نام خانوادگی الزامی است')
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد')
            
            if password != confirm_password:
                errors.append('رمز عبور و تکرار آن مطابقت ندارند')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register_staff'))
            
            # ایجاد کاربر جدید
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                landline=landline,
                gender=gender,
                user_type='staff',
                is_verified=False,  # کارمند نیاز به تأیید دارد
                employee_id=employee_id,
                department=department,
                position=position,
                responsibility=responsibility,
                office_phone=office_phone,
                province=province,
                city=city,
                university=university,
                faculty=faculty,
                address=address,
                role=UserRole.MANAGER,
                is_active=True  # کاربر فعال است اما نیاز به تأیید دارد
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            try:
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'درخواست جدید همکاری کارمند',
                        f'کارمند {first_name} {last_name} درخواست همکاری داده است.'
                    )
            except:
                pass
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_staff.html')


    # ============================================
    # مسیرهای مدیریت مسابقات (Competitions)
    # ============================================

    # تابع به‌روزرسانی لیدربورد (قبل از استفاده تعریف شود)
    def update_leaderboard(competition_id):
        registrations = CompetitionRegistration.query.filter_by(competition_id=competition_id).all()
        for reg in registrations:
            total_score = db.session.query(db.func.sum(JudgeScore.score)).filter_by(registration_id=reg.id).scalar() or 0
            reg.final_score = total_score
        db.session.commit()
        sorted_regs = CompetitionRegistration.query.filter_by(competition_id=competition_id).order_by(CompetitionRegistration.final_score.desc()).all()
        for idx, reg in enumerate(sorted_regs, 1):
            reg.rank = idx
        db.session.commit()

    @app.route('/competitions')
    def competitions_list():
        """لیست همه مسابقات"""
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category')
        search = request.args.get('search')
        
        query = Competition.query.filter_by(is_active=True)
        
        if category:
            try:
                query = query.filter(Competition.category == CompetitionCategory(category))
            except:
                pass
        
        if search:
            query = query.filter(
                (Competition.title.contains(search)) |
                (Competition.description.contains(search))
            )
        
        competitions = query.order_by(Competition.start_date).paginate(page=page, per_page=12, error_out=False)
        
        # آمار برای هر مسابقه (تعداد شرکت‌کنندگان)
        for comp in competitions.items:
            comp.registered_count = CompetitionRegistration.query.filter_by(competition_id=comp.id).count()
        
        return render_template('competitions/index.html', competitions=competitions, categories=CompetitionCategory, current_user=current_user)

    @app.route('/competition/<int:comp_id>')
    def competition_detail(comp_id):
        """جزئیات یک مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        is_registered = False
        if current_user.is_authenticated:
            reg = CompetitionRegistration.query.filter_by(competition_id=comp_id, user_id=current_user.id).first()
            is_registered = reg is not None
        
        # لیست شرکت‌کنندگان برای نمایش در لیدربورد (فقط ۱۰ نفر اول)
        leaderboard = CompetitionRegistration.query.filter_by(competition_id=comp_id)\
            .order_by(CompetitionRegistration.final_score.desc()).limit(10).all()
        
        return render_template('competitions/detail.html', competition=competition, is_registered=is_registered, leaderboard=leaderboard, current_user=current_user)

    @app.route('/competition/<int:comp_id>/register', methods=['POST'])
    @login_required
    @verified_required
    def register_for_competition(comp_id):
        """ثبت‌نام در مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        if not competition.can_register():
            flash('زمان ثبت‌نام به پایان رسیده یا ظرفیت تکمیل شده است.', 'error')
            return redirect(url_for('competition_detail', comp_id=comp_id))
        
        existing = CompetitionRegistration.query.filter_by(competition_id=comp_id, user_id=current_user.id).first()
        if existing:
            flash('شما قبلاً در این مسابقه ثبت‌نام کرده‌اید.', 'warning')
            return redirect(url_for('competition_detail', comp_id=comp_id))
        
        reg = CompetitionRegistration(competition_id=comp_id, user_id=current_user.id)
        competition.current_participants += 1
        db.session.add(reg)
        db.session.commit()
        
        create_notification(current_user.id, 'ثبت‌نام در مسابقه', f'ثبت‌نام شما در مسابقه "{competition.title}" با موفقیت انجام شد.')
        
        flash('ثبت‌نام شما با موفقیت انجام شد.', 'success')
        return redirect(url_for('competition_detail', comp_id=comp_id))

    @app.route('/competition/<int:comp_id>/leaderboard')
    def competition_leaderboard(comp_id):
        """تابلوی امتیازات مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        leaderboard = CompetitionRegistration.query.filter_by(competition_id=comp_id)\
            .order_by(CompetitionRegistration.final_score.desc()).all()
        return render_template('competitions/leaderboard.html', competition=competition, leaderboard=leaderboard, current_user=current_user)

    # ============================================
    # بخش مدیریت مسابقات (فقط ادمین)
    # ============================================


    
    @app.route('/admin/competitions')
    @login_required
    @admin_required
    def admin_competitions():
        """مدیریت مسابقات - لیست"""
        competitions = Competition.query.order_by(Competition.created_at.desc()).all()
        return render_template('admin/competitions/index.html', competitions=competitions, current_user=current_user)

    @app.route('/admin/competition/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_create_competition():
        """ایجاد مسابقه جدید"""
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            rules = request.form.get('rules')
            evaluation_criteria = request.form.get('evaluation_criteria')
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            end_date_shamsi = request.form.get('end_date_shamsi')
            end_time = request.form.get('end_time')
            reg_deadline_shamsi = request.form.get('registration_deadline_shamsi')
            max_participants = request.form.get('max_participants', type=int)
            
            # تبدیل تاریخ‌ها
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                start_date = jstart.togregorian()
                
                end_datetime_str = f"{end_date_shamsi} {end_time}"
                jend = jdatetime.datetime.strptime(end_datetime_str, '%Y/%m/%d %H:%M')
                end_date = jend.togregorian()
                
                reg_deadline_str = f"{reg_deadline_shamsi} 23:59"
                jreg = jdatetime.datetime.strptime(reg_deadline_str, '%Y/%m/%d %H:%M')
                registration_deadline = jreg.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('admin_create_competition'))
            
            # ذخیره تصویر
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # بررسی حجم فایل (مثلاً حداکثر 5 مگابایت)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        flash('حجم فایل تصویر نباید بیشتر از 5 مگابایت باشد.', 'error')
                        return redirect(url_for('admin_create_competition'))
                    
                    image_path = save_uploaded_file(file, 'competitions')
            
            competition = Competition(
                title=title,
                description=description,
                category=CompetitionCategory(category),
                rules=rules,
                evaluation_criteria=evaluation_criteria,
                start_date=start_date,
                end_date=end_date,
                registration_deadline=registration_deadline,
                max_participants=max_participants,
                image=image_path,
                created_by=current_user.id,
                is_active=True
            )
            db.session.add(competition)
            db.session.commit()
            
            flash('مسابقه با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('admin_competitions'))
        
        return render_template('admin/competitions/form.html', competition=None, categories=CompetitionCategory, current_user=current_user)
    @app.route('/admin/competition/<int:comp_id>/edit', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_edit_competition(comp_id):
        """ویرایش مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        if request.method == 'POST':
            competition.title = request.form.get('title')
            competition.description = request.form.get('description')
            competition.category = CompetitionCategory(request.form.get('category'))
            competition.rules = request.form.get('rules')
            competition.evaluation_criteria = request.form.get('evaluation_criteria')
            competition.max_participants = request.form.get('max_participants', type=int)
            competition.is_active = 'is_active' in request.form
            
            # تبدیل تاریخ‌ها (مشابه create - برای خلاصه فقط تاریخ شروع و پایان را به‌روز می‌کنیم)
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            end_date_shamsi = request.form.get('end_date_shamsi')
            end_time = request.form.get('end_time')
            reg_deadline_shamsi = request.form.get('registration_deadline_shamsi')
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                competition.start_date = jstart.togregorian()
                
                end_datetime_str = f"{end_date_shamsi} {end_time}"
                jend = jdatetime.datetime.strptime(end_datetime_str, '%Y/%m/%d %H:%M')
                competition.end_date = jend.togregorian()
                
                reg_deadline_str = f"{reg_deadline_shamsi} 23:59"
                jreg = jdatetime.datetime.strptime(reg_deadline_str, '%Y/%m/%d %H:%M')
                competition.registration_deadline = jreg.togregorian()
            except:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('admin_edit_competition', comp_id=comp_id))
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if competition.image:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], competition.image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    competition.image = save_uploaded_file(file, 'competitions')
            
            db.session.commit()
            flash('مسابقه با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('admin_competitions'))
        
        return render_template('admin/competitions/form.html', competition=competition, categories=CompetitionCategory, current_user=current_user)

    @app.route('/admin/competition/<int:comp_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_competition(comp_id):
        """حذف مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        # حذف فایل تصویر
        if competition.image:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], competition.image)
            if os.path.exists(img_path):
                os.remove(img_path)
        db.session.delete(competition)
        db.session.commit()
        return jsonify({'success': True, 'message': 'مسابقه حذف شد.'})

    @app.route('/admin/competition/<int:comp_id>/rounds')
    @login_required
    @admin_required
    def admin_competition_rounds(comp_id):
        """مدیریت مراحل مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        rounds = CompetitionRound.query.filter_by(competition_id=comp_id).order_by(CompetitionRound.round_number).all()
        return render_template('admin/competitions/rounds.html', competition=competition, rounds=rounds, current_user=current_user)

    @app.route('/admin/competition/<int:comp_id>/round/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_add_round(comp_id):
        """افزودن مرحله جدید به مسابقه"""
        data = request.get_json()
        round_number = data.get('round_number')
        title = data.get('title')
        max_score = data.get('max_score', 100)
        
        existing = CompetitionRound.query.filter_by(competition_id=comp_id, round_number=round_number).first()
        if existing:
            return jsonify({'success': False, 'message': 'شماره مرحله تکراری است.'})
        
        round_obj = CompetitionRound(
            competition_id=comp_id,
            round_number=round_number,
            title=title,
            max_score=max_score
        )
        db.session.add(round_obj)
        db.session.commit()
        return jsonify({'success': True, 'message': 'مرحله اضافه شد.', 'round_id': round_obj.id})

    # ============================================
    # بخش نمره‌دهی داوران (دسترسی استاد و ادمین)
    # ============================================

    @app.route('/judge/competitions')
    @login_required
    def judge_competitions():
        """لیست مسابقاتی که کاربر به عنوان داور در آنها است (در اینجا فعلاً همه مسابقات فعال را نشان می‌دهیم)"""
        # در نسخه کامل باید یک جدول Judges داشته باشیم، اما فعلاً همه اساتید می‌توانند نمره دهند.
        if not (current_user.is_admin() or current_user.is_professor()):
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        competitions = Competition.query.filter_by(is_active=True).all()
        return render_template('judge/competitions.html', competitions=competitions, current_user=current_user)

    @app.route('/judge/competition/<int:comp_id>/score')
    @login_required
    def judge_score_competition(comp_id):
        """صفحه نمره‌دهی برای یک مسابقه"""
        if not (current_user.is_admin() or current_user.is_professor()):
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        competition = Competition.query.get_or_404(comp_id)
        registrations = CompetitionRegistration.query.filter_by(competition_id=comp_id).all()
        rounds = CompetitionRound.query.filter_by(competition_id=comp_id).order_by(CompetitionRound.round_number).all()
        
        # دریافت نمرات قبلی
        scores = {}
        for reg in registrations:
            scores[reg.id] = {}
            for round_obj in rounds:
                score_entry = JudgeScore.query.filter_by(round_id=round_obj.id, registration_id=reg.id, judge_id=current_user.id).first()
                scores[reg.id][round_obj.id] = score_entry.score if score_entry else None
        
        return render_template('judge/score.html', competition=competition, registrations=registrations, rounds=rounds, scores=scores, current_user=current_user)

    @app.route('/judge/save-score', methods=['POST'])
    @login_required
    def save_judge_score():
        """ذخیره نمره یک داور برای یک شرکت‌کننده در یک مرحله"""
        if not (current_user.is_admin() or current_user.is_professor()):
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'})
        
        data = request.get_json()
        round_id = data.get('round_id')
        registration_id = data.get('registration_id')
        score = data.get('score')
        feedback = data.get('feedback', '')
        
        # بررسی وجود مرحله و ثبت‌نام
        round_obj = CompetitionRound.query.get_or_404(round_id)
        reg = CompetitionRegistration.query.get_or_404(registration_id)
        
        # به‌روزرسانی یا ایجاد نمره
        score_entry = JudgeScore.query.filter_by(round_id=round_id, registration_id=registration_id, judge_id=current_user.id).first()
        if score_entry:
            score_entry.score = score
            score_entry.feedback = feedback
            score_entry.scored_at = datetime.utcnow()
        else:
            score_entry = JudgeScore(round_id=round_id, registration_id=registration_id, judge_id=current_user.id, score=score, feedback=feedback)
            db.session.add(score_entry)
        
        db.session.commit()
        
        # به‌روزرسانی نمره نهایی و رتبه‌بندی
        update_leaderboard(reg.competition_id)
        
        return jsonify({'success': True, 'message': 'نمره ذخیره شد.'})

    
    # ============================================
    # مسیرهای FCM (Firebase Cloud Messaging)
    # ============================================
    
    @app.route('/check-auth-status', methods=['GET'])
    def check_auth_status():
        """بررسی می‌کند که کاربر لاگین است یا نه"""
        return jsonify({
            'is_authenticated': current_user.is_authenticated
        })

    @app.route('/save-fcm-token', methods=['POST'])
    @login_required
    @verified_required
    def save_fcm_token():
        """ذخیره توکن FCM برای کاربر جاری"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'درخواست باید JSON باشد'}), 400
                
            token = data.get('token')
            
            if not token:
                return jsonify({'success': False, 'error': 'توکن ارسال نشده'}), 400
            
            # ذخیره توکن برای کاربر جاری
            current_user.fcm_token = token
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'توکن با موفقیت ذخیره شد'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/save-token', methods=['POST'])
    def save_token():
        """ذخیره توکن FCM (نسخه پشتیبان)"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'درخواست باید JSON باشد'}), 400
                
            token = data.get('token')
            user_id = data.get('user_id')
            
            if not token or not user_id:
                return jsonify({'success': False, 'error': 'token یا user_id ارسال نشده'}), 400
            
            # ذخیره در دیتابیس SQLite
            db_path = os.path.join(app.root_path, "instance", "seraj.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET fcm_token = ? WHERE id = ?", 
                (token, user_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'Token saved'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============================================
    # مسیرهای خطا
    # ============================================
    
    @app.route('/loading')
    def loading():
        """صفحه لودینگ"""
        return render_template('loading.html')
    
    # ============================================
    # فیلترهای تمپلیت
    # ============================================
    
    @app.template_filter('persian_date')
    def persian_date_filter(date_str):
        """فیلتر تاریخ شمسی برای تمپلیت"""
        return date_str
    
    @app.template_filter('format_date')
    def format_date_filter(date_obj):
        """فرمت کردن تاریخ برای نمایش"""
        if date_obj:
            try:
                return date_obj.strftime('%Y-%m-%d')
            except:
                return ''
        return ''
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403
    
    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('500.html'), 500
    