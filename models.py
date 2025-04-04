from datetime import datetime
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='transcriber')  # 'admin' or 'transcriber'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    uploaded_audio = db.relationship('Audio', backref='uploader', lazy=True, foreign_keys='Audio.uploader_id')
    assigned_clips = db.relationship('Clip', backref='transcriber', lazy=True, foreign_keys='Clip.transcriber_id')
    transcriptions = db.relationship('Transcription', backref='transcriber', lazy=True, foreign_keys='Transcription.transcriber_id')
    reviews = db.relationship('Transcription', backref='reviewer', lazy=True, foreign_keys='Transcription.reviewed_by')

class Audio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(50), default='pending')  # pending, processing, processed, error
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clip_count = db.Column(db.Integer, default=0)
    
    # Relationships
    clips = db.relationship('Clip', backref='audio', lazy=True, cascade="all, delete-orphan")

class Clip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audio_id = db.Column(db.Integer, db.ForeignKey('audio.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=False)  # Order in the original audio
    status = db.Column(db.String(50), default='unassigned')  # unassigned, assigned, submitted, completed
    transcriber_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    transcription = db.relationship('Transcription', backref='clip', lazy=True, cascade="all, delete-orphan", uselist=False)

class Transcription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clip_id = db.Column(db.Integer, db.ForeignKey('clip.id'), nullable=False)
    transcriber_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='draft')  # draft, submitted, approved, rejected
    creation_date = db.Column(db.DateTime, default=datetime.now)
    update_date = db.Column(db.DateTime, default=datetime.now)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    review_date = db.Column(db.DateTime, nullable=True)
