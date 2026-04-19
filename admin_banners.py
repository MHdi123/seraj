from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from models import db, Banner
from datetime import datetime

admin_banners_bp = Blueprint('admin_banners', __name__, url_prefix='/admin/banners')

# تنظیمات آپلود
UPLOAD_FOLDER = 'static/uploads/banners'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_banners_bp.route('/')
@login_required
def banners_list():
    # فقط ادمین دسترسی داشته باشد
    if current_user.role != 'admin':
        flash('شما دسترسی به این بخش ندارید', 'danger')
        return redirect(url_for('index'))
    
    banners = Banner.query.order_by(Banner.order, Banner.id).all()
    return render_template('admin/banners.html', banners=banners)

@admin_banners_bp.route('/add', methods=['POST'])
@login_required
def add_banner():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'دسترسی ندارید'}), 403
    
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
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_url = f'/{UPLOAD_FOLDER}/{filename}'
    
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

@admin_banners_bp.route('/edit/<int:banner_id>', methods=['POST'])
@login_required
def edit_banner(banner_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'دسترسی ندارید'}), 403
    
    banner = Banner.query.get_or_404(banner_id)
    
    banner.title = request.form.get('title', banner.title)
    banner.link_url = request.form.get('link_url')
    banner.alt_text = request.form.get('alt_text')
    banner.order = int(request.form.get('order', banner.order))
    
    # آپلود تصویر جدید
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            # حذف تصویر قدیمی (اختیاری)
            if banner.image_url and os.path.exists(banner.image_url[1:]):
                try:
                    os.remove(banner.image_url[1:])
                except:
                    pass
            
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            banner.image_url = f'/{UPLOAD_FOLDER}/{filename}'
    
    # آدرس تصویر از ورودی
    if request.form.get('image_url'):
        banner.image_url = request.form.get('image_url')
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'بنر با موفقیت ویرایش شد'})

@admin_banners_bp.route('/toggle/<int:banner_id>', methods=['POST'])
@login_required
def toggle_banner(banner_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'دسترسی ندارید'}), 403
    
    banner = Banner.query.get_or_404(banner_id)
    banner.is_active = not banner.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': banner.is_active})

@admin_banners_bp.route('/delete/<int:banner_id>', methods=['POST'])
@login_required
def delete_banner(banner_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'دسترسی ندارید'}), 403
    
    banner = Banner.query.get_or_404(banner_id)
    
    # حذف فایل تصویر
    if banner.image_url and os.path.exists(banner.image_url[1:]):
        try:
            os.remove(banner.image_url[1:])
        except:
            pass
    
    db.session.delete(banner)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'بنر با موفقیت حذف شد'})

@admin_banners_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_banners():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'دسترسی ندارید'}), 403
    
    data = request.get_json()
    orders = data.get('orders', [])
    
    for item in orders:
        banner = Banner.query.get(item['id'])
        if banner:
            banner.order = item['order']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'ترتیب بنرها ذخیره شد'})