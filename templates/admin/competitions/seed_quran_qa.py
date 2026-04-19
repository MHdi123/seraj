# seed_quran_qa.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import QuranQA, QuranSuggestion

app = create_app()

with app.app_context():
    # حذف داده‌های قدیمی (اختیاری)
    # QuranQA.query.delete()
    # QuranSuggestion.query.delete()
    
    # داده‌های پرسش و پاسخ
    qa_data = [
        # ... داده‌هایی که قبلاً تعریف کردیم ...
    ]
    
    for data in qa_data:
        exists = QuranQA.query.filter_by(question=data['question']).first()
        if not exists:
            qa = QuranQA(**data)
            db.session.add(qa)
    
    # داده‌های پیشنهادات
    suggestions_data = [
        # ... داده‌هایی که قبلاً تعریف کردیم ...
    ]
    
    for data in suggestions_data:
        exists = QuranSuggestion.query.filter_by(
            mood=data['mood'], 
            verse_text=data['verse_text']
        ).first()
        if not exists:
            sug = QuranSuggestion(**data)
            db.session.add(sug)
    
    db.session.commit()
    print("✅ داده‌های هوش مصنوعی قرآنی با موفقیت وارد شدند!")