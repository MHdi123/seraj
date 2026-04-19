# quran_ai_fast.py
"""
سیستم سریع پرسش و پاسخ قرآنی - بدون مدل AI سنگین
پاسخ در کمتر از 50 میلی‌ثانیه
"""

import sqlite3
import json
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional


class FastQuranAI:
    """سیستم سریع قرآنی - پاسخ فوری از دیتابیس"""
    
    def __init__(self, db_path: str = 'instance/seraj.db'):
        self.db_path = db_path
        
        # کلمات کلیدی و موضوعات
        self.topic_keywords = {
            'توحید': ['خدا', 'الله', 'رب', 'اله', 'وحدانیت', 'یکتا', 'خالق', 'پروردگار'],
            'صبر': ['صبر', 'شکیبایی', 'استقامت', 'پایداری', 'تحمل', 'صبوری'],
            'آرامش': ['آرامش', 'اطمینان', 'قلب', 'سکینه', 'طمأنینه', 'آسایش'],
            'نماز': ['نماز', 'صلوة', 'سجده', 'رکوع', 'عبادت', 'قنوت'],
            'توبه': ['توبه', 'استغفار', 'بخشش', 'آمرزش', 'غفران', 'بازگشت'],
            'توکل': ['توکل', 'اعتماد', 'توسل', 'یاوری', 'پشتوانه', 'وکیل'],
        }
        
        # پاسخ‌های سریع
        self.fast_answers = {
            'توحید': '🕋 **توحید در قرآن**\n\nتوحید به معنای یکتاپرستی و اعتقاد به یگانگی خداوند است.\n\nسوره مبارکه اخلاص:\n«قُلْ هُوَ اللَّهُ أَحَدٌ»\n(بگو: او خداوند یکتاست)',
            'آیه‌الکرسی': '📖 **آیه‌الکرسی**\n\nآیه 255 سوره مبارکه بقره:\n\n«اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...»\n\nاین آیه به عنوان برترین آیه قرآن شناخته می‌شود.',
            'صبر': '💪 **صبر در قرآن**\n\nخداوند در آیه 153 سوره بقره می‌فرماید:\n«إِنَّ اللَّهَ مَعَ الصَّابِرِینَ»\n(همانا خدا با صابران است)',
            'نماز': '🕌 **نماز در قرآن**\n\nدر آیه 45 سوره عنکبوت آمده:\n«إِنَّ الصَّلَاةَ تَنْهَىٰ عَنِ الْفَحْشَاءِ وَالْمُنْكَرِ»',
            'آرامش قلب': '💚 **آرامش قلب در قرآن**\n\nخداوند در آیه 28 سوره رعد می‌فرماید:\n«أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ»',
        }
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _extract_keywords(self, text: str):
        if not text:
            return []
        clean_text = re.sub(r'[^\w\s]', '', text)
        words = clean_text.split()
        stopwords = {'و', 'به', 'از', 'با', 'برای', 'در', 'که', 'این', 'آن', 'را', 'است', 'بود', 'می', 'نیز', 'تا', 'بر', 'یا'}
        keywords = []
        for word in words:
            if len(word) > 2 and word not in stopwords:
                keywords.append(word)
        return keywords[:5]
    
    def search_verses(self, query: str, limit: int = 5):
        conn = self._get_connection()
        cursor = conn.cursor()
        keywords = self._extract_keywords(query)
        
        if not keywords:
            cursor.execute("""
                SELECT surah_name, verse_number, arabic_text, persian_text, translation
                FROM quran_verses_ai
                WHERE arabic_text IS NOT NULL AND arabic_text != ''
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit,))
        else:
            conditions = []
            params = []
            for kw in keywords[:5]:
                conditions.append("(persian_text LIKE ? OR translation LIKE ? OR keywords LIKE ?)")
                params.extend([f'%{kw}%', f'%{kw}%', f'%{kw}%'])
            
            sql = f"""
                SELECT surah_name, verse_number, arabic_text, persian_text, translation
                FROM quran_verses_ai
                WHERE {' OR '.join(conditions)}
                LIMIT ?
            """
            params.append(limit)
            cursor.execute(sql, params)
        
        results = cursor.fetchall()
        conn.close()
        
        verses = []
        for row in results:
            verses.append({
                'surah': row[0] or 'قرآن',
                'ayah': row[1] or '',
                'text': row[2] or '',
                'translation': row[4] or row[3] or ''
            })
        return verses
    
    def detect_topic(self, question: str):
        question_lower = question.lower()
        for topic, keywords in self.topic_keywords.items():
            for kw in keywords:
                if kw in question_lower:
                    return topic
        return None
    
    def get_fast_answer(self, question: str):
        question_lower = question.lower()
        for key, answer in self.fast_answers.items():
            if key in question_lower:
                return answer
        return None
    
    def get_random_verses(self, limit: int = 5):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT surah_name, verse_number, arabic_text, persian_text, translation
            FROM quran_verses_ai
            WHERE arabic_text IS NOT NULL
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        results = cursor.fetchall()
        conn.close()
        verses = []
        for row in results:
            verses.append({
                'surah': row[0] or 'قرآن',
                'ayah': row[1] or '',
                'text': row[2] or '',
                'translation': row[4] or row[3] or ''
            })
        return verses
    
    def get_verses_by_topic(self, topic: str, limit: int = 5):
        keywords = self.topic_keywords.get(topic, [topic])
        conn = self._get_connection()
        cursor = conn.cursor()
        conditions = []
        params = []
        for kw in keywords[:3]:
            conditions.append("(persian_text LIKE ? OR translation LIKE ?)")
            params.extend([f'%{kw}%', f'%{kw}%'])
        
        if conditions:
            sql = f"""
                SELECT surah_name, verse_number, arabic_text, persian_text, translation
                FROM quran_verses_ai
                WHERE {' OR '.join(conditions)}
                LIMIT ?
            """
            params.append(limit)
            cursor.execute(sql, params)
        else:
            cursor.execute("""
                SELECT surah_name, verse_number, arabic_text, persian_text, translation
                FROM quran_verses_ai
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        verses = []
        for row in results:
            verses.append({
                'surah': row[0] or 'قرآن',
                'ayah': row[1] or '',
                'text': row[2] or '',
                'translation': row[4] or row[3] or ''
            })
        return verses
    
    def _build_answer(self, question: str, verses: list):
        if not verses:
            return self._get_fallback_answer(question)
        
        topic = self.detect_topic(question)
        best_verse = verses[0]
        
        if topic:
            answer = f"در پاسخ به سوال شما درباره **{topic}**، در قرآن کریم می‌خوانیم:\n\n「{best_verse['text']}」\n\n📖 **ترجمه:** {best_verse['translation']}\n\n📍 سوره {best_verse['surah']}، آیه {best_verse['ayah']}"
        else:
            answer = f"📖 **آیه مرتبط با سوال شما:**\n\n「{best_verse['text']}」\n\n{best_verse['translation']}\n\n📍 سوره {best_verse['surah']}، آیه {best_verse['ayah']}"
        
        if len(verses) > 1:
            answer += f"\n\n📌 **آیات مرتبط دیگر:**\n"
            for v in verses[1:3]:
                answer += f"• سوره {v['surah']} آیه {v['ayah']}\n"
        return answer
    
    def _get_fallback_answer(self, question: str):
        answers = [
            f"🌙 سوال زیبایی پرسیدید!\n\nبرای پاسخ دقیق به «{question[:50]}...»، پیشنهاد می‌کنم به تفاسیر معتبر قرآن مراجعه کنید.\n\n✨ می‌توانید سوال خود را دقیق‌تر مطرح کنید.",
            "📖 از سوال شما سپاسگزارم.\n\nبرای یافتن پاسخ دقیق قرآنی، لطفاً سوال خود را با کلمات کلیدی‌تر مطرح کنید.\nمثال: «آیه درباره صبر» یا «آیه‌الکرسی»",
        ]
        return random.choice(answers)
    
    def get_suggestions(self, question: str):
        suggestions = ["آیه‌الکرسی", "آیات صبر", "تفسیر سوره توحید", "آیات آرامش‌بخش"]
        topic = self.detect_topic(question)
        if topic:
            suggestions.insert(0, f"آیات بیشتر درباره {topic}")
        return suggestions[:5]
    
    def ask_question(self, question: str, user_id=None):
        import time
        start_time = time.time()
        
        fast_answer = self.get_fast_answer(question)
        if fast_answer:
            verses = self.search_verses(question, limit=3)
            response_time = (time.time() - start_time) * 1000
            return {
                'success': True,
                'answer': fast_answer,
                'is_quranic': True,
                'related_verses': verses,
                'suggestions': self.get_suggestions(question),
                'response_time': response_time
            }
        
        verses = self.search_verses(question, limit=5)
        if verses:
            answer = self._build_answer(question, verses)
            response_time = (time.time() - start_time) * 1000
            return {
                'success': True,
                'answer': answer,
                'is_quranic': True,
                'related_verses': verses[:3],
                'suggestions': self.get_suggestions(question),
                'response_time': response_time
            }
        
        return {
            'success': True,
            'answer': self._get_fallback_answer(question),
            'is_quranic': False,
            'related_verses': [],
            'suggestions': self.get_suggestions(question),
            'response_time': (time.time() - start_time) * 1000
        }


# ============================================
# توابع کمکی برای استفاده در routes.py
# ============================================

fast_ai = None

def get_fast_ai():
    global fast_ai
    if fast_ai is None:
        fast_ai = FastQuranAI()
    return fast_ai

def ask_quran_ai(question, user_id=None):
    """پاسخ سریع به سوالات قرآنی"""
    ai = get_fast_ai()
    return ai.ask_question(question, user_id)

def analyze_quranic_text(text, user_id=None):
    """تحلیل سریع متن"""
    ai = get_fast_ai()
    verses = ai.search_verses(text, limit=3)
    keywords = ai._extract_keywords(text)
    topic = ai.detect_topic(text)
    return {'verses': verses, 'keywords': keywords, 'topic': topic, 'sentiment': 'neutral'}

def get_verse_suggestions(mood='general', limit=5):
    """پیشنهاد آیات بر اساس حال و هوا"""
    ai = get_fast_ai()
    if mood == 'امید':
        return ai.get_verses_by_topic('صبر', limit)
    elif mood == 'آرامش':
        return ai.get_verses_by_topic('آرامش', limit)
    elif mood == 'توکل':
        return ai.get_verses_by_topic('توکل', limit)
    else:
        return ai.get_random_verses(limit)

def get_ai_statistics():
    """آمار سیستم"""
    try:
        conn = sqlite3.connect('instance/seraj.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quran_verses_ai")
        total_verses = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM quran_qa_history")
        total_questions = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM quran_qa_history")
        unique_users = cursor.fetchone()[0] or 0
        conn.close()
        return {
            'total_verses': total_verses,
            'total_questions': total_questions,
            'unique_users': unique_users,
            'ai_enabled': True,
            'fast_mode': True
        }
    except:
        return {'total_verses': 0, 'total_questions': 0, 'unique_users': 0, 'ai_enabled': True, 'fast_mode': True}

def get_recent_qa(limit=10):
    """دریافت سوالات اخیر"""
    try:
        conn = sqlite3.connect('instance/seraj.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, question, answer, created_at
            FROM quran_qa_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        results = cursor.fetchall()
        conn.close()
        return [{'id': r[0], 'user_id': r[1], 'question': r[2], 'answer': r[3], 'created_at': r[4]} for r in results]
    except:
        return []