# setup_quran_ai.py
"""
اسکریپت نصب و راه‌اندازی هوش مصنوعی قرآنی
"""

import subprocess
import sys

def install_requirements():
    """نصب پکیج‌های مورد نیاز"""
    packages = [
        'sentence-transformers',
        'hazm',
        'torch',
        'numpy',
        'transformers'
    ]
    
    print("📦 در حال نصب پکیج‌های مورد نیاز...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"   ✅ {package}")
        except Exception as e:
            print(f"   ❌ {package}: {e}")

def download_model():
    """دانلود مدل هوش مصنوعی"""
    print("\n🤖 در حال دانلود مدل هوش مصنوعی...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ مدل با موفقیت دانلود شد")
    except Exception as e:
        print(f"❌ خطا در دانلود مدل: {e}")

def initialize_database():
    """راه‌اندازی دیتابیس"""
    print("\n🗄️ در حال راه‌اندازی دیتابیس...")
    try:
        from quran_ai_complete import init_quran_ai_system
        ai = init_quran_ai_system()
        print("✅ دیتابیس هوش مصنوعی راه‌اندازی شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    print("="*50)
    print("🚀 نصب هوش مصنوعی قرآنی سِراج")
    print("="*50)
    
    install_requirements()
    download_model()
    initialize_database()
    
    print("\n✅ نصب کامل شد!")
    print("📝 برای استفاده، برنامه را مجدداً اجرا کنید: python app.py")