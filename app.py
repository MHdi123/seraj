from flask import Flask, render_template, request, jsonify, url_for
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

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs('static/fonts', exist_ok=True)
    os.makedirs('static/uploads/banners', exist_ok=True)
    os.makedirs('templates/auth', exist_ok=True)
    os.makedirs('templates/participant', exist_ok=True)
    os.makedirs('templates/admin', exist_ok=True)

    db.init_app(app)
    Migrate(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد شوید.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    def to_persian_numbers(text):
        if text is None:
            return ''
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        english_digits = '0123456789'
        translation_table = str.maketrans(english_digits, persian_digits)
        return str(text).translate(translation_table)

    def parse_date_string(date_str):
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

    @app.template_filter('persian_date')
    def persian_date_filter(dt):
        if not dt:
            return ''
        
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
        
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    return jalali_date.strftime('%Y/%m/%d')
            return dt
        
        return str(dt)

    @app.template_filter('persian_datetime')
    def persian_datetime_filter(dt, format="%Y/%m/%d %H:%M:%S"):
        if not dt:
            return ''
        
        if isinstance(dt, datetime):
            try:
                jalali_date = convert_to_jalali(dt)
                if jalali_date:
                    jalali_datetime = jdatetime.datetime(
                        jalali_date.year, 
                        jalali_date.month, 
                        jalali_date.day,
                        dt.hour,
                        dt.minute,
                        dt.second
                    )
                    return jalali_datetime.strftime(format)
                else:
                    return dt.strftime(format)
            except:
                return dt.strftime(format)
        
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    jalali_datetime = jdatetime.datetime(
                        jalali_date.year,
                        jalali_date.month,
                        jalali_date.day,
                        parsed_date.hour,
                        parsed_date.minute,
                        parsed_date.second
                    )
                    return jalali_datetime.strftime(format)
                return parsed_date.strftime(format)
            return dt
        
        return str(dt)

    @app.template_filter('persian_time')
    def persian_time_filter(dt):
        if not dt:
            return ''
        
        if isinstance(dt, datetime):
            return dt.strftime('%H:%M:%S')
        
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                return parsed_date.strftime('%H:%M:%S')
            return dt
        
        return str(dt)

    @app.template_filter('persian_datetime_full')
    def persian_datetime_full_filter(dt):
        if not dt:
            return ''
        
        if isinstance(dt, datetime):
            try:
                jalali_date = convert_to_jalali(dt)
                if jalali_date:
                    return f"{jalali_date.strftime('%Y/%m/%d')} - {dt.strftime('%H:%M')}"
                else:
                    return dt.strftime('%Y/%m/%d %H:%M')
            except:
                return dt.strftime('%Y/%m/%d %H:%M')
        
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
        if not dt:
            return ''
        
        month_names = {
            1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر', 5: 'مرداد', 6: 'شهریور',
            7: 'مهر', 8: 'آبان', 9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
        }
        
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
        result = persian_date_filter(dt)
        return to_persian_numbers(result)

    @app.template_filter('persian_datetime_persian')
    def persian_datetime_persian_filter(dt):
        result = persian_datetime_full_filter(dt)
        return to_persian_numbers(result)

    @app.template_filter('persian_time_persian')
    def persian_time_persian_filter(dt):
        result = persian_time_filter(dt)
        return to_persian_numbers(result)

    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        if not dt:
            return ''
        
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

    @app.template_filter('timesince')
    def timesince_filter(dt, default="چندی پیش"):
        if not dt:
            return default
        return time_ago_filter(dt)

    @app.template_filter('to_jalali')
    def to_jalali_filter(date_str):
        return persian_date_filter(date_str)

    @app.template_filter('persian_number')
    def persian_number_filter(number):
        if number is None:
            return ''
        return to_persian_numbers(str(number))

    @app.template_filter('event_type_fa')
    def event_type_fa_filter(event_type_value):
        event_types = {
            'workshop': 'کارگاه',
            'competition': 'مسابقه',
            'halaqah': 'حلقه تلاوت',
            'lecture': 'سخنرانی',
            'other': 'سایر'
        }
        
        if hasattr(event_type_value, 'value'):
            event_type_value = event_type_value.value
        
        return event_types.get(event_type_value, str(event_type_value))

    @app.template_filter('event_status_fa')
    def event_status_fa_filter(status):
        status_map = {
            'upcoming': 'پیش‌رو',
            'ongoing': 'در حال برگزاری',
            'completed': 'پایان یافته',
            'cancelled': 'لغو شده'
        }
        return status_map.get(status, str(status))

    @app.template_filter('weekday_fa')
    def weekday_fa_filter(date_obj):
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

    @app.context_processor
    def inject_now():
        return {
            'now': datetime.now(),
            'today': datetime.now().date(),
            'now_persian': to_persian_numbers(datetime.now().strftime('%Y/%m/%d %H:%M'))
        }

    @app.context_processor
    def inject_quran_verse():
        return {
            'daily_verse': None,
            'current_date': datetime.now(),
            'current_date_str': datetime.now().strftime('%Y-%m-%d'),
            'current_date_persian': to_persian_numbers(
                persian_date_filter(datetime.now())
            )
        }
    
    @app.template_filter('persian_datetime_precise')
    def persian_datetime_precise_filter(dt, format="%Y/%m/%d %H:%M"):
        """نمایش تاریخ شمسی با ساعت و دقیقه - فرمت: ۱۴۰۲/۰۵/۲۱ ۱۵:۳۰"""
        if not dt:
            return ''
        
        if isinstance(dt, datetime):
            try:
                jalali_date = convert_to_jalali(dt)
                if jalali_date:
                    jalali_datetime = jdatetime.datetime(
                        jalali_date.year, 
                        jalali_date.month, 
                        jalali_date.day,
                        dt.hour,
                        dt.minute,
                        dt.second
                    )
                    result = jalali_datetime.strftime(format)
                    return to_persian_numbers(result)
                else:
                    return to_persian_numbers(dt.strftime(format))
            except:
                return to_persian_numbers(dt.strftime(format))
        
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if parsed_date:
                jalali_date = convert_to_jalali(parsed_date)
                if jalali_date:
                    jalali_datetime = jdatetime.datetime(
                        jalali_date.year,
                        jalali_date.month,
                        jalali_date.day,
                        parsed_date.hour,
                        parsed_date.minute,
                        parsed_date.second
                    )
                    result = jalali_datetime.strftime(format)
                    return to_persian_numbers(result)
                return to_persian_numbers(parsed_date.strftime(format))
            return dt
        
        return str(dt)

    @app.template_filter('precise_time_ago')
    def precise_time_ago_filter(dt):
        """محاسبه زمان گذشته با دقت دقیقه و اعداد فارسی"""
        if not dt:
            return 'امروز'
        
        if isinstance(dt, str):
            parsed_date = parse_date_string(dt)
            if not parsed_date:
                return dt
            dt = parsed_date
        
        if not isinstance(dt, datetime):
            return str(dt)
        
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f'{to_persian_numbers(str(int(seconds)))} ثانیه پیش'
        
        if seconds < 3600:
            minutes = int(seconds // 60)
            return f'{to_persian_numbers(str(minutes))} دقیقه پیش'
        
        if seconds < 86400:  # کمتر از 24 ساعت
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if minutes > 0:
                return f'{to_persian_numbers(str(hours))} ساعت و {to_persian_numbers(str(minutes))} دقیقه پیش'
            return f'{to_persian_numbers(str(hours))} ساعت پیش'
        
        if seconds < 604800:  # کمتر از 7 روز
            days = int(seconds // 86400)
            return f'{to_persian_numbers(str(days))} روز پیش'
        
        # بیشتر از یک هفته: نمایش تاریخ کامل
        return persian_datetime_precise_filter(dt)
    @app.context_processor
    def utility_processor():
        def endpoint_exists(endpoint):
            try:
                all_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
                return endpoint in all_endpoints
            except:
                return False
        
        def url_for_other_page(page):
            args = request.view_args.copy()
            args['page'] = page
            return url_for(request.endpoint, **args)
        
        return dict(
            endpoint_exists=endpoint_exists,
            url_for_other_page=url_for_other_page
        )

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    init_routes(app)

    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "persian_time": to_persian_numbers(
                persian_datetime_full_filter(datetime.now())
            )
        })

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)