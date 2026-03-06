import os
import sqlite3
import logging
from flask import Flask, render_template, request, redirect, url_for, g, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', template_folder='templates')
# secret key for session cookie (insecurely hard-coded for demo)
app.secret_key = 'insecure-demo-key'

# ---- logging configuration for Splunk ---------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging for attack detection
logger = logging.getLogger('vulnapp')
logger.setLevel(logging.INFO)

# File handler for logs
file_handler = logging.FileHandler(os.path.join(LOG_DIR, 'app.log'))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

# Stream handler for console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Log all requests before they are processed
@app.before_request
def log_request():
    # Don't log static files
    if request.path.startswith('/static'):
        return
    
    user = session.get('user', 'anonymous')
    logger.info(f"REQUEST | Method: {request.method} | Path: {request.path} | User: {user} | IP: {request.remote_addr} | User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

# Log all responses
@app.after_request
def log_response(response):
    logger.info(f"RESPONSE | Status: {response.status_code} | Path: {request.path}")
    return response

# ---- database helpers ------------------------------------------------------
DATABASE = os.path.join(os.path.dirname(__file__), 'users.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Create the database file and insert three sample users."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Create users table with extra columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            role TEXT
        )
    ''')
    
    # Check if we need to seed data
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        users = [
            ('alice', generate_password_hash('password1'), 'alice@email.com', '555-0101', '123 Main St, City A', 'Admin'),
            ('bob', generate_password_hash('password2'), 'bob@email.com', '555-0102', '456 Oak Ave, City B', 'User'),
            ('charlie', generate_password_hash('password3'), 'charlie@email.com', '555-0103', '789 Pine Rd, City C', 'User'),
        ]
        c.executemany('INSERT INTO users (username, password, email, phone, address, role) VALUES (?, ?, ?, ?, ?, ?)', users)
        conn.commit()
    
    conn.close()

# initialize the database when the module is imported
init_db()

# ---- routes ----------------------------------------------------------------
@app.route('/')
def index(error=None):
    return render_template('index.html', error=error)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        return render_template('index.html', error='Please enter both username and password')

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    error = None
    if user is None:
        error = 'Invalid username or password'
        logger.warning(f"LOGIN_FAILED | Username: {username} | IP: {request.remote_addr} | Reason: User not found")
    elif not check_password_hash(user['password'], password):
        error = 'Invalid username or password'
        logger.warning(f"LOGIN_FAILED | Username: {username} | IP: {request.remote_addr} | Reason: Invalid password")

    if error:
        return render_template('index.html', error=error)
    
    # Successful login
    logger.info(f"LOGIN_SUCCESS | Username: {username} | IP: {request.remote_addr}")
    session['user'] = username
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    logger.info(f"DASHBOARD_ACCESS | User: {session.get('user')} | IP: {request.remote_addr}")
    return render_template('dashboard.html', user=session.get('user'))

@app.route('/logout')
def logout():
    user = session.get('user', 'anonymous')
    logger.info(f"LOGOUT | User: {user} | IP: {request.remote_addr}")
    session.pop('user', None)
    return redirect(url_for('index'))

# --- vulnerable demonstration endpoints ------------------------------------
@app.route('/vuln/cmd', methods=['POST'])
def vuln_cmd():
    cmd = request.form.get('cmd', '')
    
    # Log command injection attack
    logger.critical(f"ATTACK_COMMAND_INJECTION | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Command: {cmd}")
    
    output = ''
    if cmd:
        output = os.popen(cmd).read()
    return render_template('vuln_cmd.html', output=output)

@app.route('/vuln/upload', methods=['POST'])
def vuln_upload():
    # Log file upload attack
    f = request.files.get('file')
    message = ''
    if f:
        filename = f.filename
        logger.critical(f"ATTACK_FILE_UPLOAD | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Filename: {filename}")
        
        path = os.path.join(os.path.dirname(__file__), 'uploads', filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f.save(path)
        message = f"Uploaded to {path}"
    return render_template('vuln_upload.html', message=message)

@app.route('/vuln/sqli', methods=['POST'])
def vuln_sqli():
    q = request.form.get('q', '')
    
    # Log SQL injection attack
    logger.critical(f"ATTACK_SQL_INJECTION | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Payload: {q}")
    
    db = get_db()
    try:
        rows = db.execute(f"SELECT username FROM users WHERE username LIKE '%{q}%'").fetchall()
    except Exception as e:
        rows = [("error",)]
        logger.error(f"SQL_ERROR | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Error: {str(e)}")
    
    # Convert rows to readable format and pass to template
    results = []
    for row in rows:
        if isinstance(row, tuple):
            results.append(str(row))
        else:
            results.append(str(dict(row)))
    
    return render_template('vuln_sqli.html', results=results)

@app.route('/vuln/xss', methods=['POST'])
def vuln_xss():
    msg = request.form.get('msg', '')
    
    # Log XSS attack
    logger.critical(f"ATTACK_XSS | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Payload: {msg}")
    
    # reflected without escaping
    return render_template('vuln_xss.html', reflected=msg)

@app.route('/vuln/idor/<int:uid>')
def vuln_idor(uid):
    # Log IDOR attack
    logger.warning(f"ATTACK_IDOR | User: {session.get('user', 'anonymous')} | IP: {request.remote_addr} | Requested_User_ID: {uid}")
    
    db = get_db()
    user = db.execute('SELECT id, username, email, phone, address, role FROM users WHERE id = ?', (uid,)).fetchone()
    user_data = ''
    if user:
        user_data = dict(user)
    else:
        user_data = "Not found"
    return render_template('vuln_idor.html', user_data=user_data)

@app.route('/main')
def main():
    return render_template('main.html')

# --- vulnerability pages (dedicated views) ---
@app.route('/vuln/cmd/page')
def vuln_cmd_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('vuln_cmd.html')

@app.route('/vuln/upload/page')
def vuln_upload_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('vuln_upload.html')

@app.route('/vuln/sqli/page')
def vuln_sqli_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('vuln_sqli.html')

@app.route('/vuln/xss/page')
def vuln_xss_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('vuln_xss.html', reflected=None)

@app.route('/vuln/idor/page')
def vuln_idor_page():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('vuln_idor.html')

if __name__ == '__main__':
    # use host='0.0.0.0' if you want to access from other machines
    app.run(debug=True)
