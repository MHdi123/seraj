# decorators.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def verified_required(f):
    """
    دکوریتور برای بررسی تأیید شدن کاربر
    فقط کاربرانی که تأیید شده‌اند می‌توانند به مسیر دسترسی داشته باشند
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('لطفاً ابتدا وارد شوید.', 'warning')
            return redirect(url_for('login'))
        
        # ادمین همیشه دسترسی دارد
        if current_user.is_admin():
            return f(*args, **kwargs)
        
        # بررسی تأیید برای استاد و کارمند
        if current_user.user_type in ['professor', 'staff']:
            if not current_user.is_verified:
                flash('⚠️ حساب کاربری شما هنوز توسط مدیر تأیید نشده است.', 'warning')
                return redirect(url_for('not_approved'))
            elif not current_user.is_active:
                flash('⚠️ حساب کاربری شما غیرفعال شده است.', 'error')
                return redirect(url_for('logout'))
        
        # دانشجوها خودکار دسترسی دارند
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """
    دکوریتور برای بررسی دسترسی کارمندان و اساتید
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('لطفاً ابتدا وارد شوید.', 'warning')
            return redirect(url_for('login'))
        
        if current_user.is_admin():
            return f(*args, **kwargs)
        
        if current_user.user_type not in ['professor', 'staff']:
            flash('⛔ دسترسی به این بخش فقط برای اساتید و کارمندان مجاز است.', 'error')
            return redirect(url_for('dashboard'))
        
        if not current_user.is_verified:
            flash('⚠️ حساب کاربری شما هنوز تأیید نشده است.', 'warning')
            return redirect(url_for('not_approved'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    دکوریتور برای بررسی ادمین بودن
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('لطفاً ابتدا وارد شوید.', 'warning')
            return redirect(url_for('login'))
        
        if not current_user.is_admin():
            flash('⛔ دسترسی به این بخش فقط برای مدیران سیستم مجاز است.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function