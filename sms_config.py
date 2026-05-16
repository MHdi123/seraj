# sms_config.py
import requests
import json
from datetime import datetime

class SMSConfig:
    # ==================== تنظیمات حساب کاربری شما ====================
    API_KEY = "HcGIdAQpaEUBq5x1QK3gMUDs9zaIAUTC34DVguYdDg7oKvFP"
    LINE_NUMBER = "30002128010714"  # شماره خطی که از آن پیامک ارسال می‌شود
    
    # ==================== آدرس‌های API ====================
    BASE_URL = "https://api.sms.ir/v1"
    SEND_URL = f"{BASE_URL}/send"
    LINE_URL = f"{BASE_URL}/line"
    CREDIT_URL = f"{BASE_URL}/credit"
    
    @classmethod
    def get_headers(cls):
        """ایجاد هدرهای مورد نیاز برای درخواست به API"""
        return {
            "X-API-KEY": cls.API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @classmethod
    def send_sms(cls, mobile, message):
        """
        ارسال پیامک با استفاده از API رسمی sms.ir
        
        بازگشت: (success: bool, response_data: dict/str)
        """
        try:
            # حذف صفر اول و استانداردسازی شماره
            if mobile.startswith('0'):
                mobile = mobile[1:]
            if not mobile.startswith('98'):
                mobile = '98' + mobile
            
            payload = {
                "mobile": mobile,
                "message": message,
                "lineNumber": cls.LINE_NUMBER,
                "sendDate": None  # ارسال فوری
            }
            
            headers = cls.get_headers()
            
            print(f"📡 در حال ارسال به API sms.ir...")
            print(f"📱 شماره مقصد: {mobile}")
            print(f"📝 متن پیام: {message[:100]}...")
            
            response = requests.post(
                cls.SEND_URL,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 1:  # موفق
                    print(f"✅ پیامک با موفقیت ارسال شد. ID: {result.get('data', {}).get('messageId')}")
                    return True, result
                else:
                    error_msg = result.get("message", "خطای ناشناخته")
                    print(f"❌ خطا از سمت سرویس: {error_msg}")
                    return False, error_msg
            else:
                print(f"❌ خطای HTTP: {response.status_code}")
                return False, f"HTTP Error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            print("❌ خطا: زمان درخواست به پایان رسید")
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            print("❌ خطا: مشکل در اتصال به اینترنت")
            return False, "Connection error"
        except Exception as e:
            print(f"❌ خطای غیرمنتظره: {str(e)}")
            return False, str(e)
    
    @classmethod
    def get_credit(cls):
        """
        دریافت اعتبار باقیمانده حساب
        
        بازگشت: (success: bool, credit: float/str)
        """
        try:
            response = requests.get(
                cls.CREDIT_URL,
                headers=cls.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 1:
                    credit = result.get("data", {}).get("credit", 0)
                    print(f"💰 اعتبار باقیمانده: {credit} تومان")
                    return True, credit
                else:
                    return False, result.get("message", "خطا در دریافت اعتبار")
            else:
                return False, f"HTTP Error: {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def format_verification_message(cls, user_name, is_approved, rejection_reason=None):
        """فرمت متن پیامک تأیید یا رد (بهینه شده برای sms.ir)"""
        
        if is_approved:
            return f"""✅ حساب کاربری شما در سامانه سراج تأیید شد.

استاد گرامی {user_name}

اکنون می‌توانید وارد پنل شوید:
https://seraj.ir/login

موفق باشید.
سامانه سراج - ترویج معارف قرآنی"""
        else:
            reason_text = f"\nدلیل: {rejection_reason}" if rejection_reason else ""
            return f"""❌ درخواست همکاری شما در سامانه سراج تأیید نشد.

استاد گرامی {user_name}{reason_text}

در صورت نیاز با پشتیبانی تماس بگیرید:
021-12345678

سامانه سراج"""
    
    @classmethod
    def format_circle_message(cls, circle_name, is_approved, rejection_reason=None):
        """فرمت پیامک تأیید/رد حلقه تلاوت"""
        
        if is_approved:
            return f"""✅ حلقه تلاوت "{circle_name}" تأیید شد.

می‌توانید جلسات را برنامه‌ریزی کنید:
https://seraj.ir/professor/circles

موفق باشید.
سامانه سراج"""
        else:
            return f"""❌ حلقه تلاوت "{circle_name}" تأیید نشد.

دلیل: {rejection_reason or 'اطلاعات ناقص'}

برای اصلاح و ارسال مجدد اقدام کنید.
سامانه سراج"""