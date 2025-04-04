from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('transcriber', 'Transcriber'), ('admin', 'Admin')])
    submit = SubmitField('Register User')

class AudioUploadForm(FlaskForm):
    audio_file = FileField('Audio File (.wav format only)', validators=[
        FileRequired(),
        FileAllowed(['wav'], 'WAV files only!')
    ])
    submit = SubmitField('Upload & Process')

class TranscriptionForm(FlaskForm):
    clip_id = HiddenField('Clip ID', validators=[DataRequired()])
    text = TextAreaField('Transcription', validators=[DataRequired()])
    submit_type = HiddenField('Submit Type', validators=[DataRequired()])  # 'save' or 'submit'
    submit = SubmitField('Save')

class AssignmentForm(FlaskForm):
    transcriber = SelectField('Assign to Transcriber', choices=[], validators=[DataRequired()])
    submit = SubmitField('Assign Selected Clips')
