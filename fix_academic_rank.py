# fix_academic_rank.py
from app import app
from models import db, User
from models import AcademicRank

with app.app_context():
    # پیدا کردن کاربرانی که academic_rank فارسی دارند
    users = User.query.filter(User.academic_rank.isnot(None)).all()
    
    mapping = {
        'استاد': AcademicRank.PROFESSOR,
        'دانشیار': AcademicRank.ASSOCIATE_PROFESSOR,
        'استادیار': AcademicRank.ASSISTANT_PROFESSOR,
        'مربی': AcademicRank.INSTRUCTOR,
        'استاد مدعو': AcademicRank.VISITING_LECTURER,
        'پژوهشگر': AcademicRank.RESEARCHER,
        'دکتر': AcademicRank.DOCTORAL,
        'کارشناسی ارشد': AcademicRank.MASTER,
        'کارشناسی': AcademicRank.BACHELOR
    }
    
    count = 0
    for user in users:
        if user.academic_rank in mapping:
            print(f"کاربر {user.username}: {user.academic_rank} -> {mapping[user.academic_rank].value}")
            user.academic_rank = mapping[user.academic_rank]
            count += 1
    
    db.session.commit()
    print(f"✅ {count} کاربر به‌روزرسانی شدند.")