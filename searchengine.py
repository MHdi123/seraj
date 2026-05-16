# ============================================
# searchengine.py - موتور جستجوی هوشمند آیات
# ============================================

import re
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class QuranSearchEngine:
    """موتور جستجوی هوشمند برای آیات قرآن"""
    
    # کلمات توقف (کلمات رایج بدون معنی خاص)
    STOP_WORDS = {'و', 'به', 'از', 'در', 'برای', 'با', 'که', 'این', 'آن', 'است', 'نیست', 'هم', 'را', 'تا', 'بر', 'برا'}
    
    # مترادف‌های دینی
    SYNONYMS = {
        'خدا': ['الله', 'پروردگار', 'خداوند', 'رب', 'الهی'],
        'پیامبر': ['رسول', 'نبی', 'حضرت محمد', 'محمد (ص)'],
        'بهشت': ['جنت', 'فردوس', 'بهشت برین'],
        'دوزخ': ['جهنم', 'سقر', 'جحیم', 'نار'],
        'نماز': ['صلوة', 'صلات', 'نماز خواندن'],
        'روزه': ['صوم', 'روزه گرفتن'],
        'زکات': ['زکوة', 'صدقه واجب'],
        'توحید': ['یکتاپرستی', 'شرک', 'شرک ورزیدن'],
        'عدالت': ['دادگری', 'انصاف', 'قسط'],
        'رحمت': ['مهربانی', 'بخشش', 'آمرزش'],
        'توبه': ['بازگشت', 'استغفار', 'آمرزش خواهی'],
    }
    
    def __init__(self, db_session):
        self.db = db_session
    
    def normalize_text(self, text):
        """نرمال‌سازی متن برای جستجو"""
        if not text:
            return ""
        
        # تبدیل به حروف کوچک
        text = text.lower()
        
        # حذف حرکات عربی
        arabic_vowels = r'[\u064B-\u065F\u0670]'
        text = re.sub(arabic_vowels, '', text)
        
        # حذف علائم نگارشی
        text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)
        
        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_keywords(self, text, with_synonyms=True):
        """استخراج کلمات کلیدی از متن"""
        normalized = self.normalize_text(text)
        words = normalized.split()
        
        # حذف کلمات توقف
        keywords = [w for w in words if w not in self.STOP_WORDS and len(w) > 1]
        
        # اضافه کردن مترادف‌ها
        if with_synonyms:
            expanded_keywords = set(keywords)
            for word in keywords:
                for synonym_group in self.SYNONYMS.values():
                    if word in synonym_group:
                        expanded_keywords.update(synonym_group)
            keywords = list(expanded_keywords)
        
        return keywords
    
    def search_verses(self, query, limit=5, use_hybrid=True):
        """جستجوی آیات مرتبط با سوال کاربر"""
        
        # نرمال‌سازی سوال
        normalized_query = self.normalize_text(query)
        keywords = self.extract_keywords(query, with_synonyms=True)
        
        # دریافت همه آیات فعال
        verses = QuranVerse.query.filter_by(is_active=True).all()
        
        results = []
        
        for verse in verses:
            # ترکیب متن برای جستجو
            search_text = f"{verse.surah_name} {verse.verse_persian or ''} {verse.translation or ''}"
            normalized_verse = self.normalize_text(search_text)
            
            score = self._calculate_relevance_score(
                query=normalized_query,
                verse_text=normalized_verse,
                keywords=keywords,
                verse=verse
            )
            
            if score > 0:
                results.append({
                    'verse': verse,
                    'score': score,
                    'surah_name': verse.surah_name,
                    'verse_number': verse.verse_number,
                    'arabic_text': verse.verse_arabic,
                    'persian_text': verse.verse_persian or verse.translation
                })
        
        # مرتب‌سازی بر اساس امتیاز
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # اضافه کردن تحلیل تخصصی برای آیات برتر
        enhanced_results = []
        for result in results[:limit]:
            analysis = self.get_verse_analysis(result['verse'].id)
            if analysis:
                result['analysis'] = analysis
            enhanced_results.append(result)
        
        return enhanced_results[:limit]
    
    def _calculate_relevance_score(self, query, verse_text, keywords, verse):
        """محاسبه امتیاز ارتباط بین سوال و آیه"""
        score = 0
        
        # 1. تطابق کامل عبارت (50 امتیاز)
        if query in verse_text:
            score += 50
        
        # 2. تطابق با کلمات کلیدی (هر کلمه 10 امتیاز)
        matched_keywords = 0
        for kw in keywords:
            if kw in verse_text:
                matched_keywords += 1
        
        score += matched_keywords * 10
        
        # 3. تطابق با موضوع آیه (30 امتیاز)
        if hasattr(verse, 'topic') and verse.topic:
            topic_normalized = self.normalize_text(verse.topic)
            if any(kw in topic_normalized for kw in keywords[:3]):
                score += 30
        
        # 4. تطابق با مفاهیم کلیدی تحلیل (20 امتیاز)
        analysis = self.get_verse_analysis(verse.id)
        if analysis:
            concepts = analysis.get_key_concepts_list()
            for concept in concepts:
                concept_norm = self.normalize_text(concept)
                if any(kw in concept_norm for kw in keywords[:2]):
                    score += 20
                    break
        
        return score
    
    def get_verse_analysis(self, verse_id):
        """دریافت تحلیل تخصصی یک آیه"""
        analysis = QuranAnalysis.query.filter_by(verse_id=verse_id, is_active=True).first()
        
        if not analysis:
            # ایجاد تحلیل پایه
            verse = QuranVerse.query.get(verse_id)
            if verse:
                analysis = self._generate_basic_analysis(verse)
        
        return analysis
    
    def _generate_basic_analysis(self, verse):
        """تولید تحلیل پایه برای آیات بدون تحلیل"""
        # استخراج مفاهیم کلیدی از متن آیه
        persian_text = verse.verse_persian or verse.translation or ""
        keywords = self.extract_keywords(persian_text, with_synonyms=False)
        
        # حذف تکراری‌ها
        unique_keywords = list(dict.fromkeys(keywords))[:5]
        
        analysis = QuranAnalysis(
            verse_id=verse.id,
            surah_name=verse.surah_name,
            verse_number=verse.verse_number,
            verse_arabic=verse.verse_arabic,
            verse_persian=verse.verse_persian or verse.translation,
            key_concepts=', '.join(unique_keywords),
            is_active=True
        )
        
        return analysis
    
    def smart_search(self, query, context=None):
        """جستجوی هوشمند با در نظر گرفتن زمینه سوال"""
        # بررسی کش
        cached = self._check_cache(query)
        if cached:
            return cached
        
        # جستجوی آیات مرتبط
        relevant_verses = self.search_verses(query, limit=8)
        
        # تحلیل محتوایی سوال
        content_analysis = self.analyze_content(query, relevant_verses)
        
        # ذخیره در کش
        self._save_to_cache(query, content_analysis, relevant_verses)
        
        return {
            'verses': relevant_verses,
            'analysis': content_analysis,
            'suggestions': self.generate_suggestions(query, relevant_verses)
        }
    
    def analyze_content(self, query, relevant_verses):
        """تحلیل محتوای سوال بر اساس آیات مرتبط"""
        
        # شناسایی موضوع اصلی
        main_topic = self._identify_topic(query, relevant_verses)
        
        # جمع‌آوری مفاهیم کلیدی از آیات مرتبط
        key_concepts = set()
        moral_messages = []
        
        for rv in relevant_verses[:3]:
            analysis = self.get_verse_analysis(rv['verse'].id)
            if analysis:
                key_concepts.update(analysis.get_key_concepts_list()[:3])
                if analysis.moral_lesson:
                    moral_messages.append(analysis.moral_lesson)
        
        return {
            'main_topic': main_topic,
            'key_concepts': list(key_concepts)[:5],
            'moral_lessons': moral_messages[:2],
            'verse_count': len(relevant_verses)
        }
    
    def _identify_topic(self, query, relevant_verses):
        """شناسایی موضوع اصلی سوال"""
        topics = {
            'توحید': ['خدا', 'الله', 'پروردگار', 'یکتا', 'شرک'],
            'نبوت': ['پیامبر', 'رسول', 'نبی', 'محمد', 'وحی'],
            'معاد': ['قیامت', 'پس از مرگ', 'رستاخیز', 'آخرت', 'بهشت', 'دوزخ'],
            'عبادات': ['نماز', 'روزه', 'حج', 'زکات', 'عبادت'],
            'اخلاق': ['صبر', 'توکل', 'اخلاق', 'رفتار', 'نیکوکاری'],
            'احکام': ['حلال', 'حرام', 'قانون', 'احکام', 'فقه'],
            'قصص': ['داستان', 'قصه', 'موسی', 'ابراهیم', 'یوسف', 'انبیا'],
        }
        
        normalized_query = self.normalize_text(query)
        
        best_topic = 'عمومی'
        best_score = 0
        
        for topic, keywords in topics.items():
            score = sum(1 for kw in keywords if kw in normalized_query)
            if score > best_score:
                best_score = score
                best_topic = topic
        
        return best_topic
    
    def generate_suggestions(self, query, relevant_verses):
        """تولید سوالات پیشنهادی مرتبط"""
        suggestions = set()
        
        # اضافه کردن سوالات مرتبط با آیات
        for rv in relevant_verses[:3]:
            analysis = self.get_verse_analysis(rv['verse'].id)
            if analysis:
                for concept in analysis.get_key_concepts_list()[:2]:
                    suggestions.add(f"تفسیر آیه درباره {concept}")
        
        # اضافه کردن سوالات عمومی
        suggestions.update([
            "تفسیر این آیه چیست؟",
            "چه درس اخلاقی از این آیه می‌گیریم؟",
            "آیات مشابه در قرآن کدامند؟",
            "شأن نزول این آیه چه بوده؟"
        ])
        
        return list(suggestions)[:4]
    
    def _check_cache(self, query):
        """بررسی وجود نتیجه در کش"""
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        cached = ContentAnalysisCache.query.filter_by(query_hash=query_hash).first()
        
        if cached and cached.expires_at and cached.expires_at > datetime.utcnow():
            cached.hit_count += 1
            self.db.commit()
            
            return {
                'verses': json.loads(cached.related_verses) if cached.related_verses else [],
                'analysis': json.loads(cached.analysis_result) if cached.analysis_result else {},
                'suggestions': json.loads(cached.query_text) if cached.query_text else []
            }
        
        return None
    
    def _save_to_cache(self, query, analysis, verses):
        """ذخیره نتایج در کش"""
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        # تبدیل به JSON
        verses_json = json.dumps([{
            'verse_id': v['verse'].id,
            'surah_name': v['surah_name'],
            'verse_number': v['verse_number'],
            'score': v['score']
        } for v in verses], ensure_ascii=False)
        
        cached = ContentAnalysisCache(
            query_hash=query_hash,
            query_text=query,
            analysis_result=json.dumps(analysis, ensure_ascii=False),
            related_verses=verses_json,
            expires_at=datetime.utcnow() + timedelta(days=7)  # کش به مدت 7 روز
        )
        
        self.db.add(cached)
        self.db.commit()