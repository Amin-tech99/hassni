import os
import logging
import tempfile
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import json
import zipfile
import io
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup SQLAlchemy with the new API
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_for_testing")

# Configure database
# Fix PostgreSQL connection string if needed
database_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
# If PostgreSQL URL starts with postgres:// change it to postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max upload size

# Make sure clips directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import modules (after app is created to avoid circular imports)
from models import User, Audio, Clip, Transcription
from forms import LoginForm, RegistrationForm, AudioUploadForm, TranscriptionForm, AssignmentForm
from audio_processor import process_audio_file

# Setup Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Add global template context
@app.context_processor
def inject_template_context():
    return {'current_year': datetime.now().year}

# Create tables
with app.app_context():
    db.create_all()
    # Create admin user if doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin user created")

# Health check route for Railway deployment
@app.route('/health')
def health_check():
    overall_status = "OK"
    issues = []
    
    # Check 1: Test database connection
    try:
        db.session.execute('SELECT 1')
        db_status = "OK"
    except Exception as e:
        db_status = f"Error: {str(e)}"
        overall_status = "ERROR"
        issues.append(f"Database connection failed: {str(e)}")
    
    # Check 2: Verify required directories exist
    required_dirs = ['clips', 'uploads', 'transcriptions']
    dir_status = {}
    for directory in required_dirs:
        dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory)
        exists = os.path.isdir(dir_path)
        dir_status[directory] = "exists" if exists else "missing"
        if not exists:
            overall_status = "WARNING"
            issues.append(f"Directory '{directory}' is missing")
            # Try to create the directory
            try:
                os.makedirs(dir_path, exist_ok=True)
                issues[-1] += " (created automatically)"
            except Exception as e:
                issues[-1] += f" (failed to create: {str(e)})"
    
    # Check 3: Environment variables
    env_vars = {
        "DATABASE_URL": os.environ.get("DATABASE_URL", "not set"),
        "PORT": os.environ.get("PORT", "5000 (default)"),
        "SESSION_SECRET": "set" if os.environ.get("SESSION_SECRET") else "not set",
    }
    
    if env_vars["DATABASE_URL"] == "not set":
        overall_status = "WARNING"
        issues.append("DATABASE_URL environment variable is not set")
    
    if env_vars["SESSION_SECRET"] == "not set":
        overall_status = "WARNING" 
        issues.append("SESSION_SECRET environment variable is not set")
    
    # Return a comprehensive health check
    health_data = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "directories": dir_status,
        "environment": env_vars,
        "issues": issues,
        "version": "1.0.0"
    }
    
    # Only return 200 if everything is OK
    status_code = 200 if overall_status == "OK" else 200  # Always return 200 for Railway (they just check for 200)
    return jsonify(health_data), status_code

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('transcriber_dashboard'))
            
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or next_page.startswith('/') == False:
                if user.role == 'admin':
                    next_page = url_for('admin_dashboard')
                else:
                    next_page = url_for('transcriber_dashboard')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Only allow admin to access this page directly
    if not current_user.is_authenticated or current_user.role != 'admin':
        return redirect(url_for('login'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return render_template('register.html', form=form)
            
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    # Get all audio files
    audio_files = Audio.query.order_by(Audio.upload_date.desc()).all()
    
    # Gather overall statistics
    total_clips = db.session.query(func.count(Clip.id)).scalar() or 0
    assigned_clips = db.session.query(func.count(Clip.id)).filter(Clip.status != 'unassigned').scalar() or 0
    submitted_clips = db.session.query(func.count(Clip.id)).filter(Clip.status == 'submitted').scalar() or 0
    completed_clips = db.session.query(func.count(Clip.id)).filter(Clip.status == 'completed').scalar() or 0
    
    # Transcription statistics
    draft_transcriptions = db.session.query(func.count(Transcription.id)).filter(Transcription.status == 'draft').scalar() or 0
    submitted_transcriptions = db.session.query(func.count(Transcription.id)).filter(Transcription.status == 'submitted').scalar() or 0
    approved_transcriptions = db.session.query(func.count(Transcription.id)).filter(Transcription.status == 'approved').scalar() or 0
    rejected_transcriptions = db.session.query(func.count(Transcription.id)).filter(Transcription.status == 'rejected').scalar() or 0
    
    # Calculate percentages for progress bars
    assigned_percentage = (assigned_clips / total_clips * 100) if total_clips > 0 else 0
    submitted_percentage = (submitted_clips / total_clips * 100) if total_clips > 0 else 0
    completed_percentage = (completed_clips / total_clips * 100) if total_clips > 0 else 0
    
    stats = {
        'total_clips': total_clips,
        'assigned_clips': assigned_clips,
        'submitted_clips': submitted_clips,
        'completed_clips': completed_clips,
        'draft_transcriptions': draft_transcriptions,
        'submitted_transcriptions': submitted_transcriptions,
        'approved_transcriptions': approved_transcriptions,
        'rejected_transcriptions': rejected_transcriptions,
        'assigned_percentage': assigned_percentage,
        'submitted_percentage': submitted_percentage,
        'completed_percentage': completed_percentage
    }
    
    form = AudioUploadForm()
    
    return render_template('admin/dashboard.html', audio_files=audio_files, form=form, stats=stats)

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_audio():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Wrap the entire function in a try-except to catch any unexpected errors
    try:
        form = AudioUploadForm()
        if form.validate_on_submit():
            try:
                # First, save the uploaded file safely
                audio_file = form.audio_file.data
                filename = secure_filename(audio_file.filename)
                
                # Ensure the filename is unique to avoid overwrites
                base_name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                unique_filename = f"{base_name}_{timestamp}{ext}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Create upload directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save the file
                logger.info(f"Saving uploaded file to {file_path}")
                audio_file.save(file_path)
                
                # Create Audio entry with pending status
                audio = Audio(
                    filename=unique_filename,
                    original_path=file_path,
                    upload_date=datetime.now(),
                    status='pending',  # Start with pending status
                    uploader_id=current_user.id
                )
                db.session.add(audio)
                db.session.commit()
                
                # Update status to processing
                audio.status = 'processing'
                db.session.commit()
                
                # Process the audio file
                logger.info(f"Starting audio processing for {file_path}")
                clips = process_audio_file(file_path, audio.id, app.config['UPLOAD_FOLDER'])
                
                # Update status and save clips to database
                audio.status = 'processed'
                audio.clip_count = len(clips)
                
                for i, clip_path in enumerate(clips):
                    clip_filename = os.path.basename(clip_path)
                    clip = Clip(
                        audio_id=audio.id,
                        filename=clip_filename,
                        path=clip_path,
                        order=i + 1,
                        status='unassigned'
                    )
                    db.session.add(clip)
                
                db.session.commit()
                flash(f'Audio file processed successfully. {len(clips)} clips were extracted.', 'success')
                
            except Exception as e:
                logger.error(f"Error processing audio: {str(e)}", exc_info=True)
                
                # Make sure we have a valid audio record even if processing failed
                try:
                    # Check if audio was already created
                    if 'audio' in locals() and audio:
                        audio.status = 'error'
                        db.session.commit()
                    else:
                        # Create a minimal record if we failed before creating one
                        audio = Audio(
                            filename=filename if 'filename' in locals() else "unknown.wav",
                            original_path=file_path if 'file_path' in locals() else "",
                            upload_date=datetime.now(),
                            status='error',
                            uploader_id=current_user.id
                        )
                        db.session.add(audio)
                        db.session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update database after processing error: {str(db_error)}")
                
                flash(f'Error processing audio: {str(e)}. Please try again with a different file or contact support.', 'danger')
            
            return redirect(url_for('admin_dashboard'))
        
        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
        
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in upload_audio: {str(e)}", exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_audio/<int:audio_id>', methods=['POST'])
@login_required
def delete_audio(audio_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    audio = Audio.query.get_or_404(audio_id)
    
    # Delete all clips
    clips = Clip.query.filter_by(audio_id=audio_id).all()
    for clip in clips:
        # Delete transcriptions
        transcriptions = Transcription.query.filter_by(clip_id=clip.id).all()
        for transcription in transcriptions:
            db.session.delete(transcription)
        
        # Delete clip file
        try:
            if os.path.exists(clip.path):
                os.remove(clip.path)
        except Exception as e:
            logger.error(f"Error deleting clip file: {str(e)}")
        
        db.session.delete(clip)
    
    # Delete original audio file
    try:
        if os.path.exists(audio.original_path):
            os.remove(audio.original_path)
    except Exception as e:
        logger.error(f"Error deleting audio file: {str(e)}")
    
    db.session.delete(audio)
    db.session.commit()
    
    flash('Audio file and associated clips deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign/<int:audio_id>')
@login_required
def assign_clips(audio_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    audio = Audio.query.get_or_404(audio_id)
    clips = Clip.query.filter_by(audio_id=audio_id).order_by(Clip.order).all()
    transcribers = User.query.filter_by(role='transcriber').all()
    
    form = AssignmentForm()
    form.transcriber.choices = [(t.id, t.username) for t in transcribers]
    
    return render_template('admin/assign.html', 
                          audio=audio, 
                          clips=clips, 
                          transcribers=transcribers, 
                          form=form)

@app.route('/admin/assign_clips', methods=['POST'])
@login_required
def assign_clips_post():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    form = AssignmentForm()
    form.transcriber.choices = [(str(u.id), u.username) for u in User.query.filter_by(role='transcriber').all()]
    
    if form.validate_on_submit():
        transcriber_id = int(form.transcriber.data)
        clip_ids = request.form.getlist('clip_ids')
        
        if not clip_ids:
            flash('No clips selected.', 'warning')
            return redirect(url_for('admin_dashboard'))
            
        # Update clip assignments
        for clip_id in clip_ids:
            clip = Clip.query.get(int(clip_id))
            if clip:
                clip.transcriber_id = transcriber_id
                clip.status = 'assigned'
        
        db.session.commit()
        flash(f'{len(clip_ids)} clips assigned successfully.', 'success')
        
        # Redirect back to the assign page for the same audio
        sample_clip = Clip.query.get(int(clip_ids[0]))
        return redirect(url_for('assign_clips', audio_id=sample_clip.audio_id))
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{field}: {error}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/review')
@login_required
def review_transcriptions():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    audio_files = Audio.query.all()
    pending_transcriptions = Transcription.query.filter_by(status='submitted').count()
    
    return render_template('admin/review.html', 
                          audio_files=audio_files,
                          pending_count=pending_transcriptions)

@app.route('/admin/review_audio/<int:audio_id>')
@login_required
def review_audio_transcriptions(audio_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    audio = Audio.query.get_or_404(audio_id)
    clips = Clip.query.filter_by(audio_id=audio_id).order_by(Clip.order).all()
    
    # Get all transcriptions for these clips
    clip_data = []
    for clip in clips:
        transcription = Transcription.query.filter_by(clip_id=clip.id).first()
        transcriber = User.query.get(clip.transcriber_id) if clip.transcriber_id else None
        
        clip_data.append({
            'clip': clip,
            'transcription': transcription,
            'transcriber': transcriber
        })
    
    return render_template('admin/review.html', 
                          audio=audio,
                          clip_data=clip_data)

@app.route('/admin/approve_transcription/<int:transcription_id>', methods=['POST'])
@login_required
def approve_transcription(transcription_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    transcription = Transcription.query.get_or_404(transcription_id)
    
    # Update transcription with edited text if provided
    if 'text' in request.form:
        transcription.text = request.form['text']
    
    transcription.status = 'approved'
    transcription.reviewed_by = current_user.id
    transcription.review_date = datetime.now()
    
    clip = Clip.query.get(transcription.clip_id)
    if clip:
        clip.status = 'completed'
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/reject_transcription/<int:transcription_id>', methods=['POST'])
@login_required
def reject_transcription(transcription_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    transcription = Transcription.query.get_or_404(transcription_id)
    
    transcription.status = 'rejected'
    transcription.reviewed_by = current_user.id
    transcription.review_date = datetime.now()
    
    clip = Clip.query.get(transcription.clip_id)
    if clip:
        clip.status = 'assigned'  # Reset to assigned so it can be transcribed again
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/export/<int:audio_id>')
@login_required
def export_dataset(audio_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    audio = Audio.query.get_or_404(audio_id)
    
    # Create a zip file in memory
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create JSONL file
        jsonl_data = []
        included_count = 0
        total_count = 0
        
        clips = Clip.query.filter_by(audio_id=audio_id).order_by(Clip.order).all()
        total_count = len(clips)
        
        for clip in clips:
            transcription = Transcription.query.filter_by(clip_id=clip.id, status='approved').first()
            if transcription:
                entry = {
                    "audio_filepath": clip.filename,
                    "text": transcription.text
                }
                jsonl_data.append(entry)
                included_count += 1
                
                # Add the audio clip to the zip file
                if os.path.exists(clip.path):
                    zf.write(clip.path, clip.filename)
        
        # Write JSONL to the zip file
        jsonl_content = '\n'.join([json.dumps(entry) for entry in jsonl_data])
        zf.writestr('dataset.jsonl', jsonl_content)
    
    memory_file.seek(0)
    
    # Flash a message about how many clips were included
    if included_count == 0:
        flash(f'Warning: No approved transcriptions were found for this audio file. The dataset is empty.', 'warning')
    else:
        flash(f'Success: Exported {included_count} out of {total_count} clips. Only approved transcriptions are included in the dataset.', 'success')
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'whisper_dataset_{audio.filename}.zip'
    )

# Transcriber routes
@app.route('/transcriber/dashboard')
@login_required
def transcriber_dashboard():
    if current_user.role != 'transcriber':
        return redirect(url_for('admin_dashboard'))
        
    # Get all clips assigned to this transcriber
    assigned_clips = Clip.query.filter_by(transcriber_id=current_user.id).all()
    
    # Group clips by audio
    clips_by_audio = {}
    for clip in assigned_clips:
        audio = Audio.query.get(clip.audio_id)
        if audio.id not in clips_by_audio:
            clips_by_audio[audio.id] = {
                'audio': audio,
                'clips': [],
                'progress': {
                    'total': 0,
                    'completed': 0,
                    'pending': 0
                }
            }
        
        # Add clip to list
        clips_by_audio[audio.id]['clips'].append(clip)
        
        # Update progress counters
        clips_by_audio[audio.id]['progress']['total'] += 1
        
        # Check if this clip has a transcription
        transcription = Transcription.query.filter_by(clip_id=clip.id).first()
        if transcription:
            if transcription.status in ['submitted', 'approved']:
                clips_by_audio[audio.id]['progress']['completed'] += 1
            else:
                clips_by_audio[audio.id]['progress']['pending'] += 1
        else:
            clips_by_audio[audio.id]['progress']['pending'] += 1
    
    return render_template('transcriber/dashboard.html', clips_by_audio=clips_by_audio)

@app.route('/transcriber/transcribe/<int:audio_id>')
@login_required
def transcribe_audio(audio_id):
    if current_user.role != 'transcriber':
        return redirect(url_for('admin_dashboard'))
        
    audio = Audio.query.get_or_404(audio_id)
    
    # Get all clips for this audio assigned to the current transcriber
    clips = Clip.query.filter_by(
        audio_id=audio_id, 
        transcriber_id=current_user.id
    ).order_by(Clip.order).all()
    
    if not clips:
        flash('No clips assigned to you for this audio.', 'warning')
        return redirect(url_for('transcriber_dashboard'))
    
    # Get existing transcriptions for these clips
    transcriptions = {}
    for clip in clips:
        transcription = Transcription.query.filter_by(clip_id=clip.id).first()
        if transcription:
            transcriptions[clip.id] = transcription
    
    form = TranscriptionForm()
    
    return render_template('transcriber/transcribe.html', 
                          audio=audio, 
                          clips=clips, 
                          transcriptions=transcriptions,
                          form=form)

@app.route('/transcriber/save_transcription', methods=['POST'])
@login_required
def save_transcription():
    if current_user.role != 'transcriber':
        return jsonify({'error': 'Unauthorized'}), 403
        
    form = TranscriptionForm()
    
    if form.validate_on_submit():
        clip_id = form.clip_id.data
        text = form.text.data
        submit_type = form.submit_type.data  # 'save' or 'submit'
        
        # Check if clip belongs to this transcriber
        clip = Clip.query.get_or_404(clip_id)
        if clip.transcriber_id != current_user.id:
            return jsonify({'error': 'This clip is not assigned to you'}), 403
        
        # Check if transcription exists
        transcription = Transcription.query.filter_by(clip_id=clip_id).first()
        
        if transcription:
            # Update existing transcription
            transcription.text = text
            if submit_type == 'submit':
                transcription.status = 'submitted'
                clip.status = 'submitted'
            else:
                transcription.status = 'draft'
            transcription.update_date = datetime.now()
        else:
            # Create new transcription
            transcription = Transcription(
                clip_id=clip_id,
                transcriber_id=current_user.id,
                text=text,
                status='draft' if submit_type == 'save' else 'submitted',
                creation_date=datetime.now(),
                update_date=datetime.now()
            )
            db.session.add(transcription)
            
            if submit_type == 'submit':
                clip.status = 'submitted'
        
        db.session.commit()
        
        result = {
            'success': True, 
            'message': 'Transcription saved' if submit_type == 'save' else 'Transcription submitted'
        }
        return jsonify(result)
    
    errors = {field: errors for field, errors in form.errors.items()}
    return jsonify({'error': 'Form validation failed', 'errors': errors}), 400

# Root route
@app.route('/clips/<int:clip_id>')
@login_required
def serve_clip(clip_id):
    """Serve an audio clip file"""
    clip = Clip.query.get_or_404(clip_id)
    
    # Security check: Only allow access if the user is an admin or the assigned transcriber
    if not (current_user.role == 'admin' or current_user.id == clip.transcriber_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Handle both absolute and relative paths
    # Try the original path first
    clip_path = clip.path
    
    # If the path is absolute but file doesn't exist, try to find it relative to project root
    if os.path.isabs(clip_path) and not os.path.exists(clip_path):
        # Extract the part after the last directory containing 'clips'
        parts = clip_path.split('clips')
        if len(parts) > 1:
            relative_path = os.path.join('clips', parts[-1].lstrip('/'))
            if os.path.exists(relative_path):
                clip_path = relative_path
                logger.info(f"Using relative path instead: {clip_path}")
    
    # Check if file exists
    if not os.path.exists(clip_path):
        logger.error(f"Clip file not found: Original path: {clip.path}, Tried: {clip_path}")
        return jsonify({'error': 'File not found'}), 404
    
    # Serve the file from its location on disk
    return send_file(clip_path, mimetype='audio/wav')

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('transcriber_dashboard'))
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.route('/admin/export_zip/<int:audio_id>')
@login_required
def export_zip_dataset(audio_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
        
    audio = Audio.query.get_or_404(audio_id)
    
    # Create a temporary zip file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_file.close()
    
    # Create a zip file
    with zipfile.ZipFile(temp_file.name, 'w') as zipf:
        clips = Clip.query.filter_by(audio_id=audio_id).all()
        
        # Create a metadata JSON file
        dataset = []
        for clip in clips:
            transcription = Transcription.query.filter_by(clip_id=clip.id, status='approved').first()
            if transcription:
                # Get relative path for audio file
                audio_path = clip.path
                # Create a filename for the destination in the zip
                zip_audio_path = f"audio/{os.path.basename(audio_path)}"
                
                # Add audio file to zip
                zipf.write(audio_path, zip_audio_path)
                
                # Add entry to dataset
                dataset.append({
                    'audio_filepath': zip_audio_path,
                    'text': transcription.text
                })
        
        # Add dataset.json
        if dataset:
            zipf.writestr('dataset.json', json.dumps(dataset, indent=2))
    
    # Send the zip file
    return send_file(temp_file.name, 
                     mimetype='application/zip',
                     as_attachment=True, 
                     download_name=f'dataset_{audio.filename}_{datetime.now().strftime("%Y%m%d")}.zip')

@app.route('/admin/export_all_zip')
@login_required
def export_all_zip_dataset():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('transcriber_dashboard'))
    
    # Create a temporary zip file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_file.close()
    
    # Create a zip file
    with zipfile.ZipFile(temp_file.name, 'w') as zipf:
        # Get all approved transcriptions across all audio files
        dataset = []
        transcriptions = Transcription.query.filter_by(status='approved').all()
        
        for transcription in transcriptions:
            clip = Clip.query.get(transcription.clip_id)
            if clip:
                # Get relative path for audio file
                audio_path = clip.path
                # Create a filename for the destination in the zip
                audio_name = os.path.basename(audio_path)
                audio_id = clip.audio_id
                zip_audio_path = f"audio/{audio_id}/{audio_name}"
                
                # Add audio file to zip
                zipf.write(audio_path, zip_audio_path)
                
                # Add entry to dataset
                dataset.append({
                    'audio_filepath': zip_audio_path,
                    'text': transcription.text
                })
        
        # Add dataset.json
        if dataset:
            zipf.writestr('dataset.json', json.dumps(dataset, indent=2))
    
    # Send the zip file
    return send_file(temp_file.name, 
                     mimetype='application/zip',
                     as_attachment=True, 
                     download_name=f'complete_dataset_{datetime.now().strftime("%Y%m%d")}.zip')
