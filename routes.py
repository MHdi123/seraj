from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import os
import secrets
import uuid
import random
from models import (
    QuranCircle,
    CircleMember,
    CircleSession,
    CircleFile,
    SessionFile,
    SessionAttendance
)
import jdatetime
from models import db, User, UserRole, Event, EventType, Registration, AIQuestion, Notification, PasswordResetToken, QuranVerse

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
    # توابع کمکی آیه روز
    # ============================================
    
    def get_daily_verse():
        """برمی‌گرداند آیه روز با اطلاعات کامل از جدول quran_verses"""
        with app.app_context():
            try:
                # دریافت همه آیات
                verses = QuranVerse.query.all()
                
                if not verses:
                    print("⚠️ هیچ آیه‌ای در دیتابیس وجود ندارد!")
                    return {
                        'title': 'آیه روز',
                        'verse': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
                        'surah': 'سوره حمد',
                        'verse_number': 1,
                        'arabic_text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
                        'translation': 'به نام خداوند بخشنده مهربان'
                    }
                
                # انتخاب آیه بر اساس تاریخ (تغییر روزانه)
                today = date.today()
                random.seed(today.toordinal())
                verse = random.choice(verses)
                
                # ساخت آبجکت برای تمپلیت
                daily_verse = {
                    'title': 'آیه روز',
                    'verse': getattr(verse, 'verse_persian', getattr(verse, 'translation', '')),
                    'surah': getattr(verse, 'surah_name', 'قرآن'),
                    'verse_number': getattr(verse, 'verse_number', ''),
                    'arabic_text': getattr(verse, 'verse_arabic', ''),
                    'translation': getattr(verse, 'verse_persian', getattr(verse, 'translation', ''))
                }
                
                return daily_verse
                
            except Exception as e:
                print(f"❌ خطا در دریافت آیه روز: {e}")
                return {
                    'title': 'آیه روز',
                    'verse': 'إِنَّ مَعَ الْعُسْرِ يُسْرًا',
                    'surah': 'سوره شرح',
                    'verse_number': 6,
                    'arabic_text': 'إِنَّ مَعَ الْعُسْرِ يُسْرًا',
                    'translation': 'همانا با سختی آسانی است'
                }

    def get_persian_date():
        """برمی‌گرداند تاریخ امروز به شمسی"""
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
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message
        )
        db.session.add(notification)
        db.session.commit()
    
    # ============================================
    # مسیرهای عمومی
    # ============================================
    
    @app.route('/')
    def index():
        """صفحه اصلی"""
        # دریافت رویدادهای فعال
        upcoming_events = Event.query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.is_active == True
        ).order_by(Event.start_date).limit(6).all()
        
        # دریافت آیه روز
        daily_verse = get_daily_verse()
        
        # دریافت تاریخ شمسی
        current_date = get_persian_date()
        
        # آمار
        active_students = User.query.filter_by(is_active=True, role=UserRole.STUDENT).count()
        events_count = Event.query.count()
        competitions_count = Event.query.filter_by(event_type=EventType.COMPETITION).count()
        workshops_count = Event.query.filter_by(event_type=EventType.WORKSHOP).count()
        
        return render_template('index.html', 
                             events=upcoming_events,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             active_students=active_students,
                             events_count=events_count,
                             competitions_count=competitions_count,
                             workshops_count=workshops_count,
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
        
        events = query.order_by(Event.start_date).paginate(
            page=page, per_page=app.config.get('POSTS_PER_PAGE', 10), error_out=False
        )
        
        return render_template('events/list.html', 
                             events=events,
                             event_types=EventType,
                             current_user=current_user)
    
    @app.route('/event/<int:event_id>')
    def event_detail(event_id):
        """صفحه جزئیات رویداد"""
        event = Event.query.get_or_404(event_id)
        
        # بررسی ثبت‌نام کاربر
        is_registered = False
        if current_user.is_authenticated:
            registration = Registration.query.filter_by(
                user_id=current_user.id,
                event_id=event_id
            ).first()
            is_registered = registration is not None
        
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
            # جستجو در رویدادها
            events_query = Event.query.filter(
                Event.is_active == True,
                (Event.title.contains(q)) | 
                (Event.description.contains(q)) |
                (Event.location.contains(q))
            ).order_by(Event.start_date)
            
            results['events'] = events_query.paginate(page=page, per_page=10, error_out=False)
            results['total'] = results['events'].total
        
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
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                student_id=student_id,
                university=university,
                faculty=faculty,
                phone=phone,
                role=UserRole.STUDENT,
                is_active=True
            )
            
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
    
    @app.route('/auth/login', methods=['GET', 'POST'])
    def login():
        """ورود کاربر"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                if user.is_active:
                    login_user(user, remember=remember)
                    
                    # به‌روزرسانی آخرین ورود
                    user.last_login = datetime.utcnow()
                    db.session.commit()
                    
                    flash(f'خوش آمدید {user.full_name}!', 'success')
                    
                    # ریدایرکت بر اساس نقش
                    if user.role == UserRole.ADMIN:
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    flash('حساب کاربری شما غیرفعال شده است. با پشتیبانی تماس بگیرید.', 'error')
            else:
                flash('نام کاربری یا رمز عبور نادرست است.', 'error')
        
        return render_template('auth/login.html')
    
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
                
                # اینجا لینک بازنشانی رمز ارسال می‌شود
                reset_link = url_for('reset_password', token=token, _external=True)
                
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
            user.password_hash = generate_password_hash(password)
            
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
    # مسیرهای کاربر عادی
    # ============================================
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """داشبورد کاربر"""
        # رویدادهای ثبت‌نام شده
        user_registrations = Registration.query.filter_by(
            user_id=current_user.id
        ).order_by(Registration.registration_date.desc()).limit(10).all()
        
        # رویدادهای پیش‌رو
        upcoming_events = Event.query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.is_active == True
        ).order_by(Event.start_date).limit(5).all()
        
        # اعلان‌های خوانده نشده
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(5).all()
        
        # دریافت آیه روز برای داشبورد
        daily_verse = get_daily_verse()
        current_date = get_persian_date()
        
        return render_template('participant/dashboard.html',
                             registrations=user_registrations,
                             upcoming_events=upcoming_events,
                             notifications=unread_notifications,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             current_user=current_user)
    
    @app.route('/event/register/<int:event_id>', methods=['POST'])
    @login_required
    def register_for_event(event_id):
        """ثبت‌نام در رویداد"""
        event = Event.query.get_or_404(event_id)
        
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
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        for admin in admins:
            create_notification(
                admin.id,
                'ثبت‌نام جدید در رویداد',
                f'کاربر {current_user.full_name} در رویداد "{event.title}" ثبت‌نام کرد.'
            )
        
        flash('ثبت‌نام شما با موفقیت انجام شد.', 'success')
        return redirect(url_for('event_detail', event_id=event_id))
    
    @app.route('/event/cancel/<int:event_id>', methods=['POST'])
    @login_required
    def cancel_registration(event_id):
        """لغو ثبت‌نام در رویداد"""
        registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event_id
        ).first_or_404()
        
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
    def profile():
        """پروفایل کاربر"""
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
        
        return render_template('participant/profile.html',
                             total_registrations=total_registrations,
                             attended_events=attended_events,
                             upcoming_registrations=upcoming_registrations,
                             current_user=current_user)
    
    @app.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
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
    def notifications():
        """لیست اعلان‌ها"""
        page = request.args.get('page', 1, type=int)
        
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('participant/notifications.html',
                             notifications=user_notifications,
                             current_user=current_user)
    
    @app.route('/notification/read/<int:notification_id>')
    @login_required
    def mark_notification_read(notification_id):
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        notification = Notification.query.get_or_404(notification_id)
        
        if notification.user_id != current_user.id:
            flash('دسترسی غیرمجاز.', 'error')
            return redirect(url_for('notifications'))
        
        notification.is_read = True
        db.session.commit()
        
        return redirect(url_for('notifications'))
    
    @app.route('/notification/read-all', methods=['POST'])
    @login_required
    def mark_all_notifications_read():
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        flash('همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.', 'success')
        return redirect(url_for('notifications'))
    
    @app.route('/my-events')
    @login_required
    def my_events():
        """رویدادهای ثبت‌نام شده کاربر"""
        page = request.args.get('page', 1, type=int)
        
        registrations = Registration.query.filter_by(
            user_id=current_user.id
        ).order_by(Registration.registration_date.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        return render_template('participant/my_events.html',
                             registrations=registrations,
                             current_user=current_user)
    
    # ============================================
    # مسیرهای مدیریتی
    # ============================================
    
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        """داشبورد ادمین"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        # آمار کلی
        total_users = User.query.count()
        total_events = Event.query.count()
        active_events = Event.query.filter_by(is_active=True).count()
        total_registrations = Registration.query.count()
        
        # رویدادهای اخیر
        recent_events = Event.query.order_by(
            Event.created_at.desc()
        ).limit(5).all()
        
        # کاربران جدید
        new_users = User.query.order_by(
            User.created_at.desc()
        ).limit(5).all()
        
        # ثبت‌نام‌های اخیر
        recent_registrations = Registration.query.order_by(
            Registration.registration_date.desc()
        ).limit(5).all()
        
        # آیه روز برای ادمین
        daily_verse = get_daily_verse()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_events=total_events,
                             active_events=active_events,
                             total_registrations=total_registrations,
                             recent_events=recent_events,
                             new_users=new_users,
                             recent_registrations=recent_registrations,
                             daily_verse=daily_verse,
                             current_user=current_user)
    
    @app.route('/admin/events')
    @login_required
    def admin_events():
        """مدیریت رویدادها"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        events = Event.query.order_by(Event.start_date.desc()).all()
        
        return render_template('admin/events.html',
                             events=events,
                             current_user=current_user)
    
    @app.route('/admin/event/create', methods=['GET', 'POST'])
    @login_required
    def create_event():
        """ایجاد رویداد جدید"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            event_type = request.form.get('event_type')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            location = request.form.get('location')
            capacity = request.form.get('capacity', type=int)
            
            try:
                start_date = datetime.fromisoformat(start_date_str)
                end_date = datetime.fromisoformat(end_date_str)
            except:
                flash('فرمت تاریخ نامعتبر است.', 'error')
                return redirect(url_for('create_event'))
            
            # ذخیره تصویر
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                image_path = save_uploaded_file(file, 'events')
            
            # ایجاد رویداد
            event = Event(
                title=title,
                description=description,
                event_type=EventType(event_type),
                start_date=start_date,
                end_date=end_date,
                location=location,
                capacity=capacity,
                image=image_path,
                created_by=current_user.id,
                is_active=True
            )
            
            db.session.add(event)
            db.session.commit()
            
            # اعلان به همه کاربران
            users = User.query.filter_by(is_active=True).all()
            for user in users:
                create_notification(
                    user.id,
                    'رویداد جدید',
                    f'رویداد "{title}" به زودی برگزار می‌شود. برای اطلاعات بیشتر به صفحه رویدادها مراجعه کنید.'
                )
            
            flash('رویداد با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('admin_events'))
        
        return render_template('admin/event_form.html',
                             event=None,
                             event_types=EventType,
                             current_user=current_user)
    
    @app.route('/admin/event/edit/<int:event_id>', methods=['GET', 'POST'])
    @login_required
    def edit_event(event_id):
        """ویرایش رویداد"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        event = Event.query.get_or_404(event_id)
        
        if request.method == 'POST':
            event.title = request.form.get('title')
            event.description = request.form.get('description')
            event.event_type = EventType(request.form.get('event_type'))
            event.start_date = datetime.fromisoformat(request.form.get('start_date'))
            event.end_date = datetime.fromisoformat(request.form.get('end_date'))
            event.location = request.form.get('location')
            event.capacity = request.form.get('capacity', type=int)
            event.is_active = request.form.get('is_active') == 'on'
            
            # به‌روزرسانی تصویر
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # حذف تصویر قدیمی
                    if event.image:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    event.image = save_uploaded_file(file, 'events')
            
            db.session.commit()
            flash('رویداد با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('admin_events'))
        
        return render_template('admin/event_form.html',
                             event=event,
                             event_types=EventType,
                             current_user=current_user)
    
    @app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
    @login_required
    def delete_event(event_id):
        """حذف رویداد"""
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'}), 403
        
        event = Event.query.get_or_404(event_id)
        
        # حذف تصویر
        if event.image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # حذف ثبت‌نام‌های مرتبط
        Registration.query.filter_by(event_id=event_id).delete()
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'رویداد با موفقیت حذف شد'})
    
    @app.route('/admin/users')
    @login_required
    def admin_users():
        """مدیریت کاربران"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        users = User.query.order_by(User.created_at.desc()).all()
        
        return render_template('admin/users.html',
                             users=users,
                             current_user=current_user)
    
    @app.route('/admin/user/toggle/<int:user_id>', methods=['GET'])
    @login_required
    def toggle_user_status(user_id):
        """فعال/غیرفعال کردن کاربر - با ریدایرکت به جای JSON"""
        if not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('admin_users'))
        
        if user_id == current_user.id:
            flash('نمی‌توانید خودتان را غیرفعال کنید', 'error')
            return redirect(url_for('admin_users'))
        
        user = User.query.get_or_404(user_id)
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
    def change_user_role(user_id):
        """تغییر نقش کاربر"""
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in [r.value for r in UserRole]:
            return jsonify({'success': False, 'message': 'نقش نامعتبر است'}), 400
        
        user = User.query.get_or_404(user_id)
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
    
    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        """گزارش‌گیری"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        # ============= آمار شرکت در رویدادها =============
        event_participation_raw = db.session.query(
            Event,
            db.func.count(Registration.id).label('participants')
        ).outerjoin(Registration, Event.id == Registration.event_id)\
         .group_by(Event.id)\
         .order_by(db.func.count(Registration.id).desc())\
         .limit(10).all()
        
        # تبدیل به فرمت مناسب برای قالب
        event_participation = []
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
        
        # ============= آمار روزانه ثبت‌نام =============
        daily_registrations_raw = db.session.query(
            db.func.date(Registration.registration_date).label('date'),
            db.func.count(Registration.id).label('count')
        ).group_by(db.func.date(Registration.registration_date))\
         .order_by(db.func.date(Registration.registration_date).desc())\
         .limit(30).all()
        
        # تبدیل به فرمت مناسب برای قالب
        daily_registrations = []
        for date, count in daily_registrations_raw:
            daily_registrations.append({
                'date': date,
                'count': count
            })
        
        # ============= آمار کاربران بر اساس دانشگاه =============
        university_stats_raw = db.session.query(
            User.university,
            db.func.count(User.id).label('count')
        ).filter(User.university.isnot(None))\
         .group_by(User.university)\
         .order_by(db.func.count(User.id).desc())\
         .limit(10).all()
        
        # تبدیل به فرمت مناسب برای قالب
        university_stats = []
        for university, count in university_stats_raw:
            university_stats.append({
                'university': university,
                'count': count
            })
        
        return render_template('admin/reports.html',
                             event_participation=event_participation,
                             daily_registrations=daily_registrations,
                             university_stats=university_stats,
                             current_user=current_user)
    
    # ============================================
    # مسیرهای هوش مصنوعی قرآنی
    # ============================================
    
    @app.route('/ai/quran', methods=['GET', 'POST'])
    @login_required
    def ai_quran():
        """پرسش و پاسخ قرآنی"""
        answer = None
        question = ""
        recent_questions = []
        suggested_verses = []
        
        # آمار
        stats = {
            'total_verses': QuranVerse.query.count(),
            'total_questions': AIQuestion.query.count(),
            'user_questions': AIQuestion.query.filter_by(user_id=current_user.id).count()
        }
        
        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            
            if question:
                if AI_ENABLED:
                    # ذخیره سوال در دیتابیس
                    ai_question = AIQuestion(
                        user_id=current_user.id,
                        question=question
                    )
                    db.session.add(ai_question)
                    db.session.commit()
                    
                    answer = ask_quran_ai(question, current_user.id)
                    
                    # به‌روزرسانی پاسخ
                    ai_question.answer = answer.get('answer', '')
                    ai_question.is_quranic = answer.get('is_quranic', True)
                    db.session.commit()
                else:
                    # حالت ساده
                    answer = {
                        "success": True,
                        "answer": f"""📖 **پاسخ ساده به سوال قرآنی:**

**سوال شما:** {question}

**پاسخ:**
این سیستم هوش مصنوعی قرآنی در حال توسعه است. 
برای پاسخ دقیق به سوال شما، می‌توانید به تفاسیر معتبر قرآن مانند:
- تفسیر المیزان
- تفسیر نمونه
- تفسیر نور

مراجعه کنید.

**آیه نمونه:**
«بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ»
(سوره الفاتحة، آیه ۱)

هر کاری را با نام خداوند بخشنده مهربان شروع کنید.
                        """,
                        "is_quranic": True,
                        "main_verse": {
                            "surah": "الفاتحة",
                            "ayah": 1,
                            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                            "translation": "به نام خداوند بخشنده مهربان"
                        }
                    }
        
        # دریافت سوالات اخیر کاربر با فرمت تاریخ مناسب
        recent_questions_raw = AIQuestion.query.filter_by(
            user_id=current_user.id
        ).order_by(AIQuestion.created_at.desc()).limit(5).all()
        
        # تبدیل تاریخ به فرمت رشته برای نمایش در تمپلیت
        recent_questions = []
        for q in recent_questions_raw:
            question_obj = {
                'id': q.id,
                'question': q.question,
                'answer': q.answer,
                'created_at': q.created_at.strftime('%Y-%m-%d') if q.created_at else '',
                'is_quranic': q.is_quranic
            }
            recent_questions.append(question_obj)
        
        # دریافت آیات تصادفی
        suggested_verses = QuranVerse.query.order_by(db.func.random()).limit(3).all()
        
        return render_template('ai/quran.html',
                             answer=answer,
                             question=question,
                             recent_questions=recent_questions,
                             suggested_verses=suggested_verses,
                             stats=stats,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/history')
    @login_required
    def ai_history():
        """تاریخچه پرسش‌ها"""
        page = request.args.get('page', 1, type=int)
        
        questions = AIQuestion.query.filter_by(
            user_id=current_user.id
        ).order_by(AIQuestion.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        return render_template('ai/history.html',
                             questions=questions,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/ask', methods=['POST'])
    @login_required
    def ask_quran():
        """پرسش و پاسخ قرآنی (پردازش فرم)"""
        question = request.form.get('question', '').strip()
        
        if not question:
            flash('لطفاً سوال خود را وارد کنید', 'error')
            return redirect(url_for('ai_quran'))
        
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
        
        # دریافت سوالات اخیر کاربر با فرمت تاریخ مناسب
        recent_questions_raw = AIQuestion.query.filter_by(
            user_id=current_user.id
        ).order_by(AIQuestion.created_at.desc()).limit(5).all()
        
        recent_questions = []
        for q in recent_questions_raw:
            question_obj = {
                'id': q.id,
                'question': q.question,
                'answer': q.answer,
                'created_at': q.created_at.strftime('%Y-%m-%d') if q.created_at else '',
                'is_quranic': q.is_quranic
            }
            recent_questions.append(question_obj)
        
        return render_template('ai/quran.html',
                             answer=answer,
                             question=question,
                             recent_questions=recent_questions,
                             suggested_verses=QuranVerse.query.order_by(db.func.random()).limit(3).all(),
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/analyze', methods=['GET', 'POST'])
    @login_required
    def ai_analyze():
        """تحلیل محتوای قرآنی"""
        analysis = None
        text = ""
        
        if request.method == 'POST':
            text = request.form.get('text', '').strip()
            
            if text:
                if AI_ENABLED:
                    analysis = analyze_quranic_text(text, current_user.id)
                else:
                    # حالت ساده
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
    def ai_suggest():
        """پیشنهاد آیات بر اساس حال و هوا"""
        verses = []
        mood = "general"
        
        if request.method == 'POST':
            mood = request.form.get('mood', 'general')
            
            # پیشنهاد آیات بر اساس mood
            if mood == 'امید':
                # آیات امیدبخش
                verses = QuranVerse.query.filter(
                    QuranVerse.verse_persian.contains('رحمت') |
                    QuranVerse.verse_persian.contains('امید')
                ).order_by(db.func.random()).limit(5).all()
            elif mood == 'آرامش':
                # آیات آرامش‌بخش
                verses = QuranVerse.query.filter(
                    QuranVerse.verse_persian.contains('آرامش') |
                    QuranVerse.verse_persian.contains('اطمینان')
                ).order_by(db.func.random()).limit(5).all()
            elif mood == 'توکل':
                # آیات توکل
                verses = QuranVerse.query.filter(
                    QuranVerse.verse_persian.contains('توکل') |
                    QuranVerse.verse_persian.contains('توسل')
                ).order_by(db.func.random()).limit(5).all()
            else:
                # آیات تصادفی
                verses = QuranVerse.query.order_by(db.func.random()).limit(5).all()
            
            # اگر آیات کافی نبود، از آیات پیش‌فرض استفاده کن
            if not verses or len(verses) < 3:
                verses = QuranVerse.query.order_by(db.func.random()).limit(5).all()
        
        # تبدیل به فرمت مورد نیاز تمپلیت
        formatted_verses = []
        for verse in verses:
            formatted_verses.append({
                'text': verse.verse_arabic,
                'translation': verse.verse_persian,
                'surah': verse.surah_name,
                'ayah': verse.verse_number
            })
        
        return render_template('ai/suggest.html',
                             verses=formatted_verses,
                             mood=mood,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    @app.route('/ai/ask_api', methods=['POST'])
    @login_required
    def ai_ask_api():
        """API برای پرسش سوال (استفاده در AJAX)"""
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'سوال الزامی است'}), 400
        
        question = data['question'].strip()
        
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
        
        return jsonify(answer)
    
    # ============================================
    # API های هوش مصنوعی
    # ============================================
    
    @app.route('/ai/api/ask', methods=['POST'])
    @login_required
    def ai_api_ask():
        """API برای پرسش سوال"""
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'سوال الزامی است'}), 400
        
        question = data['question'].strip()
        
        # ذخیره در دیتابیس
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
            answer = {
                'success': True,
                'answer': f'پاسخ به سوال: {question}\n\nسیستم هوش مصنوعی در حال توسعه است.',
                'is_quranic': True
            }
        
        return jsonify(answer)
    
    @app.route('/ai/api/statistics')
    @login_required
    def ai_api_statistics():
        """API برای آمار سیستم"""
        if AI_ENABLED:
            stats = get_ai_statistics()
        else:
            # آمار از دیتابیس خودمان
            total_questions = AIQuestion.query.count()
            user_questions = AIQuestion.query.filter_by(user_id=current_user.id).count()
            
            stats = {
                'total_questions': total_questions,
                'user_questions': user_questions,
                'ai_enabled': False,
                'system_status': 'در حال توسعه'
            }
        
        return jsonify(stats)
    
    # ============================================
    # مسیرهای ادمین برای مدیریت هوش مصنوعی
    # ============================================
    
    @app.route('/admin/ai', methods=['GET'])
    @login_required
    def admin_ai_dashboard():
        """داشبورد مدیریت هوش مصنوعی"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        if AI_ENABLED:
            stats = get_ai_statistics()
            recent_questions = get_recent_qa(limit=20)
        else:
            # آمار از دیتابیس خودمان
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
        
        return render_template('admin/ai_dashboard.html',
                             stats=stats,
                             recent_questions=recent_questions,
                             ai_enabled=AI_ENABLED,
                             current_user=current_user)
    
    # ============================================
    # API های عمومی
    # ============================================
    
    @app.route('/api/events/upcoming')
    def api_upcoming_events():
        """API دریافت رویدادهای پیش‌رو"""
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
    
    @app.route('/api/user/stats')
    @login_required
    def api_user_stats():
        """API آمار کاربر"""
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
    
    # ============================================
    # مسیر گزارش مشکل
    # ============================================
    
    @app.route('/report-issue', methods=['GET', 'POST'])
    @login_required
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
    def admin_announcement():
        """ارسال اعلامیه به همه کاربران"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            message = request.form.get('message')
            priority = request.form.get('priority', 'normal')
            
            if not title or not message:
                flash('عنوان و متن اعلامیه الزامی است.', 'error')
                return redirect(url_for('admin_announcement'))
            
            # دریافت همه کاربران فعال
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
            return redirect(url_for('admin_dashboard'))
        
        # تعداد کاربران فعال برای نمایش در فرم
        users_count = User.query.filter_by(is_active=True).count()
        return render_template('admin/announcement.html', 
                             current_user=current_user,
                             users_count=users_count)
    
    @app.route('/admin/announcements')
    @login_required
    def admin_announcements_list():
        """لیست اعلامیه‌های ارسال شده"""
        if not current_user.is_admin():
            flash('دسترسی به این بخش مجاز نیست.', 'error')
            return redirect(url_for('dashboard'))
        
        # دریافت آخرین اعلان‌های ارسالی (گروه‌بندی بر اساس عنوان)
        from sqlalchemy import func
        
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
        
        return render_template('circles/list.html',
                             circles=circles,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>')
    def circle_detail(circle_id):
        """جزئیات حلقه تلاوت"""
        circle = QuranCircle.query.get_or_404(circle_id)
        
        # بررسی عضویت کاربر
        is_member = False
        if current_user.is_authenticated:
            membership = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id
            ).first()
            is_member = membership is not None
        
        # دریافت جلسات
        upcoming_sessions = circle.sessions.filter(
            CircleSession.session_date >= datetime.now().date()
        ).order_by(CircleSession.session_date).limit(5).all()
        
        past_sessions = circle.sessions.filter(
            CircleSession.session_date < datetime.now().date()
        ).order_by(CircleSession.session_date.desc()).limit(5).all()
        
        # دریافت فایل‌ها
        files = circle.files.order_by(CircleFile.uploaded_at.desc()).limit(10).all()
        
        return render_template('circles/detail.html',
                             circle=circle,
                             is_member=is_member,
                             upcoming_sessions=upcoming_sessions,
                             past_sessions=past_sessions,
                             files=files,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>/join', methods=['POST'])
    @login_required
    def join_circle(circle_id):
        """عضویت در حلقه تلاوت"""
        circle = QuranCircle.query.get_or_404(circle_id)
        
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
    def leave_circle(circle_id):
        """خروج از حلقه تلاوت"""
        membership = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=current_user.id,
            is_active=True
        ).first_or_404()
        
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
    def circle_sessions(circle_id):
        """لیست جلسات حلقه"""
        circle = QuranCircle.query.get_or_404(circle_id)
        
        # بررسی دسترسی
        is_member = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده جلسات باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        query = circle.sessions
        
        if status == 'upcoming':
            query = query.filter(CircleSession.session_date >= datetime.now().date())
        elif status == 'past':
            query = query.filter(CircleSession.session_date < datetime.now().date())
        
        sessions = query.order_by(CircleSession.session_date.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        return render_template('circles/sessions.html',
                             circle=circle,
                             sessions=sessions,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>')
    @login_required
    def session_detail(session_id):
        """جزئیات جلسه"""
        session = CircleSession.query.get_or_404(session_id)
        circle = session.circle
        
        # بررسی دسترسی
        is_member = CircleMember.query.filter_by(
            circle_id=circle.id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        # دریافت حضور و غیاب
        attendances = session.attendances.all()
        
        # دریافت فایل‌ها
        files = session.files.order_by(SessionFile.uploaded_at.desc()).all()
        
        return render_template('circles/session_detail.html',
                             session=session,
                             circle=circle,
                             attendances=attendances,
                             files=files,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>/attendance', methods=['POST'])
    @login_required
    def mark_attendance(session_id):
        """ثبت حضور و غیاب"""
        session = CircleSession.query.get_or_404(session_id)
        
        # فقط استاد یا مدیر می‌توانند ثبت کنند
        is_teacher = CircleMember.query.filter_by(
            circle_id=session.circle_id,
            user_id=current_user.id,
            role='teacher',
            is_active=True
        ).first()
        
        if not is_teacher and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('session_detail', session_id=session_id))
        
        data = request.get_json()
        member_id = data.get('member_id')
        attended = data.get('attended', False)
        late_minutes = data.get('late_minutes', 0)
        excuse = data.get('excuse', '')
        
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


    @app.route('/circle/<int:circle_id>/files')
    @login_required
    def circle_files(circle_id):
        """فایل‌های حلقه"""
        circle = QuranCircle.query.get_or_404(circle_id)
        
        # بررسی عضویت
        is_member = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده فایل‌ها باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        files = circle.files.order_by(CircleFile.uploaded_at.desc()).all()
        session_files = SessionFile.query.join(CircleSession)\
                                        .filter(CircleSession.circle_id == circle_id)\
                                        .order_by(SessionFile.uploaded_at.desc()).all()
        
        return render_template('circles/files.html',
                             circle=circle,
                             files=files,
                             session_files=session_files,
                             current_user=current_user)


    @app.route('/circle/file/<int:file_id>/download')
    @login_required
    def download_circle_file(file_id):
        """دانلود فایل"""
        file = CircleFile.query.get_or_404(file_id)
        
        # بررسی دسترسی
        if not file.is_public:
            is_member = CircleMember.query.filter_by(
                circle_id=file.circle_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not is_member and not current_user.is_admin():
                flash('دسترسی غیرمجاز', 'error')
                return redirect(url_for('circles_list'))
        
        file.download_count += 1
        db.session.commit()
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)


    @app.route('/circle/session-file/<int:file_id>/download')
    @login_required
    def download_session_file(file_id):
        """دانلود فایل جلسه"""
        file = SessionFile.query.get_or_404(file_id)
        session = file.session
        
        # بررسی عضویت
        is_member = CircleMember.query.filter_by(
            circle_id=session.circle_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        file.download_count += 1
        db.session.commit()
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)
    
    # ============================================
    # مسیرهای جدید ثبت‌نام (اینجا قرار می‌گیرند)
    # ============================================
    
    @app.route('/auth/register/choice')
    def register_choice():
        """صفحه انتخاب نوع ثبت‌نام"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('auth/register_choice.html')

    @app.route('/auth/register/professor', methods=['GET', 'POST'])
    def register_professor():
        """ثبت‌نام استاد"""
        if current_user.is_authenticated:
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
                is_verified=False,
                academic_rank=academic_rank,
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
                is_active=False
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                notification = Notification(
                    user_id=admin.id,
                    title='درخواست جدید همکاری استاد',
                    message=f'استاد {first_name} {last_name} درخواست همکاری داده است.'
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_professor.html')

    @app.route('/auth/register/staff', methods=['GET', 'POST'])
    def register_staff():
        """ثبت‌نام کارمند امور فرهنگی"""
        if current_user.is_authenticated:
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
                is_verified=False,
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
                is_active=False
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                notification = Notification(
                    user_id=admin.id,
                    title='درخواست جدید همکاری کارمند',
                    message=f'کارمند {first_name} {last_name} درخواست همکاری داده است.'
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_staff.html')
    
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
            return date_obj.strftime('%Y-%m-%d')
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