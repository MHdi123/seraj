# quran_ai_service.py
import re
import random
import json
from sqlalchemy import or_, and_
from models import SerajQA, QuranVerse, Hadith, SerajCategory

class QuranAIService:
    """سرویس هوشمند پاسخگویی به سوالات قرآنی"""
    
    def __init__(self, db_instance):
        self.db = db_instance
    
    def find_best_answer(self, question, user_id=None):
        """پیدا کردن بهترین پاسخ با الگوریتم جستجوی هوشمند"""
        question_clean = self._normalize(question)
        
        # 1. جستجوی دقیق
        exact = SerajQA.query.filter(
            SerajQA.is_active == True,
            SerajQA.question == question
        ).first()
        if exact:
            return self._format_response(exact, question)
        
        # 2. جستجوی حاوی عبارت
        contains = SerajQA.query.filter(
            SerajQA.is_active == True,
            or_(
                SerajQA.question.ilike(f'%{question}%'),
                SerajQA.question.ilike(f'%{question_clean}%')
            )
        ).order_by(SerajQA.priority.desc()).first()
        if contains:
            return self._format_response(contains, question)
        
        # 3. جستجوی کلمات کلیدی
        keywords = self._extract_keywords(question)
        for keyword in keywords:
            if len(keyword) < 3:
                continue
            kw_match = SerajQA.query.filter(
                SerajQA.is_active == True,
                SerajQA.keywords.ilike(f'%{keyword}%')
            ).order_by(SerajQA.priority.desc()).first()
            if kw_match:
                return self._format_response(kw_match, question)
        
        # 4. جستجوی دسته‌بندی
        category = self._detect_category(question)
        if category:
            cat_match = SerajQA.query.filter(
                SerajQA.category_id == category.id,
                SerajQA.is_active == True
            ).first()
            if cat_match:
                return self._format_response(cat_match, question)
        
        # 5. پاسخ هوشمند پیش‌فرض با آیات مرتبط
        return self._generate_smart_response(question)
    
    def _format_response(self, qa_obj, original_question):
        """فرمت کردن پاسخ با آیات مرتبط و پیشنهادات"""
        # افزایش بازدید
        qa_obj.view_count = (qa_obj.view_count or 0) + 1
        self.db.session.commit()
        
        # دریافت آیات مرتبط از دیتابیس
        related_verses = self._get_related_verses(qa_obj.keywords or qa_obj.question)
        
        # پیشنهادات مشابه
        suggestions = self._get_suggestions(qa_obj.category_id, qa_obj.id)
        
        return {
            'success': True,
            'answer': qa_obj.answer_full if qa_obj.answer_full else qa_obj.answer,
            'related_verses': related_verses,
            'suggestions': suggestions,
            'qa_id': qa_obj.id,
            'category_id': qa_obj.category_id
        }
    
    def _get_related_verses(self, keyword, limit=3):
        """دریافت آیات مرتبط با موضوع"""
        verses = QuranVerse.query.filter(
            or_(
                QuranVerse.keywords.ilike(f'%{keyword}%'),
                QuranVerse.topic.ilike(f'%{keyword}%')
            ),
            QuranVerse.is_active == True
        ).limit(limit).all()
        
        result = []
        for v in verses:
            result.append({
                'text': v.verse_arabic,
                'translation': v.verse_persian or v.translation,
                'surah': f"سوره {v.surah_name}",
                'ayah': v.verse_number
            })
        
        # اگر آیات مرتبط یافت نشد، آیات تصادفی معنوی برگردان
        if not result:
            result = self._get_random_verses(limit)
        
        return result
    
    def _get_random_verses(self, limit=2):
        """دریافت آیات تصادفی با مضامین معنوی"""
        verses = QuranVerse.query.filter_by(is_active=True).limit(limit * 3).all()
        if verses:
            selected = random.sample(verses, min(limit, len(verses)))
            return [{
                'text': v.verse_arabic,
                'translation': v.verse_persian or v.translation,
                'surah': f"سوره {v.surah_name}",
                'ayah': v.verse_number
            } for v in selected]
        return []
    
    def _get_suggestions(self, category_id, exclude_id, limit=5):
        """دریافت سوالات پیشنهادی مرتبط"""
        from models import SerajQA
        suggestions = SerajQA.query.filter(
            SerajQA.category_id == category_id,
            SerajQA.id != exclude_id,
            SerajQA.is_active == True
        ).order_by(SerajQA.priority.desc()).limit(limit).all()
        
        return [s.question[:80] for s in suggestions]
    
    def _generate_smart_response(self, question):
        """تولید پاسخ هوشمندانه وقتی پاسخ دقیق یافت نشد"""
        # جستجوی حدیث مرتبط
        hadith = self._find_related_hadith(question)
        
        # جستجوی آیه مرتبط
        verses = self._get_related_verses(question, limit=2)
        
        # پیشنهادات عمومی
        general_suggestions = [
            "توحید در قرآن چیست؟",
            "آیه الکرسی و فضیلت آن",
            "اهمیت نماز در قرآن",
            "توبه و استغفار در قرآن",
            "صبر و پایداری از دیدگاه قرآن"
        ]
        
        answer = f"""📖 **پاسخ به سوال شما:** {question}

🌙 **سخن از قرآن و عترت:**
سوال خوبی پرسیدید! برای پاسخ دقیق‌تر به این موضوع، توجه شما را به این نکات جلب می‌کنم:

✨ خداوند در قرآن می‌فرماید: «و ما أَرْسَلْناکَ إِلَّا رَحْمَةً لِلْعالَمینَ» (ما تو را جز رحمتی برای جهانیان نفرستادیم)

💡 **نکته مهم:**
پاسخ کامل این سوال نیازمند بررسی دقیق‌تر است. پیشنهاد می‌کنم سوال خود را کمی دقیق‌تر بپرسید یا از سوالات پیشنهادی زیر استفاده کنید.

🙏 **دعا برای شما:** 
خدایا ما را از هدایت‌گران راه راست قرار بده.

---

📚 **سوالات پیشنهادی مرتبط:**"""
        
        for i, sug in enumerate(general_suggestions[:4], 1):
            answer += f"\n{i}. {sug}"
        
        answer += "\n\n🤲 *«رَبَّنَا آتِنَا فِی الدُّنْیَا حَسَنَةً وَفِی الْآخِرَةِ حَسَنَةً»*"
        
        return {
            'success': True,
            'answer': answer,
            'related_verses': verses,
            'suggestions': general_suggestions[:5],
            'qa_id': None,
            'category_id': None
        }
    
    def _find_related_hadith(self, question):
        """جستجوی حدیث مرتبط با موضوع"""
        hadiths = Hadith.query.filter(
            or_(
                Hadith.title.ilike(f'%{question[:30]}%'),
                Hadith.persian_text.ilike(f'%{question[:50]}%')
            )
        ).limit(2).all()
        
        result = []
        for h in hadiths:
            result.append({
                'title': h.title,
                'persian': h.persian_text[:150],
                'source': h.source
            })
        return result
    
    def _normalize(self, text):
        """نرمال‌سازی متن"""
        if not text:
            return ""
        text = text.strip().lower()
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)
        return text
    
    def _extract_keywords(self, text):
        """استخراج کلمات کلیدی از متن"""
        text = self._normalize(text)
        stopwords = ['و', 'به', 'از', 'با', 'برای', 'که', 'این', 'آن', 'است', 'آیا']
        words = text.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords
    
    def _detect_category(self, question):
        """تشخیص دسته‌بندی سوال بر اساس کلمات کلیدی"""
        from models import SerajCategory
        
        categories = SerajCategory.query.filter_by(is_active=True).all()
        question_norm = self._normalize(question)
        
        best_match = None
        best_score = 0
        
        category_keywords = {
            'توحید و خداشناسی': ['خدا', 'توحید', 'رب', 'الوهیت', 'پروردگار'],
            'نبوت و امامت': ['پیامبر', 'رسول', 'نبی', 'امام', 'وحی'],
            'معاد و قیامت': ['قیامت', 'مرگ', 'آخرت', 'بهشت', 'جهنم', 'حشر'],
            'عبادات': ['نماز', 'روزه', 'حج', 'زکات', 'خمس', 'عبادت'],
            'احکام': ['حلال', 'حرام', 'واجب', 'مستحب', 'مکروه', 'نجس'],
            'اخلاق': ['اخلاق', 'رفتار', 'صبر', 'تواضع', 'توبه', 'گناه'],
            'تفسیر': ['تفسیر', 'معنی', 'ترجمه', 'شأن نزول', 'آیه'],
            'قصص قرآنی': ['داستان', 'قصه', 'موسی', 'ابراهیم', 'یوسف', 'عیسی']
        }
        
        for cat in categories:
            score = 0
            cat_keywords = category_keywords.get(cat.name, [])
            for kw in cat_keywords:
                if kw in question_norm:
                    score += 10
            if score > best_score:
                best_score = score
                best_match = cat
        
        return best_match if best_score > 0 else None


def init_quran_ai(app):
    """مقداردهی اولیه سرویس هوش مصنوعی قرآنی"""
    from extensions import db
    app.quran_ai = QuranAIService(db)
    return app.quran_ai