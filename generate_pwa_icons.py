# generate_pwa_icons.py
from PIL import Image
import os

def generate_icons():
    """تولید آیکون‌های PWA از لوگوی اصلی"""
    
    # مسیر لوگوی اصلی
    source_logo = 'static/logo/12.png'
    
    if not os.path.exists(source_logo):
        print(f"❌ لوگوی اصلی پیدا نشد: {source_logo}")
        return
    
    # پوشه مقصد
    icons_dir = 'static/logo'
    os.makedirs(icons_dir, exist_ok=True)
    
    # سایزهای مورد نیاز PWA
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # باز کردن تصویر اصلی
    with Image.open(source_logo) as img:
        # اگر تصویر مربعی نیست، آن را مربعی کن
        width, height = img.size
        if width != height:
            # برش به مرکز برای مربعی کردن
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            img = img.crop((left, top, right, bottom))
        
        # تولید آیکون‌ها در سایزهای مختلف
        for size in icon_sizes:
            output_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
            
            # تغییر اندازه با حفظ کیفیت
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            
            # ذخیره با کیفیت بالا
            resized.save(output_path, 'PNG', optimize=True)
            print(f"✅ آیکون {size}x{size} ایجاد شد: {output_path}")

if __name__ == '__main__':
    generate_icons()