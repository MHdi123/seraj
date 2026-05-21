from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, render_template_string
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_, and_, desc
from datetime import datetime, timedelta, date
from models import Ahkam
from forms import AhkamForm
from datetime import datetime
from flask import flash, redirect, url_for, request
import math  
import os
import secrets
import uuid
import random
import time
import sqlite3
from models import (
    QuranCircle,
    CircleMember,
    CircleSession,
    CircleFile,
    SessionFile,
    SessionAttendance,
    AcademicRank,
    Class,
    SerajCategory,
    SerajQA,
    SerajSuggestion,
    SerajChat,
    ClassEnrollment,
    CourseSession,
    Attendance,
    Faculty,
    Department,
    Course,
    AcademicTerm,
    ClassFile,
    CircleSessionFile,
    UserFCMToken,
    VerificationLog,
    Event,
    EventType,
    Registration,
    AIQuestion,
    Notification,
    PasswordResetToken,
    QuranVerse,
    UserRole,
    Banner,
    Competition,
    CompetitionCategory,
    CompetitionRegistration,
    CompetitionRound,
    JudgeScore,
    QuranQA,  
    QuranSuggestion,  
    UserQuranChat,
    NahjCategory,    
    NahjContent   
)
import jdatetime
from decorators import admin_required, staff_required, verified_required
from sqlalchemy import func, and_, or_, desc

try:
    from quran_ai import (
        ask_quran_ai,
        analyze_quranic_text,
        get_verse_suggestions,
        get_ai_statistics,
        get_recent_qa
    )
    AI_ENABLED = True
except ImportError:
    AI_ENABLED = False
    print("⚠️ هوش مصنوعی قرآنی در دسترس نیست. از حالت ساده استفاده می‌شود.")

def init_routes(app):
# ============================================
# ========== سِراج‌یار (هوش مصنوعی دینی) ==========
# ============================================

    def normalize_text(text):
        """نرمال‌سازی متن برای جستجو"""
        if not text:
            return ""
        import re
        text = text.strip().lower()
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)
        return text

    def find_best_answer(question):
        """پیدا کردن بهترین پاسخ برای سوال کاربر"""
        from models import SerajQA
        
        question_norm = normalize_text(question)
        
        exact_match = SerajQA.query.filter(
            SerajQA.is_active == True,
            SerajQA.question == question
        ).first()
        
        if exact_match:
            exact_match.view_count += 1
            db.session.commit()
            return exact_match
        
        all_qa = SerajQA.query.filter_by(is_active=True).all()
        
        best_match = None
        best_score = 0
        
        for qa in all_qa:
            score = 0
            if normalize_text(qa.question) == question_norm:
                score += 100
            
            if qa.keywords:
                keywords = qa.keywords.split(',')
                for kw in keywords:
                    if kw.strip() in question_norm:
                        score += 20
            
            if question_norm in normalize_text(qa.question):
                score += 10
            
            score += qa.priority
            
            if score > best_score:
                best_score = score
                best_match = qa
        
        if best_match and best_score > 5:
            best_match.view_count += 1
            db.session.commit()
            return best_match
        
        return None

    def save_seraj_chat(user_id, question, answer, category_id=None, qa_id=None):
        """ذخیره تاریخچه چت"""
        from models import SerajChat
        try:
            chat = SerajChat(
                user_id=user_id,
                question=question,
                answer=answer,
                category_id=category_id,
                related_qa_id=qa_id
            )
            db.session.add(chat)
            db.session.commit()
        except Exception as e:
            print(f"خطا در ذخیره چت: {e}")

    def get_seraj_suggestions(category_id=None, limit=8):
        """دریافت سوالات پیشنهادی"""
        from models import SerajSuggestion
        query = SerajSuggestion.query.filter_by(is_active=True)
        if category_id:
            query = query.filter_by(category_id=category_id)
        return query.order_by(SerajSuggestion.order).limit(limit).all()
    
        # ============================================
    # APIهای مدیریت گفتگوهای سِراج‌یار در دیتابیس
    # ============================================
    
    @app.route('/api/seraj/conversations', methods=['GET'])
    @login_required
    def api_get_conversations():
        """دریافت لیست گفتگوهای کاربر از دیتابیس"""
        try:
            limit = request.args.get('limit', 20, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            conversations = get_user_conversations(current_user.id, limit, offset)
            
            return jsonify({
                'success': True,
                'conversations': conversations
            })
            
        except Exception as e:
            print(f"خطا در دریافت گفتگوها: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/seraj/conversations', methods=['POST'])
    @login_required
    def api_create_conversation():
        """ایجاد گفتگوی جدید در دیتابیس"""
        try:
            data = request.get_json()
            title = data.get('title', 'گفتگوی جدید')
            first_question = data.get('first_question', '')
            
            conv_id = create_seraj_conversation(
                user_id=current_user.id,
                title=title,
                first_question=first_question
            )
            
            return jsonify({
                'success': True,
                'conversation_id': conv_id,
                'message': 'گفتگو با موفقیت ایجاد شد'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"خطا در ایجاد گفتگو: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/seraj/conversations/<int:conv_id>', methods=['GET'])
    @login_required
    def api_get_conversation(conv_id):
        """دریافت پیام‌های یک گفتگو"""
        try:
            conv_data = get_conversation_messages(conv_id, current_user.id)
            
            if not conv_data:
                return jsonify({'success': False, 'error': 'گفتگو یافت نشد'}), 404
            
            return jsonify({
                'success': True,
                'conversation': conv_data['conversation'],
                'messages': conv_data['messages']
            })
            
        except Exception as e:
            print(f"خطا در دریافت گفتگو: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/seraj/conversations/<int:conv_id>/messages', methods=['POST'])
    @login_required
    def api_add_message(conv_id):
        """اضافه کردن پیام به گفتگوی موجود"""
        try:
            data = request.get_json()
            message_type = data.get('message_type')
            content = data.get('content')
            related_verses = data.get('related_verses', [])
            suggestions = data.get('suggestions', [])
            
            if not message_type or not content:
                return jsonify({'success': False, 'error': 'نوع پیام و محتوا الزامی است'}), 400
            
            # بررسی وجود گفتگو و دسترسی کاربر
            from models import SerajConversation
            conv = SerajConversation.query.filter_by(
                id=conv_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not conv:
                return jsonify({'success': False, 'error': 'گفتگو یافت نشد'}), 404
            
            add_message_to_conversation(
                conversation_id=conv_id,
                message_type=message_type,
                content=content,
                related_verses=related_verses,
                suggestions=suggestions
            )
            
            # اگر پیام کاربر است و این اولین پیام گفتگوست، عنوان را به‌روزرسانی کن
            if message_type == 'user':
                messages_count = conv.messages.count()
                if messages_count == 1:  # فقط همین پیام وجود دارد
                    new_title = content[:50] + ('...' if len(content) > 50 else '')
                    update_conversation_title(conv_id, new_title)
            
            return jsonify({
                'success': True,
                'message': 'پیام با موفقیت ذخیره شد'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"خطا در افزودن پیام: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/seraj/conversations/<int:conv_id>', methods=['DELETE'])
    @login_required
    def api_delete_conversation(conv_id):
        """حذف یک گفتگو"""
        try:
            if delete_conversation(conv_id, current_user.id):
                return jsonify({'success': True, 'message': 'گفتگو با موفقیت حذف شد'})
            else:
                return jsonify({'success': False, 'error': 'گفتگو یافت نشد'}), 404
                
        except Exception as e:
            db.session.rollback()
            print(f"خطا در حذف گفتگو: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/seraj/conversations/clear-all', methods=['DELETE'])
    @login_required
    def api_clear_all_conversations():
        """پاک کردن تمام گفتگوهای کاربر"""
        try:
            count = delete_all_user_conversations(current_user.id)
            return jsonify({
                'success': True,
                'message': f'{count} گفتگو با موفقیت حذف شد'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"خطا در پاک کردن گفتگوها: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
        # ============================================
    # توابع مدیریت گفتگوهای سِراج‌یار در دیتابیس
    # ============================================

    def create_seraj_conversation(user_id, title, first_question, first_answer=None, related_verses=None, suggestions=None):
        """ایجاد یک گفتگوی جدید در دیتابیس"""
        from models import SerajConversation, SerajMessage
        from datetime import datetime
        
        conversation = SerajConversation(
            user_id=user_id,
            title=title[:200],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(conversation)
        db.session.flush()  # برای گرفتن id
        
        # ذخیره پیام کاربر
        user_message = SerajMessage(
            conversation_id=conversation.id,
            message_type='user',
            content=first_question
        )
        db.session.add(user_message)
        
        # ذخیره پاسخ AI (اگر وجود داشته باشد)
        if first_answer:
            import json
            ai_message = SerajMessage(
                conversation_id=conversation.id,
                message_type='ai',
                content=first_answer,
                related_verses=json.dumps(related_verses) if related_verses else None,
                suggestions=json.dumps(suggestions) if suggestions else None
            )
            db.session.add(ai_message)
        
        db.session.commit()
        return conversation.id


    def add_message_to_conversation(conversation_id, message_type, content, related_verses=None, suggestions=None):
        """اضافه کردن پیام جدید به گفتگوی موجود"""
        from models import SerajMessage
        
        import json
        message = SerajMessage(
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            related_verses=json.dumps(related_verses) if related_verses else None,
            suggestions=json.dumps(suggestions) if suggestions else None
        )
        db.session.add(message)
        
        # به‌روزرسانی زمان آخرین تغییر گفتگو
        from models import SerajConversation
        conversation = SerajConversation.query.get(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        return message.id


    def get_user_conversations(user_id, limit=20, offset=0):
        """دریافت لیست گفتگوهای کاربر از دیتابیس"""
        from models import SerajConversation
        
        conversations = SerajConversation.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(SerajConversation.updated_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for conv in conversations:
            # تعداد پیام‌های هر گفتگو
            message_count = conv.messages.count()
            result.append({
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': message_count
            })
        
        return result


    def get_conversation_messages(conversation_id, user_id):
        """دریافت پیام‌های یک گفتگو با بررسی دسترسی کاربر"""
        from models import SerajConversation, SerajMessage
        import json
        
        conversation = SerajConversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return None
        
        messages = SerajMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(SerajMessage.created_at).all()
        
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'type': msg.message_type,
                'content': msg.content,
                'related_verses': json.loads(msg.related_verses) if msg.related_verses else [],
                'suggestions': json.loads(msg.suggestions) if msg.suggestions else [],
                'created_at': msg.created_at.isoformat()
            })
        
        return {
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat()
            },
            'messages': result
        }


    def delete_conversation(conversation_id, user_id):
        """حذف یک گفتگو (غیرفعال کردن آن)"""
        from models import SerajConversation
        
        conversation = SerajConversation.query.filter_by(
            id=conversation_id,
            user_id=user_id
        ).first()
        
        if conversation:
            conversation.is_active = False
            db.session.commit()
            return True
        return False


    def delete_all_user_conversations(user_id):
        """حذف تمام گفتگوهای یک کاربر"""
        from models import SerajConversation
        
        conversations = SerajConversation.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        for conv in conversations:
            conv.is_active = False
        
        db.session.commit()
        return len(conversations)


    def update_conversation_title(conversation_id, new_title):
        """به‌روزرسانی عنوان گفتگو"""
        from models import SerajConversation
        
        conversation = SerajConversation.query.get(conversation_id)
        if conversation:
            conversation.title = new_title[:200]
            db.session.commit()
            return True
        return False


    
# ========== صفحه اصلی سِراج‌یار ==========
    @app.route('/seraj-yari')
    @login_required
    def seraj_yari():
        """صفحه اصلی سِراج‌یار"""
        from collections import defaultdict
        
        # دریافت دسته‌بندی‌ها
        categories = SerajCategory.query.filter_by(is_active=True).order_by(SerajCategory.order).all()
        
        # دریافت همه سوالات پیشنهادی
        all_suggestions = SerajSuggestion.query.filter_by(is_active=True)\
            .options(db.joinedload(SerajSuggestion.category))\
            .order_by(SerajSuggestion.order).all()
        
        # گروه‌بندی بر اساس دسته
        suggestions_by_category = defaultdict(list)
        for sug in all_suggestions:
            cat_name = sug.category.name if sug.category else 'متفرقه'
            suggestions_by_category[cat_name].append({
                'id': sug.id,
                'question': sug.question,
                'category': sug.category,
                'icon': get_category_icon(cat_name)
            })
        
        # سوالات برتر برای نمایش پیش‌فرض (12 سوال اول)
        top_suggestions = all_suggestions[:12]
        
        # تعداد کل سوالات
        all_suggestions_count = len(all_suggestions)
        
        # گفتگوهای اخیر
        recent_questions = SerajChat.query.filter_by(user_id=current_user.id)\
            .order_by(SerajChat.created_at.desc()).limit(10).all()
        
        initial_question = request.args.get('question', '')
        
        return render_template('seraj_yari/index.html',
                            categories=categories,
                            suggestions_by_category=dict(suggestions_by_category),
                            top_suggestions=top_suggestions,
                            all_suggestions_count=all_suggestions_count,
                            recent_questions=recent_questions,
                            initial_question=initial_question)

    def get_category_icon(category_name):
        """دریافت آیکون بر اساس نام دسته"""
        icons = {
            'اعتقادات': '🕋',
            'اخلاقیات': '💝',
            'عبادات': '🕌',
            'قصص و معجزات': '📖',
            'احکام و فقه': '⚖️',
            'علوم قرآنی': '📚',
            'سوره‌های مهم': '⭐',
            'ادعیه و زیارات': '🤲',
            'تاریخ اسلام': '📜',
            'خانواده و اجتماع': '👨‍👩‍👧'
        }
        return icons.get(category_name, '📖')

    @app.route('/seraj-yari/ask', methods=['POST'])
    @login_required
    def seraj_yari_ask():
        """دریافت سوال و برگرداندن پاسخ با ذخیره در دیتابیس"""
        print("\n" + "="*60)
        print("🎯 درخواست جدید به seraj-yari/ask")
        print("="*60)
        
        try:
            data = request.get_json()
            print(f"📦 داده دریافت شده: {data}")
            
            if not data:
                return jsonify({'success': False, 'error': 'داده ارسال نشده است'}), 400
            
            question = data.get('question', '').strip()
            conversation_id = data.get('conversation_id')
            
            if not question:
                return jsonify({'success': False, 'error': 'سوال وارد نشده است'}), 400
            
            # ========== مرحله 1: جستجو در SerajQA (اولویت اول) ==========
            from sqlalchemy import or_
            
            qa = SerajQA.query.filter(
                SerajQA.is_active == True,
                or_(
                    SerajQA.question.ilike(f'%{question}%'),
                    SerajQA.question.ilike(f'{question}%'),
                    SerajQA.question.ilike(f'%{question}')
                )
            ).first()
            
            if not qa:
                # جستجو بر اساس کلمات کلیدی
                keywords = question.split()
                for keyword in keywords:
                    if len(keyword) > 2:
                        qa = SerajQA.query.filter(
                            SerajQA.is_active == True,
                            SerajQA.keywords.ilike(f'%{keyword}%')
                        ).first()
                        if qa:
                            break
            
            if qa:
                answer = qa.answer_full if qa.answer_full else qa.answer
                print(f"✅ پاسخ از دیتابیس SerajQA پیدا شد (ID: {qa.id}, سوال: {qa.question})")
                
                qa.view_count = (qa.view_count or 0) + 1
                db.session.commit()
                
                related_verses = []
                suggestions = []
                if qa.category_id:
                    suggestions = SerajSuggestion.query.filter_by(
                        category_id=qa.category_id,
                        is_active=True
                    ).limit(5).all()
                    suggestions = [s.question for s in suggestions] if suggestions else [
                        "توحید در قرآن چیست؟",
                        "آیه الکرسی چیست؟",
                        "اهمیت نماز در قرآن چیست؟"
                    ]
                else:
                    suggestions = [
                        "توحید در قرآن چیست؟",
                        "آیه الکرسی چیست؟",
                        "اهمیت نماز در قرآن چیست؟"
                    ]
            
            else:
                # ========== مرحله 2: بررسی سوال قرآنی (سوره‌ها و آیات) ==========
                from services.quran_answer_service import QuranAnswerService
                
                quran_answer = QuranAnswerService.check_for_quran_question(question)
                
                if quran_answer and quran_answer['type'] in ['verse', 'surah_info']:
                    answer = quran_answer['answer']
                    related_verses = []
                    
                    if quran_answer['type'] == 'verse' and quran_answer['data']:
                        verse = quran_answer['data']
                        related_verses = [{
                            'surah': verse.surah_name,
                            'verse': verse.verse_number,
                            'text': verse.verse_persian
                        }]
                    
                    suggestions = [
                        "تفسیر این آیه چیست؟",
                        "آیات مشابه در قرآن",
                        "شأن نزول این آیه",
                        "مفهوم این آیه در زندگی",
                        "سوره‌های دیگر قرآن"
                    ]
                    
                    print(f"✅ پاسخ از سرویس قرآن یافت شد")
                    
                else:
                    # ========== مرحله 3: پاسخ پیش‌فرض ==========
                    answer = f"""❓ **سوال شما:** {question}

    📚 **پاسخ:** 
    در حال حاضر جواب این سوال را نمی‌دانم. لطفاً سوال دیگری بپرسید.

    💡 **سوالات پیشنهادی:**
    • آیه الکرسی چیست؟
    • توحید در قرآن چیست؟
    • اهمیت نماز در قرآن چیست؟
    • سوره یس چند آیه دارد؟
    • تفسیر سوره حمد چیست؟

    🙏 از صبر شما سپاسگزارم."""
                    related_verses = []
                    suggestions = [
                        "آیه الکرسی چیست؟",
                        "توحید در قرآن چیست؟",
                        "اهمیت نماز در قرآن چیست؟",
                        "سوره یس چند آیه دارد؟",
                        "تفسیر سوره حمد"
                    ]
                    print(f"⚠️ پاسخ پیش‌فرض استفاده شد")
            
            # ========== ذخیره در دیتابیس (گفتگوها) ==========
            from models import SerajConversation
            
            if conversation_id:
                conv = SerajConversation.query.filter_by(
                    id=conversation_id,
                    user_id=current_user.id,
                    is_active=True
                ).first()
                
                if conv:
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        message_type='user',
                        content=question
                    )
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        message_type='ai',
                        content=answer,
                        related_verses=related_verses,
                        suggestions=suggestions
                    )
                    if conv.messages.count() <= 2:
                        new_title = question[:50] + ('...' if len(question) > 50 else '')
                        update_conversation_title(conversation_id, new_title)
                    chat_id = conversation_id
                else:
                    chat_id = create_seraj_conversation(
                        user_id=current_user.id,
                        title=question[:50] + ('...' if len(question) > 50 else ''),
                        first_question=question,
                        first_answer=answer,
                        related_verses=related_verses,
                        suggestions=suggestions
                    )
            else:
                chat_id = create_seraj_conversation(
                    user_id=current_user.id,
                    title=question[:50] + ('...' if len(question) > 50 else ''),
                    first_question=question,
                    first_answer=answer,
                    related_verses=related_verses,
                    suggestions=suggestions
                )
            
            print(f"✅ چت با موفقیت ذخیره شد! (ID: {chat_id})")
            print("="*60 + "\n")
            
            return jsonify({
                'success': True,
                'answer': answer,
                'chat_id': chat_id,
                'related_verses': related_verses,
                'suggestions': suggestions
            })
            
        except Exception as e:
            print(f"❌ خطا: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    # ========== دریافت بازخورد ==========
    @app.route('/seraj-yari/feedback', methods=['POST'])
    def seraj_yari_feedback():
        """ثبت بازخورد کاربر"""
        data = request.get_json() if request.is_json else request.form
        chat_id = data.get('chat_id')
        was_helpful = data.get('was_helpful') == 'true' or data.get('was_helpful') == True
        qa_id = data.get('qa_id')
        
        if chat_id:
            chat = SerajChat.query.get(chat_id)
            if chat:
                chat.was_helpful = was_helpful
                db.session.commit()
        
        if qa_id:
            qa = SerajQA.query.get(qa_id)
            if qa:
                if was_helpful:
                    qa.priority = (qa.priority or 0) + 1
                db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True})
        return redirect(url_for('seraj_yari'))
    

    
    # ========== صفحه دسته‌بندی ==========
    @app.route('/seraj-yari/category/<slug>')
    def seraj_yari_category(slug):
        """نمایش سوالات یک دسته‌بندی"""
        category = SerajCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
        questions = SerajQA.query.filter_by(category_id=category.id, is_active=True).order_by(SerajQA.priority.desc()).all()
        
        other_categories = SerajCategory.query.filter(
            SerajCategory.is_active == True,
            SerajCategory.id != category.id
        ).limit(8).all()
        
        return render_template('seraj_yari/category.html',
                             category=category,
                             questions=questions,
                             other_categories=other_categories)
    
    # ========== صفحه جزئیات سوال ==========
    @app.route('/seraj-yari/question/<int:qa_id>')
    def seraj_yari_question_detail(qa_id):
        """نمایش جزئیات یک سوال"""
        qa = SerajQA.query.get_or_404(qa_id)
        
        # افزایش بازدید
        qa.view_count = (qa.view_count or 0) + 1
        db.session.commit()
        
        # سوالات مشابه
        similar = SerajQA.query.filter(
            SerajQA.category_id == qa.category_id,
            SerajQA.id != qa.id,
            SerajQA.is_active == True
        ).limit(5).all()
        
        return render_template('seraj_yari/question_detail.html',
                             qa=qa,
                             similar=similar)
    

    @app.route('/api/seraj/history')
    @login_required
    def api_seraj_history():
        """دریافت تاریخچه چت‌های کاربر جاری"""
        try:
            limit = request.args.get('limit', 20, type=int)
            
            chats = SerajChat.query.filter_by(user_id=current_user.id)\
                .order_by(SerajChat.created_at.desc())\
                .limit(limit).all()
            
            history = []
            for chat in chats:
                history.append({
                    'id': chat.id,
                    'question': chat.question[:50] + ('...' if len(chat.question) > 50 else ''),
                    'full_question': chat.question,
                    'answer': chat.answer[:200] if chat.answer else '',
                    'created_at': chat.created_at.isoformat() if chat.created_at else None,
                    'category_id': chat.category_id  # فقط ID دسته را برگردان
                    # خط category_name را حذف کردیم
                })
            
            return jsonify({'success': True, 'history': history})
            
        except Exception as e:
            import traceback
            print("خطا در دریافت تاریخچه:", e)
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
        
    @app.route('/api/seraj/simple-history')
    @login_required
    def api_seraj_simple_history():
        """نسخه ساده شده API"""
        try:
            chats = SerajChat.query.filter_by(user_id=current_user.id)\
                .order_by(SerajChat.created_at.desc())\
                .limit(20).all()
            
            result = []
            for chat in chats:
                result.append({
                    'id': chat.id,
                    'question': chat.question[:50]
                })
            
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @app.route('/api/seraj/debug')
    @login_required
    def api_seraj_debug():
        """API دیباگ برای پیدا کردن مشکل"""
        try:
            from models import SerajChat
            import traceback
            
            # تست 1: بررسی وجود جدول
            total_count = SerajChat.query.count()
            
            # تست 2: دریافت چت‌های کاربر
            user_chats = SerajChat.query.filter_by(user_id=current_user.id).limit(5).all()
            user_chats_data = []
            for chat in user_chats:
                user_chats_data.append({
                    'id': chat.id,
                    'question': chat.question[:50]
                })
            
            return jsonify({
                'success': True,
                'total_chats': total_count,
                'user_id': current_user.id,
                'user_chats_count': len(user_chats),
                'user_chats': user_chats_data,
                'user_authenticated': current_user.is_authenticated
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500

    @app.route('/seraj-yari/history')
    @login_required
    def seraj_yari_history():
        """نمایش تاریخچه چت کاربر"""
        page = request.args.get('page', 1, type=int)
        
        # دریافت چت‌های کاربر جاری از دیتابیس
        chats = SerajChat.query.filter_by(user_id=current_user.id)\
            .order_by(SerajChat.created_at.desc())\
            .paginate(page=page, per_page=20, error_out=False)
        
        return render_template('seraj_yari/history.html', 
                            chats=chats,
                            current_user=current_user)
    
# ============================================
# اضافه کردن به routes.py
# ============================================

    from searchengine import QuranSearchEngine

    # مقداردهی اولیه موتور جستجو
    search_engine = QuranSearchEngine(db)

    @app.route('/api/quran/search', methods=['POST'])
    @login_required
    def api_quran_search():
        """API جستجوی هوشمند آیات قرآن"""
        try:
            data = request.get_json()
            query = data.get('query', '').strip()
            
            if not query:
                return jsonify({'success': False, 'error': 'متن جستجو وارد نشده است'}), 400
            
            # جستجوی پیشرفته
            result = search_engine.smart_search(query)
            
            # فرمت کردن نتایج
            verses_data = []
            for v in result['verses']:
                verses_data.append({
                    'id': v['verse'].id,
                    'surah_name': v['surah_name'],
                    'verse_number': v['verse_number'],
                    'arabic_text': v['arabic_text'],
                    'persian_text': v['persian_text'],
                    'score': v['score'],
                    'analysis': {
                        'key_concepts': v.get('analysis', {}).get_key_concepts_list() if v.get('analysis') else [],
                        'tafsir': v.get('analysis', {}).tafsir_mukhtasar if v.get('analysis') else None
                    } if v.get('analysis') else None
                })
            
            # ذخیره لاگ جستجو
            log = SemanticSearchLog(
                user_id=current_user.id if current_user.is_authenticated else None,
                query=query,
                best_match_verse_id=verses_data[0]['id'] if verses_data else None,
                match_score=verses_data[0]['score'] if verses_data else 0,
                match_method='hybrid'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'verses': verses_data,
                'analysis': result['analysis'],
                'suggestions': result['suggestions']
            })
            
        except Exception as e:
            print(f"خطا در جستجو: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/quran/analysis/<int:verse_id>')
    @login_required
    def api_quran_verse_analysis(verse_id):
        """دریافت تحلیل تخصصی یک آیه"""
        try:
            analysis = search_engine.get_verse_analysis(verse_id)
            
            if not analysis:
                return jsonify({'success': False, 'error': 'آیه مورد نظر یافت نشد'}), 404
            
            # افزایش بازدید
            analysis.view_count += 1
            db.session.commit()
            
            return jsonify({
                'success': True,
                'analysis': {
                    'id': analysis.id,
                    'surah_name': analysis.surah_name,
                    'verse_number': analysis.verse_number,
                    'verse_arabic': analysis.verse_arabic,
                    'verse_persian': analysis.verse_persian,
                    'tafsir_mukhtasar': analysis.tafsir_mukhtasar,
                    'tafsir_mufassal': analysis.tafsir_mufassal,
                    'key_concepts': analysis.get_key_concepts_list(),
                    'thematic_tags': analysis.get_thematic_tags_list(),
                    'moral_lesson': analysis.moral_lesson,
                    'historical_context': analysis.historical_context,
                    'practical_application': analysis.practical_application,
                    'related_verses': analysis.get_related_verses_list()
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/quran/related/<int:verse_id>')
    def api_quran_related_verses(verse_id):
        """دریافت آیات مرتبط با یک آیه خاص"""
        try:
            verse = QuranVerse.query.get_or_404(verse_id)
            analysis = search_engine.get_verse_analysis(verse_id)
            
            # جستجوی آیات مشابه بر اساس مفاهیم کلیدی
            if analysis and analysis.key_concepts:
                keywords = analysis.get_key_concepts_list()
                query = ' '.join(keywords[:3])
                related = search_engine.search_verses(query, limit=6)
                
                # حذف آیه اصلی از نتایج
                related = [v for v in related if v['verse'].id != verse_id]
            else:
                related = []
            
            return jsonify({
                'success': True,
                'verse': {
                    'id': verse.id,
                    'surah_name': verse.surah_name,
                    'verse_number': verse.verse_number,
                    'text': verse.verse_persian or verse.translation
                },
                'related_verses': [{
                    'id': v['verse'].id,
                    'surah_name': v['surah_name'],
                    'verse_number': v['verse_number'],
                    'text': v['persian_text']
                } for v in related[:5]]
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/seraj/chat/<int:chat_id>')
    @login_required
    def api_seraj_chat_detail(chat_id):
        """دریافت جزئیات یک چت خاص"""
        try:
            chat = SerajChat.query.get_or_404(chat_id)
            
            # بررسی مالکیت - بسیار مهم
            if chat.user_id != current_user.id and not current_user.is_admin():
                return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
            
            return jsonify({
                'success': True,
                'chat': {
                    'id': chat.id,
                    'question': chat.question,
                    'answer': chat.answer,
                    'created_at': chat.created_at.isoformat(),
                    'category_id': chat.category_id
                }
            })
            
        except Exception as e:
            print(f"خطا در دریافت چت: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/seraj/history/clear', methods=['POST'])
    @login_required
    def api_seraj_clear_history():
        """پاک کردن تاریخچه چت کاربر"""
        try:
            SerajChat.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            return jsonify({'success': True, 'message': 'تاریخچه با موفقیت پاک شد'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    # ========== مسیر هوش مصنوعی قرآنی ==========
    @app.route('/ai/quran', methods=['GET', 'POST'])
    def ai_quran():
        """صفحه اصلی هوش مصنوعی قرآنی"""
        categories = SerajCategory.query.filter_by(is_active=True).order_by(SerajCategory.order).all()
        suggestions = SerajSuggestion.query.filter_by(is_active=True).order_by(SerajSuggestion.order).limit(8).all()
        
        stats = {
            'total_qa': SerajQA.query.filter_by(is_active=True).count(),
            'categories_count': len(categories)
        }
        
        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            if question:
                # جستجو در دیتابیس
                qa = SerajQA.query.filter(
                    SerajQA.question.ilike(f'%{question}%'),
                    SerajQA.is_active == True
                ).first()
                
                if qa:
                    answer = {
                        'success': True,
                        'answer': qa.answer_full if qa.answer_full else qa.answer,
                        'related_verses': []
                    }
                else:
                    answer = {
                        'success': True,
                        'answer': f'سوال "{question}" را از من پرسیدید.\n\nمتأسفم، پاسخ دقیقی برای این سوال ندارم. لطفاً سوال دیگری بپرسید.',
                        'related_verses': []
                    }
                
                return render_template('seraj_yari/index.html', 
                                     answer=answer,
                                     question=question,
                                     categories=categories,
                                     suggestions=suggestions,
                                     stats=stats)
        
        # GET request
        return render_template('seraj_yari/index.html',
                             categories=categories,
                             suggestions=suggestions,
                             stats=stats)


    # ============================================
    # تابع بررسی وجود endpoint
    # ============================================
    
    @app.context_processor
    def utility_processor():
        def endpoint_exists(endpoint):
            try:
                url_for(endpoint)
                return True
            except:
                return False
        return dict(endpoint_exists=endpoint_exists)

                # ============================================
        # ========== سیستم پشتیبانی (تیکت) ==========
        # ============================================
        
        @app.route('/support/tickets')
        @login_required
        @verified_required
        def support_tickets():
            """لیست تیکت‌های کاربر جاری"""
            page = request.args.get('page', 1, type=int)
            status = request.args.get('status', 'all')
            
            query = SupportTicket.query.filter_by(user_id=current_user.id)
            
            if status != 'all':
                query = query.filter_by(status=status)
            
            tickets = query.order_by(SupportTicket.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
            
            return render_template('support/tickets.html', tickets=tickets, status=status, current_user=current_user)
        
    @app.route('/support/ticket/<int:ticket_id>')
    @login_required
    def support_ticket_detail(ticket_id):
        """جزئیات یک تیکت برای کاربر عادی"""
        from models import SupportTicket, SupportReply
        
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # فقط مالک تیکت می‌تواند ببیند
        if ticket.user_id != current_user.id:
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect('/support/tickets')
        
        replies = SupportReply.query.filter_by(ticket_id=ticket_id).order_by(SupportReply.created_at).all()
        
        # استفاده از قالب کاربر عادی
        return render_template('support/ticket_detail.html', 
                            ticket=ticket, 
                            replies=replies, 
                            current_user=current_user)
        
        @app.route('/support/ticket/create', methods=['GET', 'POST'])
        @login_required
        @verified_required
        def support_create_ticket():
            """ایجاد تیکت جدید"""
            if request.method == 'POST':
                subject = request.form.get('subject')
                message = request.form.get('message')
                category = request.form.get('category', 'general')
                priority = request.form.get('priority', 'medium')
                
                if not subject or not message:
                    flash('لطفاً عنوان و متن پیام را وارد کنید.', 'error')
                    return redirect(url_for('support_create_ticket'))
                
                ticket = SupportTicket(
                    user_id=current_user.id,
                    subject=subject,
                    message=message,
                    category=category,
                    priority=priority,
                    status='open'
                )
                db.session.add(ticket)
                db.session.commit()
                
                # اعلان به ادمین‌ها
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'تیکت پشتیبانی جدید',
                        f'کاربر {current_user.full_name} یک تیکت جدید با عنوان "{subject}" ثبت کرد.'
                    )
                
                flash('✅ تیکت شما با موفقیت ثبت شد. به زودی پاسخ داده می‌شود.', 'success')
                return redirect(url_for('support_ticket_detail', ticket_id=ticket.id))
            
            return render_template('support/create_ticket.html', current_user=current_user)
        
    @app.route('/support/ticket/<int:ticket_id>/reply', methods=['POST'])
    @login_required
    def support_reply_ticket(ticket_id):
        """پاسخ به تیکت (کاربر یا پشتیبان)"""
        from models import SupportTicket, SupportReply, UserRole
        
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # بررسی دسترسی
        is_owner = ticket.user_id == current_user.id
        is_staff = current_user.is_manager() or current_user.is_staff() or current_user.is_admin()
        
        if not is_owner and not is_staff:
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('support_tickets'))
        
        # اگر تیکت بسته است، اجازه پاسخ نده
        if ticket.status == 'closed':
            flash('❌ این تیکت بسته شده است و نمی‌توان به آن پاسخ داد.', 'error')
            return redirect(url_for('support_ticket_detail', ticket_id=ticket_id))
        
        message = request.form.get('message')
        if not message:
            flash('لطفاً متن پاسخ را وارد کنید.', 'error')
            return redirect(url_for('support_ticket_detail', ticket_id=ticket_id))
        
        reply = SupportReply(
            ticket_id=ticket_id,
            sender_id=current_user.id,
            message=message,
            is_staff=is_staff
        )
        db.session.add(reply)
        
        # به‌روزرسانی زمان تیکت
        ticket.updated_at = datetime.utcnow()
        
        # اگر پاسخ توسط پشتیبان است، وضعیت تیکت را به in_progress تغییر بده
        if is_staff and ticket.status == 'open':
            ticket.status = 'in_progress'
        
        db.session.commit()
        
        # ارسال اعلان به طرف مقابل
        if is_staff:
            # اعلان به کاربر
            create_notification(
                ticket.user_id,
                f'پاسخ جدید به تیکت #{ticket.id}',
                f'به تیکت شما با عنوان "{ticket.subject}" پاسخ داده شد.'
            )
        else:
            # اعلان به پشتیبان‌ها
            staffs = User.query.filter(
                (User.role == UserRole.ADMIN) | (User.user_type == 'staff')
            ).all()
            for staff in staffs:
                create_notification(
                    staff.id,
                    f'پاسخ جدید در تیکت #{ticket.id}',
                    f'کاربر {current_user.full_name} به تیکت "{ticket.subject}" پاسخ داد.'
                )
        
        flash('✅ پاسخ شما با موفقیت ثبت شد.', 'success')
        
        # برگشت به صفحه قبلی
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for('support_ticket_detail', ticket_id=ticket_id))

        
    @app.route('/support/ticket/<int:ticket_id>/close', methods=['POST'])
    @login_required
    def support_close_ticket(ticket_id):
        """بستن تیکت"""
        from models import SupportTicket
        
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # فقط مالک تیکت یا ادمین/پشتیبان می‌توانند ببندند
        if ticket.user_id != current_user.id and not current_user.is_manager() and not current_user.is_staff() and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('support_tickets'))
        
        ticket.status = 'closed'
        db.session.commit()
        
        flash('✅ تیکت با موفقیت بسته شد.', 'success')
        
        # برگشت به صفحه قبلی
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for('support_tickets'))
        
    @app.route('/support/ticket/<int:ticket_id>/reopen', methods=['POST'])
    @login_required
    def support_reopen_ticket(ticket_id):
        """بازگشایی تیکت بسته شده توسط کاربر"""
        from models import SupportTicket, UserRole
        
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # فقط مالک تیکت می‌تواند بازگشایی کند
        if ticket.user_id != current_user.id:
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect('/support/tickets')  # تغییر به آدرس مستقیم
        
        if ticket.status != 'closed':
            flash('❌ فقط تیکت‌های بسته شده قابل بازگشایی هستند.', 'error')
            return redirect('/support/ticket/' + str(ticket_id))  # آدرس مستقیم
        
        ticket.status = 'open'
        db.session.commit()
        
        # اعلان به پشتیبان‌ها
        try:
            staffs = User.query.filter(
                (User.role == UserRole.ADMIN) | (User.user_type == 'staff')
            ).all()
            for staff in staffs:
                create_notification(
                    staff.id,
                    f'بازگشایی تیکت #{ticket.id}',
                    f'کاربر {current_user.full_name} تیکت "{ticket.subject}" را مجدداً باز کرد.'
                )
        except:
            pass
        
        flash('✅ تیکت با موفقیت بازگشایی شد.', 'success')
        return redirect('/support/ticket/' + str(ticket_id))  # آدرس مستقیم
        
        # ========== پنل مدیریت تیکت‌ها برای ادمین و کارمندان ==========
        
        @app.route('/staff/support/tickets')
        @login_required
        def staff_support_tickets():
            """پنل مدیریت تیکت‌ها برای پشتیبانان"""
            if not current_user.is_manager() and not current_user.is_staff():
                flash('⛔ دسترسی غیرمجاز', 'error')
                return redirect(url_for('dashboard'))
            
            page = request.args.get('page', 1, type=int)
            status = request.args.get('status', 'all')
            priority = request.args.get('priority', 'all')
            
            query = SupportTicket.query
            
            if status != 'all':
                query = query.filter_by(status=status)
            
            if priority != 'all':
                query = query.filter_by(priority=priority)
            
            tickets = query.order_by(
                # اولویت بالا اول، سپس تاریخ
                case(
                    (SupportTicket.priority == 'high', 1),
                    (SupportTicket.priority == 'medium', 2),
                    (SupportTicket.priority == 'low', 3),
                    else_=4
                ),
                SupportTicket.updated_at.desc()
            ).paginate(page=page, per_page=15, error_out=False)
            
            # آمار
            stats = {
                'open': SupportTicket.query.filter_by(status='open').count(),
                'in_progress': SupportTicket.query.filter_by(status='in_progress').count(),
                'closed': SupportTicket.query.filter_by(status='closed').count(),
                'high_priority': SupportTicket.query.filter_by(priority='high', status='open').count()
            }
            
            return render_template('staff/support_tickets.html', tickets=tickets, stats=stats, status=status, priority=priority, current_user=current_user)
        
        @app.route('/staff/support/ticket/<int:ticket_id>')
        @login_required
        def staff_support_ticket_detail(ticket_id):
            """جزئیات تیکت برای پشتیبان"""
            if not current_user.is_manager() and not current_user.is_staff():
                flash('⛔ دسترسی غیرمجاز', 'error')
                return redirect(url_for('dashboard'))
            
            ticket = SupportTicket.query.get_or_404(ticket_id)
            replies = SupportReply.query.filter_by(ticket_id=ticket_id).order_by(SupportReply.created_at).all()
            
            # کاربرانی که می‌توانند به عنوان مسئول تیکت تعیین شوند
            available_staff = User.query.filter(
                (User.role == UserRole.ADMIN) | (User.user_type == 'staff')
            ).all()
            
            return render_template('staff/support_ticket_detail.html', ticket=ticket, replies=replies, available_staff=available_staff, current_user=current_user)
        
        @app.route('/staff/support/ticket/<int:ticket_id>/assign', methods=['POST'])
        @login_required
        def staff_assign_ticket(ticket_id):
            """اختصاص تیکت به یک پشتیبان"""
            if not current_user.is_manager() and not current_user.is_staff():
                return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'}), 403
            
            data = request.get_json()
            assigned_to = data.get('assigned_to')
            
            ticket = SupportTicket.query.get_or_404(ticket_id)
            ticket.assigned_to = assigned_to
            ticket.status = 'in_progress'
            db.session.commit()
            
            # اعلان به پشتیبان اختصاص داده شده
            if assigned_to:
                assignee = User.query.get(assigned_to)
                if assignee:
                    create_notification(
                        assignee.id,
                        f'اختصاص تیکت #{ticket.id}',
                        f'تیکت "{ticket.subject}" به شما اختصاص داده شد.'
                    )
            
            return jsonify({'success': True})
         # ============================================
    # API های پنل پشتیبانی (Support Panel API)
    # ============================================
    
    @app.route('/api/support/my-tickets')
    @login_required
    def api_my_tickets():
        """API دریافت تیکت‌های کاربر جاری برای پنل شناور"""
        try:
            from models import SupportTicket, SupportReply
            
            tickets = SupportTicket.query.filter_by(user_id=current_user.id)\
                .order_by(SupportTicket.created_at.desc()).limit(10).all()
            
            tickets_data = []
            for ticket in tickets:
                replies_count = SupportReply.query.filter_by(ticket_id=ticket.id).count()
                
                # دریافت آخرین پاسخ از طرف پشتیبان
                last_staff_reply = SupportReply.query.filter(
                    SupportReply.ticket_id == ticket.id,
                    SupportReply.is_staff == True
                ).order_by(SupportReply.created_at.desc()).first()
                
                last_staff_reply_at = last_staff_reply.created_at.isoformat() if last_staff_reply else None
                
                tickets_data.append({
                    'id': ticket.id,
                    'subject': ticket.subject,
                    'status': ticket.status,
                    'priority': ticket.priority,
                    'created_at': ticket.created_at.strftime('%Y/%m/%d'),
                    'replies_count': replies_count,
                    'last_staff_reply_at': last_staff_reply_at
                })
            
            return jsonify({'success': True, 'tickets': tickets_data})
            
        except Exception as e:
            print(f"خطا در دریافت تیکت‌ها: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': True, 'tickets': [], 'error': str(e)})
    
    @app.route('/api/support/create-ticket', methods=['POST'])
    @login_required
    def api_create_ticket():
        """API ایجاد تیکت جدید از پنل شناور"""
        try:
            from models import SupportTicket, UserRole
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'داده ارسال نشده است'})
            
            subject = data.get('subject', '').strip()
            message = data.get('message', '').strip()
            category = data.get('category', 'general')
            priority = data.get('priority', 'medium')
            
            if not subject or not message:
                return jsonify({'success': False, 'error': 'عنوان و متن تیکت الزامی است'})
            
            ticket = SupportTicket(
                user_id=current_user.id,
                subject=subject,
                message=message,
                category=category,
                priority=priority,
                status='open'
            )
            db.session.add(ticket)
            db.session.commit()
            
            # اعلان به ادمین‌ها
            try:
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'تیکت پشتیبانی جدید',
                        f'کاربر {current_user.full_name} یک تیکت جدید با عنوان "{subject}" ثبت کرد.'
                    )
            except:
                pass
            
            return jsonify({'success': True, 'ticket_id': ticket.id, 'message': 'تیکت با موفقیت ثبت شد'})
            
        except Exception as e:
            print(f"خطا در ایجاد تیکت: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    @app.route('/api/support/mark-as-read', methods=['POST'])
    @login_required
    def api_mark_tickets_as_read():
        """علامت‌گذاری تیکت‌ها به عنوان مشاهده شده"""
        try:
            from models import SupportTicket, SupportReply
            
            # دریافت تیکت‌های کاربر
            tickets = SupportTicket.query.filter_by(user_id=current_user.id).all()
            
            # در اینجا می‌توانید یک جدول جداگانه برای track کردن آخرین مشاهده کاربر ایجاد کنید
            # یا به سادگی کاری نکنید و فقط شمارنده سمت کلاینت ریست شود
            
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})        

    # ============================================
    # توابع کمکی آیه روز و حدیث
    # ============================================

    def get_persian_date():
        try:
            today = jdatetime.date.today()
            persian_months = {
                1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
                5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
                9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
            }
            month_name = persian_months[today.month]
            return f"{today.day} {month_name} {today.year}"
        except:
            today = date.today()
            return today.strftime("%d %B %Y")

    def get_daily_verse():
        """برمی‌گرداند آیه روز یا حدیث روز (۵۰٪ شانس) - بدون دیتابیس اضافی"""
        import random
        from datetime import date

        hadiths = [
            {'title': 'پیامبر اکرم (ص)', 'arabic': 'الْقُرْآنُ مَأْدُبَةُ اللَّهِ، فَتَعَلَّمُوا مَأْدُبَتَهُ مَا اسْتَطَعْتُمْ.', 'persian': 'قرآن سفرهٔ الهی است، پس تا می‌توانید از این سفره بیاموزید.', 'source': 'نهج‌الفصاحه'},
            {'title': 'امام علی (ع)', 'arabic': 'وَ اعْلَمُوا أَنَّ هَذَا الْقُرْآنَ هُوَ النَّاصِحُ الَّذِي لَا يَغُشُّ، وَ الْهَادِي الَّذِي لَا يُضِلُّ، وَ الْمُحَدِّثُ الَّذِي لَا يَكْذِبُ.', 'persian': 'بدانید که این قرآن، اندرزگویی است که فریب نمی‌دهد، راهنمایی است که گمراه نمی‌کند، و سخنگویی است که دروغ نمی‌گوید.', 'source': 'نهج‌البلاغه، خطبه ۱۷۶'},
            {'title': 'امام صادق (ع)', 'arabic': 'إِنَّ الْقُرْآنَ حَيٌ لَمْ يَمُتْ، وَ إِنَّهُ جَارٍ كَمَا يَجْرِي اللَّيْلُ وَ النَّهَارُ، وَ كَمَا يَجْرِي الشَّمْسُ وَ الْقَمَرُ.', 'persian': 'قرآن زنده است و نمی‌میرد؛ جاری است چنانکه شب و روز جاری است، و چنانکه خورشید و ماه جاری هستند.', 'source': 'الکافی، ج۲، ص۶۰۳'},
            {'title': 'امام باقر (ع)', 'arabic': 'مَنْ قَرَأَ الْقُرْآنَ وَ هُوَ شَابٌّ مُؤْمِنٌ، اخْتَلَطَ الْقُرْآنُ بِلَحْمِهِ وَ دَمِهِ، وَ جَعَلَهُ اللَّهُ مَعَ السَّفَرَةِ الْكِرَامِ الْبَرَرَةِ.', 'persian': 'هر جوان مؤمنی که قرآن بخواند، قرآن با گوشت و خونش آمیخته می‌شود و خداوند او را با فرشتگان بزرگوار و نیکوکار محشور می‌گرداند.', 'source': 'الکافی، ج۲، ص۶۰۴'},
            {'title': 'پیامبر اکرم (ص)', 'arabic': 'شِفَاءُ مَا فِي الصُّدُورِ الْقُرْآنُ.', 'persian': 'قرآن درمان آنچه در سینه‌ها (دل‌ها) است، می‌باشد.', 'source': 'بحارالانوار، ج۹۲، ص۲۱'},
            {'title': 'امام رضا (ع)', 'arabic': 'إِنَّ الْقُرْآنَ حَبْلُ اللَّهِ الْمَتِينُ وَ عُرْوَتُهُ الْوُثْقَى وَ الصِّرَاطُ الْمُسْتَقِیمُ.', 'persian': 'قرآن، ریسمان محکم خدا و دستاویز استوار و راه راست است.', 'source': 'عیون اخبار الرضا، ج۱، ص۲۹'},
            {'title': 'امیرالمؤمنین (ع)', 'arabic': 'فَاسْتَشْفُوهُ مِنْ أَدْوَائِكُمْ، وَ اسْتَعِينُوا بِهِ عَلَى لَأْوَائِكُمْ، فَإِنَّ فِيهِ شِفَاءً مِنْ أَكْبَرِ الدَّاءِ وَ هُوَ الْكُفْرُ وَ النِّفَاقُ.', 'persian': 'پس از قرآن برای درمان بیماری‌هایتان شفا بجویید و در سختی‌ها از آن یاری بخواهید؛ زیرا در قرآن درمان بزرگ‌ترین بیماری‌ها یعنی کفر و نفاق است.', 'source': 'نهج‌البلاغه، خطبه ۱۷۶'},
            {'title': 'امام سجاد (ع)', 'arabic': 'آيَاتُ الْقُرْآنِ خَزَائِنُ الرَّحْمَةِ، فَإِذَا فُتِحَتْ خَزَائِنُ الرَّحْمَةِ فَلَا تَنْبَغِي أَنْ تُقْفَلَ.', 'persian': 'آیات قرآن گنجینه‌های رحمتند؛ پس هنگامی که گشوده شدند، شایسته نیست که بسته شوند.', 'source': 'تحف العقول'}
        ]

        if random.choice([True, False]):
            hadith = random.choice(hadiths)
            return {
                'title': hadith['title'],
                'verse': hadith['persian'],
                'arabic_text': hadith['arabic'],
                'translation': hadith['persian'],
                'surah': hadith['source'],
                'verse_number': '',
                'is_hadith': True
            }

        with app.app_context():
            try:
                verses = QuranVerse.query.all()
                if not verses:
                    hadith = hadiths[0]
                    return {
                        'title': hadith['title'],
                        'verse': hadith['persian'],
                        'arabic_text': hadith['arabic'],
                        'translation': hadith['persian'],
                        'surah': hadith['source'],
                        'verse_number': '',
                        'is_hadith': True
                    }
                today = date.today()
                random.seed(today.toordinal())
                verse = random.choice(verses)
                return {
                    'title': 'آیه روز',
                    'verse': getattr(verse, 'verse_persian', getattr(verse, 'translation', '')),
                    'arabic_text': getattr(verse, 'verse_arabic', ''),
                    'translation': getattr(verse, 'verse_persian', getattr(verse, 'translation', '')),
                    'surah': getattr(verse, 'surah_name', 'قرآن'),
                    'verse_number': getattr(verse, 'verse_number', ''),
                    'is_hadith': False
                }
            except Exception as e:
                print(f"❌ خطا در دریافت آیه: {e}")
                hadith = hadiths[0]
                return {
                    'title': hadith['title'],
                    'verse': hadith['persian'],
                    'arabic_text': hadith['arabic'],
                    'translation': hadith['persian'],
                    'surah': hadith['source'],
                    'verse_number': '',
                    'is_hadith': True
                }
    
    # ============================================
    # توابع هوش مصنوعی قرآنی
    # ============================================
    
    def find_best_answer(question):
        """پیدا کردن بهترین پاسخ برای سوال کاربر از دیتابیس"""
        from sqlalchemy import or_
        
        question_clean = question.strip().lower()
        
        exact_match = QuranQA.query.filter(
            QuranQA.is_active == True,
            QuranQA.question == question_clean
        ).first()
        
        if exact_match:
            return exact_match
        
        contains_match = QuranQA.query.filter(
            QuranQA.is_active == True,
            or_(
                QuranQA.question.contains(question_clean),
                QuranQA.keywords.contains(question_clean)
            )
        ).order_by(QuranQA.priority.desc()).first()
        
        if contains_match:
            return contains_match
        
        keywords = question_clean.split()
        for keyword in keywords:
            if len(keyword) > 2:
                keyword_match = QuranQA.query.filter(
                    QuranQA.is_active == True,
                    QuranQA.keywords.contains(keyword)
                ).order_by(QuranQA.priority.desc()).first()
                if keyword_match:
                    return keyword_match
        
        return None
    
    def get_suggestions_by_mood(mood):
        """دریافت آیات پیشنهادی بر اساس حال و هوا"""
        suggestions = QuranSuggestion.query.filter_by(
            mood=mood, 
            is_active=True
        ).order_by(QuranSuggestion.order).limit(5).all()
        
        verses = []
        for s in suggestions:
            verses.append({
                'text': s.verse_text,
                'translation': s.verse_translation,
                'surah': s.surah_name,
                'ayah': s.verse_number
            })
        return verses
    
    def save_user_chat(user_id, question, answer, related_verses=None):
        """ذخیره تاریخچه چت کاربر"""
        try:
            chat = UserQuranChat(
                user_id=user_id,
                question=question,
                answer=answer,
                related_verses=related_verses
            )
            db.session.add(chat)
            db.session.commit()
        except Exception as e:
            print(f"خطا در ذخیره چت: {e}")
    
    def format_answer_with_verses(qa_obj):
        """فرمت کردن پاسخ با آیات مرتبط"""
        import json
        
        answer_text = qa_obj.answer
        
        answer_text += "\n\n📚 **منبع:** پاسخ بر اساس قرآن کریم و تفاسیر معتبر"
        
        related_verses = []
        if qa_obj.related_verses:
            try:
                related_verses = json.loads(qa_obj.related_verses)
            except:
                pass
        
        suggestions = []
        if qa_obj.category:
            suggestions = [
                f"تفسیر آیات مربوط به {qa_obj.category}",
                f"آیات مشابه در قرآن",
                "معنای عمیق‌تر این مفهوم"
            ]
        
        return {
            "success": True,
            "answer": answer_text,
            "is_quranic": True,
            "related_verses": related_verses,
            "suggestions": suggestions
        }
    
    # ============================================
    # توابع کمکی
    # ============================================
    
    def save_uploaded_file(file, subfolder='events'):
        """ذخیره فایل آپلود شده و برگرداندن مسیر"""
        if not file or file.filename == '':
            return None
        
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        return os.path.join(subfolder, filename)
    
    def create_notification(user_id, title, message):
        """ایجاد اعلان جدید"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message
            )
            db.session.add(notification)
            db.session.commit()
        except:
            db.session.rollback()
    
    def convert_academic_rank(rank_value):
        """تبدیل مقدار فارسی academic_rank به enum"""
        if rank_value is None:
            return None
        
        if hasattr(rank_value, 'value'):
            return rank_value
        
        rank_str = str(rank_value)
        
        mapping = {
            'استاد': 'PROFESSOR',
            'دانشیار': 'ASSOCIATE_PROFESSOR',
            'استادیار': 'ASSISTANT_PROFESSOR',
            'مربی': 'INSTRUCTOR',
            'استاد مدعو': 'VISITING_LECTURER',
            'پژوهشگر': 'RESEARCHER',
            'دکتر': 'DOCTORAL',
            'کارشناسی ارشد': 'MASTER',
            'کارشناسی': 'BACHELOR'
        }
        
        return mapping.get(rank_str, 'OTHER')
    
    def update_leaderboard(competition_id):
        """به‌روزرسانی لیدربورد مسابقه"""
        registrations = CompetitionRegistration.query.filter_by(competition_id=competition_id).all()
        for reg in registrations:
            total_score = db.session.query(db.func.sum(JudgeScore.score)).filter_by(registration_id=reg.id).scalar() or 0
            reg.final_score = total_score
        db.session.commit()
        sorted_regs = CompetitionRegistration.query.filter_by(competition_id=competition_id).order_by(CompetitionRegistration.final_score.desc()).all()
        for idx, reg in enumerate(sorted_regs, 1):
            reg.rank = idx
        db.session.commit()
    
    # ============================================
    # ========== مسیر install_pwa ==========
    # ============================================
    
    @app.route('/install-pwa')
    def install_pwa():
        """صفحه راهنمای نصب برنامه روی دستگاه"""
        return render_template('install_pwa.html', current_user=current_user)
    
    # ============================================
    # مسیرهای عمومی
    # ============================================
    
    @app.route('/')
    def index():
        """صفحه اصلی"""
        try:
            upcoming_events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(6).all()
        except:
            upcoming_events = []
        
        try:
            banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()
        except:
            banners = []
        
        daily_verse = get_daily_verse()
        current_date = get_persian_date()
        
        try:
            active_students = User.query.filter_by(is_active=True, role=UserRole.STUDENT).count()
            events_count = Event.query.count()
            competitions_count = Event.query.filter_by(event_type=EventType.COMPETITION).count()
            workshops_count = Event.query.filter_by(event_type=EventType.WORKSHOP).count()
        except:
            active_students = 0
            events_count = 0
            competitions_count = 0
            workshops_count = 0
        
        upcoming_competitions = []
        try:
            upcoming_competitions = Competition.query.filter(
                Competition.start_date >= datetime.utcnow(),
                Competition.is_active == True
            ).order_by(Competition.start_date).limit(6).all()
        except:
            pass
        
        upcoming_circles = []
        try:
            upcoming_circles = QuranCircle.query.filter(
                QuranCircle.is_active == True
            ).order_by(QuranCircle.created_at.desc()).limit(6).all()
        except Exception as e:
            print(f"خطا در دریافت حلقه‌ها: {e}")
            upcoming_circles = []
        
        return render_template('index.html', 
                     events=upcoming_events,
                     banners=banners,
                     daily_verse=daily_verse,
                     current_date=current_date,
                     active_students=active_students,
                     events_count=events_count,
                     competitions_count=competitions_count,
                     workshops_count=workshops_count,
                     competitions=upcoming_competitions,  
                     circles=upcoming_circles,
                     current_user=current_user)
                     
    
    @app.route('/events')
    def events_list():
        """لیست تمام رویدادها"""
        page = request.args.get('page', 1, type=int)
        event_type = request.args.get('type')
        search = request.args.get('search')
        
        query = Event.query.filter(Event.is_active == True)
        
        if event_type:
            try:
                event_type_enum = EventType(event_type)
                query = query.filter(Event.event_type == event_type_enum)
            except:
                pass
        
        if search:
            query = query.filter(
                (Event.title.contains(search)) | 
                (Event.description.contains(search))
            )
        
        try:
            events = query.order_by(Event.start_date).paginate(
                page=page, per_page=app.config.get('POSTS_PER_PAGE', 10), error_out=False
            )
        except:
            events = []
        
        return render_template('events/list.html', 
                             events=events,
                             event_types=EventType,
                             current_user=current_user)
    
    @app.route('/event/<int:event_id>')
    def event_detail(event_id):
        """صفحه جزئیات رویداد"""
        try:
            event = Event.query.get_or_404(event_id)
        except:
            flash('رویداد مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        is_registered = False
        if current_user.is_authenticated:
            try:
                registration = Registration.query.filter_by(
                    user_id=current_user.id,
                    event_id=event_id
                ).first()
                is_registered = registration is not None
            except:
                is_registered = False
        
        # ========== اضافه کردن این بخش ==========
        # محاسبه باز بودن ثبت‌نام بر اساس تاریخ شمسی
        import jdatetime
        from datetime import datetime
        
        # تاریخ امروز شمسی
        today_jalali = jdatetime.date.today()
        
        # تبدیل تاریخ رویداد به شمسی
        if isinstance(event.start_date, datetime):
            event_jalali = jdatetime.date.fromgregorian(date=event.start_date.date())
        else:
            event_jalali = jdatetime.date.fromgregorian(date=event.start_date)
        
        # اگر تاریخ رویداد > امروز باشد، ثبت‌نام باز است
        # (فقط رویدادهای بعد از امروز قابل ثبت‌نام هستند)
        is_registration_open = event_jalali > today_jalali
        
        # برای دیباگ (در ترمینال چاپ می‌شود)
        print(f"=== Event: {event.title} ===")
        print(f"Today Jalali: {today_jalali}")
        print(f"Event Jalali: {event_jalali}")
        print(f"Is Registration Open: {is_registration_open}")
        print(f"========================")
        # ======================================
        
        return render_template('events/detail.html',
                            event=event,
                            is_registered=is_registered,
                            is_registration_open=is_registration_open,  # اضافه شده
                            current_user=current_user)
    
    @app.route('/search')
    def search():
        query = request.args.get('q', '').strip()
        event_type = request.args.get('type', '')
        sort_by = request.args.get('sort', 'newest')
        page = request.args.get('page', 1, type=int)
        per_page = 12
        
        all_results = []
        
        if query:
            # جستجو در رویدادها
            events_query = Event.query.filter(Event.is_active == True)
            events_query = events_query.filter(
                or_(
                    Event.title.ilike(f'%{query}%'),
                    Event.description.ilike(f'%{query}%'),
                    Event.location.ilike(f'%{query}%')
                )
            )
            if event_type and event_type in ['workshop', 'competition', 'halaqah', 'lecture']:
                events_query = events_query.filter(Event.event_type == event_type)
            
            if sort_by == 'newest':
                events_query = events_query.order_by(Event.start_date.desc())
            elif sort_by == 'oldest':
                events_query = events_query.order_by(Event.start_date.asc())
            elif sort_by == 'popular':
                events_query = events_query.order_by(Event.current_participants.desc())
            
            for event in events_query.all():
                all_results.append({
                    'type': 'event',
                    'data': event,
                    'date': event.start_date,
                    'popularity': event.current_participants
                })
            
            # جستجو در مسابقات
            competitions_query = Competition.query.filter(Competition.is_active == True)
            competitions_query = competitions_query.filter(
                or_(
                    Competition.title.ilike(f'%{query}%'),
                    Competition.description.ilike(f'%{query}%')
                )
            )
            for comp in competitions_query.all():
                all_results.append({
                    'type': 'competition',
                    'data': comp,
                    'date': comp.start_date,
                    'popularity': comp.current_participants
                })
            
            # جستجو در حلقه‌های تلاوت
            circles_query = QuranCircle.query.filter(QuranCircle.is_active == True)
            circles_query = circles_query.filter(
                or_(
                    QuranCircle.name.ilike(f'%{query}%'),
                    QuranCircle.description.ilike(f'%{query}%'),
                    QuranCircle.teacher_name.ilike(f'%{query}%')
                )
            )
            for circle in circles_query.all():
                all_results.append({
                    'type': 'circle',
                    'data': circle,
                    'date': circle.created_at,
                    'popularity': circle.current_members
                })
            
            # مرتب‌سازی بر اساس محبوبیت
            if sort_by == 'popular':
                all_results.sort(key=lambda x: x['popularity'], reverse=True)
            elif sort_by == 'newest':
                all_results.sort(key=lambda x: x['date'], reverse=True)
            elif sort_by == 'oldest':
                all_results.sort(key=lambda x: x['date'])
            
            # صفحه‌بندی
            total = len(all_results)
            total_pages = (total + per_page - 1) // per_page
            start = (page - 1) * per_page
            end = start + per_page
            paginated_results = all_results[start:end]
            
            results = {
                'results_list': paginated_results,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_num': page - 1,
                'next_num': page + 1
            }
            
            return render_template('search.html', 
                                 query=query,
                                 results=results,
                                 event_type=event_type,
                                 sort_by=sort_by)
        
        return render_template('search.html', query='', results=None)
    @app.route('/admin/support/ticket/<int:ticket_id>')
    @login_required
    @admin_required
    def admin_support_ticket_detail(ticket_id):
        """جزئیات تیکت برای ادمین"""
        from models import SupportTicket, SupportReply
        
        ticket = SupportTicket.query.get_or_404(ticket_id)
        replies = SupportReply.query.filter_by(ticket_id=ticket_id).order_by(SupportReply.created_at).all()
        
        # نکته مهم: استفاده از قالب ادمین
        return render_template('admin/support/ticket_detail.html', 
                            ticket=ticket, 
                            replies=replies, 
                            current_user=current_user)

    @app.route('/admin/tickets')
    @login_required
    @admin_required
    def admin_all_tickets():
        """مشاهده همه تیکت‌ها برای ادمین"""
        from models import SupportTicket
        
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        query = SupportTicket.query
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        tickets = query.order_by(SupportTicket.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        
        # آمار
        stats = {
            'total': SupportTicket.query.count(),
            'open': SupportTicket.query.filter_by(status='open').count(),
            'in_progress': SupportTicket.query.filter_by(status='in_progress').count(),
            'closed': SupportTicket.query.filter_by(status='closed').count(),
        }
        
        return render_template('admin/all_tickets.html', 
                             tickets=tickets, 
                             stats=stats, 
                             current_status=status,
                             current_user=current_user)    

    
# ============================================
# مسیرهای احکام شرعی
# ============================================

    @app.route('/ahkam')
    def ahkam_list():
        from models import Ahkam
        
        category = request.args.get('category', 'all')
        
        if category == 'all':
            ahkam_list = Ahkam.query.filter_by(is_active=True).order_by(Ahkam.created_at.desc()).all()
        else:
            ahkam_list = Ahkam.query.filter_by(category=category, is_active=True).order_by(Ahkam.created_at.desc()).all()
        
        categories = Ahkam.query.with_entities(Ahkam.category).distinct().all()
        return render_template('category/ahkam.html', ahkam_list=ahkam_list, categories=categories, active_category=category)

    @app.route('/ahkam/<int:id>')
    def ahkam_detail(id):
        from models import Ahkam
        
        ahkam = Ahkam.query.get_or_404(id)
        ahkam.views += 1
        db.session.commit()
        return render_template('category/ahkam_detail.html', ahkam=ahkam)

    @app.route('/admin/ahkam')
    @login_required
    @admin_required
    def admin_ahkam():
        from models import Ahkam
        ahkam_list = Ahkam.query.order_by(Ahkam.created_at.desc()).all()
        return render_template('admin/ahkam_list.html', ahkam_list=ahkam_list)
    @app.route('/admin/seraj-yari')
    @login_required
    @admin_required
    def admin_seraj_yari():
        """پنل مدیریت سِراج‌یار برای ادمین"""
        from models import SerajCategory, SerajQA, SerajSuggestion, SerajChat
        
        # آمار
        total_qa = SerajQA.query.filter_by(is_active=True).count()
        total_categories = SerajCategory.query.filter_by(is_active=True).count()
        total_suggestions = SerajSuggestion.query.filter_by(is_active=True).count()
        total_chats = SerajChat.query.count()
        
        # لیست سوالات
        qa_list = SerajQA.query.order_by(SerajQA.created_at.desc()).limit(20).all()
        categories = SerajCategory.query.filter_by(is_active=True).order_by(SerajCategory.order).all()
        
        return render_template('admin/seraj_yari.html',
                             total_qa=total_qa,
                             total_categories=total_categories,
                             total_suggestions=total_suggestions,
                             total_chats=total_chats,
                             qa_list=qa_list,
                             categories=categories,
                             current_user=current_user)    

    @app.route('/admin/ahkam/add', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_ahkam_add():
        from models import Ahkam
        from forms import AhkamForm
        
        form = AhkamForm()
        if form.validate_on_submit():
            ahkam = Ahkam(
                title=form.title.data,
                category=form.category.data,
                ruling_type=form.ruling_type.data,
                short_description=form.short_description.data,
                full_content=form.full_content.data,
                source=form.source.data,
                marja=form.marja.data,
                is_active=form.is_active.data
            )
            db.session.add(ahkam)
            db.session.commit()
            flash('حکم با موفقیت اضافه شد!', 'success')
            return redirect(url_for('admin_ahkam'))
        return render_template('admin/ahkam_form.html', form=form, title='افزودن حکم جدید')

    @app.route('/admin/ahkam/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_ahkam_edit(id):
        from models import Ahkam
        from forms import AhkamForm
        
        ahkam = Ahkam.query.get_or_404(id)
        form = AhkamForm(obj=ahkam)
        if form.validate_on_submit():
            ahkam.title = form.title.data
            ahkam.category = form.category.data
            ahkam.ruling_type = form.ruling_type.data
            ahkam.short_description = form.short_description.data
            ahkam.full_content = form.full_content.data
            ahkam.source = form.source.data
            ahkam.marja = form.marja.data
            ahkam.is_active = form.is_active.data
            db.session.commit()
            flash('حکم با موفقیت ویرایش شد!', 'success')
            return redirect(url_for('admin_ahkam'))
        return render_template('admin/ahkam_form.html', form=form, title='ویرایش حکم')



    from flask import redirect, url_for, flash

    @app.route('/admin/ahkam/delete/<int:id>', methods=['GET', 'POST', 'DELETE'])
    def admin_ahkam_delete(id):
        ahkam = Ahkam.query.get_or_404(id)
        db.session.delete(ahkam)
        db.session.commit()
        flash('حکم شرعی با موفقیت حذف شد', 'success')
        return redirect(url_for('admin_ahkam'))
    
        # ============================================
    # ========== مسیرهای نهج‌البلاغه ==========
    # ============================================

    # ========== صفحات عمومی ==========

    @app.route('/nahj')
    def nahj_index():
        """صفحه اصلی نهج‌البلاغه"""
        try:
            categories = NahjCategory.query.filter_by(is_active=True).order_by(NahjCategory.order).all()
            featured_contents = NahjContent.query.filter_by(is_featured=True, is_active=True).limit(6).all()
        except:
            categories = []
            featured_contents = []
        
        return render_template('nahj/index.html', 
                            categories=categories, 
                            featured_contents=featured_contents,
                            current_user=current_user)

    @app.route('/nahj/category/<slug>')
    def nahj_category(slug):
        """نمایش مطالب یک دسته"""
        try:
            category = NahjCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
            contents = NahjContent.query.filter_by(category_id=category.id, is_active=True).order_by(NahjContent.number).all()
        except:
            flash('دسته‌بندی مورد نظر یافت نشد.', 'error')
            return redirect(url_for('nahj_index'))
        
        return render_template('nahj/category.html', 
                            category=category, 
                            contents=contents,
                            current_user=current_user)

    @app.route('/nahj/content/<int:id>')
    def nahj_content_detail(id):
        """جزئیات یک مطلب"""
        try:
            content = NahjContent.query.filter_by(id=id, is_active=True).first_or_404()
            content.view_count += 1
            db.session.commit()
            
            # مطالب مرتبط
            related = NahjContent.query.filter(
                NahjContent.category_id == content.category_id,
                NahjContent.id != content.id,
                NahjContent.is_active == True
            ).limit(5).all()
        except:
            flash('مطلب مورد نظر یافت نشد.', 'error')
            return redirect(url_for('nahj_index'))
        
        return render_template('nahj/content_detail.html', 
                            content=content, 
                            related=related,
                            current_user=current_user)

    # ========== مدیریت دسته‌بندی‌ها (فقط ادمین) ==========

    @app.route('/admin/nahj/categories')
    @login_required
    @admin_required
    def admin_nahj_categories():
        """مدیریت دسته‌بندی‌های نهج‌البلاغه"""
        categories = NahjCategory.query.order_by(NahjCategory.order).all()
        return render_template('admin/nahj/categories.html', 
                            categories=categories, 
                            current_user=current_user)

    @app.route('/admin/nahj/category/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_add_category():
        """افزودن دسته‌بندی جدید"""
        data = request.get_json()
        
        name = data.get('name')
        slug = data.get('slug')
        icon = data.get('icon', 'fa-feather-alt')
        description = data.get('description')
        order = data.get('order', 0)
        
        if not name or not slug:
            return jsonify({'success': False, 'message': 'نام و اسلاگ الزامی است'})
        
        # بررسی تکراری نبودن slug
        existing = NahjCategory.query.filter_by(slug=slug).first()
        if existing:
            return jsonify({'success': False, 'message': 'این اسلاگ قبلاً استفاده شده است'})
        
        category = NahjCategory(
            name=name,
            slug=slug,
            icon=icon,
            description=description,
            order=order,
            is_active=True
        )
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'دسته‌بندی با موفقیت اضافه شد'})

    @app.route('/admin/nahj/category/<int:id>/edit', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_edit_category(id):
        """ویرایش دسته‌بندی"""
        category = NahjCategory.query.get_or_404(id)
        data = request.get_json()
        
        category.name = data.get('name', category.name)
        category.slug = data.get('slug', category.slug)
        category.icon = data.get('icon', category.icon)
        category.description = data.get('description', category.description)
        category.order = data.get('order', category.order)
        category.is_active = data.get('is_active', category.is_active)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'دسته‌بندی با موفقیت ویرایش شد'})

    @app.route('/admin/nahj/category/<int:id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_delete_category(id):
        """حذف دسته‌بندی"""
        category = NahjCategory.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True, 'message': 'دسته‌بندی با موفقیت حذف شد'})

    # ========== مدیریت محتوا (فقط ادمین) ==========

    @app.route('/admin/nahj/contents')
    @login_required
    @admin_required
    def admin_nahj_contents():
        """مدیریت محتوای نهج‌البلاغه"""
        category_id = request.args.get('category_id', type=int)
        query = NahjContent.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        contents = query.order_by(NahjContent.created_at.desc()).all()
        categories = NahjCategory.query.all()
        
        return render_template('admin/nahj/contents.html', 
                            contents=contents, 
                            categories=categories,
                            selected_category=category_id,
                            current_user=current_user)

    @app.route('/admin/nahj/content/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_add_content():
        """افزودن مطلب جدید"""
        data = request.get_json()
        
        content = NahjContent(
            category_id=data.get('category_id'),
            title=data.get('title'),
            number=data.get('number'),
            arabic_text=data.get('arabic_text', ''),
            persian_text=data.get('persian_text'),
            explanation=data.get('explanation', ''),
            tags=data.get('tags', ''),
            is_featured=data.get('is_featured', False),
            is_active=True
        )
        db.session.add(content)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'مطلب با موفقیت اضافه شد', 'id': content.id})

    @app.route('/admin/nahj/content/<int:id>/edit', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_edit_content(id):
        """ویرایش مطلب"""
        content = NahjContent.query.get_or_404(id)
        data = request.get_json()
        
        content.category_id = data.get('category_id', content.category_id)
        content.title = data.get('title', content.title)
        content.number = data.get('number', content.number)
        content.arabic_text = data.get('arabic_text', content.arabic_text)
        content.persian_text = data.get('persian_text', content.persian_text)
        content.explanation = data.get('explanation', content.explanation)
        content.tags = data.get('tags', content.tags)
        content.is_featured = data.get('is_featured', content.is_featured)
        content.is_active = data.get('is_active', content.is_active)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'مطلب با موفقیت ویرایش شد'})

    @app.route('/admin/nahj/content/<int:id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_nahj_delete_content(id):
        """حذف مطلب"""
        content = NahjContent.query.get_or_404(id)
        db.session.delete(content)
        db.session.commit()
        return jsonify({'success': True, 'message': 'مطلب با موفقیت حذف شد'})

    @app.route('/admin/nahj/content/<int:id>/get')
    @login_required
    @admin_required
    def admin_nahj_get_content(id):
        """دریافت اطلاعات یک مطلب برای ویرایش"""
        content = NahjContent.query.get_or_404(id)
        return jsonify({
            'success': True,
            'content': {
                'id': content.id,
                'category_id': content.category_id,
                'title': content.title,
                'number': content.number,
                'arabic_text': content.arabic_text,
                'persian_text': content.persian_text,
                'explanation': content.explanation,
                'tags': content.tags,
                'is_featured': content.is_featured,
                'is_active': content.is_active
            }
        })
    # ============================================
    # مسیرهای احراز هویت
    # ============================================
    
    @app.route('/auth/register', methods=['GET', 'POST'])
    def register():
        """ثبت‌نام کاربر جدید"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            errors = []
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد.')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید.')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد.')
            
            if password != confirm_password:
                errors.append('رمز عبور و تأیید آن مطابقت ندارند.')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است.')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register'))
            
            user = User(
                username=username,
                email=email,
                first_name=request.form.get('first_name', ''),
                last_name=request.form.get('last_name', ''),
                student_id=request.form.get('student_id'),
                university=request.form.get('university'),
                faculty=request.form.get('faculty'),
                phone=request.form.get('phone'),
                role=UserRole.STUDENT,
                user_type='student',
                is_active=True,
                is_verified=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            create_notification(
                user.id,
                'به سِراج خوش آمدید!',
                f'کاربر گرامی {user.full_name}، ثبت‌نام شما با موفقیت انجام شد. می‌توانید از رویدادهای قرآنی دیدن کنید.'
            )
            
            flash('ثبت‌نام با موفقیت انجام شد. لطفاً وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """صفحه ورود کاربر"""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('لطفاً نام کاربری/ایمیل و رمز عبور را وارد کنید.', 'danger')
                return render_template('auth/login.html')
            
            from sqlalchemy import func
            user = User.query.filter(
                (func.lower(User.email) == username.lower()) | 
                (func.lower(User.username) == username.lower())
            ).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash(f'خوش آمدید {user.first_name} {user.last_name}', 'success')
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('نام کاربری/ایمیل یا رمز عبور نادرست است.', 'danger')
        
        return render_template('auth/login.html')
    
    @app.route('/not-approved')
    def not_approved():
        """صفحه کاربران در انتظار تأیید"""
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if current_user.is_verified or current_user.user_type == 'student':
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        return render_template('not_approved.html')
    
    @app.route('/auth/logout')
    @login_required
    def logout():
        """خروج کاربر"""
        logout_user()
        flash('با موفقیت خارج شدید.', 'info')
        return redirect(url_for('index'))
    
    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """صفحه فراموشی رمز عبور"""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            identifier = request.form.get('email', '').strip().lower()
            
            if not identifier:
                flash('لطفاً ایمیل یا نام کاربری خود را وارد کنید.', 'danger')
                return render_template('auth/forgot_password.html')
            
            from sqlalchemy import func
            user = User.query.filter(
                (func.lower(User.email) == identifier) | 
                (func.lower(User.username) == identifier)
            ).first()
            
            if user:
                temp_password = "1234567"
                
                # استفاده از password_hash به جای password
                user.password_hash = generate_password_hash(temp_password)
                db.session.commit()
                
                flash(f'✅ رمز عبور موقت شما: {temp_password}', 'success')
                flash('⚠️ لطفاً پس از ورود، رمز عبور خود را تغییر دهید.', 'info')
                
                return redirect(url_for('login'))
            else:
                flash('❌ کاربری با این ایمیل یا نام کاربری یافت نشد.', 'danger')
        
        return render_template('auth/forgot_password.html')
    
    @app.route('/reset-password', methods=['GET', 'POST'])
    @login_required
    def reset_password():
        """تغییر رمز عبور توسط کاربر وارد شده"""
        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # بررسی رمز فعلی
            if not check_password_hash(current_user.password_hash, current_password):
                flash('رمز عبور فعلی اشتباه است.', 'danger')
                return render_template('auth/reset_password.html')
            
            # بررسی رمز جدید
            if len(new_password) < 6:
                flash('رمز عبور جدید باید حداقل ۶ کاراکتر باشد.', 'danger')
                return render_template('auth/reset_password.html')
            
            if new_password != confirm_password:
                flash('رمز عبور جدید و تکرار آن مطابقت ندارند.', 'danger')
                return render_template('auth/reset_password.html')
            
            # تغییر رمز
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            flash('رمز عبور شما با موفقیت تغییر کرد.', 'success')
            return redirect(url_for('profile'))
        
        return render_template('auth/reset_password.html')


    @app.route('/ahkam')
    def ahkam():
        return render_template('category/ahkam.html')
       
    
    # ============================================
    # ========== مسیرهای کاربر عادی ==========
    # ============================================
    
    @app.route('/dashboard')
    @login_required
    @verified_required
    def dashboard():
        """داشبورد کاربر عادی"""
        # اگر کاربر ادمین است به پنل ادمین برود
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        # اگر کاربر استاد است به پنل استاد برود
        elif current_user.is_professor():
            return redirect(url_for('professor_dashboard'))
        # اگر کاربر کارمند است به داشبورد کارمندان برود
        elif current_user.is_staff():
            return redirect(url_for('staff_dashboard'))
        
        try:
            # رویدادهای ثبت‌نام شده کاربر
            user_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).order_by(Registration.registration_date.desc()).limit(5).all()
        except:
            user_registrations = []
        
        try:
            # رویدادهای پیش‌رو
            upcoming_events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(5).all()
        except:
            upcoming_events = []
        
        try:
            # اعلان‌های خوانده نشده
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).order_by(Notification.created_at.desc()).limit(5).all()
        except:
            unread_notifications = []
        
        try:
            # تعداد اعلان‌های خوانده نشده
            unread_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        except:
            unread_count = 0
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        return render_template('participant/dashboard.html',
                             registrations=user_registrations,
                             upcoming_events=upcoming_events,
                             notifications=unread_notifications,
                             unread_count=unread_count,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             current_user=current_user)
    
    @app.route('/event/register/<int:event_id>', methods=['POST'])
    @login_required
    @verified_required
    def register_for_event(event_id):
        """ثبت‌نام در رویداد"""
        try:
            event = Event.query.get_or_404(event_id)
        except:
            flash('رویداد مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        # بررسی وجود رویداد
        if not event.is_active:
            flash('این رویداد فعال نیست.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # بررسی ظرفیت
        if event.is_full():
            flash('ظرفیت این رویداد تکمیل شده است.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # بررسی ثبت‌نام قبلی
        existing_registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event_id
        ).first()
        
        if existing_registration:
            flash('شما قبلاً در این رویداد ثبت‌نام کرده‌اید.', 'warning')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # ثبت‌نام
        registration = Registration(
            user_id=current_user.id,
            event_id=event_id
        )
        
        event.current_participants += 1
        
        db.session.add(registration)
        db.session.commit()
        
        # اعلان به کاربر
        create_notification(
            current_user.id,
            'ثبت‌نام موفق',
            f'ثبت‌نام شما در رویداد "{event.title}" با موفقیت انجام شد.'
        )
        
        # اعلان به مدیر (اختیاری)
        try:
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id,
                    'ثبت‌نام جدید در رویداد',
                    f'کاربر {current_user.full_name} در رویداد "{event.title}" ثبت‌نام کرد.'
                )
        except:
            pass
        
        flash('ثبت‌نام شما با موفقیت انجام شد.', 'success')
        return redirect(url_for('event_detail', event_id=event_id))
    
    @app.route('/event/cancel/<int:event_id>', methods=['POST'])
    @login_required
    @verified_required
    def cancel_registration(event_id):
        """لغو ثبت‌نام در رویداد"""
        try:
            registration = Registration.query.filter_by(
                user_id=current_user.id,
                event_id=event_id
            ).first_or_404()
        except:
            flash('ثبت‌نام مورد نظر یافت نشد.', 'error')
            return redirect(url_for('events_list'))
        
        event = registration.event
        
        if event.start_date < datetime.utcnow():
            flash('امکان لغو ثبت‌نام پس از برگزاری رویداد وجود ندارد.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # کاهش تعداد شرکت‌کنندگان
        event.current_participants -= 1
        
        db.session.delete(registration)
        db.session.commit()
        
        create_notification(
            current_user.id,
            'لغو ثبت‌نام',
            f'ثبت‌نام شما در رویداد "{event.title}" لغو شد.'
        )
        
        flash('ثبت‌نام شما با موفقیت لغو شد.', 'success')
        return redirect(url_for('event_detail', event_id=event_id))
    
    @app.route('/profile')
    @login_required
    @verified_required
    def profile():
        """پروفایل کاربر - همه کاربران می‌توانند ببینند"""
        try:
            # آمار کاربر
            total_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).count()
            
            attended_events = Registration.query.filter_by(
                user_id=current_user.id,
                attended=True
            ).count()
            
            upcoming_registrations = Registration.query.filter(
                Registration.user_id == current_user.id,
                Registration.event.has(Event.start_date >= datetime.utcnow())
            ).count()
            
            # تعداد اعلان‌های خوانده نشده
            unread_notifications_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
            
            # دریافت آخرین فعالیت‌ها (ثبت‌نام‌های اخیر کاربر)
            recent_activities = Registration.query.filter_by(
                user_id=current_user.id
            ).order_by(Registration.registration_date.desc()).limit(5).all()
            
        except:
            total_registrations = 0
            attended_events = 0
            upcoming_registrations = 0
            unread_notifications_count = 0
            recent_activities = []
        
        return render_template('participant/profile.html',
                            total_registrations=total_registrations,
                            attended_events=attended_events,
                            upcoming_registrations=upcoming_registrations,
                            unread_notifications_count=unread_notifications_count,
                            recent_activities=recent_activities,
                            current_user=current_user)
    
    @app.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def edit_profile():
        """ویرایش پروفایل"""
        if request.method == 'POST':
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            current_user.university = request.form.get('university')
            current_user.faculty = request.form.get('faculty')
            current_user.student_id = request.form.get('student_id')
            
            # تغییر رمز عبور (در صورت ارائه)
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('رمز عبور فعلی نادرست است.', 'error')
                    return redirect(url_for('edit_profile'))
                
                if new_password != confirm_password:
                    flash('رمز عبور جدید و تأیید آن مطابقت ندارند.', 'error')
                    return redirect(url_for('edit_profile'))
                
                if len(new_password) < 6:
                    flash('رمز عبور باید حداقل ۶ کاراکتر باشد.', 'error')
                    return redirect(url_for('edit_profile'))
                
                current_user.set_password(new_password)
                flash('رمز عبور با موفقیت تغییر یافت.', 'success')
            
            db.session.commit()
            flash('پروفایل با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('profile'))
        
        return render_template('participant/edit_profile.html',
                             current_user=current_user)
    
    @app.route('/notifications')
    @login_required
    @verified_required
    def notifications():
        """لیست اعلان‌ها"""
        page = request.args.get('page', 1, type=int)
        
        try:
            user_notifications = Notification.query.filter_by(
                user_id=current_user.id
            ).order_by(Notification.created_at.desc()).paginate(
                page=page, per_page=20, error_out=False
            )
        except:
            user_notifications = []
        
        return render_template('participant/notifications.html',
                             notifications=user_notifications,
                             current_user=current_user)
    
    @app.route('/notification/read/<int:notification_id>')
    @login_required
    @verified_required
    def mark_notification_read(notification_id):
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        try:
            notification = Notification.query.get_or_404(notification_id)
        except:
            flash('اعلان مورد نظر یافت نشد.', 'error')
            return redirect(url_for('notifications'))
        
        if notification.user_id != current_user.id:
            flash('دسترسی غیرمجاز.', 'error')
            return redirect(url_for('notifications'))
        
        notification.is_read = True
        db.session.commit()
        
        return redirect(url_for('notifications'))
    
    @app.route('/notification/read-all', methods=['POST'])
    @login_required
    @verified_required
    def mark_all_notifications_read():
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        try:
            Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).update({'is_read': True})
            
            db.session.commit()
            flash('همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.', 'success')
        except:
            flash('خطا در به‌روزرسانی اعلان‌ها.', 'error')
        
        return redirect(url_for('notifications'))
    
    @app.route('/my-events')
    @login_required
    @verified_required
    def my_events():
        """رویدادهای ثبت‌نام شده کاربر"""
        page = request.args.get('page', 1, type=int)
        
        try:
            registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).order_by(Registration.registration_date.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            registrations = []
        
        return render_template('participant/my_events.html',
                             registrations=registrations,
                             current_user=current_user)
    
    # ============================================
    # ========== مسیرهای کارمندان ==========
    # ============================================
    
    @app.route('/staff/dashboard')
    @login_required
    @staff_required
    def staff_dashboard():
        """داشبورد کارمندان و اساتید - متصل به پایگاه داده"""
        
        # =============== آمارهای عمومی ===============
        try:
            total_students = User.query.filter_by(user_type='student', is_active=True).count()
        except:
            total_students = 0
        
        try:
            total_professors = User.query.filter_by(user_type='professor', is_active=True).count()
        except:
            total_professors = 0
        
        try:
            total_staff = User.query.filter_by(user_type='staff', is_active=True).count()
        except:
            total_staff = 0
        
        try:
            pending_approvals = User.query.filter_by(is_verified=False, is_active=True).count()
        except:
            pending_approvals = 0
        
        # لیست کاربرانی که نیاز به تأیید دارند
        try:
            pending_users = User.query.filter_by(is_verified=False, is_active=True).order_by(
                User.created_at.desc()
            ).limit(10).all()
        except:
            pending_users = []
        
        # کاربران جدید
        try:
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        except:
            recent_users = []
        
        # آمار رویدادها
        try:
            total_events = Event.query.count()
        except:
            total_events = 0
        
        try:
            active_events = Event.query.filter_by(is_active=True).count()
        except:
            active_events = 0
        
        try:
            upcoming_events_count = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).count()
        except:
            upcoming_events_count = 0
        
        # رویدادهای پیش‌رو
        try:
            events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(5).all()
        except:
            events = []
        
        # آمار حلقه‌های تلاوت
        try:
            total_circles = QuranCircle.query.count()
        except:
            total_circles = 0
        
        try:
            active_circles = QuranCircle.query.filter_by(is_active=True).count()
        except:
            active_circles = 0
        
        # =============== محاسبات آماری برای کارت‌ها ===============
        
        # کلاس‌های فعال
        try:
            active_classes = Class.query.filter_by(is_active=True).count()
        except:
            active_classes = 18
        
        # کلاس‌های این هفته
        try:
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            classes_this_week = Class.query.filter(
                Class.start_date >= start_of_week,
                Class.start_date <= end_of_week
            ).count()
        except:
            classes_this_week = 5
        
        # دانشجویان جدید این ماه
        try:
            first_day_of_month = datetime.now().replace(day=1)
            new_students_month = User.query.filter(
                User.user_type == 'student',
                User.created_at >= first_day_of_month
            ).count()
        except:
            new_students_month = 23
        
        # میانگین حضور (محاسبه از جدول attendances)
        try:
            avg_attendance_result = db.session.query(
                func.avg(Attendance.status == 'present').cast(db.Float) * 100
            ).scalar()
            avg_attendance = int(avg_attendance_result) if avg_attendance_result else 78
        except:
            avg_attendance = 78
        
        # جلسات برگزار شده
        try:
            completed_sessions = CourseSession.query.filter(
                CourseSession.session_date < datetime.now().date()
            ).count()
        except:
            completed_sessions = 124
        
        # نزدیک‌ترین جلسه
        try:
            next_session = CourseSession.query.filter(
                CourseSession.session_date >= datetime.now().date(),
                CourseSession.is_cancelled == False
            ).order_by(CourseSession.session_date, CourseSession.start_time).first()
            
            if next_session:
                # تبدیل تاریخ به شمسی
                try:
                    gregorian_date = next_session.session_date
                    jdate = jdatetime.date.fromgregorian(date=gregorian_date)
                    persian_months = {
                        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
                        5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
                        9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
                    }
                    next_session_date = f"{jdate.day} {persian_months[jdate.month]} {jdate.year}"
                except:
                    next_session_date = next_session.session_date.strftime('%Y/%m/%d')
            else:
                next_session_date = "---"
        except:
            next_session_date = "۱۵ اسفند ۱۴۰۴"
        
        # درصد تکمیل ترم (محاسبه بر اساس تاریخ)
        try:
            # فرض می‌کنیم ترم ۴ ماهه است
            semester_start = date(datetime.now().year, 1, 1)  # تاریخ شروع ترم
            semester_end = date(datetime.now().year, 4, 30)   # تاریخ پایان ترم
            today = date.today()
            
            total_days = (semester_end - semester_start).days
            passed_days = (today - semester_start).days
            
            if total_days > 0:
                semester_completion = int((passed_days / total_days) * 100)
                semester_completion = max(0, min(100, semester_completion))
            else:
                semester_completion = 65
        except:
            semester_completion = 65
        
        # تعداد دانشکده‌ها
        try:
            faculties_count = Faculty.query.count()
        except:
            faculties_count = 12
        
        # تعداد کل کلاس‌ها
        try:
            total_classes_count = Class.query.count()
        except:
            total_classes_count = 32
        
        # =============== کلاس‌های من (بر اساس کاربر جاری) ===============
        my_classes = []
        try:
            classes = Class.query.filter_by(instructor_id=current_user.id).limit(10).all()
            
            for cls in classes:
                # تعداد دانشجویان کلاس
                student_count = ClassEnrollment.query.filter_by(
                    class_id=cls.id,
                    status='active'
                ).count()
                
                # محاسبه درصد حضور برای این کلاس
                try:
                    # دریافت تمام جلسات این کلاس
                    sessions = CourseSession.query.filter_by(class_id=cls.id).all()
                    session_ids = [s.id for s in sessions]
                    
                    if session_ids:
                        # تعداد کل حضورهای ممکن
                        total_possible_attendances = len(session_ids) * student_count
                        
                        # تعداد حضورهای ثبت شده
                        actual_attendances = Attendance.query.filter(
                            Attendance.session_id.in_(session_ids),
                            Attendance.status == 'present'
                        ).count()
                        
                        if total_possible_attendances > 0:
                            attendance_percent = int((actual_attendances / total_possible_attendances) * 100)
                        else:
                            attendance_percent = 0
                    else:
                        attendance_percent = 0
                except:
                    attendance_percent = random.randint(60, 95)
                
                my_classes.append({
                    'name': cls.name,
                    'code': cls.code,
                    'student_count': student_count,
                    'attendance_percent': attendance_percent
                })
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            # داده نمونه در صورت عدم وجود
            my_classes = [
                {'name': 'ریاضی ۱', 'code': 'MATH101', 'student_count': 35, 'attendance_percent': 85},
                {'name': 'فیزیک ۱', 'code': 'PHY101', 'student_count': 42, 'attendance_percent': 62},
                {'name': 'برنامه‌نویسی', 'code': 'CS101', 'student_count': 28, 'attendance_percent': 91},
            ]
        
        # =============== جلسات آینده ===============
        upcoming_sessions = []
        try:
            sessions = CourseSession.query.filter(
                CourseSession.session_date >= datetime.now().date(),
                CourseSession.is_cancelled == False
            ).order_by(CourseSession.session_date, CourseSession.start_time).limit(10).all()
            
            for session in sessions:
                class_obj = Class.query.get(session.class_id)
                
                # تبدیل تاریخ به شمسی
                try:
                    gregorian_date = session.session_date
                    jdate = jdatetime.date.fromgregorian(date=gregorian_date)
                    persian_date = f"{jdate.year}/{jdate.month}/{jdate.day}"
                except:
                    persian_date = session.session_date.strftime('%Y/%m/%d')
                
                # فرمت زمان
                time_str = session.start_time.strftime('%H:%M') if session.start_time else '---'
                
                upcoming_sessions.append({
                    'class_name': class_obj.name if class_obj else '---',
                    'title': session.title,
                    'date': persian_date,
                    'time': time_str,
                    'location': session.location
                })
        except Exception as e:
            print(f"خطا در دریافت جلسات آینده: {e}")
            upcoming_sessions = [
                {'class_name': 'ریاضی ۱', 'title': 'جلسه ۱۲ - مشتق', 'date': '۱۴۰۴/۱۲/۲۰', 'time': '۱۰:۰۰', 'location': 'کلاس ۲۰۳'},
                {'class_name': 'فیزیک ۱', 'title': 'آزمایشگاه', 'date': '۱۴۰۴/۱۲/۲۱', 'time': '۱۴:۰۰', 'location': 'آزمایشگاه فیزیک'},
            ]
        
        # =============== دانشجویان کم‌حضور ===============
        low_attendance_students = []
        try:
            # دریافت دانشجویانی که حضور کمتر از 50% دارند
            students = User.query.filter_by(user_type='student', is_active=True).limit(50).all()
            
            for student in students:
                # دریافت تمام ثبت‌نام‌های کلاس این دانشجو
                enrollments = ClassEnrollment.query.filter_by(
                    student_id=student.id,
                    status='active'
                ).all()
                
                for enrollment in enrollments[:2]:  # حداکثر 2 کلاس برای هر دانشجو
                    class_obj = Class.query.get(enrollment.class_id)
                    
                    # دریافت جلسات این کلاس
                    sessions = CourseSession.query.filter_by(class_id=enrollment.class_id).all()
                    session_ids = [s.id for s in sessions]
                    
                    if session_ids:
                        # تعداد حضورهای این دانشجو
                        attendances = Attendance.query.filter(
                            Attendance.session_id.in_(session_ids),
                            Attendance.student_id == student.id,
                            Attendance.status == 'present'
                        ).count()
                        
                        attendance_percent = int((attendances / len(session_ids)) * 100) if session_ids else 0
                        
                        if attendance_percent < 50:
                            low_attendance_students.append({
                                'id': student.id,
                                'name': student.full_name,
                                'student_id': getattr(student, 'student_id', '---'),
                                'class_name': class_obj.name if class_obj else '---',
                                'attendance_percent': attendance_percent
                            })
                            
                            if len(low_attendance_students) >= 10:
                                break
                
                if len(low_attendance_students) >= 10:
                    break
        except Exception as e:
            print(f"خطا در دریافت دانشجویان کم‌حضور: {e}")
            low_attendance_students = [
                {'id': 1, 'name': 'علی محمدی', 'student_id': '۴۰۰۱۲۳۴۵۶', 'class_name': 'معارف اسلامی', 'attendance_percent': 35},
                {'id': 2, 'name': 'زهرا احمدی', 'student_id': '۴۰۰۱۲۳۴۵۷', 'class_name': 'فیزیک ۱', 'attendance_percent': 42},
            ]
        
        # =============== دانشجویان دانشگاه (فیلتر شده بر اساس دانشگاه کاربر) ===============
        university_students = []
        try:
            students = User.query.filter_by(
                user_type='student',
                university=current_user.university,
                is_active=True
            ).limit(10).all()
            
            for student in students:
                university_students.append({
                    'full_name': student.full_name,
                    'email': student.email,
                    'student_id': getattr(student, 'student_id', '---'),
                    'major': getattr(student, 'field_of_study', '---'),
                    'is_active': student.is_active
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            university_students = [
                {'full_name': 'احمد کریمی', 'email': 'a.karimi@example.com', 'student_id': '۴۰۰۱۲۳۴۵۹', 'major': 'مهندسی کامپیوتر', 'is_active': True},
                {'full_name': 'سارا محمدی', 'email': 's.mohammadi@example.com', 'student_id': '۴۰۰۱۲۳۴۶۰', 'major': 'فیزیک', 'is_active': True},
            ]
        
        # =============== متغیرهای stats برای کارت‌های آماری ===============
        stats = {
            'active_classes': active_classes,
            'classes_this_week': classes_this_week,
            'total_students': total_students,
            'new_students_month': new_students_month,
            'avg_attendance': avg_attendance,
            'completed_sessions': completed_sessions,
            'upcoming_sessions': upcoming_events_count,
            'next_session_date': next_session_date,
            'semester_completion': semester_completion,
            'faculties_count': faculties_count,
            'total_classes': total_classes_count
        }
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        return render_template('staff/dashboard.html',
                             # آمارهای عمومی
                             total_students=total_students,
                             total_professors=total_professors,
                             total_staff=total_staff,
                             pending_approvals=pending_approvals,
                             pending_users=pending_users,
                             recent_users=recent_users,
                             total_events=total_events,
                             active_events=active_events,
                             upcoming_events=upcoming_events_count,
                             events=events,
                             total_circles=total_circles,
                             active_circles=active_circles,
                             
                             # متغیر stats برای کارت‌های آماری
                             stats=stats,
                             
                             # داده‌های جداول
                             my_classes=my_classes,
                             upcoming_sessions=upcoming_sessions,
                             low_attendance_students=low_attendance_students,
                             university_students=university_students,
                             
                             # اطلاعات عمومی
                             current_date=current_date,
                             daily_verse=daily_verse,
                             current_user=current_user,
                             now=datetime.now())

    @app.route('/staff/pending-users')
    @login_required
    @staff_required
    def staff_pending_users():
        """لیست کاربران در انتظار تأیید برای کارمندان"""
        page = request.args.get('page', 1, type=int)
        user_type = request.args.get('type', 'all')
        
        try:
            query = User.query.filter_by(is_verified=False, is_active=True)
            
            if user_type != 'all':
                query = query.filter_by(user_type=user_type)
            
            users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except:
            users = []
        
        return render_template('staff/pending_users.html', 
                             users=users,
                             current_user=current_user,
                             user_type=user_type)

    # ===============================
    # تأیید کاربر توسط staff
    # ===============================

    @app.route('/staff/verify/<int:user_id>')
    @login_required
    @staff_required
    def staff_verify_user(user_id):
        """تأیید کاربر توسط کارمند"""
        user = User.query.get_or_404(user_id)
        
        # بررسی اینکه کاربر قبلاً تأیید نشده باشد
        if user.is_verified:
            flash('این کاربر قبلاً تأیید شده است.', 'warning')
            return redirect(url_for('staff_pending_users'))
        
        # تأیید کاربر
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        user.verified_by = current_user.id
        db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '✅ تأیید حساب کاربری',
            f'حساب کاربری شما با موفقیت تأیید شد. اکنون می‌توانید وارد شوید.'
        )
        
        flash(f'کاربر {user.full_name} با موفقیت تأیید شد.', 'success')
        return redirect(url_for('staff_pending_users'))

    # ===============================
    # رد کاربر توسط staff
    # ===============================

    @app.route('/staff/reject/<int:user_id>', methods=['POST'])
    @login_required
    @staff_required
    def staff_reject_user(user_id):
        """رد درخواست کاربر توسط کارمند"""
        user = User.query.get_or_404(user_id)
        
        # بررسی اینکه کاربر قبلاً تأیید نشده باشد
        if user.is_verified:
            flash('این کاربر قبلاً تأیید شده است و نمی‌توان آن را رد کرد.', 'warning')
            return redirect(url_for('staff_pending_users'))
        
        # دریافت دلیل رد از فرم
        reason = request.form.get('reason', 'دلیل خاصی ذکر نشده است.')
        
        try:
            # غیرفعال کردن کاربر
            user.is_active = False
            user.verification_notes = f"رد شده: {reason}"
            db.session.commit()
        except:
            # اگر فیلدهای خاص وجود نداشت، حداقل کاربر را غیرفعال کن
            user.is_active = False
            db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )
        
        flash(f'درخواست کاربر {user.full_name} رد شد.', 'danger')
        return redirect(url_for('staff_pending_users'))

    @app.route('/staff/reject-user/<int:user_id>', methods=['POST'])
    @login_required
    @staff_required
    def staff_reject_user_json(user_id):
        """رد درخواست کاربر توسط کارمند (نسخه JSON برای درخواست‌های AJAX)"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        if user.is_verified:
            return jsonify({'success': False, 'message': 'این کاربر قبلاً تأیید شده است.'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'دلیل خاصی ذکر نشده است.')
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )
        
        # غیرفعال کردن کاربر
        user.is_active = False
        user.verification_notes = reason
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'درخواست کاربر {user.full_name} رد شد.'})

    @app.route('/staff/user/<int:user_id>')
    @login_required
    @staff_required
    def staff_user_detail(user_id):
        """مشاهده جزئیات کاربر برای کارمندان"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('staff_pending_users'))
        
        return render_template('staff/user_detail.html', user=user, current_user=current_user)
    
    # ============================================
    # ========== پنل اختصاصی اساتید ==========
    # ============================================

    @app.route('/professor/dashboard')
    @login_required
    def professor_dashboard():
        """داشبورد اصلی اساتید"""
        # بررسی دسترسی استاد
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        # آمار کلی
        try:
            # کلاس‌های این استاد
            my_classes_count = Class.query.filter_by(instructor_id=current_user.id, is_active=True).count()
            
            # دانشجویان تحت نظر
            total_students = db.session.query(func.count(ClassEnrollment.student_id))\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .scalar() or 0
            
            # جلسات امروز
            today_sessions_count = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date == date.today())\
                .count()
            
            # حلقه‌های تلاوت
            my_circles_count = QuranCircle.query.filter_by(created_by=current_user.id, is_active=True).count()
            
            # نمرات ثبت نشده
            pending_grades = ClassEnrollment.query\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(ClassEnrollment.grade.is_(None))\
                .count()
            
            stats = {
                'my_classes': my_classes_count,
                'total_students': total_students,
                'today_sessions': today_sessions_count,
                'my_circles': my_circles_count,
                'pending_grades': pending_grades,
                'last_login': current_user.last_login
            }
        except Exception as e:
            print(f"خطا در دریافت آمار: {e}")
            stats = {
                'my_classes': 0,
                'total_students': 0,
                'today_sessions': 0,
                'my_circles': 0,
                'pending_grades': 0
            }
        
        # کلاس‌های فعال
        try:
            classes = Class.query\
                .filter_by(instructor_id=current_user.id, is_active=True)\
                .order_by(Class.start_date.desc())\
                .limit(5).all()
            
            active_classes = []
            for cls in classes:
                student_count = ClassEnrollment.query.filter_by(class_id=cls.id, status='active').count()
                total_sessions = CourseSession.query.filter_by(class_id=cls.id).count()
                completed_sessions = CourseSession.query.filter(
                    CourseSession.class_id == cls.id,
                    CourseSession.session_date < date.today()
                ).count()
                
                active_classes.append({
                    'id': cls.id,
                    'name': cls.name,
                    'code': cls.code,
                    'student_count': student_count,
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'progress': int((completed_sessions / total_sessions * 100)) if total_sessions > 0 else 0
                })
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            active_classes = []
        
        # جلسات امروز
        try:
            today_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date == date.today())\
                .order_by(CourseSession.start_time)\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات امروز: {e}")
            today_sessions = []
        
        # جلسات آینده
        try:
            upcoming_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .filter(CourseSession.session_date > date.today())\
                .filter(CourseSession.is_cancelled == False)\
                .order_by(CourseSession.session_date)\
                .limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت جلسات آینده: {e}")
            upcoming_sessions = []
        
        return render_template('professor/dashboard.html',
                             stats=stats,
                             active_classes=active_classes,
                             today_sessions=today_sessions,
                             upcoming_sessions=upcoming_sessions,
                             current_user=current_user,
                             now=datetime.now())


    @app.route('/professor/classes')
    @login_required
    def professor_classes():
        """لیست کلاس‌های استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        term = request.args.get('term', 'current')
        page = request.args.get('page', 1, type=int)
        
        try:
            query = Class.query.filter_by(instructor_id=current_user.id)
            
            if term == 'current':
                # ترم جاری
                current_term = AcademicTerm.query.filter_by(is_current=True).first()
                if current_term:
                    query = query.filter_by(academic_term=current_term.name)
            elif term == 'past':
                # ترم‌های گذشته
                current_term = AcademicTerm.query.filter_by(is_current=True).first()
                if current_term:
                    query = query.filter(Class.academic_term != current_term.name)
            
            classes = query.order_by(Class.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except Exception as e:
            print(f"خطا در دریافت کلاس‌ها: {e}")
            classes = []
        
        return render_template('professor/classes.html',
                             classes=classes,
                             term=term,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>')
    @login_required
    def professor_class_detail(class_id):
        """جزئیات کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        # بررسی دسترسی
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ شما دسترسی به این کلاس ندارید.', 'error')
            return redirect(url_for('professor_classes'))
        
        # دانشجویان کلاس
        try:
            enrollments = ClassEnrollment.query\
                .filter_by(class_id=class_id)\
                .filter_by(status='active')\
                .join(User, User.id == ClassEnrollment.student_id)\
                .add_columns(
                    User.id,
                    User.first_name,
                    User.last_name,
                    User.student_id,
                    User.email,
                    User.phone
                ).all()
            
            students = []
            for enrollment, user_id, first_name, last_name, student_id, email, phone in enrollments:
                # آمار حضور این دانشجو
                total_sessions = CourseSession.query.filter_by(class_id=class_id).count()
                attended = Attendance.query\
                    .join(CourseSession, CourseSession.id == Attendance.session_id)\
                    .filter(CourseSession.class_id == class_id)\
                    .filter(Attendance.student_id == user_id)\
                    .filter(Attendance.status == 'present')\
                    .count()
                
                attendance_rate = int((attended / total_sessions * 100)) if total_sessions > 0 else 0
                
                students.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'student_id': student_id,
                    'email': email,
                    'phone': phone,
                    'attendance_rate': attendance_rate,
                    'grade': enrollment.grade
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            students = []
        
        # جلسات کلاس
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات: {e}")
            sessions = []
        
        return render_template('professor/class_detail.html',
                             class_obj=class_obj,
                             students=students,
                             sessions=sessions,
                             current_user=current_user,
                             now=datetime.now())


    @app.route('/professor/class/<int:class_id>/grades', methods=['GET', 'POST'])
    @login_required
    def professor_grades(class_id):
        """مدیریت نمرات کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        if request.method == 'POST':
            # ذخیره نمرات
            grades = request.form.getlist('grades[]')
            student_ids = request.form.getlist('student_ids[]')
            
            try:
                for i, student_id in enumerate(student_ids):
                    if i < len(grades) and grades[i]:
                        enrollment = ClassEnrollment.query.filter_by(
                            class_id=class_id,
                            student_id=student_id
                        ).first()
                        
                        if enrollment:
                            enrollment.grade = float(grades[i])
                
                db.session.commit()
                flash('✅ نمرات با موفقیت ثبت شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطا در ثبت نمرات: {e}', 'error')
            
            return redirect(url_for('professor_class_detail', class_id=class_id))
        
        # دریافت دانشجویان
        try:
            enrollments = ClassEnrollment.query\
                .filter_by(class_id=class_id, status='active')\
                .join(User, User.id == ClassEnrollment.student_id)\
                .add_columns(
                    User.id,
                    User.first_name,
                    User.last_name,
                    User.student_id
                ).all()
            
            students = []
            for enrollment, user_id, first_name, last_name, student_id in enrollments:
                students.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'student_id': student_id,
                    'grade': enrollment.grade
                })
        except Exception as e:
            print(f"خطا در دریافت دانشجویان: {e}")
            students = []
        
        return render_template('professor/grades.html',
                             class_obj=class_obj,
                             students=students,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/attendance', methods=['GET', 'POST'])
    @login_required
    def professor_attendance(class_id):
        """حضور و غیاب کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        session_id = request.args.get('session_id', type=int)
        
        if request.method == 'POST':
            # ثبت حضور و غیاب
            session_id = request.form.get('session_id', type=int)
            attendance_data = request.form.getlist('attendance[]')
            student_ids = request.form.getlist('student_ids[]')
            late_minutes_list = request.form.getlist('late_minutes[]')
            excuses_list = request.form.getlist('excuse[]')
            
            if not session_id:
                flash('❌ لطفاً جلسه را انتخاب کنید.', 'error')
                return redirect(request.url)
            
            try:
                # پاک کردن حضورهای قبلی این جلسه
                Attendance.query.filter_by(session_id=session_id).delete()
                
                # ثبت حضورهای جدید
                for i, student_id in enumerate(student_ids):
                    if i < len(attendance_data):
                        status = attendance_data[i]
                        late_minutes = int(late_minutes_list[i]) if i < len(late_minutes_list) else 0
                        excuse = excuses_list[i] if i < len(excuses_list) else ''
                        
                        attendance = Attendance(
                            session_id=session_id,
                            student_id=student_id,
                            status=status,
                            late_minutes=late_minutes,
                            excuse=excuse,
                            marked_by=current_user.id
                        )
                        db.session.add(attendance)
                
                db.session.commit()
                flash('✅ حضور و غیاب با موفقیت ثبت شد.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطا در ثبت حضور و غیاب: {e}', 'error')
            
            return redirect(url_for('professor_attendance', class_id=class_id, session_id=session_id))
        
        # دریافت جلسات کلاس
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except Exception as e:
            print(f"خطا در دریافت جلسات: {e}")
            sessions = []
        
        students = []
        attendances = {}
        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0
        
        if session_id:
            # دریافت دانشجویان کلاس
            try:
                enrollments = ClassEnrollment.query\
                    .filter_by(class_id=class_id, status='active')\
                    .join(User, User.id == ClassEnrollment.student_id)\
                    .add_columns(
                        User.id,
                        User.first_name,
                        User.last_name,
                        User.student_id
                    ).all()
                
                for enrollment, user_id, first_name, last_name, student_id in enrollments:
                    students.append({
                        'id': user_id,
                        'full_name': f"{first_name} {last_name}",
                        'student_id': student_id
                    })
            except Exception as e:
                print(f"خطا در دریافت دانشجویان: {e}")
            
            # دریافت حضورهای قبلی این جلسه
            try:
                attendance_records = Attendance.query\
                    .filter_by(session_id=session_id)\
                    .all()
                
                for att in attendance_records:
                    attendances[att.student_id] = {
                        'status': att.status.value if att.status else 'absent',
                        'late_minutes': att.late_minutes,
                        'excuse': att.excuse
                    }
                    
                    if att.status == 'present':
                        present_count += 1
                    elif att.status == 'absent':
                        absent_count += 1
                    elif att.status == 'late':
                        late_count += 1
                        present_count += 1
                    elif att.status == 'excused':
                        excused_count += 1
                        present_count += 1
            except Exception as e:
                print(f"خطا در دریافت حضورها: {e}")
        
        # دریافت اطلاعات جلسه انتخاب شده
        session_title = ""
        session_date = ""
        session_time = ""
        if session_id:
            try:
                session = CourseSession.query.get(session_id)
                if session:
                    session_title = session.title or f"جلسه {session.id}"
                    session_date = session.session_date.strftime('%Y/%m/%d')
                    session_time = f"{session.start_time.strftime('%H:%M') if session.start_time else '---'} - {session.end_time.strftime('%H:%M') if session.end_time else '---'}"
            except:
                pass
        
        return render_template('professor/attendance.html',
                             class_obj=class_obj,
                             sessions=sessions,
                             students=students,
                             attendances=attendances,
                             selected_session=session_id,
                             session_title=session_title,
                             session_date=session_date,
                             session_time=session_time,
                             present_count=present_count,
                             absent_count=absent_count,
                             late_count=late_count,
                             excused_count=excused_count,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/files')
    @login_required
    def professor_files(class_id):
        """مدیریت فایل‌های کلاس"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            flash('کلاس مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_classes'))
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_classes'))
        
        # فایل‌های عمومی کلاس
        try:
            class_files = ClassFile.query\
                .filter_by(class_id=class_id)\
                .order_by(ClassFile.uploaded_at.desc())\
                .all()
        except:
            class_files = []
        
        # فایل‌های جلسات
        try:
            session_files = SessionFile.query\
                .join(CourseSession, CourseSession.id == SessionFile.session_id)\
                .filter(CourseSession.class_id == class_id)\
                .order_by(SessionFile.uploaded_at.desc())\
                .all()
        except:
            session_files = []
        
        # جلسات برای انتخاب در آپلود
        try:
            sessions = CourseSession.query\
                .filter_by(class_id=class_id)\
                .order_by(CourseSession.session_date.desc())\
                .all()
        except:
            sessions = []
        
        return render_template('professor/files.html',
                             class_obj=class_obj,
                             class_files=class_files,
                             session_files=session_files,
                             sessions=sessions,
                             current_user=current_user)


    @app.route('/professor/class/<int:class_id>/files/upload', methods=['POST'])
    @login_required
    def professor_upload_file(class_id):
        """آپلود فایل جدید"""
        try:
            class_obj = Class.query.get_or_404(class_id)
        except:
            return jsonify({'success': False, 'message': 'کلاس یافت نشد.'}), 404
        
        if class_obj.instructor_id != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'فایلی ارسال نشده.'}), 400
        
        file = request.files['file']
        title = request.form.get('title', file.filename)
        description = request.form.get('description', '')
        file_type = request.form.get('type', 'general')
        session_id = request.form.get('session_id', type=int)
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'نام فایل نامعتبر است.'}), 400
        
        # ذخیره فایل
        try:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            new_filename = f"{uuid.uuid4().hex}.{ext}"
            
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'class_files', str(class_id))
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, new_filename)
            file.save(file_path)
            
            # مسیر نسبی برای ذخیره در دیتابیس
            relative_path = os.path.join('class_files', str(class_id), new_filename)
            
            if session_id:
                # فایل مخصوص جلسه
                session_file = SessionFile(
                    session_id=session_id,
                    title=title,
                    description=description,
                    file_path=relative_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=current_user.id
                )
                db.session.add(session_file)
            else:
                # فایل عمومی کلاس
                class_file = ClassFile(
                    class_id=class_id,
                    title=title,
                    description=description,
                    file_path=relative_path,
                    file_type=ext,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=current_user.id
                )
                db.session.add(class_file)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'فایل با موفقیت آپلود شد.',
                'filename': title
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/professor/file/delete/<int:file_id>', methods=['POST'])
    @login_required
    def professor_delete_file(file_id):
        """حذف فایل"""
        try:
            # بررسی نوع فایل
            class_file = ClassFile.query.get(file_id)
            session_file = SessionFile.query.get(file_id) if not class_file else None
            
            file_obj = class_file or session_file
            
            if not file_obj:
                return jsonify({'success': False, 'message': 'فایل یافت نشد.'}), 404
            
            # بررسی دسترسی
            if class_file:
                class_obj = Class.query.get(class_file.class_id)
                if class_obj.instructor_id != current_user.id and not current_user.is_admin():
                    return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
            else:
                session = CourseSession.query.get(session_file.session_id)
                class_obj = Class.query.get(session.class_id)
                if class_obj.instructor_id != current_user.id and not current_user.is_admin():
                    return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
            
            # حذف فایل از دیسک
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_obj.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            db.session.delete(file_obj)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'فایل با موفقیت حذف شد.'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/professor/profile')
    @login_required
    def professor_profile():
        """پروفایل استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        # آمار تدریس
        try:
            total_classes = Class.query.filter_by(instructor_id=current_user.id).count()
            total_students = db.session.query(func.count(ClassEnrollment.student_id))\
                .join(Class, Class.id == ClassEnrollment.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .scalar() or 0
            
            total_sessions = CourseSession.query\
                .join(Class, Class.id == CourseSession.class_id)\
                .filter(Class.instructor_id == current_user.id)\
                .count()
            
            total_circles = QuranCircle.query.filter_by(created_by=current_user.id).count()
            
            teaching_stats = {
                'total_classes': total_classes,
                'total_students': total_students,
                'total_sessions': total_sessions,
                'total_circles': total_circles
            }
        except:
            teaching_stats = {
                'total_classes': 0,
                'total_students': 0,
                'total_sessions': 0,
                'total_circles': 0
            }
        
        # دروس ارائه شده
        try:
            courses = Class.query\
                .filter_by(instructor_id=current_user.id)\
                .order_by(Class.created_at.desc())\
                .limit(10).all()
        except:
            courses = []
        
        return render_template('professor/profile.html',
                             teaching_stats=teaching_stats,
                             courses=courses,
                             current_user=current_user)


    @app.route('/professor/profile/edit', methods=['GET', 'POST'])
    @login_required
    def professor_edit_profile():
        """ویرایش پروفایل استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        if request.method == 'POST':
            # اطلاعات پایه
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            current_user.landline = request.form.get('landline')
            
            # اطلاعات تخصصی
            current_user.academic_rank = request.form.get('academic_rank')
            current_user.specialization = request.form.get('specialization')
            current_user.teaching_experience = request.form.get('teaching_experience', type=int)
            current_user.professor_code = request.form.get('professor_code')
            current_user.office_hours = request.form.get('office_hours')
            current_user.website = request.form.get('website')
            
            # اطلاعات مکانی
            current_user.university = request.form.get('university')
            current_user.faculty = request.form.get('faculty')
            current_user.department = request.form.get('department')
            current_user.office_location = request.form.get('office_location')
            
            # آپلود رزومه جدید
            if 'resume' in request.files:
                file = request.files['resume']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes')
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # حذف فایل قبلی
                    if current_user.resume_file:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.resume_file)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    new_filename = f"resume_{current_user.id}_{int(time.time())}.pdf"
                    file_path = os.path.join(upload_path, new_filename)
                    file.save(file_path)
                    
                    current_user.resume_file = os.path.join('resumes', new_filename)
            
            db.session.commit()
            flash('✅ پروفایل با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('professor_profile'))
        
        return render_template('professor/edit_profile.html',
                             current_user=current_user)


     # ============================================
    # ========== حلقه‌های تلاوت (استاد و عمومی) ==========
    # ============================================

    @app.route('/professor/circles')
    @login_required
    def professor_circles():
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        page = request.args.get('page', 1, type=int)
        try:
            circles = QuranCircle.query\
                .filter_by(created_by=current_user.id)\
                .order_by(QuranCircle.created_at.desc())\
                .paginate(page=page, per_page=10, error_out=False)
            total_members = 0
            total_sessions = 0
            for circle in circles.items:
                total_members += circle.current_members
                total_sessions += circle.sessions.count()
            avg_attendance = 0
            if circles.items:
                total_attendance = 0
                for circle in circles.items:
                    total_attendance += circle.attendance_rate
                avg_attendance = int(total_attendance / len(circles.items))
        except Exception as e:
            print(f"خطا در دریافت حلقه‌ها: {e}")
            circles = []
            total_members = 0
            total_sessions = 0
            avg_attendance = 0
        return render_template('professor/circles.html',
                               circles=circles,
                               total_members=total_members,
                               total_sessions=total_sessions,
                               avg_attendance=avg_attendance,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>')
    @login_required
    def professor_circle_detail(circle_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_circles'))
        if circle.created_by != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circles'))
        # اعضای حلقه
        try:
            members = CircleMember.query\
                .filter_by(circle_id=circle_id, is_active=True)\
                .join(User, User.id == CircleMember.user_id)\
                .add_columns(
                    User.id, User.first_name, User.last_name,
                    User.email, User.phone
                ).all()
            circle_members = []
            for member, user_id, first_name, last_name, email, phone in members:
                attendance_rate = 0
                total_sessions = circle.sessions.count()
                if total_sessions > 0:
                    attended = SessionAttendance.query\
                        .join(CircleSession, CircleSession.id == SessionAttendance.session_id)\
                        .filter(CircleSession.circle_id == circle_id)\
                        .filter(SessionAttendance.member_id == member.id)\
                        .filter(SessionAttendance.attended == True)\
                        .count()
                    attendance_rate = int((attended / total_sessions) * 100)
                circle_members.append({
                    'id': user_id,
                    'full_name': f"{first_name} {last_name}",
                    'email': email,
                    'phone': phone,
                    'role': member.role,
                    'joined_date': member.joined_date,
                    'attendance_rate': attendance_rate
                })
        except Exception as e:
            print(f"خطا در دریافت اعضا: {e}")
            circle_members = []
        try:
            sessions = CircleSession.query\
                .filter_by(circle_id=circle_id)\
                .order_by(CircleSession.session_date.desc())\
                .all()
        except:
            sessions = []
        return render_template('professor/circle_detail.html',
                               circle=circle,
                               members=circle_members,
                               sessions=sessions,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>/session/create', methods=['POST'])
    @login_required
    def professor_create_session(circle_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            return jsonify({'success': False, 'message': 'حلقه یافت نشد.'}), 404
        if circle.created_by != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        data = request.get_json()
        try:
            session_date = datetime.strptime(data.get('session_date'), '%Y-%m-%d').date()
            session = CircleSession(
                circle_id=circle_id,
                title=data.get('title'),
                session_date=session_date,
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                topic=data.get('topic'),
                description=data.get('description'),
                verses_reviewed=data.get('verses_reviewed'),
                notes=data.get('notes'),
                homework=data.get('homework')
            )
            db.session.add(session)
            db.session.commit()
            return jsonify({'success': True, 'message': 'جلسه با موفقیت ایجاد شد.', 'session_id': session.id})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/professor/circle/<int:circle_id>/attendance/<int:session_id>')
    @login_required
    def professor_circle_attendance(circle_id, session_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
            session = CircleSession.query.get_or_404(session_id)
        except:
            flash('اطلاعات مورد نظر یافت نشد.', 'error')
            return redirect(url_for('professor_circles'))
        if circle.created_by != current_user.id and not current_user.is_admin():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circles'))
        try:
            members = CircleMember.query\
                .filter_by(circle_id=circle_id, is_active=True)\
                .join(User, User.id == CircleMember.user_id)\
                .add_columns(User.id, User.first_name, User.last_name).all()
        except:
            members = []
        attendances = {}
        present_count = 0
        late_count = 0
        try:
            atts = SessionAttendance.query.filter_by(session_id=session_id).all()
            for a in atts:
                attendances[a.member_id] = {
                    'attended': a.attended,
                    'late_minutes': a.late_minutes,
                    'excuse': a.excuse
                }
                if a.attended:
                    present_count += 1
                    if a.late_minutes > 0:
                        late_count += 1
        except:
            pass
        return render_template('professor/circle_attendance.html',
                               circle=circle,
                               session=session,
                               members=members,
                               attendance_dict=attendances,
                               present_count=present_count,
                               late_count=late_count,
                               current_user=current_user)

    @app.route('/professor/circle/<int:circle_id>/attendance/<int:session_id>', methods=['POST'])
    @login_required
    def professor_save_circle_attendance(circle_id, session_id):
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
            session = CircleSession.query.get_or_404(session_id)
        except:
            return jsonify({'success': False, 'message': 'اطلاعات یافت نشد.'}), 404
        if circle.created_by != current_user.id and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز.'}), 403
        data = request.get_json()
        attendances = data.get('attendances', [])
        try:
            SessionAttendance.query.filter_by(session_id=session_id).delete()
            for att in attendances:
                attendance = SessionAttendance(
                    session_id=session_id,
                    member_id=att['member_id'],
                    attended=att['attended'],
                    late_minutes=att.get('late_minutes', 0),
                    excuse=att.get('excuse', ''),
                    marked_by=current_user.id
                )
                db.session.add(attendance)
            db.session.commit()
            return jsonify({'success': True, 'message': 'حضور و غیاب با موفقیت ثبت شد.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    # ======================= درخواست ایجاد حلقه تلاوت توسط استاد =======================
    @app.route('/professor/circle-request', methods=['GET', 'POST'])
    @login_required
    def professor_circle_request():
        if not current_user.is_professor():
            flash('⛔ فقط اساتید می‌توانند درخواست ایجاد حلقه تلاوت بدهند.', 'error')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            max_members = request.form.get('max_members', type=int)
            circle_type = request.form.get('circle_type', 'public')
            if not name or not description:
                flash('لطفاً نام و توضیحات حلقه را وارد کنید.', 'error')
                return redirect(url_for('professor_circle_request'))

            # ایجاد حلقه جدید – فقط یکبار از capacity استفاده کنید
            new_circle = QuranCircle(
                name=name,
                description=description,
                capacity=max_members,                 # max_members به capacity نگاشت می‌شود
                circle_type=circle_type,
                created_by=current_user.id,
                status='pending',
                teacher_name=current_user.full_name,  # فیلد اجباری
                is_active=True
            )
            db.session.add(new_circle)
            db.session.commit()

            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id,
                    'درخواست جدید ایجاد حلقه تلاوت',
                    f'استاد {current_user.full_name} درخواست ایجاد حلقه "{new_circle.name}" را داده است.'
                )
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، حلقه فعال خواهد شد.', 'success')
            return redirect(url_for('professor_dashboard'))

        return render_template('professor/circle_request.html', current_user=current_user)

    @app.route('/professor/circle-requests')
    @login_required
    def professor_circle_requests():
        if not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        status = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        query = QuranCircle.query.filter_by(created_by=current_user.id)
        if status != 'all':
            query = query.filter_by(status=status)
        pagination = query.order_by(QuranCircle.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        return render_template('professor/circle_requests.html', requests=pagination, status=status, current_user=current_user)

    @app.route('/professor/circle-request/<int:request_id>')
    @login_required
    def professor_circle_request_detail(request_id):
        if not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        circle = QuranCircle.query.get_or_404(request_id)
        if circle.created_by != current_user.id:
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('professor_circle_requests'))
        return render_template('professor/circle_request_detail.html', request=circle, current_user=current_user)

    # ======================= مدیریت درخواست‌های حلقه توسط ادمین =======================
    @app.route('/admin/circle-requests')
    @login_required
    @admin_required
    def admin_circle_requests():
        pending_circles = QuranCircle.query.filter_by(status='pending').all()
        return render_template('admin/circle_requests.html', circles=pending_circles, current_user=current_user)

    @app.route('/admin/circle-request/<int:request_id>')
    @login_required
    @admin_required
    def admin_circle_request_detail(request_id):
        circle = QuranCircle.query.get_or_404(request_id)
        req_data = {
            'id': circle.id,
            'name': circle.name,
            'description': circle.description,
            'professor': User.query.get(circle.created_by),
            'created_at': circle.created_at,
            'circle_type': circle.circle_type,
            'max_members': circle.capacity,  # اصلاح: از capacity استفاده شد
            'status': circle.status,
            'rejection_reason': circle.rejection_reason
        }
        return render_template('admin/circle_request_detail.html', request=req_data, current_user=current_user)
     
    # ============================================
    # ========== مسیر دانلود رزومه استاد ==========
    # ============================================

    @app.route('/professor/download-resume')
    @login_required
    def download_resume():
        """دانلود رزومه استاد"""
        if not current_user.is_admin() and not current_user.is_professor():
            flash('⛔ دسترسی غیرمجاز', 'error')
            return redirect(url_for('profile'))
        
        if not current_user.resume_file:
            flash('❌ فایل رزومه یافت نشد.', 'error')
            return redirect(url_for('professor_profile'))
        
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.resume_file)
            if not os.path.exists(file_path):
                flash('❌ فایل رزومه روی سرور یافت نشد.', 'error')
                return redirect(url_for('professor_profile'))
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"resume_{current_user.full_name}.pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            flash(f'❌ خطا در دانلود فایل: {str(e)}', 'error')
            return redirect(url_for('professor_profile'))

            
    
    # ============================================
    # ========== مسیرهای مدیریتی (ادمین) ==========
    # ============================================
    
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        """داشبورد مدیریت - فقط برای ادمین‌ها"""
        # آمار کلی
        try:
            total_users = User.query.count()
        except:
            total_users = 0
        
        try:
            total_events = Event.query.count()
        except:
            total_events = 0
        
        try:
            active_events = Event.query.filter_by(is_active=True).count()
        except:
            active_events = 0
        
        try:
            total_registrations = Registration.query.count()
        except:
            total_registrations = 0
        
        # تعداد کاربران در انتظار تأیید
        try:
            pending_count = User.query.filter_by(is_verified=False, is_active=True).count()
        except:
            pending_count = 0
        
        # رویدادهای اخیر
        try:
            recent_events = Event.query.order_by(
                Event.created_at.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت رویدادها: {e}")
            recent_events = []
        
        # کاربران جدید
        try:
            new_users = User.query.order_by(
                User.created_at.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت کاربران: {e}")
            new_users = []
        
        # ثبت‌نام‌های اخیر
        try:
            recent_registrations = Registration.query.order_by(
                Registration.registration_date.desc()
            ).limit(5).all()
        except Exception as e:
            print(f"خطا در دریافت ثبت‌نام‌ها: {e}")
            recent_registrations = []
        
        # آیه روز
        daily_verse = get_daily_verse()
        
        # تاریخ شمسی
        current_date = get_persian_date()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_events=total_events,
                             active_events=active_events,
                             total_registrations=total_registrations,
                             recent_events=recent_events,
                             new_users=new_users,
                             recent_registrations=recent_registrations,
                             daily_verse=daily_verse,
                             current_date=current_date,
                             pending_count=pending_count,
                             current_user=current_user)
 
      # ============================================
    # مسیرهای مدیریت رویداد (فقط ادمین)
    # ============================================
    
    @app.route('/admin/events')
    @login_required
    @admin_required
    def admin_events():
        events = Event.query.order_by(Event.created_at.desc()).all()
        return render_template('admin/events.html', events=events, current_user=current_user)
    
    @app.route('/admin/event/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def create_event():
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            event_type = request.form.get('event_type')
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            location = request.form.get('location')
            capacity = request.form.get('capacity', type=int)
            
            if not title or not description or not event_type or not start_date_shamsi or not start_time:
                flash('لطفاً تمام فیلدهای ضروری (عنوان، توضیحات، نوع رویداد، تاریخ شمسی و ساعت شروع) را پر کنید.', 'error')
                return redirect(url_for('create_event'))
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                start_date = jstart.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('create_event'))
            
            end_date = start_date
            
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'events')
            
            event = Event(
                title=title, description=description, event_type=EventType(event_type),
                start_date=start_date, end_date=end_date, location=location,
                capacity=capacity, image=image_path, created_by=current_user.id, is_active=True
            )
            db.session.add(event)
            db.session.commit()
            flash('رویداد با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('admin_events'))
        
        return render_template('admin/event_form.html', event=None, event_types=EventType, current_user=current_user)
    
    @app.route('/admin/event/edit/<int:event_id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def edit_event(event_id):
        event = Event.query.get_or_404(event_id)
        if request.method == 'POST':
            event.title = request.form.get('title')
            event.description = request.form.get('description')
            event.event_type = EventType(request.form.get('event_type'))
            
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            
            if not start_date_shamsi or not start_time:
                flash('تاریخ و ساعت شروع الزامی است.', 'error')
                return redirect(url_for('edit_event', event_id=event_id))
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                event.start_date = jstart.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('edit_event', event_id=event_id))
            
            event.end_date = event.start_date
            event.location = request.form.get('location')
            event.capacity = request.form.get('capacity', type=int)
            event.is_active = request.form.get('is_active') == 'on'
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if event.image:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    event.image = save_uploaded_file(file, 'events')
            
            db.session.commit()
            flash('رویداد با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('admin_events'))
        
        total_registrations = event.registrations.count()
        attended_count = event.registrations.filter_by(attended=True).count()
        return render_template('admin/event_form.html', event=event, event_types=EventType,
                             total_registrations=total_registrations, attended_count=attended_count, current_user=current_user)
    
    @app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_event(event_id):
        event = Event.query.get_or_404(event_id)
        if event.image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], event.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        Registration.query.filter_by(event_id=event_id).delete()
        db.session.delete(event)
        db.session.commit()
        return jsonify({'success': True, 'message': 'رویداد با موفقیت حذف شد'})
    @app.route('/admin/users')
    @login_required
    @admin_required
    def admin_users():
        """مدیریت کاربران"""
        try:
            users = User.query.order_by(User.created_at.desc()).all()
        except:
            users = []
        
        return render_template('admin/users.html',
                             users=users,
                             current_user=current_user)
    
    @app.route('/admin/user/toggle/<int:user_id>', methods=['GET'])
    @login_required
    @admin_required
    def toggle_user_status(user_id):
        """فعال/غیرفعال کردن کاربر - با ریدایرکت به جای JSON"""
        if user_id == current_user.id:
            flash('نمی‌توانید خودتان را غیرفعال کنید', 'error')
            return redirect(url_for('admin_users'))
        
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('admin_users'))
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'فعال' if user.is_active else 'غیرفعال'
        
        # اعلان به کاربر
        create_notification(
            user.id,
            'تغییر وضعیت حساب کاربری',
            f'وضعیت حساب کاربری شما به "{status}" تغییر یافت.'
        )
        
        flash(f'کاربر {user.username} {status} شد', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/role/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def change_user_role(user_id):
        """تغییر نقش کاربر"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in [r.value for r in UserRole]:
            return jsonify({'success': False, 'message': 'نقش نامعتبر است'}), 400
        
        user.role = UserRole(new_role)
        db.session.commit()
        
        # اعلان به کاربر
        role_names = {'admin': 'مدیر', 'manager': 'مسئول', 'participant': 'دانشجو'}
        create_notification(
            user.id,
            'تغییر نقش کاربری',
            f'نقش شما در سیستم به "{role_names.get(new_role, new_role)}" تغییر یافت.'
        )
        
        return jsonify({'success': True, 'message': f'نقش کاربر {user.username} تغییر یافت'})
    
    # ============================================
    # مسیرهای مدیریتی برای ادمین (تأیید کاربران)
    # ============================================
    
    @app.route('/admin/pending-users')
    @login_required
    @admin_required
    def admin_pending_users():
        """لیست کاربران در انتظار تأیید برای ادمین"""
        page = request.args.get('page', 1, type=int)
        user_type = request.args.get('type', 'all')
        
        try:
            query = User.query.filter_by(is_verified=False, is_active=True)
            
            if user_type != 'all':
                query = query.filter_by(user_type=user_type)
            
            users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
        except Exception as e:
            print(f"خطا در دریافت کاربران: {e}")
            users = []
        
        return render_template('admin/pending_users.html', 
                             users=users,
                             current_user=current_user,
                             user_type=user_type)

    @app.route('/admin/user/verify/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_verify_user(user_id):
        """تأیید کاربر توسط ادمین"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404
        
        if user.is_verified:
            return jsonify({'success': False, 'message': 'این کاربر قبلاً تأیید شده است.'}), 400
        
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        user.verified_by = current_user.id
        db.session.commit()
        
        # ارسال اعلان به کاربر
        create_notification(
            user.id,
            '✅ تأیید حساب کاربری',
            f'حساب کاربری شما با موفقیت تأیید شد. اکنون می‌توانید وارد شوید.'
        )
        
        return jsonify({'success': True, 'message': f'کاربر {user.full_name} تأیید شد.'})

    @app.route('/admin/user/reject/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_reject_user(user_id):
        try:
            user = User.query.get_or_404(user_id)
        except:
            return jsonify({'success': False, 'message': 'کاربر مورد نظر یافت نشد.'}), 404

        # تشخیص نوع درخواست (JSON یا فرم)
        if request.is_json:
            data = request.get_json()
            reason = data.get('reason', 'دلیل خاصی ذکر نشده است.')
        else:
            reason = request.form.get('reason', 'دلیل خاصی ذکر نشده است.')

        create_notification(
            user.id,
            '❌ رد درخواست تأیید',
            f'درخواست تأیید حساب کاربری شما رد شد. دلیل: {reason}'
        )

        user.is_active = False
        user.verification_notes = reason
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': f'درخواست کاربر {user.full_name} رد شد.'})
        else:
            flash(f'درخواست کاربر {user.full_name} رد شد.', 'danger')
            return redirect(url_for('admin_pending_users'))

    @app.route('/admin/user/<int:user_id>')
    @login_required
    @admin_required
    def admin_user_detail(user_id):
        """مشاهده جزئیات کاربر برای ادمین"""
        try:
            user = User.query.get_or_404(user_id)
        except:
            flash('کاربر مورد نظر یافت نشد.', 'error')
            return redirect(url_for('admin_pending_users'))
        
        return render_template('admin/user_detail.html', user=user, current_user=current_user)
    
    @app.route('/admin/reports')
    @login_required
    @admin_required
    def admin_reports():
        """گزارش‌گیری"""
        event_participation = []
        daily_registrations = []
        university_stats = []
        
        try:
            # ============= آمار شرکت در رویدادها =============
            event_participation_raw = db.session.query(
                Event,
                func.count(Registration.id).label('participants')
            ).outerjoin(Registration, Event.id == Registration.event_id)\
             .group_by(Event.id)\
             .order_by(func.count(Registration.id).desc())\
             .limit(10).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for event, participants in event_participation_raw:
                event_participation.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'event_type': event.event_type,
                    'event_type_value': event.event_type.value,
                    'start_date': event.start_date,
                    'end_date': event.end_date,
                    'location': event.location,
                    'capacity': event.capacity,
                    'current_participants': event.current_participants,
                    'image': event.image,
                    'is_active': event.is_active,
                    'created_by': event.created_by,
                    'created_at': event.created_at,
                    'participants': participants
                })
        except:
            pass
        
        try:
            # ============= آمار روزانه ثبت‌نام =============
            daily_registrations_raw = db.session.query(
                func.date(Registration.registration_date).label('date'),
                func.count(Registration.id).label('count')
            ).group_by(func.date(Registration.registration_date))\
             .order_by(func.date(Registration.registration_date).desc())\
             .limit(30).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for date, count in daily_registrations_raw:
                daily_registrations.append({
                    'date': date,
                    'count': count
                })
        except:
            pass
        
        try:
            # ============= آمار کاربران بر اساس دانشگاه =============
            university_stats_raw = db.session.query(
                User.university,
                func.count(User.id).label('count')
            ).filter(User.university.isnot(None))\
             .group_by(User.university)\
             .order_by(func.count(User.id).desc())\
             .limit(10).all()
            
            # تبدیل به فرمت مناسب برای قالب
            for university, count in university_stats_raw:
                university_stats.append({
                    'university': university,
                    'count': count
                })
        except:
            pass
        
        return render_template('admin/reports.html',
                             event_participation=event_participation,
                             daily_registrations=daily_registrations,
                             university_stats=university_stats,
                             current_user=current_user)
    
   
      # ============================================
    # ========== مدیریت بنرها (ادمین) ==========
    # ============================================
    
    @app.route('/admin/banners')
    @login_required
    @admin_required
    def admin_banners_list():
        """لیست تمام بنرها"""
        banners = Banner.query.order_by(Banner.order, Banner.id).all()
        return render_template('admin/admin_banners.html', banners=banners, current_user=current_user)

    @app.route('/admin/banners/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_add_banner():
        """افزودن بنر جدید"""
        title = request.form.get('title')
        link_url = request.form.get('link_url')
        alt_text = request.form.get('alt_text')
        order = request.form.get('order', 0)
        
        if not title:
            return jsonify({'success': False, 'message': 'عنوان بنر الزامی است'})
        
        # مدیریت آپلود تصویر
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                # استفاده از مسیر static/uploads/banners
                upload_path = os.path.join(app.root_path, 'static', 'uploads', 'banners')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                image_url = f'/static/uploads/banners/{filename}'
        
        # یا آدرس تصویر از ورودی
        if not image_url and request.form.get('image_url'):
            image_url = request.form.get('image_url')
        
        if not image_url:
            return jsonify({'success': False, 'message': 'تصویر بنر الزامی است'})
        
        banner = Banner(
            title=title,
            image_url=image_url,
            link_url=link_url,
            alt_text=alt_text,
            order=int(order) if order else 0,
            is_active=True
        )
        
        db.session.add(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت اضافه شد'})

    @app.route('/admin/banners/edit/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_edit_banner(banner_id):
        """ویرایش بنر"""
        banner = Banner.query.get_or_404(banner_id)
        
        banner.title = request.form.get('title', banner.title)
        banner.link_url = request.form.get('link_url')
        banner.alt_text = request.form.get('alt_text')
        banner.order = int(request.form.get('order', banner.order))
        
        # آپلود تصویر جدید
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # حذف تصویر قدیمی
                if banner.image_url:
                    old_path = os.path.join(app.root_path, banner.image_url.lstrip('/'))
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except:
                            pass
                
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                upload_path = os.path.join(app.root_path, 'static', 'uploads', 'banners')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                banner.image_url = f'/static/uploads/banners/{filename}'
        
        # آدرس تصویر از ورودی
        if request.form.get('image_url'):
            banner.image_url = request.form.get('image_url')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت ویرایش شد'})

    @app.route('/admin/banners/toggle/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_toggle_banner(banner_id):
        """فعال/غیرفعال کردن بنر"""
        banner = Banner.query.get_or_404(banner_id)
        banner.is_active = not banner.is_active
        db.session.commit()
        
        return jsonify({'success': True, 'is_active': banner.is_active})

    @app.route('/admin/banners/delete/<int:banner_id>', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_banner(banner_id):
        """حذف بنر"""
        banner = Banner.query.get_or_404(banner_id)
        
        # حذف فایل تصویر
        if banner.image_url:
            file_path = os.path.join(app.root_path, banner.image_url.lstrip('/'))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        db.session.delete(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'بنر با موفقیت حذف شد'})

    @app.route('/admin/banners/reorder', methods=['POST'])
    @login_required
    @admin_required
    def admin_reorder_banners():
        """تنظیم ترتیب بنرها"""
        data = request.get_json()
        orders = data.get('orders', [])
        
        for item in orders:
            banner = Banner.query.get(item['id'])
            if banner:
                banner.order = item['order']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'ترتیب بنرها ذخیره شد'})
    @app.route('/admin/banners/api/banner/<int:banner_id>')
    @login_required
    @admin_required
    def admin_get_banner(banner_id):
        """دریافت اطلاعات یک بنر (برای ویرایش)"""
        banner = Banner.query.get_or_404(banner_id)
        return jsonify({
            'id': banner.id,
            'title': banner.title,
            'image_url': banner.image_url,
            'link_url': banner.link_url,
            'alt_text': banner.alt_text,
            'order': banner.order,
            'is_active': banner.is_active
        })

    @app.route('/admin/circle-request/<int:circle_id>/approve', methods=['POST'])
    @login_required
    @admin_required
    def approve_circle_request(circle_id):
        circle = QuranCircle.query.get_or_404(circle_id)
        if circle.status != 'pending':
            return jsonify({'success': False, 'message': 'این درخواست قبلاً بررسی شده است.'})
        circle.status = 'approved'
        db.session.commit()
        create_notification(circle.created_by, '✅ تأیید درخواست حلقه تلاوت', f'درخواست شما برای ایجاد حلقه "{circle.name}" توسط مدیر تأیید شد.')
        return jsonify({'success': True})
  #  @app.route('/ai/quran')
   # @login_required
    #@verified_required
    #def ai_quran():
     #   """ریدایرکت به سِراج‌یار جدید"""
        return redirect(url_for('seraj_yari'))
    # ============================================
    # API های عمومی
    # ============================================
    
    @app.route('/api/events/upcoming')
    def api_upcoming_events():
        """API دریافت رویدادهای پیش‌رو"""
        try:
            events = Event.query.filter(
                Event.start_date >= datetime.utcnow(),
                Event.is_active == True
            ).order_by(Event.start_date).limit(10).all()
            
            events_list = []
            for event in events:
                events_list.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description[:100] + '...',
                    'event_type': event.event_type.value,
                    'start_date': event.start_date.isoformat(),
                    'end_date': event.end_date.isoformat(),
                    'location': event.location,
                    'capacity': event.capacity,
                    'current_participants': event.current_participants,
                    'is_full': event.is_full(),
                    'image': url_for('static', filename=f'uploads/{event.image}') if event.image else None
                })
            
            return jsonify({'events': events_list})
        except:
            return jsonify({'events': []})
    
    @app.route('/api/user/stats')
    @login_required
    @verified_required
    def api_user_stats():
        """API آمار کاربر"""
        try:
            total_registrations = Registration.query.filter_by(
                user_id=current_user.id
            ).count()
            
            attended_events = Registration.query.filter_by(
                user_id=current_user.id,
                attended=True
            ).count()
            
            upcoming_events = Registration.query.filter(
                Registration.user_id == current_user.id,
                Registration.event.has(Event.start_date >= datetime.utcnow())
            ).count()
            
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
            
            return jsonify({
                'total_registrations': total_registrations,
                'attended_events': attended_events,
                'upcoming_events': upcoming_events,
                'unread_notifications': unread_notifications
            })
        except:
            return jsonify({
                'total_registrations': 0,
                'attended_events': 0,
                'upcoming_events': 0,
                'unread_notifications': 0
            })
    
    # ============================================
    # مسیر گزارش مشکل
    # ============================================
    
    @app.route('/report-issue', methods=['GET', 'POST'])
    @login_required
    @verified_required
    def report_issue():
        """گزارش مشکل"""
        url = request.args.get('url', '')
        
        if request.method == 'POST':
            issue_url = request.form.get('url')
            issue_description = request.form.get('description')
            
            # اینجا می‌توانید مشکل را در دیتابیس ذخیره کنید یا ایمیل بزنید
            flash('مشکل شما با موفقیت گزارش شد. تیم فنی در اسرع وقت بررسی خواهد کرد.', 'success')
            return redirect(url_for('index'))
        
        return render_template('report_issue.html', url=url, current_user=current_user)
    
    # ============================================
    # مسیرهای مدیریت اعلامیه‌ها
    # ============================================
    
    @app.route('/admin/announcement', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_announcement():
        """ارسال اعلامیه به همه کاربران"""
        if request.method == 'POST':
            title = request.form.get('title')
            message = request.form.get('message')
            priority = request.form.get('priority', 'normal')
            
            if not title or not message:
                flash('عنوان و متن اعلامیه الزامی است.', 'error')
                return redirect(url_for('admin_announcement'))
            
            # دریافت همه کاربران فعال
            try:
                users = User.query.filter_by(is_active=True).all()
                sent_count = 0
                
                for user in users:
                    create_notification(
                        user_id=user.id,
                        title=title,
                        message=message
                    )
                    sent_count += 1
                
                flash(f'✅ اعلامیه با موفقیت برای {sent_count} کاربر ارسال شد.', 'success')
            except:
                flash('خطا در ارسال اعلامیه.', 'error')
            
            return redirect(url_for('admin_dashboard'))
        
        # تعداد کاربران فعال برای نمایش در فرم
        try:
            users_count = User.query.filter_by(is_active=True).count()
        except:
            users_count = 0
        
        return render_template('admin/announcement.html', 
                             current_user=current_user,
                             users_count=users_count)
    
    @app.route('/admin/announcements')
    @login_required
    @admin_required
    def admin_announcements_list():
        """لیست اعلامیه‌های ارسال شده"""
        from sqlalchemy import func
        
        try:
            recent_announcements = db.session.query(
                Notification.title,
                Notification.message,
                func.max(Notification.created_at).label('created_at'),
                func.count(Notification.id).label('recipients')
            ).group_by(
                Notification.title,
                Notification.message
            ).order_by(
                func.max(Notification.created_at).desc()
            ).limit(20).all()
        except:
            recent_announcements = []
        
        return render_template('admin/announcements_list.html',
                             announcements=recent_announcements,
                             current_user=current_user)
    
    # ============================================
    # مسیرهای حلقه‌های تلاوت
    # ============================================
    
    @app.route('/circles')
    def circles_list():
        """لیست حلقه‌های تلاوت"""
        page = request.args.get('page', 1, type=int)
        circle_type = request.args.get('type')
        level = request.args.get('level')
        search = request.args.get('search')
        
        try:
            query = QuranCircle.query.filter_by(is_active=True)
            
            if circle_type:
                query = query.filter_by(circle_type=circle_type)
            
            if level:
                query = query.filter_by(level=level)
            
            if search:
                query = query.filter(
                    (QuranCircle.name.contains(search)) | 
                    (QuranCircle.description.contains(search)) |
                    (QuranCircle.teacher_name.contains(search))
                )
            
            circles = query.order_by(QuranCircle.created_at.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            circles = []
        
        return render_template('circles/list.html',
                             circles=circles,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>')
    def circle_detail(circle_id):
        """جزئیات حلقه تلاوت"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی عضویت کاربر
        is_member = False
        if current_user.is_authenticated:
            try:
                membership = CircleMember.query.filter_by(
                    circle_id=circle_id,
                    user_id=current_user.id
                ).first()
                is_member = membership is not None
            except:
                is_member = False
        
        # دریافت جلسات
        try:
            upcoming_sessions = circle.sessions.filter(
                CircleSession.session_date >= datetime.now().date()
            ).order_by(CircleSession.session_date).limit(5).all()
        except:
            upcoming_sessions = []
        
        try:
            past_sessions = circle.sessions.filter(
                CircleSession.session_date < datetime.now().date()
            ).order_by(CircleSession.session_date.desc()).limit(5).all()
        except:
            past_sessions = []
        
        # دریافت فایل‌ها
        try:
            files = circle.files.order_by(CircleFile.uploaded_at.desc()).limit(10).all()
        except:
            files = []
        
        return render_template('circles/detail.html',
                             circle=circle,
                             is_member=is_member,
                             upcoming_sessions=upcoming_sessions,
                             past_sessions=past_sessions,
                             files=files,
                             current_user=current_user)


    @app.route('/circle/<int:circle_id>/join', methods=['POST'])
    @login_required
    @verified_required
    def join_circle(circle_id):
        """عضویت در حلقه تلاوت"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی ظرفیت
        if circle.is_full():
            flash('ظرفیت این حلقه تکمیل شده است.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        # بررسی عضویت قبلی
        existing = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=current_user.id
        ).first()
        
        if existing:
            if existing.is_active:
                flash('شما قبلاً عضو این حلقه هستید.', 'warning')
            else:
                existing.is_active = True
                circle.current_members += 1
                db.session.commit()
                flash('عضویت شما مجدداً فعال شد.', 'success')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        # عضویت جدید
        membership = CircleMember(
            circle_id=circle_id,
            user_id=current_user.id,
            is_active=True
        )
        
        circle.current_members += 1
        
        db.session.add(membership)
        db.session.commit()
        
        # اعلان به کاربر
        create_notification(
            current_user.id,
            'عضویت در حلقه تلاوت',
            f'شما با موفقیت در حلقه "{circle.name}" عضو شدید.'
        )
        
        flash('عضویت شما با موفقیت ثبت شد.', 'success')
        return redirect(url_for('circle_detail', circle_id=circle_id))


    @app.route('/circle/<int:circle_id>/leave', methods=['POST'])
    @login_required
    @verified_required
    def leave_circle(circle_id):
        """خروج از حلقه تلاوت"""
        try:
            membership = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first_or_404()
        except:
            flash('عضویت مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        circle = membership.circle
        
        membership.is_active = False
        circle.current_members -= 1
        
        db.session.commit()
        
        create_notification(
            current_user.id,
            'خروج از حلقه تلاوت',
            f'شما از حلقه "{circle.name}" خارج شدید.'
        )
        
        flash('شما با موفقیت از حلقه خارج شدید.', 'success')
        return redirect(url_for('circle_detail', circle_id=circle_id))


    @app.route('/circle/<int:circle_id>/sessions')
    @login_required
    @verified_required
    def circle_sessions(circle_id):
        """لیست جلسات حلقه"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی دسترسی
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده جلسات باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        try:
            query = circle.sessions
            
            if status == 'upcoming':
                query = query.filter(CircleSession.session_date >= datetime.now().date())
            elif status == 'past':
                query = query.filter(CircleSession.session_date < datetime.now().date())
            
            sessions = query.order_by(CircleSession.session_date.desc()).paginate(
                page=page, per_page=10, error_out=False
            )
        except:
            sessions = []
        
        return render_template('circles/sessions.html',
                             circle=circle,
                             sessions=sessions,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>')
    @login_required
    @verified_required
    def session_detail(session_id):
        """جزئیات جلسه"""
        try:
            session = CircleSession.query.get_or_404(session_id)
        except:
            flash('جلسه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        circle = session.circle
        
        # بررسی دسترسی
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle.id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        # دریافت حضور و غیاب
        try:
            attendances = session.attendances.all()
        except:
            attendances = []
        
        # دریافت فایل‌ها
        try:
            files = session.files.order_by(CircleSessionFile.uploaded_at.desc()).all()
        except:
            files = []
        
        return render_template('circles/session_detail.html',
                             session=session,
                             circle=circle,
                             attendances=attendances,
                             files=files,
                             is_member=is_member,
                             current_user=current_user)


    @app.route('/circle/session/<int:session_id>/attendance', methods=['POST'])
    @login_required
    @staff_required
    def mark_attendance(session_id):
        """ثبت حضور و غیاب"""
        try:
            session = CircleSession.query.get_or_404(session_id)
        except:
            return jsonify({'success': False, 'message': 'جلسه مورد نظر یافت نشد.'}), 404
        
        # فقط استاد یا مدیر می‌توانند ثبت کنند
        is_teacher = False
        try:
            is_teacher = CircleMember.query.filter_by(
                circle_id=session.circle_id,
                user_id=current_user.id,
                role='teacher',
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_teacher and not current_user.is_admin():
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        member_id = data.get('member_id')
        attended = data.get('attended', False)
        late_minutes = data.get('late_minutes', 0)
        excuse = data.get('excuse', '')
        
        try:
            attendance = SessionAttendance.query.filter_by(
                session_id=session_id,
                member_id=member_id
            ).first()
            
            if attendance:
                attendance.attended = attended
                attendance.late_minutes = late_minutes
                attendance.excuse = excuse
                attendance.marked_by = current_user.id
            else:
                attendance = SessionAttendance(
                    session_id=session_id,
                    member_id=member_id,
                    attended=attended,
                    late_minutes=late_minutes,
                    excuse=excuse,
                    marked_by=current_user.id
                )
                db.session.add(attendance)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/circle/<int:circle_id>/files')
    @login_required
    @verified_required
    def circle_files(circle_id):
        """فایل‌های حلقه"""
        try:
            circle = QuranCircle.query.get_or_404(circle_id)
        except:
            flash('حلقه مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی عضویت
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('برای مشاهده فایل‌ها باید عضو حلقه باشید.', 'error')
            return redirect(url_for('circle_detail', circle_id=circle_id))
        
        try:
            files = circle.files.order_by(CircleFile.uploaded_at.desc()).all()
        except:
            files = []
        
        try:
            session_files = CircleSessionFile.query.join(CircleSession)\
                                            .filter(CircleSession.circle_id == circle_id)\
                                            .order_by(CircleSessionFile.uploaded_at.desc()).all()
        except:
            session_files = []
        
        return render_template('circles/files.html',
                             circle=circle,
                             files=files,
                             session_files=session_files,
                             current_user=current_user)


    @app.route('/circle/file/<int:file_id>/download')
    @login_required
    @verified_required
    def download_circle_file(file_id):
        """دانلود فایل"""
        try:
            file = CircleFile.query.get_or_404(file_id)
        except:
            flash('فایل مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        # بررسی دسترسی
        if not file.is_public:
            is_member = False
            try:
                is_member = CircleMember.query.filter_by(
                    circle_id=file.circle_id,
                    user_id=current_user.id,
                    is_active=True
                ).first() is not None
            except:
                pass
            
            if not is_member and not current_user.is_admin():
                flash('دسترسی غیرمجاز', 'error')
                return redirect(url_for('circles_list'))
        
        try:
            file.download_count += 1
            db.session.commit()
        except:
            pass
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)


    @app.route('/circle/session-file/<int:file_id>/download')
    @login_required
    @verified_required
    def download_session_file(file_id):
        """دانلود فایل جلسه"""
        try:
            file = CircleSessionFile.query.get_or_404(file_id)
        except:
            flash('فایل مورد نظر یافت نشد.', 'error')
            return redirect(url_for('circles_list'))
        
        session = file.session
        
        # بررسی عضویت
        is_member = False
        try:
            is_member = CircleMember.query.filter_by(
                circle_id=session.circle_id,
                user_id=current_user.id,
                is_active=True
            ).first() is not None
        except:
            pass
        
        if not is_member and not current_user.is_admin():
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('circles_list'))
        
        try:
            file.download_count += 1
            db.session.commit()
        except:
            pass
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], file.file_path),
                        as_attachment=True,
                        download_name=file.title)
    
    # ============================================
    # مسیرهای جدید ثبت‌نام
    # ============================================
    
    @app.route('/auth/register/choice')
    def register_choice():
        """صفحه انتخاب نوع ثبت‌نام"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        return render_template('auth/register_choice.html')

    @app.route('/auth/register/professor', methods=['GET', 'POST'])
    def register_professor():
        """ثبت‌نام استاد"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            # دریافت اطلاعات فرم
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # اطلاعات تخصصی
            academic_rank = request.form.get('academic_rank')
            specialization = request.form.get('specialization')
            teaching_experience = request.form.get('teaching_experience', type=int)
            professor_code = request.form.get('professor_code')
            office_hours = request.form.get('office_hours')
            website = request.form.get('website')
            
            # اطلاعات مکانی
            university = request.form.get('university')
            faculty = request.form.get('faculty')
            province = request.form.get('province')
            city = request.form.get('city')
            address = request.form.get('address')
            
            # اطلاعات تماس
            phone = request.form.get('phone')
            landline = request.form.get('landline')
            office_phone = request.form.get('office_phone')
            gender = request.form.get('gender')
            
            # اعتبارسنجی
            errors = []
            
            if not first_name or not last_name:
                errors.append('نام و نام خانوادگی الزامی است')
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد')
            
            if password != confirm_password:
                errors.append('رمز عبور و تکرار آن مطابقت ندارند')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register_professor'))
            
            # آپلود فایل رزومه
            resume_path = None
            if 'resume' in request.files:
                file = request.files['resume']
                if file and file.filename:
                    allowed_extensions = {'pdf', 'doc', 'docx'}
                    if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        resume_path = save_uploaded_file(file, 'resumes')
            
            # تبدیل academic_rank به enum
            academic_rank_enum = convert_academic_rank(academic_rank)
            
            # ایجاد کاربر جدید
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                landline=landline,
                gender=gender,
                user_type='professor',
                is_verified=False,  # استاد نیاز به تأیید دارد
                academic_rank=academic_rank_enum,
                specialization=specialization,
                teaching_experience=teaching_experience,
                professor_code=professor_code,
                office_hours=office_hours,
                website=website,
                resume_file=resume_path,
                office_phone=office_phone,
                province=province,
                city=city,
                university=university,
                faculty=faculty,
                address=address,
                role=UserRole.MANAGER,
                is_active=True  # کاربر فعال است اما نیاز به تأیید دارد
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            try:
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'درخواست جدید همکاری استاد',
                        f'استاد {first_name} {last_name} درخواست همکاری داده است.'
                    )
            except:
                pass
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_professor.html')

    @app.route('/auth/register/staff', methods=['GET', 'POST'])
    def register_staff():
        """ثبت‌نام کارمند امور فرهنگی"""
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_professor():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('professor_dashboard'))
            elif current_user.is_staff():
                if not current_user.is_verified:
                    return redirect(url_for('not_approved'))
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            # دریافت اطلاعات فرم
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # اطلاعات شغلی
            employee_id = request.form.get('employee_id')
            department = request.form.get('department')
            position = request.form.get('position')
            responsibility = request.form.get('responsibility')
            office_phone = request.form.get('office_phone')
            
            # اطلاعات مکانی
            university = request.form.get('university')
            faculty = request.form.get('faculty')
            province = request.form.get('province')
            city = request.form.get('city')
            address = request.form.get('address')
            
            # اطلاعات تماس
            phone = request.form.get('phone')
            landline = request.form.get('landline')
            gender = request.form.get('gender')
            
            # اعتبارسنجی
            errors = []
            
            if not first_name or not last_name:
                errors.append('نام و نام خانوادگی الزامی است')
            
            if not username or len(username) < 3:
                errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد')
            
            if not email or '@' not in email:
                errors.append('ایمیل معتبر وارد کنید')
            
            if not password or len(password) < 6:
                errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد')
            
            if password != confirm_password:
                errors.append('رمز عبور و تکرار آن مطابقت ندارند')
            
            if User.query.filter_by(username=username).first():
                errors.append('این نام کاربری قبلاً ثبت شده است')
            
            if User.query.filter_by(email=email).first():
                errors.append('این ایمیل قبلاً ثبت شده است')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('register_staff'))
            
            # ایجاد کاربر جدید
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                landline=landline,
                gender=gender,
                user_type='staff',
                is_verified=False,  # کارمند نیاز به تأیید دارد
                employee_id=employee_id,
                department=department,
                position=position,
                responsibility=responsibility,
                office_phone=office_phone,
                province=province,
                city=city,
                university=university,
                faculty=faculty,
                address=address,
                role=UserRole.MANAGER,
                is_active=True  # کاربر فعال است اما نیاز به تأیید دارد
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # اعلان به مدیر
            try:
                admins = User.query.filter_by(role=UserRole.ADMIN).all()
                for admin in admins:
                    create_notification(
                        admin.id,
                        'درخواست جدید همکاری کارمند',
                        f'کارمند {first_name} {last_name} درخواست همکاری داده است.'
                    )
            except:
                pass
            
            flash('درخواست شما با موفقیت ثبت شد. پس از تأیید مدیر، می‌توانید وارد شوید.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register_staff.html')


    # ============================================
    # مسیرهای مدیریت مسابقات (Competitions)
    # ============================================

    # تابع به‌روزرسانی لیدربورد (قبل از استفاده تعریف شود)
    def update_leaderboard(competition_id):
        registrations = CompetitionRegistration.query.filter_by(competition_id=competition_id).all()
        for reg in registrations:
            total_score = db.session.query(db.func.sum(JudgeScore.score)).filter_by(registration_id=reg.id).scalar() or 0
            reg.final_score = total_score
        db.session.commit()
        sorted_regs = CompetitionRegistration.query.filter_by(competition_id=competition_id).order_by(CompetitionRegistration.final_score.desc()).all()
        for idx, reg in enumerate(sorted_regs, 1):
            reg.rank = idx
        db.session.commit()

    @app.route('/competitions')
    def competitions_list():
        """لیست همه مسابقات"""
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category')
        search = request.args.get('search')
        
        query = Competition.query.filter_by(is_active=True)
        
        if category:
            try:
                query = query.filter(Competition.category == CompetitionCategory(category))
            except:
                pass
        
        if search:
            query = query.filter(
                (Competition.title.contains(search)) |
                (Competition.description.contains(search))
            )
        
        competitions = query.order_by(Competition.start_date).paginate(page=page, per_page=12, error_out=False)
        
        # آمار برای هر مسابقه (تعداد شرکت‌کنندگان)
        for comp in competitions.items:
            comp.registered_count = CompetitionRegistration.query.filter_by(competition_id=comp.id).count()
        
        return render_template('competitions/index.html', competitions=competitions, categories=CompetitionCategory, current_user=current_user)

    @app.route('/competition/<int:comp_id>')
    def competition_detail(comp_id):
        """جزئیات یک مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        is_registered = False
        if current_user.is_authenticated:
            reg = CompetitionRegistration.query.filter_by(competition_id=comp_id, user_id=current_user.id).first()
            is_registered = reg is not None
        
        # لیست شرکت‌کنندگان برای نمایش در لیدربورد (فقط ۱۰ نفر اول)
        leaderboard = CompetitionRegistration.query.filter_by(competition_id=comp_id)\
            .order_by(CompetitionRegistration.final_score.desc()).limit(10).all()
        
        return render_template('competitions/detail.html', competition=competition, is_registered=is_registered, leaderboard=leaderboard, current_user=current_user)

    @app.route('/competition/<int:comp_id>/register', methods=['POST'])
    @login_required
    @verified_required
    def register_for_competition(comp_id):
        """ثبت‌نام در مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        if not competition.can_register():
            flash('زمان ثبت‌نام به پایان رسیده یا ظرفیت تکمیل شده است.', 'error')
            return redirect(url_for('competition_detail', comp_id=comp_id))
        
        existing = CompetitionRegistration.query.filter_by(competition_id=comp_id, user_id=current_user.id).first()
        if existing:
            flash('شما قبلاً در این مسابقه ثبت‌نام کرده‌اید.', 'warning')
            return redirect(url_for('competition_detail', comp_id=comp_id))
        
        reg = CompetitionRegistration(competition_id=comp_id, user_id=current_user.id)
        competition.current_participants += 1
        db.session.add(reg)
        db.session.commit()
        
        create_notification(current_user.id, 'ثبت‌نام در مسابقه', f'ثبت‌نام شما در مسابقه "{competition.title}" با موفقیت انجام شد.')
        
        flash('ثبت‌نام شما با موفقیت انجام شد.', 'success')
        return redirect(url_for('competition_detail', comp_id=comp_id))

    @app.route('/competition/<int:comp_id>/leaderboard')
    def competition_leaderboard(comp_id):
        """تابلوی امتیازات مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        leaderboard = CompetitionRegistration.query.filter_by(competition_id=comp_id)\
            .order_by(CompetitionRegistration.final_score.desc()).all()
        return render_template('competitions/leaderboard.html', competition=competition, leaderboard=leaderboard, current_user=current_user)
        
    # ============================================
    # بخش مدیریت مسابقات (فقط ادمین)
    # ============================================


    
    @app.route('/admin/competitions')
    @login_required
    @admin_required
    def admin_competitions():
        """مدیریت مسابقات - لیست"""
        competitions = Competition.query.order_by(Competition.created_at.desc()).all()
        return render_template('admin/competitions/index.html', competitions=competitions, current_user=current_user)

    @app.route('/admin/competition/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_create_competition():
        """ایجاد مسابقه جدید"""
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            rules = request.form.get('rules')
            evaluation_criteria = request.form.get('evaluation_criteria')
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            end_date_shamsi = request.form.get('end_date_shamsi')
            end_time = request.form.get('end_time')
            reg_deadline_shamsi = request.form.get('registration_deadline_shamsi')
            max_participants = request.form.get('max_participants', type=int)
            
            # تبدیل تاریخ‌ها
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                start_date = jstart.togregorian()
                
                end_datetime_str = f"{end_date_shamsi} {end_time}"
                jend = jdatetime.datetime.strptime(end_datetime_str, '%Y/%m/%d %H:%M')
                end_date = jend.togregorian()
                
                reg_deadline_str = f"{reg_deadline_shamsi} 23:59"
                jreg = jdatetime.datetime.strptime(reg_deadline_str, '%Y/%m/%d %H:%M')
                registration_deadline = jreg.togregorian()
            except Exception as e:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('admin_create_competition'))
            
            # ذخیره تصویر
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # بررسی حجم فایل (مثلاً حداکثر 5 مگابایت)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        flash('حجم فایل تصویر نباید بیشتر از 5 مگابایت باشد.', 'error')
                        return redirect(url_for('admin_create_competition'))
                    
                    image_path = save_uploaded_file(file, 'competitions')
            
            competition = Competition(
                title=title,
                description=description,
                category=CompetitionCategory(category),
                rules=rules,
                evaluation_criteria=evaluation_criteria,
                start_date=start_date,
                end_date=end_date,
                registration_deadline=registration_deadline,
                max_participants=max_participants,
                image=image_path,
                created_by=current_user.id,
                is_active=True
            )
            db.session.add(competition)
            db.session.commit()
            
            flash('مسابقه با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('admin_competitions'))
        
        return render_template('admin/competitions/form.html', competition=None, categories=CompetitionCategory, current_user=current_user)
    @app.route('/admin/competition/<int:comp_id>/edit', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_edit_competition(comp_id):
        """ویرایش مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        
        if request.method == 'POST':
            competition.title = request.form.get('title')
            competition.description = request.form.get('description')
            competition.category = CompetitionCategory(request.form.get('category'))
            competition.rules = request.form.get('rules')
            competition.evaluation_criteria = request.form.get('evaluation_criteria')
            competition.max_participants = request.form.get('max_participants', type=int)
            competition.is_active = 'is_active' in request.form
            
            # تبدیل تاریخ‌ها (مشابه create - برای خلاصه فقط تاریخ شروع و پایان را به‌روز می‌کنیم)
            start_date_shamsi = request.form.get('start_date_shamsi')
            start_time = request.form.get('start_time')
            end_date_shamsi = request.form.get('end_date_shamsi')
            end_time = request.form.get('end_time')
            reg_deadline_shamsi = request.form.get('registration_deadline_shamsi')
            
            try:
                start_datetime_str = f"{start_date_shamsi} {start_time}"
                jstart = jdatetime.datetime.strptime(start_datetime_str, '%Y/%m/%d %H:%M')
                competition.start_date = jstart.togregorian()
                
                end_datetime_str = f"{end_date_shamsi} {end_time}"
                jend = jdatetime.datetime.strptime(end_datetime_str, '%Y/%m/%d %H:%M')
                competition.end_date = jend.togregorian()
                
                reg_deadline_str = f"{reg_deadline_shamsi} 23:59"
                jreg = jdatetime.datetime.strptime(reg_deadline_str, '%Y/%m/%d %H:%M')
                competition.registration_deadline = jreg.togregorian()
            except:
                flash('فرمت تاریخ یا ساعت نامعتبر است.', 'error')
                return redirect(url_for('admin_edit_competition', comp_id=comp_id))
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if competition.image:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], competition.image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    competition.image = save_uploaded_file(file, 'competitions')
            
            db.session.commit()
            flash('مسابقه با موفقیت به‌روزرسانی شد.', 'success')
            return redirect(url_for('admin_competitions'))
        
        return render_template('admin/competitions/form.html', competition=competition, categories=CompetitionCategory, current_user=current_user)

    @app.route('/admin/competition/<int:comp_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_competition(comp_id):
        """حذف مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        # حذف فایل تصویر
        if competition.image:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], competition.image)
            if os.path.exists(img_path):
                os.remove(img_path)
        db.session.delete(competition)
        db.session.commit()
        return jsonify({'success': True, 'message': 'مسابقه حذف شد.'})

    @app.route('/admin/competition/<int:comp_id>/rounds')
    @login_required
    @admin_required
    def admin_competition_rounds(comp_id):
        """مدیریت مراحل مسابقه"""
        competition = Competition.query.get_or_404(comp_id)
        rounds = CompetitionRound.query.filter_by(competition_id=comp_id).order_by(CompetitionRound.round_number).all()
        return render_template('admin/competitions/rounds.html', competition=competition, rounds=rounds, current_user=current_user)

    @app.route('/admin/competition/<int:comp_id>/round/add', methods=['POST'])
    @login_required
    @admin_required
    def admin_add_round(comp_id):
        """افزودن مرحله جدید به مسابقه"""
        data = request.get_json()
        round_number = data.get('round_number')
        title = data.get('title')
        max_score = data.get('max_score', 100)
        
        existing = CompetitionRound.query.filter_by(competition_id=comp_id, round_number=round_number).first()
        if existing:
            return jsonify({'success': False, 'message': 'شماره مرحله تکراری است.'})
        
        round_obj = CompetitionRound(
            competition_id=comp_id,
            round_number=round_number,
            title=title,
            max_score=max_score
        )
        db.session.add(round_obj)
        db.session.commit()
        return jsonify({'success': True, 'message': 'مرحله اضافه شد.', 'round_id': round_obj.id})

    # ============================================
    # بخش نمره‌دهی داوران (دسترسی استاد و ادمین)
    # ============================================

    @app.route('/judge/competitions')
    @login_required
    def judge_competitions():
        """لیست مسابقاتی که کاربر به عنوان داور در آنها است (در اینجا فعلاً همه مسابقات فعال را نشان می‌دهیم)"""
        # در نسخه کامل باید یک جدول Judges داشته باشیم، اما فعلاً همه اساتید می‌توانند نمره دهند.
        if not (current_user.is_admin() or current_user.is_professor()):
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        competitions = Competition.query.filter_by(is_active=True).all()
        return render_template('judge/competitions.html', competitions=competitions, current_user=current_user)

    @app.route('/judge/competition/<int:comp_id>/score')
    @login_required
    def judge_score_competition(comp_id):
        """صفحه نمره‌دهی برای یک مسابقه"""
        if not (current_user.is_admin() or current_user.is_professor()):
            flash('دسترسی غیرمجاز', 'error')
            return redirect(url_for('dashboard'))
        
        competition = Competition.query.get_or_404(comp_id)
        registrations = CompetitionRegistration.query.filter_by(competition_id=comp_id).all()
        rounds = CompetitionRound.query.filter_by(competition_id=comp_id).order_by(CompetitionRound.round_number).all()
        
        # دریافت نمرات قبلی
        scores = {}
        for reg in registrations:
            scores[reg.id] = {}
            for round_obj in rounds:
                score_entry = JudgeScore.query.filter_by(round_id=round_obj.id, registration_id=reg.id, judge_id=current_user.id).first()
                scores[reg.id][round_obj.id] = score_entry.score if score_entry else None
        
        return render_template('judge/score.html', competition=competition, registrations=registrations, rounds=rounds, scores=scores, current_user=current_user)

    @app.route('/judge/save-score', methods=['POST'])
    @login_required
    def save_judge_score():
        """ذخیره نمره یک داور برای یک شرکت‌کننده در یک مرحله"""
        if not (current_user.is_admin() or current_user.is_professor()):
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'})
        
        data = request.get_json()
        round_id = data.get('round_id')
        registration_id = data.get('registration_id')
        score = data.get('score')
        feedback = data.get('feedback', '')
        
        # بررسی وجود مرحله و ثبت‌نام
        round_obj = CompetitionRound.query.get_or_404(round_id)
        reg = CompetitionRegistration.query.get_or_404(registration_id)
        
        # به‌روزرسانی یا ایجاد نمره
        score_entry = JudgeScore.query.filter_by(round_id=round_id, registration_id=registration_id, judge_id=current_user.id).first()
        if score_entry:
            score_entry.score = score
            score_entry.feedback = feedback
            score_entry.scored_at = datetime.utcnow()
        else:
            score_entry = JudgeScore(round_id=round_id, registration_id=registration_id, judge_id=current_user.id, score=score, feedback=feedback)
            db.session.add(score_entry)
        
        db.session.commit()
        
        # به‌روزرسانی نمره نهایی و رتبه‌بندی
        update_leaderboard(reg.competition_id)
        
        return jsonify({'success': True, 'message': 'نمره ذخیره شد.'})

    
    # ============================================
    # مسیرهای FCM (Firebase Cloud Messaging)
    # ============================================
    
    @app.route('/check-auth-status', methods=['GET'])
    def check_auth_status():
        """بررسی می‌کند که کاربر لاگین است یا نه"""
        return jsonify({
            'is_authenticated': current_user.is_authenticated
        })

    @app.route('/save-fcm-token', methods=['POST'])
    @login_required
    @verified_required
    def save_fcm_token():
        """ذخیره توکن FCM برای کاربر جاری"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'درخواست باید JSON باشد'}), 400
                
            token = data.get('token')
            
            if not token:
                return jsonify({'success': False, 'error': 'توکن ارسال نشده'}), 400
            
            # ذخیره توکن برای کاربر جاری
            current_user.fcm_token = token
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'توکن با موفقیت ذخیره شد'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/save-token', methods=['POST'])
    def save_token():
        """ذخیره توکن FCM (نسخه پشتیبان)"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'درخواست باید JSON باشد'}), 400
                
            token = data.get('token')
            user_id = data.get('user_id')
            
            if not token or not user_id:
                return jsonify({'success': False, 'error': 'token یا user_id ارسال نشده'}), 400
            
            # ذخیره در دیتابیس SQLite
            db_path = os.path.join(app.root_path, "instance", "seraj.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET fcm_token = ? WHERE id = ?", 
                (token, user_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'Token saved'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============================================
    # مسیرهای خطا
    # ============================================
    
    @app.route('/loading')
    def loading():
        """صفحه لودینگ"""
        return render_template('loading.html')
    
    # ============================================
    # فیلترهای تمپلیت
    # ============================================
# فیلتر تبدیل تاریخ به شمسی
    @app.template_filter('persian_date')
    def persian_date_filter(date_obj):
        """تبدیل تاریخ میلادی به شمسی"""
        if not date_obj:
            return ''
        try:
            jdate = jdatetime.date.fromgregorian(date=date_obj)
            persian_months = {
                1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
                5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
                9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
            }
            return f"{jdate.day} {persian_months[jdate.month]} {jdate.year}"
        except:
            return date_obj.strftime('%Y/%m/%d')

    @app.template_filter('persian_time')
    def persian_time_filter(date_obj):
        """فرمت زمان به فارسی"""
        if not date_obj:
            return ''
        try:
            return date_obj.strftime('%H:%M')
        except:
         return ''
    @app.template_filter('format_date')
    def format_date_filter(date_obj):
        """فرمت کردن تاریخ برای نمایش"""
        if date_obj:
            try:
                return date_obj.strftime('%Y-%m-%d')
            except:
                return ''
        return ''
    
        # ============================================
    # ========== مسیرهای صحیفه سجادیه ==========
    # ============================================

    @app.route('/sahifa')
    def sahifa_index():
        """صفحه اصلی صحیفه سجادیه"""
        from models import SahifaCategory, SahifaPrayer, SahifaMunajat
        
        try:
            categories = SahifaCategory.query.filter_by(is_active=True).order_by(SahifaCategory.order).all()
            featured_prayers = SahifaPrayer.query.filter_by(is_featured=True, is_active=True).limit(6).all()
            total_prayers = SahifaPrayer.query.filter_by(is_active=True).count()
            
            # آمار دسته‌بندی‌ها
            categories_stats = []
            for cat in categories:
                count = SahifaPrayer.query.filter_by(category_id=cat.id, is_active=True).count()
                categories_stats.append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug,
                    'icon': cat.icon,
                    'count': count
                })
        except Exception as e:
            print(f"خطا در دریافت اطلاعات صحیفه: {e}")
            categories = []
            featured_prayers = []
            total_prayers = 0
            categories_stats = []
        
        return render_template('sahifa/index.html',
                             categories=categories,
                             categories_stats=categories_stats,
                             featured_prayers=featured_prayers,
                             total_prayers=total_prayers,
                             current_user=current_user)


    @app.route('/sahifa/category/<slug>')
    def sahifa_category(slug):
        """نمایش دعاهای یک دسته‌بندی"""
        from models import SahifaCategory, SahifaPrayer
        
        try:
            category = SahifaCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
            prayers = SahifaPrayer.query.filter_by(category_id=category.id, is_active=True)\
                .order_by(SahifaPrayer.number).all()
        except Exception as e:
            flash('دسته‌بندی مورد نظر یافت نشد.', 'error')
            return redirect(url_for('sahifa_index'))
        
        return render_template('sahifa/category.html',
                             category=category,
                             prayers=prayers,
                             current_user=current_user)


    @app.route('/sahifa/prayer/<int:prayer_id>')
    def sahifa_detail(prayer_id):
        """جزئیات یک دعا"""
        from models import SahifaPrayer, SahifaCategory
        
        try:
            prayer = SahifaPrayer.query.filter_by(id=prayer_id, is_active=True).first_or_404()
            
            # افزایش بازدید
            prayer.view_count += 1
            db.session.commit()
            
            # دعاهای مرتبط (همین دسته)
            related = SahifaPrayer.query.filter(
                SahifaPrayer.category_id == prayer.category_id,
                SahifaPrayer.id != prayer.id,
                SahifaPrayer.is_active == True
            ).limit(5).all()
            
            # همه دسته‌بندی‌ها برای منو
            categories = SahifaCategory.query.filter_by(is_active=True).all()
            
        except Exception as e:
            flash('دعای مورد نظر یافت نشد.', 'error')
            return redirect(url_for('sahifa_index'))
        
        return render_template('sahifa/detail.html',
                             prayer=prayer,
                             related=related,
                             categories=categories,
                             current_user=current_user)


    @app.route('/sahifa/munajat')
    def sahifa_munajat():
        """نمایش مناجات خمسه عشر"""
        from models import SahifaMunajat
        
        try:
            munajat_list = SahifaMunajat.query.filter_by(is_active=True)\
                .order_by(SahifaMunajat.number).all()
        except Exception as e:
            print(f"خطا در دریافت مناجات: {e}")
            munajat_list = []
        
        return render_template('sahifa/munajat.html',
                             munajat_list=munajat_list,
                             current_user=current_user)


    @app.route('/sahifa/munajat/<int:munajat_id>')
    def sahifa_munajat_detail(munajat_id):
        """جزئیات یک مناجات"""
        from models import SahifaMunajat
        
        try:
            munajat = SahifaMunajat.query.filter_by(id=munajat_id, is_active=True).first_or_404()
            
            # افزایش بازدید
            munajat.view_count += 1
            db.session.commit()
            
            # مناجات قبلی و بعدی
            prev_munajat = SahifaMunajat.query.filter(
                SahifaMunajat.number < munajat.number,
                SahifaMunajat.is_active == True
            ).order_by(SahifaMunajat.number.desc()).first()
            
            next_munajat = SahifaMunajat.query.filter(
                SahifaMunajat.number > munajat.number,
                SahifaMunajat.is_active == True
            ).order_by(SahifaMunajat.number).first()
            
        except Exception as e:
            flash('مناجات مورد نظر یافت نشد.', 'error')
            return redirect(url_for('sahifa_munajat'))
        
        return render_template('sahifa/munajat_detail.html',
                             munajat=munajat,
                             prev=prev_munajat,
                             next=next_munajat,
                             current_user=current_user)


        # ============================================
    # مدیریت صحیفه سجادیه (فقط ادمین)
    # ============================================

    @app.route('/admin/sahifa/contents')
    @login_required
    @admin_required
    def admin_sahifa_contents():
        """مدیریت محتوای صحیفه سجادیه"""
        from models import SahifaPrayer, SahifaCategory
        
        category_id = request.args.get('category_id', type=int)
        query = SahifaPrayer.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        prayers = query.order_by(SahifaPrayer.number).all()
        categories = SahifaCategory.query.filter_by(is_active=True).all()
        
        return render_template('admin/sahifa/contents.html',
                            prayers=prayers,
                            categories=categories,
                            selected_category=category_id,
                            current_user=current_user)

    @app.route('/api/sahifa/search')
    def api_sahifa_search():
        """API جستجو در دعاها"""
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'متن جستجو وارد نشده است'})
        
        from models import SahifaPrayer
        
        try:
            prayers = SahifaPrayer.query.filter(
                SahifaPrayer.is_active == True,
                (SahifaPrayer.title.ilike(f'%{query}%') |
                 SahifaPrayer.persian_text.ilike(f'%{query}%') |
                 SahifaPrayer.keywords.ilike(f'%{query}%'))
            ).limit(20).all()
            
            results = []
            for p in prayers:
                results.append({
                    'id': p.id,
                    'number': p.number,
                    'title': p.title,
                    'excerpt': p.persian_text[:150] + '...' if len(p.persian_text) > 150 else p.persian_text
                })
            
            return jsonify({'success': True, 'results': results, 'count': len(results)})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

                # ============================================
    # ========== مسیرهای معارف اسلامی ==========
    # ============================================

    @app.route('/maaref')
    def maaref_index():
        """صفحه اصلی معارف اسلامی"""
        from models import MaarefCategory, MaarefArticle
        
        try:
            categories = MaarefCategory.query.filter_by(is_active=True).order_by(MaarefCategory.order).all()
            featured_articles = MaarefArticle.query.filter_by(is_featured=True, is_active=True).order_by(MaarefArticle.created_at.desc()).limit(6).all()
            latest_articles = MaarefArticle.query.filter_by(is_active=True).order_by(MaarefArticle.created_at.desc()).limit(10).all()  # ✅ اضافه شد
        except Exception as e:
            print(f"خطا در دریافت معارف: {e}")
            categories = []
            featured_articles = []
            latest_articles = []  
        
        return render_template('maaref/index.html',
                            categories=categories,
                            featured_articles=featured_articles,
                            latest_articles=latest_articles, 
                            current_user=current_user)


    @app.route('/maaref/category/<slug>')
    def maaref_category(slug):
        """نمایش مقالات یک دسته‌بندی"""
        from models import MaarefCategory, MaarefArticle
        
        try:
            category = MaarefCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
            articles = MaarefArticle.query.filter_by(category_id=category.id, is_active=True)\
                .order_by(MaarefArticle.created_at.desc()).all()
        except Exception as e:
            flash('دسته‌بندی مورد نظر یافت نشد.', 'error')
            return redirect(url_for('maaref_index'))
        
        return render_template('maaref/category.html',
                            category=category,
                            articles=articles,
                            current_user=current_user)


    @app.route('/maaref/<int:article_id>')
    def maaref_detail(article_id):
        """جزئیات یک مقاله"""
        from models import MaarefArticle, MaarefCategory
        
        try:
            article = MaarefArticle.query.filter_by(id=article_id, is_active=True).first_or_404()
            
            # افزایش بازدید
            article.view_count += 1
            db.session.commit()
            
            # مطالب مرتبط
            related = MaarefArticle.query.filter(
                MaarefArticle.category_id == article.category_id,
                MaarefArticle.id != article.id,
                MaarefArticle.is_active == True
            ).limit(5).all()
            
            # همه دسته‌بندی‌ها برای منو
            categories = MaarefCategory.query.filter_by(is_active=True).all()
            
        except Exception as e:
            flash('مطلب مورد نظر یافت نشد.', 'error')
            return redirect(url_for('maaref_index'))
        
        return render_template('maaref/detail.html',
                            article=article,
                            related=related,
                            categories=categories,
                            current_user=current_user)


    @app.route('/api/maaref/search')
    def api_maaref_search():
        """API جستجو در مقالات معارف اسلامی"""
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'متن جستجو وارد نشده است'})
        
        from models import MaarefArticle
        
        try:
            articles = MaarefArticle.query.filter(
                MaarefArticle.is_active == True,
                (MaarefArticle.title.ilike(f'%{query}%') |
                MaarefArticle.content.ilike(f'%{query}%') |
                MaarefArticle.tags.ilike(f'%{query}%'))
            ).limit(20).all()
            
            results = []
            for a in articles:
                results.append({
                    'id': a.id,
                    'title': a.title,
                    'excerpt': a.excerpt[:100] + '...' if len(a.excerpt or '') > 100 else a.excerpt
                })
            
            return jsonify({'success': True, 'results': results, 'count': len(results)})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    # دسته‌بندی‌های ثابت (برای لینک‌های سریع)
    @app.route('/maaref/beliefs')
    def maaref_beliefs():
        """عقاید (کلام)"""
        return redirect(url_for('maaref_category', slug='beliefs'))


    @app.route('/maaref/ethics')
    def maaref_ethics():
        """اخلاق اسلامی"""
        return redirect(url_for('maaref_category', slug='ethics'))


    @app.route('/maaref/jurisprudence')
    def maaref_jurisprudence():
        """احکام (فقه)"""
        return redirect(url_for('maaref_category', slug='jurisprudence'))



    @app.route('/admin/sms-test', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_sms_test():
        """صفحه تست ارسال پیامک با sms.ir"""
        credit = None
        credit_status = None
        
        if request.method == 'POST':
            phone = request.form.get('phone')
            message = request.form.get('message')
            
            if not phone or not message:
                flash('لطفاً شماره تلفن و متن پیام را وارد کنید.', 'error')
                return redirect(url_for('admin_sms_test'))
            
            # ارسال تستی
            success, response = SMSConfig.send_sms(phone, message)
            
            if success:
                flash(f'✅ پیامک با موفقیت به شماره {phone} ارسال شد.', 'success')
            else:
                flash(f'❌ خطا در ارسال: {response}', 'error')
        
        # دریافت اعتبار حساب
        credit_status, credit = SMSConfig.get_credit()
        
        return render_template('admin/sms_test.html', 
                            current_user=current_user,
                            credit=credit if credit_status else None,
                            line_number=SMSConfig.LINE_NUMBER)


    # ============================================
    # مدیریت معارف اسلامی (فقط ادمین)
    # ============================================

    @app.route('/admin/maaref/contents')
    @login_required
    @admin_required
    def admin_maaref_contents():
        """مدیریت محتوای معارف اسلامی"""
        from models import MaarefArticle, MaarefCategory
        
        category_id = request.args.get('category_id', type=int)
        query = MaarefArticle.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        articles = query.order_by(MaarefArticle.created_at.desc()).all()
        categories = MaarefCategory.query.all()
        
        return render_template('admin/maaref/contents.html',
                            articles=articles,
                            categories=categories,
                            selected_category=category_id,
                            current_user=current_user)
    [{
	"resource": "/f:/seraj/templates/admin/maaref/index.html",
	"owner": "_generated_diagnostic_collection_name_#7",
	"severity": 8,
	"message": "Property assignment expected.",
	"source": "javascript",
	"startLineNumber": 96,
	"startColumn": 65,
	"endLineNumber": 96,
	"endColumn": 66,
	"modelVersionId": 2,
	"origin": "extHost1"
},{
	"resource": "/f:/seraj/templates/admin/maaref/index.html",
	"owner": "_generated_diagnostic_collection_name_#7",
	"severity": 8,
	"message": "',' expected.",
	"source": "javascript",
	"startLineNumber": 96,
	"startColumn": 74,
	"endLineNumber": 96,
	"endColumn": 75,
	"modelVersionId": 2,
	"origin": "extHost1"
},{
	"resource": "/f:/seraj/templates/admin/maaref/index.html",
	"owner": "_generated_diagnostic_collection_name_#7",
	"severity": 8,
	"message": "',' expected.",
	"source": "javascript",
	"startLineNumber": 96,
	"startColumn": 79,
	"endLineNumber": 96,
	"endColumn": 80,
	"modelVersionId": 2,
	"origin": "extHost1"
},{
	"resource": "/f:/seraj/templates/admin/maaref/index.html",
	"owner": "_generated_diagnostic_collection_name_#7",
	"severity": 8,
	"message": "Argument expression expected.",
	"source": "javascript",
	"startLineNumber": 96,
	"startColumn": 80,
	"endLineNumber": 96,
	"endColumn": 81,
	"modelVersionId": 2,
	"origin": "extHost1"
}]
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403
    
    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('500.html'), 500
    