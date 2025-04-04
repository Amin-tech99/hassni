#!/bin/bash
set -e

# Add timestamp to each line of output
timestamp() {
  while IFS= read -r line; do
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $line"
  done
}

# Start the script with a clear header and timestamp
echo "===============================================" | timestamp
echo "RAILWAY DEPLOYMENT - PRESTART INITIALIZATION" | timestamp
echo "===============================================" | timestamp

echo "Starting prestart script..." | timestamp

# Create necessary directories with verbose output
echo "Creating required directories..." | timestamp
mkdir -p clips && echo "  ✓ clips directory ready" | timestamp
mkdir -p uploads && echo "  ✓ uploads directory ready" | timestamp
mkdir -p transcriptions && echo "  ✓ transcriptions directory ready" | timestamp
mkdir -p instance && echo "  ✓ instance directory ready" | timestamp

# Print environment information
echo "Environment information:" | timestamp
echo "  - Python version: $(python --version 2>&1)" | timestamp
echo "  - Current directory: $(pwd)" | timestamp
echo "  - Available disk space: $(df -h . | awk 'NR==2 {print $4}' || echo 'unknown')" | timestamp
echo "  - Memory: $(free -m | awk 'NR==2{printf "%.1f GB / %.1f GB (%.1f%%)", $3/1024, $2/1024, $3*100/$2}')" | timestamp
echo "  - CPU: $(cat /proc/cpuinfo | grep "model name" | head -n 1 | cut -d ':' -f 2 | sed 's/^[ \t]*//')" | timestamp

# Check Railway-specific environment variables
echo "Checking Railway environment..." | timestamp
if [ -n "$RAILWAY_STATIC_URL" ]; then
  echo "  ✓ Running in Railway environment" | timestamp
  echo "  - Project ID: ${RAILWAY_PROJECT_ID:-not set}" | timestamp
  echo "  - Service ID: ${RAILWAY_SERVICE_ID:-not set}" | timestamp
  echo "  - Environment: ${RAILWAY_ENVIRONMENT:-not set}" | timestamp
else
  echo "  ⚠ Not running in Railway environment" | timestamp
fi

# Check essential environment variables
echo "Checking critical environment variables..." | timestamp
if [ -z "$DATABASE_URL" ]; then
  echo "  ✗ CRITICAL: DATABASE_URL is not set! Database operations will fail." | timestamp
  # Don't fail early, let the app try to handle this
else
  echo "  ✓ DATABASE_URL is set" | timestamp
  
  # Check database URL format for common errors
  if [[ "$DATABASE_URL" == postgres://* ]]; then
    echo "  ⚠ WARNING: DATABASE_URL starts with postgres:// instead of postgresql://" | timestamp
    echo "    This will be automatically corrected at runtime" | timestamp
  fi
fi

if [ -z "$SESSION_SECRET" ]; then
  echo "  ✗ WARNING: SESSION_SECRET is not set! Using a random value for this session." | timestamp
  export SESSION_SECRET="$(openssl rand -hex 32 || echo 'temporary-secret-key')"
  echo "  ✓ Generated temporary SESSION_SECRET" | timestamp
else
  echo "  ✓ SESSION_SECRET is set" | timestamp
fi

# Check PORT variable (used by Railway)
if [ -z "$PORT" ]; then
  echo "  ⚠ WARNING: PORT environment variable is not set. Defaulting to 5000." | timestamp
  export PORT=5000
else
  echo "  ✓ PORT is set to $PORT" | timestamp
fi

# Test database connection with better error handling
echo "Testing database connection..." | timestamp
if [ -n "$DATABASE_URL" ]; then
  # Use a temporary connection test script
  cat > /tmp/db_test.py << 'EOL'
import sys
import psycopg2
import time
from urllib.parse import urlparse

# Parse the connection string to report issues more clearly
def parse_db_url(url):
    parsed = urlparse(url)
    return {
        'scheme': parsed.scheme,
        'username': parsed.username,
        'password': '***' if parsed.password else None,
        'hostname': parsed.hostname,
        'port': parsed.port,
        'path': parsed.path
    }

# Try connecting with retry logic
url = sys.argv[1]
db_info = parse_db_url(url)

# Replace postgres:// with postgresql:// if needed
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql://', 1)
    print(f"  ℹ Corrected URL scheme from postgres:// to postgresql://")

max_retries = 3
retry_delay = 2
attempt = 1

while attempt <= max_retries:
    try:
        print(f"  ℹ Attempt {attempt}/{max_retries}: Connecting to {db_info['hostname']}:{db_info['port']}{db_info['path']}...")
        conn = psycopg2.connect(url, connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"  ✓ Database connection successful")
        print(f"  ℹ Database info: {version.split(',')[0]}")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        error_msg = str(e).strip()
        print(f"  ✗ Connection error: {error_msg}")
        
        if "could not connect to server" in error_msg or "connection refused" in error_msg:
            print(f"  ⚠ Database server may be unreachable")
        elif "password authentication failed" in error_msg:
            print(f"  ⚠ Database credentials are incorrect")
        elif "database" in error_msg and "does not exist" in error_msg:
            print(f"  ⚠ Database does not exist")
        
        if attempt < max_retries:
            print(f"  ℹ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            attempt += 1
            retry_delay *= 2  # Exponential backoff
        else:
            print(f"  ✗ Failed to connect to database after {max_retries} attempts")
            sys.exit(1)
EOL

  if python /tmp/db_test.py "$DATABASE_URL"; then
    echo "  ✓ Database connection validated" | timestamp
  else
    echo "  ⚠ WARNING: Database connection issues detected. The application may not function correctly." | timestamp
  fi
  
  # Clean up the test script
  rm -f /tmp/db_test.py
fi

# Run database migrations with comprehensive error handling and reporting
echo "Initializing database..." | timestamp
python -c "
import sys
import traceback
import time
from datetime import datetime

start_time = time.time()

try:
    print(f'  ℹ Starting database initialization at {datetime.now().isoformat()}')
    
    # First import the app and db
    from app import app, db, User
    app.app_context().push()
    
    # Create all tables
    print('  ℹ Creating database schema...')
    db.create_all()
    print(f'  ✓ Database schema created/updated successfully ({time.time() - start_time:.2f}s)')
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print('  ℹ Creating default admin user...')
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('  ✓ Default admin user created')
    else:
        print('  ✓ Admin user already exists')
    
    # Run clip path fix if needed
    print('  ℹ Running clip path fix script...')
    from fix_clip_paths import fix_clip_paths
    fixed_count = fix_clip_paths()
    if fixed_count > 0:
        print(f'  ✓ Fixed {fixed_count} clip paths')
    else:
        print('  ✓ No clip paths needed fixing')
    
    print(f'  ✓ Database initialization completed in {time.time() - start_time:.2f}s')
    
except Exception as e:
    elapsed = time.time() - start_time
    print(f'  ✗ ERROR initializing database after {elapsed:.2f}s: {str(e)}')
    print('  ℹ Full traceback:')
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)
" || echo "  ✗ Database initialization failed. The application may not work correctly." | timestamp

# Ensure correct permissions (important in containerized environments)
echo "Setting correct permissions..." | timestamp
chmod -R 755 clips uploads transcriptions instance || echo "  ⚠ WARNING: Could not set permissions" | timestamp

# Verify critical files exist
echo "Verifying critical application files..." | timestamp
for file in main.py app.py models.py forms.py audio_processor.py; do
  if [ -f "$file" ]; then
    echo "  ✓ $file exists" | timestamp
  else
    echo "  ✗ CRITICAL: $file is missing! Application will not function correctly." | timestamp
  fi
done

# Check for FFmpeg (needed for audio processing)
echo "Checking for FFmpeg..." | timestamp
if command -v ffmpeg &>/dev/null; then
  FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d ' ' -f 3)
  echo "  ✓ FFmpeg found (version $FFMPEG_VERSION)" | timestamp
else
  echo "  ⚠ WARNING: FFmpeg not found. Audio processing will not work correctly." | timestamp
fi

# Check for PyTorch (needed for silero-vad)
echo "Checking PyTorch installation..." | timestamp
if python -c "import torch; print(f'PyTorch {torch.__version__} found ({torch.cuda.is_available() and \"CUDA available\" or \"CPU only\"})')" 2>/dev/null; then
  echo "  ✓ PyTorch is installed" | timestamp
else
  echo "  ⚠ WARNING: PyTorch not installed or having issues. Audio processing may fail." | timestamp
fi

echo "===============================================" | timestamp
echo "✓ Prestart initialization completed successfully" | timestamp
echo "===============================================" | timestamp
