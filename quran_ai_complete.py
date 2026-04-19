# quran_ai_complete.py
"""
سیستم هوش مصنوعی قرآنی کامل با استفاده از sentence-transformers
برای جستجوی معنایی و پردازش زبان طبیعی
"""

import sqlite3
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import re

# برای embedding
try:
    from sentence_transformers import SentenceTransformer
    import torch
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("⚠️ sentence-transformers نصب نیست. برای نصب: pip install sentence-transformers")

# برای پردازش زبان فارسی
try:
    from hazm import Normalizer, word_tokenize, stopwords_list
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False
    print("⚠️ hazm نصب نیست. برای نصب: pip install hazm")

import os

class QuranAISystem:
    """سیستم هوش مصنوعی قرآنی"""
    
    def __init__(self, db_path: str = 'instance/seraj.db'):
        self.db_path = db_path
        self.model = None
        self._init_model()
        self._init_database()
        
    def _init_model(self):
        """بارگذاری مدل embedding"""
        if EMBEDDING_AVAILABLE:
            try:
                # مدل multilingual برای پشتیبانی از فارسی و عربی
                self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
                print("✅ مدل هوش مصنوعی بارگذاری شد")
            except Exception as e:
                print(f"❌ خطا در بارگذاری مدل: {e}")
                self.model = None
        else:
            print("⚠️ مدل embedding در دسترس نیست")
    
    def _init_database(self):
        """ایجاد جداول دیتابیس در صورت نیاز"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول آیات با embedding
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quran_verses_ai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surah_number INTEGER,
                surah_name TEXT,
                verse_number INTEGER,
                arabic_text TEXT,
                persian_text TEXT,
                translation TEXT,
                embedding BLOB,
                keywords TEXT,
                topics TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # جدول تاریخچه پرسش و پاسخ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quran_qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT NOT NULL,
                question_embedding BLOB,
                answer TEXT,
                related_verses TEXT,
                confidence FLOAT,
                response_time FLOAT,
                feedback INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # جدول موضوعات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quran_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                parent_id INTEGER,
                keywords TEXT,
                description TEXT,
                FOREIGN KEY (parent_id) REFERENCES quran_topics(id)
            )
        """)
        
        # جدول ارتباط آیات با موضوعات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verse_topic_mapping (
                verse_id INTEGER,
                topic_id INTEGER,
                relevance FLOAT,
                PRIMARY KEY (verse_id, topic_id),
                FOREIGN KEY (verse_id) REFERENCES quran_verses_ai(id),
                FOREIGN KEY (topic_id) REFERENCES quran_topics(id)
            )
        """)
        
        # جدول پیشنهادات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quran_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                verse_id INTEGER,
                suggestion_type TEXT,
                reason TEXT,
                viewed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (verse_id) REFERENCES quran_verses_ai(id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ جداول هوش مصنوعی قرآنی ایجاد/بررسی شدند")
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """دریافت بردار embedding برای یک متن"""
        if self.model is None or not text:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"خطا در تولید embedding: {e}")
            return None
    
    def extract_keywords(self, text: str) -> List[str]:
        """استخراج کلمات کلیدی از متن"""
        keywords = []
        
        if HAZM_AVAILABLE:
            try:
                normalizer = Normalizer()
                text = normalizer.normalize(text)
                tokens = word_tokenize(text)
                stopwords = set(stopwords_list())
                
                # فیلتر کردن کلمات
                for token in tokens:
                    if len(token) > 2 and token not in stopwords:
                        keywords.append(token)
            except:
                pass
        
        # اگر hazm در دسترس نبود، از روش ساده استفاده کن
        if not keywords:
            # حذف علائم نگارشی
            clean_text = re.sub(r'[^\w\s]', '', text)
            words = clean_text.split()
            
            # کلمات پرتکرار فارسی
            stopwords = {'و', 'به', 'از', 'با', 'برای', 'در', 'که', 'این', 'آن', 
                        'را', 'است', 'بود', 'شود', 'می', 'نیز', 'تا', 'بر', 'یا'}
            
            for word in words:
                if len(word) > 2 and word not in stopwords:
                    keywords.append(word)
        
        return keywords[:10]  # حداکثر 10 کلمه کلیدی
    
    def add_quran_verses(self, verses_data: List[Dict]):
        """اضافه کردن آیات قرآن به دیتابیس با embedding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for verse in verses_data:
            # ترکیب متن عربی و فارسی برای embedding بهتر
            combined_text = f"{verse.get('arabic_text', '')} {verse.get('persian_text', '')} {verse.get('translation', '')}"
            
            # تولید embedding
            embedding = self.get_embedding(combined_text)
            embedding_blob = embedding.tobytes() if embedding is not None else None
            
            # استخراج کلمات کلیدی
            keywords = self.extract_keywords(verse.get('persian_text', '') + ' ' + verse.get('translation', ''))
            
            cursor.execute("""
                INSERT OR REPLACE INTO quran_verses_ai 
                (surah_number, surah_name, verse_number, arabic_text, persian_text, translation, embedding, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                verse.get('surah_number'),
                verse.get('surah_name'),
                verse.get('verse_number'),
                verse.get('arabic_text'),
                verse.get('persian_text'),
                verse.get('translation'),
                embedding_blob,
                json.dumps(keywords, ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ {len(verses_data)} آیه به دیتابیس اضافه شد")
    
    def search_similar_verses(self, query: str, top_k: int = 5) -> List[Dict]:
        """جستجوی آیات مشابه با استفاده از embedding"""
        if self.model is None:
            return self._search_by_keywords(query, top_k)
        
        # تولید embedding برای query
        query_embedding = self.get_embedding(query)
        if query_embedding is None:
            return self._search_by_keywords(query, top_k)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # دریافت همه آیات با embedding
        cursor.execute("SELECT id, surah_name, verse_number, arabic_text, persian_text, translation, embedding FROM quran_verses_ai WHERE embedding IS NOT NULL")
        verses = cursor.fetchall()
        conn.close()
        
        if not verses:
            return []
        
        # محاسبه شباهت کسینوسی
        similarities = []
        for verse in verses:
            verse_id, surah_name, verse_number, arabic_text, persian_text, translation, embedding_blob = verse
            
            try:
                verse_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                # شباهت کسینوسی
                similarity = np.dot(query_embedding, verse_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(verse_embedding))
                similarities.append((similarity, {
                    'id': verse_id,
                    'surah': surah_name,
                    'ayah': verse_number,
                    'text': arabic_text,
                    'translation': translation or persian_text,
                    'similarity': float(similarity)
                }))
            except:
                continue
        
        # مرتب‌سازی بر اساس شباهت
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1] for item in similarities[:top_k]]
    
    def _search_by_keywords(self, query: str, top_k: int = 5) -> List[Dict]:
        """جستجوی مبتنی بر کلمات کلیدی (fallback)"""
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ساخت شرط جستجو
        conditions = []
        params = []
        for kw in keywords[:5]:
            conditions.append("(persian_text LIKE ? OR translation LIKE ? OR keywords LIKE ?)")
            params.extend([f'%{kw}%', f'%{kw}%', f'%{kw}%'])
        
        if not conditions:
            conn.close()
            return []
        
        sql = f"""
            SELECT id, surah_name, verse_number, arabic_text, persian_text, translation
            FROM quran_verses_ai
            WHERE {' OR '.join(conditions)}
            LIMIT ?
        """
        params.append(top_k)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'surah': r[1],
            'ayah': r[2],
            'text': r[3],
            'translation': r[5] or r[4]
        } for r in results]
    
    def ask_question(self, question: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """پاسخ به سوال کاربر با استفاده از آیات مرتبط"""
        import time
        start_time = time.time()
        
        # جستجوی آیات مرتبط
        similar_verses = self.search_similar_verses(question, top_k=5)
        
        # ساخت پاسخ بر اساس آیات پیدا شده
        if similar_verses:
            answer = self._generate_answer_from_verses(question, similar_verses)
        else:
            answer = {
                'success': True,
                'answer': "متأسفم، نتوانستم آیه مرتبطی با سوال شما پیدا کنم. لطفاً سوال خود را واضح‌تر مطرح کنید یا موضوع دیگری بپرسید.",
                'is_quranic': False
            }
        
        # اضافه کردن آیات مرتبط به پاسخ
        answer['related_verses'] = similar_verses
        answer['confidence'] = similar_verses[0]['similarity'] if similar_verses else 0.0
        
        # ذخیره در تاریخچه
        self._save_qa_history(question, answer, user_id, time.time() - start_time)
        
        # تولید پیشنهادات
        answer['suggestions'] = self._generate_suggestions(question, similar_verses)
        
        return answer
    
    def _generate_answer_from_verses(self, question: str, verses: List[Dict]) -> Dict:
        """تولید پاسخ بر اساس آیات پیدا شده"""
        if not verses:
            return {
                'success': False,
                'answer': "آیه مرتبطی پیدا نشد.",
                'is_quranic': False
            }
        
        best_verse = verses[0]
        
        # ساخت پاسخ خلاقانه بر اساس آیه اول
        answers_templates = [
            f"در قرآن کریم می‌خوانیم:\n\n「{best_verse['text']}」\n\nترجمه: {best_verse['translation']}\n\nاین آیه از سوره {best_verse['surah']} آیه {best_verse['ayah']} است.",
            
            f"خداوند متعال در قرآن می‌فرماید:\n\n「{best_verse['text']}」\n\n{best_verse['translation']}\n\n(سوره {best_verse['surah']}، آیه {best_verse['ayah']})",
            
            f"پاسخ سوال شما در این آیه نورانی نهفته است:\n\n「{best_verse['text']}」\n\n{best_verse['translation']}"
        ]
        
        import random
        answer_text = random.choice(answers_templates)
        
        # اگر آیات بیشتری وجود دارد، آنها را هم اضافه کن
        if len(verses) > 1:
            answer_text += f"\n\n📖 آیات مرتبط دیگر:\n"
            for v in verses[1:3]:
                answer_text += f"\n• سوره {v['surah']} آیه {v['ayah']}: {v['translation'][:100]}..."
        
        return {
            'success': True,
            'answer': answer_text,
            'is_quranic': True,
            'main_verse': best_verse
        }
    
    def _generate_suggestions(self, question: str, verses: List[Dict]) -> List[str]:
        """تولید پیشنهادات برای ادامه گفتگو"""
        suggestions = [
            "تفسیر این آیه را بخوانید",
            "آیات مشابه را ببینید",
            "درباره موضوع این آیه بیشتر بدانید"
        ]
        
        if verses:
            topics = ["توحید", "نبوت", "معاد", "اخلاق", "عبادت", "صبر", "توکل", "توبه"]
            suggestions.append(f"آیاتی درباره {random.choice(topics)}")
            suggestions.append("آیه روز را ببینید")
        
        return suggestions[:4]
    
    def _save_qa_history(self, question: str, answer: Dict, user_id: Optional[int], response_time: float):
        """ذخیره سوال و پاسخ در تاریخچه"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # تولید embedding سوال
        question_embedding = self.get_embedding(question)
        embedding_blob = question_embedding.tobytes() if question_embedding is not None else None
        
        cursor.execute("""
            INSERT INTO quran_qa_history 
            (user_id, question, question_embedding, answer, related_verses, confidence, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            question,
            embedding_blob,
            answer.get('answer'),
            json.dumps(answer.get('related_verses', []), ensure_ascii=False),
            answer.get('confidence'),
            response_time
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_content(self, text: str) -> Dict[str, Any]:
        """تحلیل محتوای دینی متن ورودی"""
        # استخراج کلمات کلیدی
        keywords = self.extract_keywords(text)
        
        # جستجوی آیات مرتبط
        related_verses = self.search_similar_verses(text, top_k=3)
        
        # تشخیص موضوع (ساده)
        topics = self._detect_topics(text)
        
        # تحلیل احساسات (ساده)
        sentiment = self._analyze_sentiment(text)
        
        return {
            'verses': related_verses,
            'keywords': keywords,
            'topics': topics,
            'sentiment': sentiment,
            'word_count': len(text.split()),
            'has_quranic_content': len(related_verses) > 0
        }
    
    def _detect_topics(self, text: str) -> List[str]:
        """تشخیص موضوعات قرآنی از متن"""
        topic_keywords = {
            'توحید': ['خدا', 'الله', 'رب', 'اله', 'وحدانیت', 'یکتا'],
            'نبوت': ['پیامبر', 'رسول', 'نبی', 'محمد', 'خاتم'],
            'معاد': ['قیامت', 'آخرت', 'مرگ', 'پس از مرگ', 'رستاخیز', 'بهشت', 'جهنم'],
            'اخلاق': ['اخلاق', 'رفتار', 'پاکی', 'صداقت', 'عدالت', 'انصاف', 'بخشش'],
            'عبادت': ['نماز', 'روزه', 'حج', 'زکات', 'عبادت', 'پرستش', 'سجده'],
            'خانواده': ['خانواده', 'همسر', 'فرزند', 'والدین', 'ازدواج', 'طلاق'],
            'صبر': ['صبر', 'شکیبایی', 'استقامت', 'پایداری'],
            'توکل': ['توکل', 'اعتماد', 'توسل', 'یاوری']
        }
        
        detected_topics = []
        text_lower = text.lower()
        
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    detected_topics.append(topic)
                    break
        
        return detected_topics[:5]
    
    def _analyze_sentiment(self, text: str) -> str:
        """تحلیل احساسات متن (ساده)"""
        positive_words = ['خوب', 'عالی', 'زیبا', 'امید', 'شادی', 'نعمت', 'رحمت', 'بخشش', 'محبت']
        negative_words = ['بد', 'شر', 'گناه', 'عذاب', 'دوزخ', 'ناراحتی', 'اندوه', 'ترس', 'نگرانی']
        
        text_lower = text.lower()
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """دریافت تاریخچه سوالات کاربر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, question, answer, confidence, created_at
            FROM quran_qa_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'question': r[1],
            'answer': r[2],
            'confidence': r[3],
            'created_at': r[4]
        } for r in results]
    
    def get_daily_verse(self, user_id: Optional[int] = None) -> Dict:
        """دریافت آیه روز (با در نظر گرفتن تاریخچه کاربر)"""
        import random
        from datetime import date
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # اگر کاربر دارد، بر اساس تاریخچه او پیشنهاد بده
        if user_id:
            cursor.execute("""
                SELECT topic_id FROM verse_topic_mapping
                WHERE verse_id IN (
                    SELECT verse_id FROM quran_suggestions WHERE user_id = ?
                )
                GROUP BY topic_id ORDER BY COUNT(*) DESC LIMIT 1
            """, (user_id,))
            preferred_topic = cursor.fetchone()
            
            if preferred_topic:
                cursor.execute("""
                    SELECT v.id, v.surah_name, v.verse_number, v.arabic_text, v.translation
                    FROM quran_verses_ai v
                    JOIN verse_topic_mapping vt ON vt.verse_id = v.id
                    WHERE vt.topic_id = ?
                    ORDER BY RANDOM() LIMIT 1
                """, (preferred_topic[0],))
                verse = cursor.fetchone()
                
                if verse:
                    conn.close()
                    return {
                        'id': verse[0],
                        'surah': verse[1],
                        'ayah': verse[2],
                        'text': verse[3],
                        'translation': verse[4],
                        'reason': 'بر اساس سوالات قبلی شما'
                    }
        
        # آیه تصادفی
        cursor.execute("""
            SELECT id, surah_name, verse_number, arabic_text, translation
            FROM quran_verses_ai
            ORDER BY RANDOM() LIMIT 1
        """)
        verse = cursor.fetchone()
        conn.close()
        
        if verse:
            return {
                'id': verse[0],
                'surah': verse[1],
                'ayah': verse[2],
                'text': verse[3],
                'translation': verse[4],
                'reason': 'آیه روز'
            }
        
        return None
    
    def add_feedback(self, qa_id: int, feedback: int):
        """ثبت بازخورد کاربر برای بهبود سیستم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE quran_qa_history
            SET feedback = ?
            WHERE id = ?
        """, (feedback, qa_id))
        
        conn.commit()
        conn.close()


# نمونه داده برای تست
SAMPLE_VERSES = [
    {
        'surah_number': 1,
        'surah_name': 'فاتحه',
        'verse_number': 1,
        'arabic_text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
        'persian_text': 'به نام خداوند بخشنده مهربان',
        'translation': 'به نام خداوند بخشنده‌ترین و مهربان‌ترین'
    },
    {
        'surah_number': 2,
        'surah_name': 'بقره',
        'verse_number': 255,
        'arabic_text': 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ',
        'persian_text': 'خداوند، که معبودی جز او نیست، زنده و برپا دارنده است',
        'translation': 'خداوند هیچ معبودی جز او نیست، زنده و پاینده است'
    },
    {
        'surah_number': 94,
        'surah_name': 'شرح',
        'verse_number': 5,
        'arabic_text': 'فَإِنَّ مَعَ الْعُسْرِ يُسْرًا',
        'persian_text': 'پس بی‌گمان با دشواری، آسانی است',
        'translation': 'به درستی که همراه با سختی، آسانی است'
    },
    {
        'surah_number': 2,
        'surah_name': 'بقره',
        'verse_number': 286,
        'arabic_text': 'لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا',
        'persian_text': 'خداوند هیچ کس را جز به اندازه توانش تکلیف نمی‌کند',
        'translation': 'خداوند به هیچ کس جز به اندازه توانایی‌اش تکلیف نمی‌کند'
    },
    {
        'surah_number': 3,
        'surah_name': 'آل عمران',
        'verse_number': 159,
        'arabic_text': 'وَشَاوِرْهُمْ فِي الْأَمْرِ',
        'persian_text': 'و در کارها با آنان مشورت کن',
        'translation': 'و در کارها با آن‌ها مشورت کن'
    },
    {
        'surah_number': 49,
        'surah_name': 'حجرات',
        'verse_number': 13,
        'arabic_text': 'إِنَّ أَكْرَمَكُمْ عِنْدَ اللَّهِ أَتْقَاكُمْ',
        'persian_text': 'بی‌گمان ارجمندترین شما نزد خداوند پرهیزکارترین شماست',
        'translation': 'همانا گرامی‌ترین شما نزد خدا پرهیزکارترین شماست'
    },
    {
        'surah_number': 13,
        'surah_name': 'رعد',
        'verse_number': 28,
        'arabic_text': 'أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ',
        'persian_text': 'آگاه باشید که با یاد خداوند دلها آرام می‌گیرد',
        'translation': 'بدانید که با یاد خدا دلها آرام می‌گیرد'
    }
]


def init_quran_ai_system(db_path: str = 'instance/seraj.db'):
    """راه‌اندازی اولیه سیستم هوش مصنوعی قرآنی"""
    system = QuranAISystem(db_path)
    
    # بررسی اینکه آیا داده وجود دارد
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quran_verses_ai")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        print("📖 در حال بارگذاری آیات نمونه...")
        system.add_quran_verses(SAMPLE_VERSES)
        print("✅ آیات نمونه با موفقیت بارگذاری شدند")
    
    return system


# نمونه استفاده
if __name__ == "__main__":
    # راه‌اندازی سیستم
    ai = init_quran_ai_system()
    
    # تست پرسش و پاسخ
    questions = [
        "آرامش قلب در قرآن چیست؟",
        "خداوند در مورد صبر چه می‌گوید؟",
        "آیه‌الکرسی را به من نشان بده",
        "تکلیف انسان تا چه اندازه است؟"
    ]
    
    for q in questions:
        print(f"\n{'='*50}")
        print(f"❓ سوال: {q}")
        result = ai.ask_question(q)
        print(f"📖 پاسخ:\n{result['answer']}")
        if result.get('related_verses'):
            print(f"🔗 آیات مرتبط: {len(result['related_verses'])} آیه")