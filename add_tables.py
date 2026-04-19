# add_tables.py
from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'circle_requests' not in tables:
        print("در حال ایجاد جدول circle_requests...")
        db.session.execute(text("""
            CREATE TABLE circle_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                circle_type VARCHAR(50),
                level VARCHAR(50),
                meeting_days VARCHAR(200),
                meeting_time VARCHAR(50),
                meeting_location VARCHAR(300),
                duration_hours INTEGER DEFAULT 1,
                max_members INTEGER DEFAULT 20,
                status VARCHAR(20) DEFAULT 'pending',
                admin_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME,
                reviewed_by INTEGER,
                FOREIGN KEY (professor_id) REFERENCES users(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        """))
        print("✓ جدول circle_requests ایجاد شد")
    
    if 'circle_join_requests' not in tables:
        print("در حال ایجاد جدول circle_join_requests...")
        db.session.execute(text("""
            CREATE TABLE circle_join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                circle_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                motivation TEXT,
                experience TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                admin_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME,
                reviewed_by INTEGER,
                FOREIGN KEY (circle_id) REFERENCES quran_circles(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        """))
        print("✓ جدول circle_join_requests ایجاد شد")
    
    db.session.commit()
    print("✅ همه جدول‌ها با موفقیت ایجاد شدند!")