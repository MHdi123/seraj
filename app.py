# app.py
from flask import Flask, render_template
from extensions import db, login_manager
from config import Config
from models import User
from routes import init_routes
from datetime import datetime
import os
import jdatetime
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ========== پوشه‌های مورد نیاز ==========
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('static/fonts', exist_ok=True)
    os.makedirs('templates/auth', exist_ok=True)
    os.makedirs('templates/participant', exist_ok=True)
    os.makedirs('templates/admin', exist_ok=True)

    # ========== دیتابیس ==========
    db.init_app(app)
    Migrate(app, db)

    # ========== Flask-Login ==========
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد شوید.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ========== فیلترهای Jinja2 ==========
    @app.template_filter('persian_date')
    def persian_date(dt):
        if dt is None:
            return ''
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d')
            except:
                return dt
        if isinstance(dt, datetime):
            try:
                jalali_date = jdatetime.date.fromgregorian(date=dt.date())
                return jalali_date.strftime('%Y/%m/%d')
            except:
                return dt.strftime('%Y/%m/%d')
        return str(dt)

    @app.template_filter('persian_datetime')
    def persian_datetime(dt):
        if dt is None:
            return ''
        if isinstance(dt, datetime):
            try:
                jalali_date = jdatetime.date.fromgregorian(date=dt.date())
                return f"{jalali_date.strftime('%Y/%m/%d')} - {dt.strftime('%H:%M')}"
            except:
                return dt.strftime('%Y/%m/%d %H:%M')
        return str(dt)

    @app.template_filter('time_ago')
    def time_ago(dt):
        if dt is None:
            return ''
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except:
                return dt
        now = datetime.utcnow()
        diff = now - dt
        if diff.days > 365:
            return f'{diff.days // 365} سال پیش'
        elif diff.days > 30:
            return f'{diff.days // 30} ماه پیش'
        elif diff.days > 0:
            return f'{diff.days} روز پیش'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} ساعت پیش'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60} دقیقه پیش'
        else:
            return 'همین الان'

    @app.template_filter('to_jalali')
    def to_jalali(date_str):
        if not date_str:
            return ''
        try:
            if isinstance(date_str, str):
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                jalali_date = jdatetime.date.fromgregorian(date=dt.date())
                return jalali_date.strftime('%Y/%m/%d')
        except:
            pass
        return date_str

    # ========== Context Processors ==========
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow(), 'today': datetime.now().date()}

    @app.context_processor
    def inject_quran_verse():
        return {
            'daily_verse': None,
            'current_date': datetime.now(),
            'current_date_str': datetime.now().strftime('%Y-%m-%d')
        }

    # ========== مدیریت خطاها ==========
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # ========== روت‌ها ==========
    init_routes(app)

    return app

# فقط اپلیکیشن را بسازیم
app = create_app()
