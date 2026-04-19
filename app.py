# app.py
from flask import Flask, render_template, request, jsonify
from extensions import db, login_manager
from config import Config
from models import User
from routes import init_routes
from datetime import datetime
import os
import jdatetime
from flask_migrate import Migrate
import sqlite3

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # =================== ساخت پوشه‌های مورد نیاز ===================
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs('static/fonts', exist_ok=True)
    os.makedirs('static/uploads/banners', exist_ok=True)
    os.makedirs('templates/auth', exist_ok=True)
    os.makedirs('templates/participant', exist_ok=True)
    os.makedirs('templates/admin', exist_ok=True)

    # =================== دیتابیس ===================
    db.init_app(app)
    Migrate(app, db)

    # =================== Flask-Login ===================
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد شوید.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # =================== توابع کمکی برای تبدیل تاریخ ===================
    def to_persian_numbers(text):
        """تبدیل اعداد انگلیسی به فارسی"""
        if text is None:
            return ''
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        english_digits = '0123456789'
        translation_table = str.maketrans(english_digits, persian_digits)
        return str(text).translate(translation_table)

    def parse_date_string(date_str):
        """تبدیل رشته تاریخ به شیء datetime با فرمت‌های مختلف"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d',
            '%d-%m-%Y %H:%M:%S',
            '%d-%m-%Y %H:%M',
            '%d-%m-%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def convert_to_jalali(date_obj):
        """تبدیل تاریخ میلادی به شمسی"""
        if date_obj is None:
            return None
        
        try:
            if isinstance(date_obj, datetime):
                return jdatetime.date.fromgregorian(date=date_obj.date())
            elif hasattr(date_obj, 'date') and callable(getattr(date_obj, 'date')):
                return jdatetime.date.fromgregorian(date=date_obj.date())
            else:
                return None
        except:
            return None

    # =================== فیلترهای Jinja2 ===================
    
    @app.template_filter('persian_date')
    def persian_date_filter(dt):
        """
        تبدیل تاریخ میلادی به شمسی (فقط تاریخ)
        ورودی: datetime, date, string
        خروجی: string (format: YYYY/MM/DD)
        """
        if not dt:
            return ''
        
        # اگر شیء datetime یا date است
        if isinstance(dt, (datetime, jdatetime.date)) or hasattr(dt, 'date'):
            try:
                if isinstance(dt, datetime):
                    jalali_date = convert_to_jalali(dt)
                elif hasattr(dt, 'date'):
                    jalali_date = convert_to_jalali(dt.date())
                else:
                    jalali_date = dt
                
                if jalali_date:
                    return jalali_date.strftime('%Y/%m/%d')
                else:
                    return str(dt)
            except:
                return str(dt)
        
        # اگر string است
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    return jalali_date.strftime('%Y/%m/%d')
            return dt
        
        return str(dt)

    @app.template_filter('persian_datetime')
    def persian_datetime_filter(dt):
        """
        تبدیل تاریخ و زمان میلادی به شمسی
        ورودی: datetime, string
        خروجی: string (format: YYYY/MM/DD - HH:MM)
        """
        if not dt:
            return ''
        
        # اگر شیء datetime است
        if isinstance(dt, datetime):
            try:
                jalali_date = convert_to_jalali(dt)
                if jalali_date:
                    return f"{jalali_date.strftime('%Y/%m/%d')} - {dt.strftime('%H:%M')}"
                else:
                    return dt.strftime('%Y/%m/%d %H:%M')
            except:
                return dt.strftime('%Y/%m/%d %H:%M')
        
        # اگر string است
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    return f"{jalali_date.strftime('%Y/%m/%d')} - {parsed_date.strftime('%H:%M')}"
            return dt
        
        return str(dt)

    @app.template_filter('persian_date_full')
    def persian_date_full_filter(dt):
        """
        تبدیل تاریخ میلادی به شمسی با نام ماه
        ورودی: datetime, date, string
        خروجی: string (format: DAY Month YYYY)
        """
        if not dt:
            return ''
        
        month_names = {
            1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر', 5: 'مرداد', 6: 'شهریور',
            7: 'مهر', 8: 'آبان', 9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
        }
        
        # اگر شیء datetime یا date است
        if isinstance(dt, (datetime, jdatetime.date)) or hasattr(dt, 'date'):
            try:
                if isinstance(dt, datetime):
                    jalali_date = convert_to_jalali(dt)
                elif hasattr(dt, 'date'):
                    jalali_date = convert_to_jalali(dt.date())
                else:
                    jalali_date = dt
                
                if jalali_date:
                    month_name = month_names.get(jalali_date.month, '')
                    return f"{jalali_date.day} {month_name} {jalali_date.year}"
                else:
                    return str(dt)
            except:
                return str(dt)
        
        # اگر string است
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    month_name = month_names.get(jalali_date.month, '')
                    return f"{jalali_date.day} {month_name} {jalali_date.year}"
            return dt
        
        return str(dt)

    @app.template_filter('persian_date_persian')
    def persian_date_persian_filter(dt):
        """
        تبدیل تاریخ میلادی به شمسی با اعداد فارسی
        ورودی: datetime, date, string
        خروجی: string (format: YYYY/MM/DD با اعداد فارسی)
        """
        result = persian_date_filter(dt)
        return to_persian_numbers(result)

    @app.template_filter('persian_datetime_persian')
    def persian_datetime_persian_filter(dt):
        """
        تبدیل تاریخ و زمان میلادی به شمسی با اعداد فارسی
        ورودی: datetime, string
        خروجی: string (format: YYYY/MM/DD - HH:MM با اعداد فارسی)
        """
        result = persian_datetime_filter(dt)
        return to_persian_numbers(result)

    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        """
        محاسبه زمان گذشته نسبت به الان
        ورودی: datetime, string
        خروجی: string (مثال: ۲ ساعت پیش)
        """
        if not dt:
            return ''
        
        # تبدیل به datetime اگر string است
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if not parsed_date:
                return dt
            dt = parsed_date
        
        if not isinstance(dt, datetime):
            return str(dt)
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f'{to_persian_numbers(str(years))} سال پیش'
        elif diff.days > 30:
            months = diff.days // 30
            return f'{to_persian_numbers(str(months))} ماه پیش'
        elif diff.days > 0:
            return f'{to_persian_numbers(str(diff.days))} روز پیش'
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f'{to_persian_numbers(str(hours))} ساعت پیش'
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f'{to_persian_numbers(str(minutes))} دقیقه پیش'
        else:
            return 'همین الان'

    @app.template_filter('to_jalali')
    def to_jalali_filter(date_str):
        """
        فیلتر ساده برای تبدیل تاریخ (نگهداری برای سازگاری)
        """
        return persian_date_filter(date_str)

    @app.template_filter('persian_number')
    def persian_number_filter(number):
        """
        تبدیل اعداد به فارسی
        ورودی: عدد یا رشته
        خروجی: string با اعداد فارسی
        """
        if number is None:
            return ''
        return to_persian_numbers(str(number))

    @app.template_filter('event_type_fa')
    def event_type_fa_filter(event_type_value):
        """
        تبدیل نوع رویداد به فارسی
        ورودی: string یا Enum
        خروجی: string
        """
        event_types = {
            'workshop': 'کارگاه',
            'competition': 'مسابقه',
            'halaqah': 'حلقه تلاوت',
            'lecture': 'سخنرانی',
            'other': 'سایر'
        }
        
        # اگر Enum است
        if hasattr(event_type_value, 'value'):
            event_type_value = event_type_value.value
        
        return event_types.get(event_type_value, str(event_type_value))

    @app.template_filter('event_status_fa')
    def event_status_fa_filter(status):
        """
        تبدیل وضعیت رویداد به فارسی
        ورودی: string
        خروجی: string
        """
        status_map = {
            'upcoming': 'پیش‌رو',
            'ongoing': 'در حال برگزاری',
            'completed': 'پایان یافته',
            'cancelled': 'لغو شده'
        }
        return status_map.get(status, str(status))

    @app.template_filter('weekday_fa')
    def weekday_fa_filter(date_obj):
        """
        دریافت نام روز هفته به فارسی
        ورودی: datetime, date
        خروجی: string
        """
        if not date_obj:
            return ''
        
        weekdays = [
            'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 
            'جمعه', 'شنبه', 'یک‌شنبه'
        ]
        
        try:
            if isinstance(date_obj, (datetime, jdatetime.date)):
                return weekdays[date_obj.weekday()]
            elif hasattr(date_obj, 'weekday'):
                return weekdays[date_obj.weekday()]
        except:
            pass
        
        return ''

    # =================== Context Processors ===================
    
    @app.context_processor
    def inject_now():
        """اضافه کردن زمان فعلی به تمام قالب‌ها"""
        return {
            'now': datetime.now(),
            'today': datetime.now().date(),
            'now_persian': to_persian_numbers(datetime.now().strftime('%Y/%m/%d %H:%M'))
        }

    @app.context_processor
    def inject_quran_verse():
        """اضافه کردن آیه روز به تمام قالب‌ها"""
        # اینجا می‌توانید منطق دریافت آیه روز را پیاده‌سازی کنید
        return {
            'daily_verse': None,
            'current_date': datetime.now(),
            'current_date_str': datetime.now().strftime('%Y-%m-%d'),
            'current_date_persian': to_persian_numbers(
                persian_date_filter(datetime.now())
            )
        }

    @app.context_processor
    def utility_processor():
        """توابع کمکی برای استفاده در قالب‌ها"""
        
        def endpoint_exists(endpoint):
            """بررسی وجود endpoint"""
            try:
                all_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
                return endpoint in all_endpoints
            except:
                return False
        
        def url_for_other_page(page):
            """ایجاد URL برای صفحه‌بندی"""
            args = request.view_args.copy()
            args['page'] = page
            return url_for(request.endpoint, **args)
        
        return dict(
            endpoint_exists=endpoint_exists,
            url_for_other_page=url_for_other_page
        )

    # =================== مدیریت خطاها ===================
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # =================== روت‌ها ===================
    init_routes(app)

    # =================== FCM Token Endpoint (MOVED TO routes.py) ===================
    # این تابع به فایل routes.py منتقل شده است تا از تکرار جلوگیری شود
    # مسیر /save-token در routes.py با کیفیت بهتر پیاده‌سازی شده است
    # و از دکوریتورهای login_required و verified_required استفاده می‌کند

    # =================== Health Check ===================
    @app.route("/health")
    def health_check():
        """بررسی سلامت برنامه"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "persian_time": to_persian_numbers(
                persian_datetime_filter(datetime.now())
            )
        })

    return app


# =================== اجرای اپلیکیشن ===================
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)