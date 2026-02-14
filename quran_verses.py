from datetime import date, datetime
from models import QuranVerse
from app import app
import random
import jdatetime

def get_daily_verse():
    """برمی‌گرداند آیه روز با اطلاعات کامل"""
    with app.app_context():
        # دریافت همه آیات فعال
        verses = QuranVerse.query.filter_by(is_active=True).all()
        
        if not verses:
            return None
        
        # انتخاب آیه بر اساس تاریخ (تغییر روزانه)
        today = date.today()
        random.seed(today.toordinal())
        verse = random.choice(verses)
        
        # ساخت آبجکت برای تمپلیت
        daily_verse = {
            'title': 'آیه روز',  # یا هر عنوان دلخواه
            'verse': verse.verse_persian,
            'surah': verse.surah_name,  # فرض می‌کنم این فیلد وجود داره
            'verse_number': verse.verse_number,  # شماره آیه
            'translation': verse.translation,  # ترجمه
            'arabic_text': verse.arabic_text  # متن عربی
        }
        
        return daily_verse

def get_persian_date():
    """برمی‌گرداند تاریخ امروز به شمسی"""
    today = jdatetime.date.today()
    return today.strftime("%d %B %Y")  # مثلاً ۲۵ اسفند ۱۴۰۲