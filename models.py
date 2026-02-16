from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

# ================================
# ENUMS
# ================================

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    STUDENT = "participant"

# ❌ UserType به طور کامل حذف شد - به جای آن از String استفاده می‌کنیم

class EventType(enum.Enum):
    WORKSHOP = "workshop"
    COMPETITION = "competition"
    HALAQAH = "halaqah"
    LECTURE = "lecture"
    OTHER = "other"

# ================ ENUM های جدید ================
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Degree(enum.Enum):
    ASSOCIATE = "کاردانی"
    BACHELOR = "کارشناسی"
    BACHELOR_CONTINUOUS = "کارشناسی پیوسته"
    BACHELOR_DISCONTINUOUS = "کارشناسی ناپیوسته"
    MASTER = "کارشناسی ارشد"
    MASTER_CONTINUOUS = "کارشناسی ارشد پیوسته"
    MASTER_DISCONTINUOUS = "کارشناسی ارشد ناپیوسته"
    PHD = "دکتری"
    POSTDOC = "پسا دکتری"
    MEDICAL = "پزشکی عمومی"
    RESIDENCY = "دستیاری"

class AcademicRank(enum.Enum):
    PROFESSOR = "استاد"
    ASSOCIATE_PROFESSOR = "دانشیار"
    ASSISTANT_PROFESSOR = "استادیار"
    INSTRUCTOR = "مربی"
    VISITING_LECTURER = "مدرس مدعو"

# ================================
# USER MODEL (COMPLETE WITH ALL TYPES)
# ================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    # ========== فیلدهای اصلی ==========
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # ========== اطلاعات هویتی ==========
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    
    # ========== اطلاعات تماس ==========
    phone = db.Column(db.String(20), nullable=False)  # تلفن همراه - الزامی
    landline = db.Column(db.String(20), nullable=True)  # تلفن ثابت - اختیاری
    
    # ========== اطلاعات فردی ==========
    gender = db.Column(db.Enum(Gender), nullable=False)  # جنسیت - الزامی
    
    # ========== نوع کاربر - دیگر Enum نیست، String است ==========
    user_type = db.Column(db.String(20), nullable=False, default='student')
    
    # ========== وضعیت تأیید (جدید) ==========
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    
    # ========== اطلاعات دانشجویی (مخصوص دانشجویان) ==========
    student_id = db.Column(db.String(50), nullable=True)  # شماره دانشجویی
    entrance_year = db.Column(db.String(4), nullable=True)  # سال ورود
    degree = db.Column(db.Enum(Degree), nullable=True)  # مقطع تحصیلی
    field_of_study = db.Column(db.String(150), nullable=True)  # رشته تحصیلی
    
    # ========== اطلاعات استاد (مخصوص اساتید) ==========
    academic_rank = db.Column(db.Enum(AcademicRank), nullable=True)  # مرتبه علمی
    specialization = db.Column(db.String(200), nullable=True)  # تخصص
    resume_file = db.Column(db.String(500), nullable=True)  # فایل رزومه
    teaching_experience = db.Column(db.Integer, nullable=True)  # سابقه تدریس (سال)
    professor_code = db.Column(db.String(50), nullable=True)  # کد استادی
    office_hours = db.Column(db.String(200), nullable=True)  # ساعات حضور در دفتر
    website = db.Column(db.String(200), nullable=True)  # وبسایت شخصی
    
    # ========== اطلاعات کارمند (مخصوص کارکنان) ==========
    employee_id = db.Column(db.String(50), nullable=True)  # کد پرسنلی
    department = db.Column(db.String(100), nullable=True)  # واحد سازمانی
    position = db.Column(db.String(100), nullable=True)  # سمت
    office_phone = db.Column(db.String(20), nullable=True)  # تلفن دفتر کار
    responsibility = db.Column(db.Text, nullable=True)  # حوزه مسئولیت
    
    # ========== اطلاعات مکانی (مشترک) ==========
    province = db.Column(db.String(100), nullable=False)  # استان - الزامی
    city = db.Column(db.String(100), nullable=False)  # شهر - الزامی
    university = db.Column(db.String(150), nullable=False)  # دانشگاه - الزامی
    faculty = db.Column(db.String(150), nullable=False)  # دانشکده - الزامی
    address = db.Column(db.Text, nullable=True)  # آدرس کامل
    
    # ========== اطلاعات سیستم ==========
    role = db.Column(db.Enum(UserRole), default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # ========== روابط ==========
    verifier = db.relationship("User", foreign_keys=[verified_by], remote_side=[id])

    # ========== property و متدها ==========
    @property
    def full_name(self):
        """نام کامل کاربر"""
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, password):
        """تنظیم رمز عبور"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """بررسی رمز عبور"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """بررسی مدیر بودن"""
        return self.role == UserRole.ADMIN

    def is_manager(self):
        """بررسی مسئول بودن"""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    def get_user_type_display(self):
        """دریافت نمایش فارسی نوع کاربر"""
        types = {
            'student': 'دانشجو',
            'professor': 'استاد',
            'staff': 'کارمند امور فرهنگی'
        }
        return types.get(self.user_type, '')
    
    def get_status_display(self):
        """دریافت وضعیت تأیید"""
        if self.is_verified:
            return "تأیید شده"
        return "در انتظار تأیید"
    
    def get_gender_display(self):
        """دریافت نمایش فارسی جنسیت"""
        gender_map = {
            Gender.MALE: "مرد",
            Gender.FEMALE: "زن",
            Gender.OTHER: "سایر"
        }
        return gender_map.get(self.gender, "")
    
    def get_degree_display(self):
        """دریافت نمایش فارسی مقطع تحصیلی"""
        return self.degree.value if self.degree else ""
    
    def get_academic_rank_display(self):
        """دریافت نمایش فارسی مرتبه علمی"""
        return self.academic_rank.value if self.academic_rank else ""

# ================================
# EVENT MODEL
# ================================

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.Enum(EventType), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    capacity = db.Column(db.Integer)
    current_participants = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship("User", backref="created_events")
    registrations = db.relationship(
        "Registration",
        backref="event",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def is_full(self):
        """بررسی تکمیل ظرفیت"""
        return self.capacity and self.current_participants >= self.capacity

    def remaining_capacity(self):
        """ظرفیت باقی‌مانده"""
        if self.capacity:
            return self.capacity - self.current_participants
        return None

# ================================
# REGISTRATION MODEL
# ================================

class Registration(db.Model):
    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="registered")
    attended = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="registrations")

    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_registration"),
    )

# ================================
# NOTIFICATION MODEL
# ================================

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")

# ================================
# AI QUESTION MODEL
# ================================

class AIQuestion(db.Model):
    __tablename__ = "ai_questions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    is_quranic = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="ai_questions")

# ================================
# QURAN VERSES
# ================================
class QuranVerse(db.Model):
    __tablename__ = 'quran_verses'
    
    id = db.Column(db.Integer, primary_key=True)
    surah_name = db.Column(db.String(100))  # نام سوره
    surah_number = db.Column(db.Integer)  # شماره سوره
    verse_number = db.Column(db.Integer)  # شماره آیه
    verse_arabic = db.Column(db.Text)  # متن عربی
    verse_persian = db.Column(db.Text)  # ترجمه فارسی
    translation = db.Column(db.Text)  # ترجمه (اگر جداگانه هست)
    keywords = db.Column(db.String(500))  # کلمات کلیدی (اختیاری)
    topic = db.Column(db.String(100))  # موضوع (اختیاری)
    is_active = db.Column(db.Boolean, default=True)
    
# ================================
# PASSWORD RESET TOKEN
# ================================

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="reset_tokens")

# ================================
# حلقه تلاوت و جلسات
# ================================

class QuranCircle(db.Model):
    """حلقه تلاوت - گروه اصلی"""
    __tablename__ = "quran_circles"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # نام حلقه
    description = db.Column(db.Text)  # توضیحات
    teacher_name = db.Column(db.String(200), nullable=False)  # نام استاد
    teacher_bio = db.Column(db.Text)  # بیوگرافی استاد
    teacher_image = db.Column(db.String(200))  # تصویر استاد
    circle_type = db.Column(db.String(50), default="general")  # نوع: general, memorization, tajweed, tafsir
    level = db.Column(db.String(50), default="beginner")  # سطح: beginner, intermediate, advanced
    days_of_week = db.Column(db.String(200))  # روزهای برگزاری (JSON یا CSV)
    start_time = db.Column(db.String(10))  # زمان شروع
    end_time = db.Column(db.String(10))  # زمان پایان
    location = db.Column(db.String(200))  # مکان برگزاری
    is_online = db.Column(db.Boolean, default=False)  # آیا آنلاین است؟
    online_link = db.Column(db.String(500))  # لینک جلسه آنلاین
    capacity = db.Column(db.Integer)  # ظرفیت
    current_members = db.Column(db.Integer, default=0)  # اعضای فعلی
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_circles")
    sessions = db.relationship("CircleSession", backref="circle", lazy="dynamic", cascade="all, delete-orphan")
    members = db.relationship("CircleMember", backref="circle", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("CircleFile", backref="circle", lazy="dynamic", cascade="all, delete-orphan")
    
    def is_full(self):
        """بررسی تکمیل ظرفیت"""
        return self.capacity and self.current_members >= self.capacity
    
    def remaining_capacity(self):
        """ظرفیت باقی‌مانده"""
        if self.capacity:
            return self.capacity - self.current_members
        return None
    
    @property
    def next_session(self):
        """دریافت جلسه بعدی"""
        from datetime import datetime
        return self.sessions.filter(CircleSession.session_date >= datetime.now().date())\
                            .order_by(CircleSession.session_date).first()
    
    @property
    def last_session(self):
        """دریافت آخرین جلسه برگزار شده"""
        from datetime import datetime
        return self.sessions.filter(CircleSession.session_date < datetime.now().date())\
                            .order_by(CircleSession.session_date.desc()).first()


class CircleSession(db.Model):
    """جلسات حلقه تلاوت"""
    __tablename__ = "circle_sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    title = db.Column(db.String(200))  # عنوان جلسه
    session_date = db.Column(db.Date, nullable=False)  # تاریخ جلسه
    start_time = db.Column(db.String(10))  # زمان شروع
    end_time = db.Column(db.String(10))  # زمان پایان
    topic = db.Column(db.String(500))  # موضوع جلسه
    description = db.Column(db.Text)  # توضیحات کامل جلسه
    verses_reviewed = db.Column(db.Text)  # آیات تلاوت شده
    notes = db.Column(db.Text)  # نکات جلسه
    homework = db.Column(db.Text)  # تکلیف جلسه بعد
    is_held = db.Column(db.Boolean, default=False)  # آیا برگزار شده؟
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    attendances = db.relationship("SessionAttendance", backref="session", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("SessionFile", backref="session", lazy="dynamic", cascade="all, delete-orphan")
    
    @property
    def attendance_count(self):
        """تعداد حاضرین در جلسه"""
        return self.attendances.filter_by(attended=True).count()
    
    @property
    def total_members(self):
        """تعداد کل اعضای حلقه"""
        return self.circle.members.filter_by(is_active=True).count()


class CircleMember(db.Model):
    """عضویت در حلقه تلاوت"""
    __tablename__ = "circle_members"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)  # تاریخ عضویت
    is_active = db.Column(db.Boolean, default=True)  # آیا عضو فعال است؟
    role = db.Column(db.String(50), default="member")  # نقش: member, assistant, teacher
    notes = db.Column(db.Text)  # یادداشت‌ها
    
    user = db.relationship("User", backref="circle_memberships")
    attendances = db.relationship("SessionAttendance", backref="member", lazy="dynamic")
    
    __table_args__ = (
        db.UniqueConstraint("circle_id", "user_id", name="unique_circle_member"),
    )
    
    @property
    def attendance_rate(self):
        """درصد حضور در جلسات"""
        total_sessions = self.circle.sessions.filter_by(is_held=True).count()
        if total_sessions == 0:
            return 0
        attended = self.attendances.filter_by(attended=True).count()
        return round((attended / total_sessions) * 100)


class SessionAttendance(db.Model):
    """حضور و غیاب جلسات"""
    __tablename__ = "session_attendances"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("circle_sessions.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("circle_members.id"), nullable=False)
    attended = db.Column(db.Boolean, default=False)  # آیا حضور داشته؟
    excuse = db.Column(db.String(200))  # علت غیبت (در صورت وجود)
    late_minutes = db.Column(db.Integer, default=0)  # دقیقه تأخیر
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"))  # ثبت‌کننده حضور
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)  # زمان ثبت
    
    marker = db.relationship("User", foreign_keys=[marked_by])
    
    __table_args__ = (
        db.UniqueConstraint("session_id", "member_id", name="unique_attendance"),
    )


class CircleFile(db.Model):
    """فایل‌های عمومی حلقه"""
    __tablename__ = "circle_files"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, audio, video, image, etc
    file_size = db.Column(db.Integer)  # حجم فایل به بایت
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)  # آیا برای همه اعضا قابل مشاهده است؟
    download_count = db.Column(db.Integer, default=0)
    
    uploader = db.relationship("User", foreign_keys=[uploaded_by])


class SessionFile(db.Model):
    """فایل‌های جلسات (ضبط جلسه، جزوه و...)"""
    __tablename__ = "session_files"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("circle_sessions.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, audio, video, image, etc
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    uploader = db.relationship("User", foreign_keys=[uploaded_by])


class CircleSchedule(db.Model):
    """برنامه جلسات (برای تکرار هفتگی)"""
    __tablename__ = "circle_schedules"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    day_of_week = db.Column(db.Integer)  # 0=شنبه, 1=یکشنبه, ... 6=جمعه
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    is_active = db.Column(db.Boolean, default=True)
    
    circle = db.relationship("QuranCircle", backref="schedules")


class UserFCMToken(db.Model):
    __tablename__ = "user_fcm_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fcm_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fcm_token = db.Column(db.String(255), nullable=True)
    user = db.relationship("User", backref="fcm_tokens")

