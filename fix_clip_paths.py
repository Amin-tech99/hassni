import os
import logging
from app import app, db
from models import Clip, Audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_clip_paths():
    with app.app_context():
        logger.info("Starting clip paths fix migration...")
        
        # Get all clips
        clips = Clip.query.all()
        fixed_count = 0
        
        for clip in clips:
            if os.path.isabs(clip.path) and '/clips/' in clip.path:
                # Extract the part after the last directory containing 'clips'
                parts = clip.path.split('clips')
                if len(parts) > 1:
                    relative_path = os.path.join('clips', parts[-1].lstrip('/'))
                    
                    # Update the clip path to the relative version
                    logger.info(f"Updating clip {clip.id} path from '{clip.path}' to '{relative_path}'")
                    clip.path = relative_path
                    fixed_count += 1
        
        if fixed_count > 0:
            # Commit the changes
            db.session.commit()
            logger.info(f"Migration complete. Fixed {fixed_count} clip paths.")
        else:
            logger.info("No clips needed path fixing.")

if __name__ == "__main__":
    fix_clip_paths()