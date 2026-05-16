# services/quran_answer_service.py
from models import QuranVerse, Surah, db
from utils.quran_extractor import extract_verse_info, extract_surah_from_question

class QuranAnswerService:
    
    @staticmethod
    def answer_question(question):
        """
        پاسخ به سوال کاربر
        return: dict با کلیدهای answer, type, data
        """
        info = extract_verse_info(question)
        
        if not info:
            return {
                "answer": "❌ لطفاً نام سوره و شماره آیه را به درستی وارد کنید.\n"
                          "مثال: آیه 26 سوره بقره\n"
                          "مثال: سوره 2 آیه 255\n"
                          "مثال: سوره یس",
                "type": "error",
                "data": None
            }
        
        # حالت 1: فقط اطلاعات سوره (بدون آیه)
        if not info["has_verse"] and info["surah"]:
            surah = Surah.query.filter_by(number=info["surah"]["number"]).first()
            if surah:
                return {
                    "answer": f"📖 **سوره {surah.persian_name}**\n\n"
                              f"🆔 شماره: {surah.number}\n"
                              f"🌙 نام عربی: {surah.arabic_name}\n"
                              f"📜 تعداد آیات: {surah.verses_count or 'نامشخص'}\n"
                              f"📍 نزول: {'مکی' if surah.is_makki else 'مدنی'}",
                    "type": "surah_info",
                    "data": surah
                }
            else:
                return {
                    "answer": f"📖 **سوره {info['surah']['persian_name']}**\n\n"
                              f"🆔 شماره: {info['surah']['number']}\n"
                              f"🌙 نام عربی: {info['surah']['arabic_name']}",
                    "type": "surah_info",
                    "data": None
                }
        
        # حالت 2: آیه مشخص
        if info["has_verse"] and info["surah"]:
            verse = QuranVerse.query.filter(
                QuranVerse.verse_number == info["verse_number"],
                QuranVerse.surah_name.ilike(f"%{info['surah']['persian_name']}%")
            ).first()
            
            if verse:
                return {
                    "answer": f"📖 **سوره {verse.surah_name} - آیه {verse.verse_number}**\n\n"
                              f"🕌 **متن عربی:**\n{verse.verse_arabic}\n\n"
                              f"🇮🇷 **متن فارسی:**\n{verse.verse_persian}\n\n"
                              f"📝 **ترجمه:**\n{verse.translation}",
                    "type": "verse",
                    "data": verse
                }
            else:
                return {
                    "answer": f"⚠️ آیه {info['verse_number']} سوره {info['surah']['persian_name']} در دیتابیس یافت نشد.\n"
                              f"به زودی اضافه خواهد شد.",
                    "type": "not_found",
                    "data": info
                }
        
        return {
            "answer": "❌ سوره مورد نظر یافت نشد. لطفاً نام سوره را به فارسی یا عربی وارد کنید.",
            "type": "error",
            "data": None
        }
    
    @staticmethod
    def check_for_quran_question(question):
        """بررسی می‌کند آیا سوال کاربر درباره قرآن است و اگر آره پاسخ می‌دهد"""
        info = extract_verse_info(question)
        if info:
            return QuranAnswerService.answer_question(question)
        return None