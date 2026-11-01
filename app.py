from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from database import connect, init_db
from seed import seed
from utils import generate_password_from_name, vietqr_link
import hmac
import json
import os
import secrets
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from assistant_knowledge import SYSTEM_INSTRUCTION, page_context


def load_local_environment():
    """Nạp khóa cục bộ từ .env mà không đưa bí mật vào mã nguồn."""
    env_file = Path(__file__).with_name('.env')
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() and not key.lstrip().startswith('#'):
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


load_local_environment()

app = Flask(__name__)
secret_file = Path(__file__).with_name('.flask_secret_key')
if os.environ.get('FLASK_SECRET_KEY'):
    app.secret_key = os.environ['FLASK_SECRET_KEY']
else:
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32), encoding='utf-8')
    app.secret_key = secret_file.read_text(encoding='utf-8').strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024
init_db()
with connect() as db:
    populated = db.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
if not populated:
    seed()


@app.context_processor
def inject_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['_csrf_token']}


@app.context_processor
def inject_navigation_user():
    return {'nav_user': current_user()}


@app.before_request
def protect_state_changes():
    if request.method == 'POST':
        expected = session.get('_csrf_token', '')
        supplied = request.form.get('_csrf_token', '') or request.headers.get('X-CSRF-Token', '')
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, description='Yêu cầu không hợp lệ. Vui lòng tải lại trang và thử lại.')


@app.post('/api/assistant')
def assistant_reply():
    payload = request.get_json(silent=True) or {}
    message = payload.get('message', '')
    page_path = payload.get('page', '/')
    if not isinstance(message, str) or not message.strip() or len(message) > 1200:
        return {'error': 'Câu hỏi phải có nội dung và không dài quá 1.200 ký tự.'}, 400
    if not isinstance(page_path, str) or page_path not in {
        '/', '/login', '/portal/dashboard', '/portal/payments', '/portal/parking',
        '/portal/giving', '/admin/dashboard', '/admin/finance', '/admin/accounts'
    }:
        page_path = '/'

    page_title, page_guide = page_context(page_path)
    authenticated_user = current_user()
    history = payload.get('history', [])
    if not isinstance(history, list):
        history = []
    transcript = []
    for item in history[-10:]:
        if isinstance(item, dict) and item.get('role') in ('user', 'assistant') and isinstance(item.get('text'), str):
            transcript.append(f"{item['role']}: {item['text'][:1200]}")
    transcript.append(f"Trang hiện tại: {page_title} ({page_path}). Hướng dẫn đúng của trang: {page_guide}")
    if authenticated_user:
        transcript.append(
            f"Xác thực hệ thống: phiên đăng nhập hợp lệ của {authenticated_user['role']}; "
            "máy chủ đã xác nhận tài khoản thuộc cộng đồng NEU. Không hỏi người dùng có thuộc NEU hay không. "
            "Hãy chào và hướng dẫn trực tiếp theo trang hiện tại."
        )
    transcript.append(f"Câu hỏi mới của người dùng: {message.strip()}")
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        return {'reply': page_guide}

    request_body = json.dumps({
        'model': 'gemini-3.5-flash-lite',
        'input': '\n'.join(transcript),
        'system_instruction': SYSTEM_INSTRUCTION,
        'generation_config': {'thinking_level': 'low', 'max_output_tokens': 400},
        'store': False,
    }).encode('utf-8')
    gemini_request = Request(
        'https://generativelanguage.googleapis.com/v1beta/interactions',
        data=request_body,
        headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
        method='POST',
    )
    try:
        with urlopen(gemini_request, timeout=18) as response:
            result = json.loads(response.read().decode('utf-8'))
        reply = '\n'.join(
            part.get('text', '')
            for step in result.get('steps', []) if step.get('type') == 'model_output'
            for part in step.get('content', []) if part.get('type') == 'text'
        ).strip()
        if not reply:
            raise ValueError('Gemini returned no text')
        return {'reply': reply, 'model': 'gemini-3.5-flash-lite'}
    except HTTPError as error:
        app.logger.info('Gemini request failed with HTTP status %s', error.code)
        return {'reply': page_guide, 'model': None}
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {'reply': page_guide, 'model': None}


def current_user():
    with connect() as db:
        return db.execute('SELECT * FROM users WHERE username=?', (session.get('username'),)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user['role'] != 'ADMIN':
            flash('Bạn không có quyền thực hiện thao tác này.', 'error')
            return redirect(url_for('admin'))
        return view(*args, **kwargs)
    return wrapped


@app.get('/')
def gate():
    return render_template('gate.html')


@app.get('/login')
def login():
    return render_template('login.html')


@app.post('/login')
def do_login():
    username, password = request.form.get('username','').strip(), request.form.get('password','')
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE username=? AND password=?', (username,password)).fetchone()
    if not user:
        flash('Tên đăng nhập hoặc mật khẩu không chính xác.', 'error')
        return redirect(url_for('login'))
    session.clear()
    session['username'] = user['username']
    session['_csrf_token'] = secrets.token_urlsafe(32)
    return redirect(url_for('admin') if user['role']=='ADMIN' else url_for('portal'))


@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('gate'))


@app.get('/portal/dashboard')
@login_required
def portal():
    user = current_user()
    if user['role']=='ADMIN':
        return redirect(url_for('admin'))
    with connect() as db:
        academics = db.execute('SELECT * FROM academic_records WHERE username=? ORDER BY id',(user['username'],)).fetchall()
        lectures = db.execute('SELECT * FROM lecture_payments WHERE username=? ORDER BY id DESC',(user['username'],)).fetchall()
    return render_template('portal.html',user=user,academics=academics,lectures=lectures)


@app.get('/portal/payments')
@login_required
def portal_payments():
    user=current_user()
    if user['role']=='ADMIN':
        return redirect(url_for('admin'))
    with connect() as db:
        transactions=db.execute('SELECT * FROM transactions WHERE username=? ORDER BY id DESC LIMIT 30',(user['username'],)).fetchall()
    return render_template('portal_payments.html',user=user,transactions=transactions)


@app.get('/portal/parking')
@login_required
def parking_page():
    user=current_user()
    if user['role']=='ADMIN':
        return redirect(url_for('admin'))
    with connect() as db:
        logs=db.execute('SELECT * FROM parking_logs WHERE username=? ORDER BY id DESC LIMIT 30',(user['username'],)).fetchall()
        tariffs=db.execute('SELECT * FROM parking_tariffs ORDER BY vehicle,time_band').fetchall()
    return render_template('portal_parking.html',user=user,logs=logs,tariffs=tariffs,now_date=datetime.now().strftime('%Y-%m-%d'))


@app.get('/portal/giving')
@login_required
def giving_page():
    user=current_user()
    if user['role']=='ADMIN':
        return redirect(url_for('admin'))
    with connect() as db:
        honors=db.execute("SELECT d.*,u.full_name FROM donations d JOIN users u ON u.username=d.username WHERE d.status='APPROVED' AND d.visibility!='Ẩn danh' ORDER BY d.id DESC LIMIT 20").fetchall()
        own=db.execute('SELECT * FROM donations WHERE username=? ORDER BY id DESC LIMIT 10',(user['username'],)).fetchall()
    return render_template('portal_giving.html',user=user,honors=honors,own_donations=own)


@app.post('/portal/topup')
@login_required
def topup():
    amount_text = request.form.get('amount', '').strip()
    payer_name = request.form.get('payer_name', '').strip()
    payment_reference = request.form.get('payment_reference', '').strip().upper()
    confirmed = request.form.get('confirmed_payment') == '1'
    if not amount_text.isdecimal() or not payer_name or not payment_reference or not confirmed:
        flash('Vui lòng điền số tiền, họ tên người chuyển, mã tham chiếu và xác nhận đã chuyển khoản.', 'error')
    elif len(payer_name) > 120 or len(payment_reference) > 80 or not re.fullmatch(r'[A-Z0-9][A-Z0-9._/-]{3,79}', payment_reference):
        flash('Họ tên hoặc mã tham chiếu giao dịch không hợp lệ.', 'error')
    else:
        amount = int(amount_text)
        user=current_user()
        if payer_name.casefold() != user['full_name'].casefold():
            flash('Họ tên người chuyển phải khớp với hồ sơ tài khoản.', 'error')
        elif amount < 10000 or amount > 50000000 or amount % 1000:
            flash('Số tiền phải từ 10.000đ đến 50.000.000đ và là bội số của 1.000đ.', 'error')
        else:
            memo=f"NAPTHE {user['username']} {amount} | Ref: {payment_reference}"
            try:
                with connect() as db:
                    db.execute("INSERT INTO transactions(username,kind,amount,memo,payment_reference) VALUES(?,?,?,?,?)",(user['username'],'TOPUP',amount,memo,payment_reference))
                flash('Đã ghi nhận yêu cầu nạp tiền, đang chờ Admin đối soát.', 'success')
            except Exception:
                flash('Mã tham chiếu này đã được sử dụng hoặc dữ liệu gửi lên không hợp lệ.', 'error')
    return redirect(url_for('portal_payments'))


@app.post('/portal/monthly-pass')
@login_required
def monthly_pass():
    user=current_user(); vehicle=request.form.get('vehicle','Xe máy'); plate=request.form.get('plate','').strip()
    payment_reference=request.form.get('payment_reference','').strip().upper()
    amount=45000 if vehicle=='Xe đạp' else 70000
    payer_name=request.form.get('payer_name','').strip()
    if payer_name != user['full_name']:
        flash('Vui lòng xác nhận họ tên khớp với hồ sơ tài khoản.', 'error')
    elif request.form.get('confirmed_payment') != '1' or not re.fullmatch(r'[A-Z0-9][A-Z0-9._/-]{3,79}',payment_reference) or vehicle not in ('Xe đạp','Xe máy') or (vehicle=='Xe máy' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 -]{3,19}', plate)) or (vehicle=='Xe đạp' and plate):
        flash('Vui lòng xác nhận thanh toán và nhập thông tin phương tiện hợp lệ (biển số bắt buộc với xe máy).', 'error')
    else:
        with connect() as db:
            try:
                db.execute('INSERT INTO transactions(username,kind,amount,memo,vehicle,plate,payment_reference) VALUES(?,?,?,?,?,?,?)',(user['username'],'MONTHLY_PASS',amount,f"THANG {user['username']} {vehicle} {plate} | Ref: {payment_reference}",vehicle,plate,payment_reference))
                flash('Yêu cầu đăng ký đã được gửi, đang chờ Admin xác nhận thanh toán.', 'success')
            except Exception:
                flash('Mã tham chiếu này đã được sử dụng hoặc dữ liệu gửi lên không hợp lệ.', 'error')
    return redirect(url_for('portal_payments'))


@app.post('/portal/parking')
@login_required
def parking():
    user=current_user(); band=request.form.get('band','Trước 18h'); vehicle=user['vehicle']; subscribed=bool(user['pass_until'] and user['pass_until']>=datetime.now().strftime('%Y-%m-%d'))
    if request.form.get('confirmed') != '1' or band not in ('Trước 18h','Sau 18h') or vehicle not in ('Xe đạp','Xe máy'):
        flash('Khung giờ hoặc loại phương tiện không hợp lệ.', 'error')
        return redirect(url_for('parking_page'))
    with connect() as db:
        tariff=db.execute('SELECT member_fee FROM parking_tariffs WHERE vehicle=? AND time_band=?',(vehicle,band)).fetchone()
        fee=0 if subscribed else tariff['member_fee']
        debit=db.execute('UPDATE users SET balance=balance-? WHERE username=? AND balance>=?',(fee,user['username'],fee))
        if debit.rowcount != 1:
            flash('Số dư không đủ. Vui lòng nạp tiền trước khi gửi xe.', 'error')
        else:
            db.execute('INSERT INTO parking_logs(username,vehicle,time_band,fee) VALUES(?,?,?,?)',(user['username'],vehicle,band,fee))
            flash(f'Quẹt thẻ thành công. Phí lượt này: {fee:,}đ.', 'success')
    return redirect(url_for('parking_page'))


@app.post('/portal/donate')
@login_required
def donate():
    user=current_user(); amount=request.form.get('amount',type=int); visibility=request.form.get('visibility','Ẩn danh')
    purpose=request.form.get('purpose','Quỹ học bổng')
    if request.form.get('confirmed') != '1' or visibility not in ('Công khai đầy đủ','Chỉ hiện tên','Ẩn danh') or purpose not in ('Quỹ học bổng','Hỗ trợ gửi xe sinh viên'):
        flash('Vui lòng chọn mục đích và phạm vi hiển thị hợp lệ.', 'error')
    elif not amount or amount<1000 or amount>user['balance'] or amount%1000:
        flash('Số tiền đóng góp không hợp lệ hoặc số dư không đủ.', 'error')
    else:
        with connect() as db:
            debit=db.execute('UPDATE users SET balance=balance-? WHERE username=? AND balance>=?',(amount,user['username'],amount))
            if debit.rowcount:
                db.execute("INSERT INTO donations(username,amount,purpose,visibility,status) VALUES(?,?,?,?, 'PENDING')",(user['username'],amount,purpose,visibility))
                flash('Cảm ơn bạn đã đóng góp cho cộng đồng NEU.', 'success')
            else:
                flash('Số dư đã thay đổi và không đủ cho khoản đóng góp này.', 'error')
    return redirect(url_for('giving_page'))


@app.get('/admin/dashboard')
@login_required
def admin():
    user=current_user()
    if user['role']!='ADMIN' and not user['finance_manager']:
        flash('Tài khoản chưa được cấp quyền quản lý tài chính.', 'error')
        return redirect(url_for('portal'))
    with connect() as db:
        pending=db.execute("SELECT t.*,u.full_name FROM transactions t JOIN users u ON t.username=u.username WHERE t.status='PENDING' ORDER BY t.id DESC").fetchall()
        pending_donations=db.execute("SELECT d.*,u.full_name FROM donations d JOIN users u ON d.username=u.username WHERE d.status='PENDING' ORDER BY d.id DESC").fetchall() if user['role']=='ADMIN' else []
        count=db.execute("SELECT COUNT(*) n FROM transactions WHERE status='PENDING'").fetchone()['n']
    return render_template('admin.html',user=user,pending=pending,pending_donations=pending_donations,pending_count=count)


app.add_url_rule('/admin/finance', endpoint='finance', view_func=admin)


@app.get('/admin/accounts')
@admin_required
def admin_accounts():
    with connect() as db:
        users=db.execute("SELECT * FROM users WHERE role!='ADMIN' ORDER BY role,username").fetchall()
    return render_template('admin_accounts.html',user=current_user(),users=users)


@app.post('/admin/transactions/<int:txid>/<action>')
@login_required
def review_transaction(txid,action):
    actor=current_user()
    if actor['role']!='ADMIN' and not actor['finance_manager']:
        flash('Bạn không có quyền duyệt giao dịch.', 'error'); return redirect(url_for('admin'))
    if action not in ('approve','reject'):
        flash('Thao tác không hợp lệ.', 'error')
        return redirect(url_for('admin'))
    with connect() as db:
        tx=db.execute("SELECT * FROM transactions WHERE id=? AND status='PENDING'",(txid,)).fetchone()
        if not tx:
            flash('Giao dịch không tồn tại hoặc đã được xử lý.', 'error')
        elif action=='approve':
            if tx['kind'] not in ('TOPUP','MONTHLY_PASS'):
                flash('Loại giao dịch không hợp lệ, không thể duyệt.', 'error')
                return redirect(url_for('admin'))
            claimed=db.execute("UPDATE transactions SET status='APPROVED' WHERE id=? AND status='PENDING'",(txid,))
            if claimed.rowcount != 1:
                flash('Giao dịch đã được xử lý bởi thao tác khác.', 'error')
                return redirect(url_for('admin'))
            if tx['kind']=='TOPUP':
                db.execute('UPDATE users SET balance=balance+? WHERE username=?',(tx['amount'],tx['username']))
            elif tx['kind']=='MONTHLY_PASS':
                expiry=(datetime.now()+timedelta(days=30)).strftime('%Y-%m-%d')
                db.execute("UPDATE users SET pass_until=?,plate=?,vehicle=? WHERE username=?",(expiry,tx['plate'] or '',tx['vehicle'] or 'Xe máy',tx['username']))
                db.execute("UPDATE cards SET card_type='Thẻ tháng KTX' WHERE username=?",(tx['username'],))
            db.execute('INSERT INTO accounting_entries(transaction_id,username,kind,amount) VALUES(?,?,?,?)',(txid,tx['username'],tx['kind'],tx['amount']))
            flash('Đã duyệt giao dịch và tạo bút toán kế toán.', 'success')
        elif action=='reject':
            db.execute("UPDATE transactions SET status='REJECTED' WHERE id=?",(txid,)); flash('Đã từ chối yêu cầu.', 'success')
        else:
            flash('Thao tác không hợp lệ.', 'error')
    return redirect(url_for('admin'))


@app.post('/admin/users')
@admin_required
def create_user():
    username=request.form.get('username','').strip(); name=request.form.get('full_name','').strip(); role=request.form.get('role','STUDENT')
    dob=request.form.get('dob','').strip(); department=request.form.get('department','').strip(); vehicle=request.form.get('vehicle','')
    valid_dob=False
    try:
        valid_dob=bool(dob) and datetime.strptime(dob,'%d/%m/%Y').strftime('%d/%m/%Y')==dob
    except ValueError:
        pass
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,20}',username) or not name or len(name)>120 or not generate_password_from_name(name) or len(department)>120 or not department or not valid_dob or role not in ('STUDENT','LECTURER') or vehicle not in ('Xe máy','Xe đạp'):
        flash('Vui lòng nhập mã, họ tên và vai trò hợp lệ.', 'error')
    else:
        try:
            with connect() as db:
                db.execute('INSERT INTO users(username,password,full_name,role,dob,department,vehicle,balance) VALUES(?,?,?,?,?,?,?,50000)',(username,generate_password_from_name(name),name,role,dob,department,vehicle))
                db.execute('INSERT INTO cards(username) VALUES(?)',(username,))
            flash(f'Đã tạo {username}; mật khẩu ban đầu là {generate_password_from_name(name)}.', 'success')
        except Exception:
            flash('Mã tài khoản đã tồn tại hoặc dữ liệu không hợp lệ.', 'error')
    return redirect(url_for('admin_accounts'))


@app.post('/admin/users/<username>/update')
@admin_required
def update_user(username):
    name=request.form.get('full_name','').strip()
    department=request.form.get('department','').strip(); vehicle=request.form.get('vehicle','Xe máy'); pass_type=request.form.get('pass_type','hourly')
    if not name or len(name)>120 or not generate_password_from_name(name) or len(department)>120 or vehicle not in ('Xe máy','Xe đạp') or pass_type not in ('hourly','monthly'):
        flash('Thông tin hồ sơ không hợp lệ.', 'error')
        return redirect(url_for('admin_accounts'))
    expiry=(datetime.now()+timedelta(days=30)).strftime('%Y-%m-%d') if pass_type=='monthly' else None
    with connect() as db:
        db.execute('UPDATE users SET full_name=?,password=?,department=?,vehicle=?,pass_until=? WHERE username=?',(name,generate_password_from_name(name),department,vehicle,expiry,username))
        db.execute("UPDATE cards SET card_type=? WHERE username=?",('Thẻ tháng KTX' if pass_type=='monthly' else 'Thẻ thường xuyên - Theo lượt',username))
    flash('Đã cập nhật hồ sơ và mật khẩu theo họ tên mới.', 'success'); return redirect(url_for('admin_accounts'))


@app.post('/admin/users/<username>/balance')
@admin_required
def update_balance(username):
    amount=request.form.get('balance',type=int)
    if amount is None or amount<0 or amount>1000000000: flash('Số dư phải là số nguyên từ 0 đến 1.000.000.000đ.', 'error')
    else:
        with connect() as db: db.execute('UPDATE users SET balance=? WHERE username=?',(amount,username))
        flash('Đã cập nhật số dư.', 'success')
    return redirect(url_for('admin_accounts'))


@app.post('/admin/users/<username>/finance')
@admin_required
def finance_role(username):
    if request.form.get('enabled') not in ('0','1'):
        flash('Giá trị phân quyền không hợp lệ.', 'error')
        return redirect(url_for('admin_accounts'))
    enabled=1 if request.form.get('enabled')=='1' else 0
    with connect() as db:
        db.execute("UPDATE users SET finance_manager=? WHERE username=? AND role='LECTURER'",(enabled,username))
        if enabled:
            db.execute("INSERT OR IGNORE INTO role_assignments(username,permission,granted_by) VALUES(?,'FINANCE_MANAGER',?)",(username,session['username']))
        else:
            db.execute("DELETE FROM role_assignments WHERE username=? AND permission='FINANCE_MANAGER'",(username,))
    flash('Đã cập nhật quyền quản lý tài chính.', 'success'); return redirect(url_for('admin_accounts'))


@app.post('/admin/users/<username>/delete')
@admin_required
def delete_user(username):
    with connect() as db:
        db.execute("DELETE FROM accounting_entries WHERE username=?",(username,))
        db.execute("DELETE FROM users WHERE username=? AND role!='ADMIN'",(username,))
    flash('Đã xóa tài khoản và dữ liệu liên kết.', 'success'); return redirect(url_for('admin_accounts'))


@app.post('/admin/donations/<int:donation_id>/<action>')
@admin_required
def review_donation(donation_id, action):
    if action not in ('approve','reject'):
        flash('Thao tác không hợp lệ.', 'error')
        return redirect(url_for('admin'))
    status='APPROVED' if action=='approve' else 'REJECTED'
    with connect() as db:
        result=db.execute("UPDATE donations SET status=? WHERE id=? AND status='PENDING'",(status,donation_id))
    flash('Đã duyệt hiển thị Bảng vinh danh.' if action=='approve' and result.rowcount else ('Đã từ chối hiển thị.' if result.rowcount else 'Khoản đóng góp đã được xử lý.'), 'success' if result.rowcount else 'error')
    return redirect(url_for('admin'))


@app.post('/admin/reset')
@admin_required
def reset_demo():
    with connect() as db:
        db.execute('DELETE FROM accounting_entries'); db.execute('DELETE FROM transactions'); db.execute('DELETE FROM parking_logs'); db.execute('DELETE FROM donations'); db.execute('DELETE FROM cards'); db.execute('DELETE FROM users')
    seed(); session.clear(); flash('Đã khôi phục dữ liệu mẫu ban đầu.', 'success'); return redirect(url_for('gate'))


if __name__=='__main__':
    app.run(debug=True)
