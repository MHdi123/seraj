# models.py
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

class EventType(enum.Enum):
    WORKSHOP = "workshop"
    COMPETITION = "competition"
    HALAQAH = "halaqah"
    LECTURE = "lecture"
    OTHER = "other"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value == value:
                    return member
            value_upper = value.upper()
            for member in cls:
                if member.name == value_upper:
                    return member
        return None

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

class AttendanceStatus(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    
    @classmethod
    def get_display(cls, status):
        displays = {
            "present": "حاضر",
            "absent": "غایب",
            "late": "تأخیر",
            "excused": "موجه"
        }
        return displays.get(status, status)

class EnrollmentStatus(enum.Enum):
    ACTIVE = "active"
    DROPPED = "dropped"
    COMPLETED = "completed"
    PENDING = "pending"
    
    @classmethod
    def get_display(cls, status):
        displays = {
            "active": "فعال",
            "dropped": "انصراف داده",
            "completed": "تکمیل شده",
            "pending": "در انتظار"
        }
        return displays.get(status, status)

class SessionStatus(enum.Enum):
    SCHEDULED = "scheduled"
    HELD = "held"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


# ================================
# USER MODEL
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
    phone = db.Column(db.String(20), nullable=False, default='')
    landline = db.Column(db.String(20), nullable=True)
    
    # ========== اطلاعات فردی ==========
    gender = db.Column(db.String(10), nullable=False, default='male')
    
    # ========== نوع کاربر ==========
    user_type = db.Column(db.String(20), nullable=False, default='student')
    
    # ========== وضعیت تأیید ==========
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    
    # ========== اطلاعات دانشجویی ==========
    student_id = db.Column(db.String(50), nullable=True)
    entrance_year = db.Column(db.String(4), nullable=True)
    degree = db.Column(db.Enum(Degree), nullable=True)
    field_of_study = db.Column(db.String(150), nullable=True)
    
    # ========== اطلاعات استاد ==========
    academic_rank = db.Column(db.String(50), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    resume_file = db.Column(db.String(500), nullable=True)
    teaching_experience = db.Column(db.Integer, nullable=True)
    professor_code = db.Column(db.String(50), nullable=True)
    office_hours = db.Column(db.String(200), nullable=True)
    office_location = db.Column(db.String(200), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    
    # ========== اطلاعات کارمند ==========
    employee_id = db.Column(db.String(50), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    office_phone = db.Column(db.String(20), nullable=True)
    responsibility = db.Column(db.Text, nullable=True)
    
    # ========== اطلاعات مکانی ==========
    province = db.Column(db.String(100), nullable=False, default='')
    city = db.Column(db.String(100), nullable=False, default='')
    university = db.Column(db.String(150), nullable=False, default='')
    faculty = db.Column(db.String(150), nullable=False, default='')
    address = db.Column(db.Text, nullable=True)
    
    # ========== اطلاعات سیستم ==========
    role = db.Column(db.Enum(UserRole), default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)

    # ========== FCM token ==========
    fcm_token = db.Column(db.String(500), nullable=True)

    # ========== روابط ==========
    verifier = db.relationship("User", foreign_keys=[verified_by], remote_side=[id])

    # ========== property و متدها ==========
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_manager(self):
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    def is_professor(self):
        return self.user_type == 'professor'
    
    def is_staff(self):
        return self.user_type == 'staff'
    
    def can_access_staff_panel(self):
        return self.is_admin() or (self.is_staff() and self.is_verified)
    
    def can_access_professor_panel(self):
        return self.is_admin() or (self.is_professor() and self.is_verified)
    
    def get_user_type_display(self):
        types = {
            'student': 'دانشجو',
            'professor': 'استاد',
            'staff': 'کارمند امور فرهنگی'
        }
        return types.get(self.user_type, '')
    
    def get_status_display(self):
        if self.is_verified:
            return "تأیید شده"
        return "در انتظار تأیید"
    
    def get_status_class(self):
        if self.is_verified:
            return "bg-green-100 text-green-800"
        return "bg-yellow-100 text-yellow-800"
    
    def get_status_icon(self):
        if self.is_verified:
            return "fas fa-check-circle text-green-600"
        return "fas fa-clock text-yellow-600"
    
    def get_gender_display(self):
        gender_map = {
            'male': 'مرد',
            'female': 'زن',
            'other': 'سایر'
        }
        return gender_map.get(self.gender, self.gender)
    
    def get_degree_display(self):
        return self.degree.value if self.degree else ""
    
    def get_academic_rank_display(self):
        rank_map = {
            'PROFESSOR': 'استاد',
            'ASSOCIATE_PROFESSOR': 'دانشیار',
            'ASSISTANT_PROFESSOR': 'استادیار',
            'INSTRUCTOR': 'مربی',
            'VISITING_LECTURER': 'مدرس مدعو'
        }
        return rank_map.get(self.academic_rank, self.academic_rank or '')

    def __repr__(self):
        return f'<User {self.username}>'


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

    creator = db.relationship("User", foreign_keys=[created_by], backref="created_events")
    registrations = db.relationship(
        "Registration",
        backref="event",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def is_full(self):
        return self.capacity and self.current_participants >= self.capacity

    def remaining_capacity(self):
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

    user = db.relationship("User", foreign_keys=[user_id], backref="registrations")

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

    user = db.relationship("User", foreign_keys=[user_id], backref="notifications")


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

    user = db.relationship("User", foreign_keys=[user_id], backref="ai_questions")


# ================================
# QURAN VERSES
# ================================

class QuranVerse(db.Model):
    __tablename__ = 'quran_verses'
    
    id = db.Column(db.Integer, primary_key=True)
    surah_name = db.Column(db.String(100))
    surah_number = db.Column(db.Integer)
    verse_number = db.Column(db.Integer)
    verse_arabic = db.Column(db.Text)
    verse_persian = db.Column(db.Text)
    translation = db.Column(db.Text)
    keywords = db.Column(db.String(500))
    topic = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<QuranVerse {self.surah_name} - {self.verse_number}>'

class Hadith(db.Model):
    __tablename__ = 'hadiths'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)          # عنوان: پیامبر اکرم (ص)
    arabic_text = db.Column(db.Text, nullable=False)           # متن عربی
    persian_text = db.Column(db.Text, nullable=False)          # ترجمه فارسی
    source = db.Column(db.String(200), nullable=False)         # منبع
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Hadith {self.title}>'

# ================================
# PASSWORD RESET TOKEN
# ================================

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='reset_tokens')


# ================================
# FACULTY MODEL
# ================================

class Faculty(db.Model):
    __tablename__ = "faculties"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    university = db.Column(db.String(200), nullable=False)
    dean = db.Column(db.String(200))
    description = db.Column(db.Text)
    established_year = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    departments = db.relationship("Department", back_populates="faculty", lazy="dynamic")
    classes = db.relationship("Class", back_populates="faculty", lazy="dynamic")
    
    def __repr__(self):
        return f'<Faculty {self.name}>'


# ================================
# DEPARTMENT MODEL
# ================================

class Department(db.Model):
    __tablename__ = "departments"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"))
    head = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    faculty = db.relationship("Faculty", back_populates="departments")
    courses = db.relationship("Course", back_populates="department", lazy="dynamic")
    
    def __repr__(self):
        return f'<Department {self.name}>'


# ================================
# COURSE MODEL
# ================================

class Course(db.Model):
    __tablename__ = "courses"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    credits = db.Column(db.Integer, default=3)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    description = db.Column(db.Text)
    prerequisites = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    department = db.relationship("Department", back_populates="courses")
    classes = db.relationship("Class", back_populates="course", lazy="dynamic")
    
    def __repr__(self):
        return f'<Course {self.name} - {self.code}>'


# ================================
# ACADEMIC TERM MODEL
# ================================

class AcademicTerm(db.Model):
    __tablename__ = "academic_terms"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AcademicTerm {self.name}>'


# ================================
# CLASS MODEL
# ================================

class Class(db.Model):
    __tablename__ = "classes"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"))
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    academic_term = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    schedule = db.Column(db.String(500))
    location = db.Column(db.String(200))
    capacity = db.Column(db.Integer, default=30)
    credits = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    instructor = db.relationship("User", foreign_keys=[instructor_id], backref="taught_classes")
    faculty = db.relationship("Faculty", foreign_keys=[faculty_id], back_populates="classes")
    course = db.relationship("Course", foreign_keys=[course_id], back_populates="classes")
    enrollments = db.relationship("ClassEnrollment", back_populates="class_obj", lazy="dynamic", cascade="all, delete-orphan")
    sessions = db.relationship("CourseSession", back_populates="class_obj", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("ClassFile", back_populates="class_obj", lazy="dynamic", cascade="all, delete-orphan")
    
    @property
    def student_count(self):
        return self.enrollments.filter_by(status='active').count()
    
    @property
    def total_sessions(self):
        return self.sessions.count()
    
    @property
    def completed_sessions(self):
        from datetime import date
        return self.sessions.filter(CourseSession.session_date < date.today()).count()
    
    @property
    def upcoming_sessions(self):
        from datetime import date
        return self.sessions.filter(
            CourseSession.session_date >= date.today(),
            CourseSession.is_cancelled == False
        ).count()
    
    @property
    def attendance_rate(self):
        total_possible = self.student_count * self.total_sessions
        if total_possible == 0:
            return 0
        
        total_attended = db.session.query(db.func.count(Attendance.id))\
            .join(CourseSession, CourseSession.id == Attendance.session_id)\
            .filter(CourseSession.class_id == self.id)\
            .filter(Attendance.status == 'present')\
            .scalar() or 0
        
        return int((total_attended / total_possible) * 100)
    
    def __repr__(self):
        return f'<Class {self.name} - {self.code}>'


# ================================
# CLASS ENROLLMENT MODEL
# ================================

class ClassEnrollment(db.Model):
    __tablename__ = "class_enrollments"
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE)
    grade = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text)
    
    # روابط
    class_obj = db.relationship("Class", foreign_keys=[class_id], back_populates="enrollments")
    student = db.relationship("User", foreign_keys=[student_id], backref="class_enrollments")
    
    __table_args__ = (
        db.UniqueConstraint("class_id", "student_id", name="unique_class_enrollment"),
    )
    
    @property
    def attendance_rate(self):
        total_sessions = CourseSession.query.filter_by(class_id=self.class_id).count()
        if total_sessions == 0:
            return 0
        
        attended = Attendance.query\
            .join(CourseSession, CourseSession.id == Attendance.session_id)\
            .filter(CourseSession.class_id == self.class_id)\
            .filter(Attendance.student_id == self.student_id)\
            .filter(Attendance.status == 'present')\
            .count()
        
        return int((attended / total_sessions) * 100)
    
    def get_status_display(self):
        return EnrollmentStatus.get_display(self.status.value if self.status else 'pending')
    
    def __repr__(self):
        return f'<ClassEnrollment {self.class_id} - {self.student_id}>'


# ================================
# COURSE SESSION MODEL
# ================================

class CourseSession(db.Model):
    __tablename__ = "class_sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    title = db.Column(db.String(200))
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    location = db.Column(db.String(200))
    topic = db.Column(db.Text)
    materials = db.Column(db.Text)
    status = db.Column(db.Enum(SessionStatus), default=SessionStatus.SCHEDULED)
    is_cancelled = db.Column(db.Boolean, default=False)
    cancel_reason = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    class_obj = db.relationship("Class", foreign_keys=[class_id], back_populates="sessions")
    attendances = db.relationship("Attendance", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("SessionFile", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    
    @property
    def total_students(self):
        return ClassEnrollment.query.filter_by(class_id=self.class_id, status='active').count()
    
    @property
    def present_count(self):
        return self.attendances.filter_by(status='present').count()
    
    @property
    def absent_count(self):
        return self.attendances.filter_by(status='absent').count()
    
    @property
    def late_count(self):
        return self.attendances.filter_by(status='late').count()
    
    @property
    def excused_count(self):
        return self.attendances.filter_by(status='excused').count()
    
    @property
    def attendance_percentage(self):
        total = self.total_students
        if total == 0:
            return 0
        return int((self.present_count / total) * 100)
    
    def __repr__(self):
        return f'<CourseSession {self.id} - {self.session_date}>'


# ================================
# ATTENDANCE MODEL
# ================================

class Attendance(db.Model):
    __tablename__ = "attendances"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    late_minutes = db.Column(db.Integer, default=0)
    excuse = db.Column(db.Text)
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    session = db.relationship("CourseSession", foreign_keys=[session_id], back_populates="attendances")
    student = db.relationship("User", foreign_keys=[student_id], backref="attendances")
    marker = db.relationship("User", foreign_keys=[marked_by], backref="marked_attendances")
    
    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="unique_session_student_attendance"),
    )
    
    def get_status_display(self):
        return AttendanceStatus.get_display(self.status.value if self.status else 'absent')
    
    def __repr__(self):
        return f'<Attendance {self.session_id} - {self.student_id} - {self.status}>'


# ================================
# CLASS FILE MODEL
# ================================

class ClassFile(db.Model):
    __tablename__ = "class_files"
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # روابط
    class_obj = db.relationship("Class", foreign_keys=[class_id], back_populates="files")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_class_files")
    
    def __repr__(self):
        return f'<ClassFile {self.title}>'


# ================================
# SESSION FILE MODEL
# ================================

class SessionFile(db.Model):
    __tablename__ = "session_files"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # روابط
    session = db.relationship("CourseSession", foreign_keys=[session_id], back_populates="files")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_session_files")
    
    def __repr__(self):
        return f'<SessionFile {self.title}>'


# ================================
# QURAN CIRCLE MODELS (تنها یک بار)
# ================================

class QuranCircle(db.Model):
    __tablename__ = "quran_circles"  # توجه: نام جدول "quran_circles" (جمع)
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    teacher_name = db.Column(db.String(200), nullable=False)
    teacher_bio = db.Column(db.Text)
    teacher_image = db.Column(db.String(200))
    circle_type = db.Column(db.String(50), default="general")
    level = db.Column(db.String(50), default="beginner")
    days_of_week = db.Column(db.String(200))
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    location = db.Column(db.String(200))
    is_online = db.Column(db.Boolean, default=False)
    online_link = db.Column(db.String(500))
    capacity = db.Column(db.Integer)
    current_members = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # فیلدهای جدید برای سیستم درخواست و تأیید
    status = db.Column(db.String(20), default='pending')        # pending, approved, rejected
    rejection_reason = db.Column(db.String(255), nullable=True) # دلیل رد
    
    # روابط
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_circles")
    sessions = db.relationship("CircleSession", back_populates="circle", lazy="dynamic", cascade="all, delete-orphan")
    members = db.relationship("CircleMember", back_populates="circle", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("CircleFile", back_populates="circle", lazy="dynamic", cascade="all, delete-orphan")
    
    def is_full(self):
        return self.capacity and self.current_members >= self.capacity
    
    def remaining_capacity(self):
        if self.capacity:
            return self.capacity - self.current_members
        return None
    
    @property
    def next_session(self):
        from datetime import date
        return self.sessions.filter(CircleSession.session_date >= date.today())\
                            .order_by(CircleSession.session_date).first()
    
    @property
    def last_session(self):
        from datetime import date
        return self.sessions.filter(CircleSession.session_date < date.today())\
                            .order_by(CircleSession.session_date.desc()).first()
    
    @property
    def attendance_rate(self):
        total_members = self.members.filter_by(is_active=True).count()
        total_sessions = self.sessions.count()
        
        if total_members == 0 or total_sessions == 0:
            return 0
        
        total_attendances = SessionAttendance.query\
            .join(CircleSession, CircleSession.id == SessionAttendance.session_id)\
            .filter(CircleSession.circle_id == self.id)\
            .filter(SessionAttendance.attended == True)\
            .count()
        
        total_possible = total_members * total_sessions
        return int((total_attendances / total_possible) * 100)
    
    def __repr__(self):
        return f'<QuranCircle {self.name}>'


class CircleMember(db.Model):
    __tablename__ = "circle_members"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(50), default="member")
    notes = db.Column(db.Text)
    
    # روابط
    circle = db.relationship("QuranCircle", foreign_keys=[circle_id], back_populates="members")
    user = db.relationship("User", foreign_keys=[user_id], backref="circle_memberships")
    attendances = db.relationship("SessionAttendance", back_populates="member", lazy="dynamic")
    
    __table_args__ = (
        db.UniqueConstraint("circle_id", "user_id", name="unique_circle_member"),
    )
    
    @property
    def attendance_rate(self):
        total_sessions = CircleSession.query.filter_by(circle_id=self.circle_id).count()
        if total_sessions == 0:
            return 0
        attended = self.attendances.filter_by(attended=True).count()
        return int((attended / total_sessions) * 100)
    
    def __repr__(self):
        return f'<CircleMember {self.circle_id} - {self.user_id}>'


class CircleSession(db.Model):
    __tablename__ = "circle_sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    title = db.Column(db.String(200))
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    topic = db.Column(db.String(500))
    description = db.Column(db.Text)
    verses_reviewed = db.Column(db.Text)
    notes = db.Column(db.Text)
    homework = db.Column(db.Text)
    is_held = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    circle = db.relationship("QuranCircle", foreign_keys=[circle_id], back_populates="sessions")
    attendances = db.relationship("SessionAttendance", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    files = db.relationship("CircleSessionFile", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    
    @property
    def attendance_count(self):
        return self.attendances.filter_by(attended=True).count()
    
    @property
    def total_members(self):
        return CircleMember.query.filter_by(circle_id=self.circle_id, is_active=True).count()
    
    @property
    def attendance_percentage(self):
        total = self.total_members
        if total == 0:
            return 0
        return int((self.attendance_count / total) * 100)
    
    def __repr__(self):
        return f'<CircleSession {self.id} - {self.session_date}>'


class SessionAttendance(db.Model):
    __tablename__ = "session_attendances"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("circle_sessions.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("circle_members.id"), nullable=False)
    attended = db.Column(db.Boolean, default=False)
    excuse = db.Column(db.String(200))
    late_minutes = db.Column(db.Integer, default=0)
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    session = db.relationship("CircleSession", foreign_keys=[session_id], back_populates="attendances")
    member = db.relationship("CircleMember", foreign_keys=[member_id], back_populates="attendances")
    marker = db.relationship("User", foreign_keys=[marked_by], backref="marked_circle_attendances")
    
    __table_args__ = (
        db.UniqueConstraint("session_id", "member_id", name="unique_attendance"),
    )
    
    def __repr__(self):
        return f'<SessionAttendance {self.session_id} - {self.member_id}>'


class CircleFile(db.Model):
    __tablename__ = "circle_files"
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("quran_circles.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    download_count = db.Column(db.Integer, default=0)
    
    # روابط
    circle = db.relationship("QuranCircle", foreign_keys=[circle_id], back_populates="files")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_circle_files")
    
    def __repr__(self):
        return f'<CircleFile {self.title}>'


class CircleSessionFile(db.Model):
    __tablename__ = "circle_session_files"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("circle_sessions.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # روابط
    session = db.relationship("CircleSession", foreign_keys=[session_id], back_populates="files")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_circle_session_files")
    
    def __repr__(self):
        return f'<CircleSessionFile {self.title}>'


# ================================
# FCM TOKEN MODEL
# ================================

class UserFCMToken(db.Model):
    __tablename__ = "user_fcm_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fcm_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    user = db.relationship("User", foreign_keys=[user_id], backref="fcm_tokens")


# ================================
# VERIFICATION LOG MODEL
# ================================

class VerificationLog(db.Model):
    __tablename__ = "verification_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    performed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    user = db.relationship("User", foreign_keys=[user_id], backref="verification_logs")
    performer = db.relationship("User", foreign_keys=[performed_by], backref="performed_verifications")
    
    def __repr__(self):
        return f'<VerificationLog {self.user_id} - {self.action} by {self.performed_by}>'


# ================================
# BANNER MODEL
# ================================

class Banner(db.Model):
    __tablename__ = 'banners'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    link_url = db.Column(db.String(500), nullable=True)
    alt_text = db.Column(db.String(200), nullable=True)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Banner {self.title}>'

        # ================================
# COMPETITION MODELS
# ================================

class CompetitionCategory(enum.Enum):
    MEMORIZATION = "memorization"      # حفظ
    TARTEEL = "tarteel"                # ترتیل
    TAFSIR = "tafsir"                  # تفسیر
    AZAN = "azan"                      # اذان
    RECITATION = "recitation"          # تلاوت تحقیق
    OTHER = "other"

class Competition(db.Model):
    __tablename__ = "competitions"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum(CompetitionCategory), nullable=False)
    rules = db.Column(db.Text)                     # قوانین مسابقه
    evaluation_criteria = db.Column(db.Text)       # معیارهای ارزیابی
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime, nullable=False)
    max_participants = db.Column(db.Integer)
    current_participants = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_competitions")
    registrations = db.relationship("CompetitionRegistration", backref="competition", lazy="dynamic", cascade="all, delete-orphan")
    rounds = db.relationship("CompetitionRound", backref="competition", lazy="dynamic", cascade="all, delete-orphan")
    
    def is_full(self):
        return self.max_participants and self.current_participants >= self.max_participants
    
    def can_register(self):
        return self.is_active and not self.is_full() and datetime.utcnow() < self.registration_deadline
    
    def __repr__(self):
        return f'<Competition {self.title}>'

class CompetitionRegistration(db.Model):
    __tablename__ = "competition_registrations"
    
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="registered")  # registered, confirmed, rejected, disqualified
    notes = db.Column(db.Text)
    final_score = db.Column(db.Float, default=0)
    rank = db.Column(db.Integer)
    
    user = db.relationship("User", foreign_keys=[user_id], backref="competition_registrations")
    
    __table_args__ = (
        db.UniqueConstraint("competition_id", "user_id", name="unique_competition_registration"),
    )
    
    def __repr__(self):
        return f'<CompetitionRegistration {self.competition_id} - {self.user_id}>'

class CompetitionRound(db.Model):
    __tablename__ = "competition_rounds"
    
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    max_score = db.Column(db.Float, default=100)
    
    # روابط
    scores = db.relationship("JudgeScore", backref="round", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.UniqueConstraint("competition_id", "round_number", name="unique_round_number"),
    )
    
    def __repr__(self):
        return f'<CompetitionRound {self.competition_id} - R{self.round_number}>'

class JudgeScore(db.Model):
    __tablename__ = "judge_scores"
    
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("competition_rounds.id"), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey("competition_registrations.id"), nullable=False)
    judge_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text)
    scored_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # روابط
    registration = db.relationship("CompetitionRegistration", foreign_keys=[registration_id], backref="scores")
    judge = db.relationship("User", foreign_keys=[judge_id], backref="given_scores")
    
    __table_args__ = (
        db.UniqueConstraint("round_id", "registration_id", "judge_id", name="unique_judge_score"),
    )
    
    def __repr__(self):
        return f'<JudgeScore {self.round_id} - {self.registration_id} - {self.score}>'

# برای محاسبه خودکار لیدربورد می‌توانیم یک ویو یا متد در مدل داشته باشیم
def update_leaderboard(competition_id):
    """به‌روزرسانی نمرات نهایی و رتبه‌بندی شرکت‌کنندگان یک مسابقه"""
    registrations = CompetitionRegistration.query.filter_by(competition_id=competition_id).all()
    for reg in registrations:
        total_score = db.session.query(db.func.sum(JudgeScore.score)).filter_by(registration_id=reg.id).scalar() or 0
        reg.final_score = total_score
    db.session.commit()
    
    # محاسبه رتبه
    sorted_regs = CompetitionRegistration.query.filter_by(competition_id=competition_id).order_by(CompetitionRegistration.final_score.desc()).all()
    for idx, reg in enumerate(sorted_regs, 1):
        reg.rank = idx
    db.session.commit()

   # ============================================
# مدل‌های هوش مصنوعی قرآنی
# ============================================

class QuranQA(db.Model):
    __tablename__ = 'quran_qa'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    keywords = db.Column(db.String(500))
    answer = db.Column(db.Text, nullable=False)
    related_verses = db.Column(db.Text)
    category = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<QuranQA {self.question[:50]}>'


class UserQuranChat(db.Model):
    __tablename__ = 'user_quran_chats'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    related_verses = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", foreign_keys=[user_id], backref="quran_chats")
    
    def __repr__(self):
        return f'<UserQuranChat {self.user_id} - {self.created_at}>'


class QuranSuggestion(db.Model):
    __tablename__ = 'quran_suggestions'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50), nullable=False)
    verse_text = db.Column(db.Text, nullable=False)
    verse_translation = db.Column(db.Text, nullable=False)
    surah_name = db.Column(db.String(100))
    verse_number = db.Column(db.Integer)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<QuranSuggestion {self.mood} - {self.surah_name}:{self.verse_number}>'