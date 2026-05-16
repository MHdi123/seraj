from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class AhkamForm(FlaskForm):
    title = StringField('عنوان حکم', validators=[DataRequired(), Length(min=3, max=200)])
    category = SelectField('دسته‌بندی', choices=[
        ('نماز', 'احکام نماز'),
        ('روزه', 'احکام روزه'),
        ('خمس', 'خمس و زکات'),
        ('زکات', 'زکات'),
        ('محرمات', 'محرمات'),
        ('طهارت', 'احکام طهارت'),
        ('معاملات', 'معاملات')
    ], validators=[DataRequired()])
    ruling_type = SelectField('نوع حکم', choices=[
        ('واجب', 'واجب'),
        ('مستحب', 'مستحب'),
        ('حرام', 'حرام'),
        ('مکروه', 'مکروه'),
        ('مباح', 'مباح')
    ], validators=[DataRequired()])
    short_description = TextAreaField('خلاصه حکم', validators=[DataRequired(), Length(max=300)])
    full_content = TextAreaField('متن کامل حکم', validators=[DataRequired()])
    source = StringField('منبع', validators=[Length(max=200)])
    marja = StringField('مرجع تقلید', validators=[Length(max=100)])
    is_active = BooleanField('فعال', default=True)
    submit = SubmitField('ذخیره')