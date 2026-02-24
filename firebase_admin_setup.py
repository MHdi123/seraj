# firebase_admin_setup.py
import firebase_admin
from firebase_admin import credentials, messaging

# مسیر فایل کلید JSON که گرفتی
cred_path = r"F:\seraj\firebase-adminsdk.json"

# ساخت credential و اتصال به Firebase
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

def send_notification(token, title, body):
    """
    ارسال پیام به یک کاربر
    """
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token
    )
    try:
        response = messaging.send(message)
        print(f"پیام ارسال شد: {response}")
    except Exception as e:
        print("خطا در ارسال پیام:", e)