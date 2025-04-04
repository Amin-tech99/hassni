import os
import logging
from app import app, db
from models import Clip, Audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_clip_paths():
    """
    Fix paths in clip records to ensure they are relative (for Railway deployment compatibility).
    Also checks for and corrects any other path-related issues.
    
    Returns:
        int: Number of clips fixed
    """
    with app.app_context():
        logger.info("Starting clip paths fix migration...")
        
        # Get all clips
        clips = Clip.query.all()
        fixed_count = 0
        error_count = 0
        
        for clip in clips:
            original_path = clip.path
            needs_update = False
            
            # Case 1: Fix absolute paths
            if os.path.isabs(original_path):
                # Extract the part after the last directory containing 'clips'
                if '/clips/' in original_path:
                    parts = original_path.split('clips')
                    if len(parts) > 1:
                        relative_path = os.path.join('clips', parts[-1].lstrip('/'))
                        clip.path = relative_path
                        needs_update = True
                # Handle other absolute paths that might not contain 'clips'
                else:
                    # Get just the filename and put it in the clips directory
                    filename = os.path.basename(original_path)
                    
                    # Find the audio record to get the audio_id
                    audio = Audio.query.get(clip.audio_id)
                    if audio:
                        # Make a path like 'clips/audio_1/clip_name.wav'
                        relative_path = os.path.join('clips', f'audio_{audio.id}', filename)
                        clip.path = relative_path
                        needs_update = True
            
            # Case 2: Fix malformed paths (e.g., double slashes, backslashes in Unix)
            if '\\' in clip.path and os.name != 'nt':  # Convert Windows paths on Unix
                clip.path = clip.path.replace('\\', '/')
                needs_update = True
            
            if '//' in clip.path:  # Fix double slashes
                clip.path = clip.path.replace('//', '/')
                needs_update = True
            
            # Case 3: Path doesn't start with 'clips' but should
            if not clip.path.startswith('clips/') and not clip.path.startswith('./clips/'):
                # If it's just a filename, add clips/audio_id/ prefix
                if '/' not in clip.path and '\\' not in clip.path:
                    audio = Audio.query.get(clip.audio_id)
                    if audio:
                        clip.path = os.path.join('clips', f'audio_{audio.id}', clip.path)
                        needs_update = True
            
            # Case 4: Check for existence of file and correct if possible
            if needs_update or not os.path.exists(clip.path):
                # First check if the file exists at the corrected path
                if os.path.exists(clip.path):
                    # Great, the path is now correct and file exists
                    pass
                else:
                    # File doesn't exist at the corrected path
                    # Try a few variations to find it
                    variations = [
                        # Try with app root path
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), clip.path),
                        # Try with different clips folder formats
                        os.path.join('clips', f'audio_{clip.audio_id}', os.path.basename(clip.path)),
                        os.path.join('clips', str(clip.audio_id), os.path.basename(clip.path)),
                    ]
                    
                    for var_path in variations:
                        if os.path.exists(var_path):
                            # Found it! Use the relative version
                            rel_parts = var_path.split(os.path.dirname(os.path.abspath(__file__)))
                            if len(rel_parts) > 1:
                                # Convert to relative path
                                rel_path = rel_parts[1].lstrip('/')
                                clip.path = rel_path
                            else:
                                # If can't make relative, use as is but log it
                                clip.path = var_path
                                logger.warning(f"Could not make path relative for clip {clip.id}: {var_path}")
                            
                            needs_update = True
                            break
            
            # Update if needed and log the change
            if needs_update:
                logger.info(f"Fixing clip {clip.id} path from '{original_path}' to '{clip.path}'")
                fixed_count += 1
            
            # Final check - if the file still doesn't exist
            if not os.path.exists(clip.path):
                logger.error(f"Could not find file for clip {clip.id} at path '{clip.path}'")
                error_count += 1
        
        # Commit changes if any were made
        if fixed_count > 0:
            db.session.commit()
            logger.info(f"Migration complete. Fixed {fixed_count} clip paths. Errors: {error_count}")
        else:
            logger.info("No clips needed path fixing.")
        
        return fixed_count

if __name__ == "__main__":
    # When run as a script, show more detailed logs and return error code on problems
    try:
        fixed = fix_clip_paths()
        print(f"Fixed {fixed} clip paths. Done!")
    except Exception as e:
        logger.exception("Error running clip path fix")
        exit(1)