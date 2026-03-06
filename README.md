# Vulnerable app by Bunny Walker (Flask wrapper for login-form-20)

This folder (now called `VulnappbyBunnyWalker`) contains a minimal Flask application that serves the static HTML/CSS/JS assets from the original `login-form-20` template.

## Structure

```
VulnappbyBunnyWalker/
├── app.py            # simple Flask server
├── requirements.txt  # dependencies (Flask)
├── templates/        # Jinja2 templates (index.html, main.html)
└── static/           # copy css, js, images, fonts from original project here
    ├── css/
    ├── js/
    ├── images/
    └── fonts/
```

> **Note:** the original project directory `login-form-20/login-form-20` contains the files you need to copy into `static/`.

## Usage

1. **Copy assets**
   ```powershell
   # from Windows workspace
   cd .\login-form-20\login-form-20
   xcopy /E /I css ..\VulnappbyBunnyWalker\static\css
   xcopy /E /I js ..\VulnappbyBunnyWalker\static\js
   xcopy /E /I images ..\VulnappbyBunnyWalker\static\images
   xcopy /E /I fonts ..\VulnappbyBunnyWalker\static\fonts
   ```
   or just drag the folders into `VulnappbyBunnyWalker/static`.

2. **Install dependencies**
   ```bash
   # on Windows, Kali or any Linux:
   python -m venv venv
   # activate the virtualenv
   # Windows PowerShell:
   #   .\venv\Scripts\Activate
   # macOS/Linux/Kali:
   #   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   # with the virtual environment active
   python app.py
   # you should see output like:
   #   * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
   # then open a browser on the same machine and go to
   # http://localhost:5000/
   ```

4. **Linux/Kali-specific notes**
   * If you copy the project to a Kali box (e.g. via `scp` or USB), simply repeat the copy-assets step (or git clone the repo) and follow the same commands above.
   * Make sure Python 3, the venv module and `pip` are installed (`sudo apt install python3 python3-venv python3-pip`).  If `run.sh` fails with "venv/bin/activate: No such file or directory" you probably need to install `python3-venv` (the package that provides `venv`).
   * You can run the server in the background with `nohup python app.py &` or use `screen`/`tmux`.
   * The SQLite CLI is usually available on Kali; you can inspect `users.db` there as described previously.
   * A convenience script `run.sh` has been provided in this folder.  On a Linux machine run:

     ```bash
     cd VulnappbyBunnyWalker
     bash run.sh
     ```

     The script will copy the static assets from the original template, create/activate a virtual environment, install requirements, and launch the Flask app.


4. **Login database**
   The app uses a lightweight SQLite database (`users.db`) stored alongside `app.py`.  On first run the file is created automatically and seeded with three users.  You can log in using any of the following credentials (they’re also shown in the dashboard after successful login):

   | Username | Password    |
   |----------|-------------|
   | alice    | password1   |
   | bob      | password2   |
   | charlie  | password3   |

   Passwords are hashed using `werkzeug.security` (this is why you won’t see the plaintext in the DB).

   The application now uses Flask's built-in session system. On login a cookie named `session` is set with the username; the secret key is hard‑coded (`insecure-demo-key`) to make the token predictable, demonstrating **session hijacking/fixation** vulnerability. There is no session expiry or regeneration.

   
### Vulnerability playground

The dashboard contains several insecure endpoints for testing purposes.  Below are the flaws you can play with and simple ways to exploit them once logged in with one of the credentials listed above.

- **Command injection** (`/vuln/cmd`) – the server blindly passes the `cmd` field to `os.popen()`.  Try entering `whoami`, `id`, `dir`, `ls -la` or even `echo hacked` to see the output.  You can chain additional commands using `;` or `&&` (e.g. `whoami; cat /etc/passwd`).

- **File upload** (`/vuln/upload`) – there is no client‑side or server‑side validation, so you can upload any file and it will be saved to `VulnappbyBunnyWalker/uploads/<filename>`.  Use it to drop a webshell, scripts, or simply demonstrate arbitrary file write.  The returned response shows the full path where the file landed.

- **SQL injection** (`/vuln/sqli`) – the query is constructed via string concatenation with the `q` parameter.  Submitting `alice` returns Alice’s record; submitting `' OR '1'='1` returns every username.  You can even inject `'; DROP TABLE users; --` to wipe the table (in the demo database).

- **Reflected XSS** (`/vuln/xss`) – whatever you type into `msg` is echoed raw in the HTTP response.  Enter `<script>alert('XSS')</script>` to trigger a popup, or craft a link that pre‑populates the form and sends the payload to another user.

- **IDOR (Insecure Direct Object Reference)** (`/vuln/idor/<id>`) – after logging in you can access any user’s information by visiting `/vuln/idor/2`, `/vuln/idor/3`, etc.  There is no authorization check; the numeric ID is all that stands between you and another profile.  Try guessing sequential IDs to enumerate accounts.

- **Session hijacking/fixation** – the session cookie value is printed on the dashboard (`{{ request.cookies.get('session') }}`).  Because `app.secret_key` is hard‑coded, the cookie remains valid across restarts.  Copy the cookie value into another browser or Incognito window and you’ll be instantly logged in as the original user.  You can also set the cookie before authenticating to “fix” a session ID.

These vulnerabilities are intentionally insecure and meant for learning and testing; remove or fix them before using this code in any real environment.

   Passwords are hashed using `werkzeug.security`.

   If you need to adjust the users you can either modify `app.py`'s `init_db()` logic, or open the database with `sqlite3`:

   ```bash
   sqlite3 users.db
   sqlite> SELECT username FROM users;
   sqlite> INSERT INTO users (username, password) VALUES ('dave', '...');
   ```

5. **Deploying to Kali**
   - Copy the entire `VulnappbyBunnyWalker` directory to your Kali machine (scp, USB, etc.).
   - Repeat the installation steps above on Kali.

5. **Optional tweaks**
   - Enable `app.run(host='0.0.0.0')` in `app.py` for remote access.
   - Add more routes or backend logic as needed.

---

This setup lets you paste the full project into a Linux environment and run it using Flask. The HTML remains unchanged except for using `url_for('static',...)` to resolve asset paths.