import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from twilio.rest import Client
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv() 

# -------------------------------
# Flask App Setup
# -------------------------------
app = Flask(__name__)

# Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///epolice.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mp3', 'pdf'}

# Mail config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

# Twilio config
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

twilio_client = Client(TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)
migrate = Migrate(app, db)

# -------------------------------
# Database Models
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    father_name = db.Column(db.String(150))
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(150), unique=True)
    address = db.Column(db.String(200))
    district = db.Column(db.String(100))
    state = db.Column(db.String(50))
    police_station = db.Column(db.String(100))
    role = db.Column(db.String(20))  # complainant / police / admin
    imei = db.Column(db.String(50), nullable=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    location = db.Column(db.String(255), nullable=True)

    firs = db.relationship('FIR', foreign_keys='FIR.complainant_id', backref='complainant', lazy=True)
    assigned_firs = db.relationship('FIR', foreign_keys='FIR.assigned_police_id', backref='assigned_police', lazy=True)
    updates = db.relationship('FIRStatusUpdate', backref='updated_by', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        if not self.is_active:
            return None
        return super().get_id()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class FIR(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complainant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200))
    occurrence_date = db.Column(db.DateTime)
    place_of_occurrence = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    assigned_police_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    imei = db.Column(db.String(50), nullable=True)
    multimedia_files = db.Column(db.Text, nullable=True)
    updates = db.relationship('FIRStatusUpdate', backref='fir', lazy=True)
    evidences = db.relationship('Evidence', backref='fir', lazy=True)
    location = db.Column(db.String(255), nullable=True)

class FIRStatusUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fir_id = db.Column(db.Integer, db.ForeignKey('fir.id'), nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20))
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Evidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fir_id = db.Column(db.Integer, db.ForeignKey('fir.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default="Pending")
    remarks = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class EvidenceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=False)
    action = db.Column(db.String(50))
    remarks = db.Column(db.Text, nullable=True)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    evidence = db.relationship('Evidence', backref='logs')
    performed_by = db.relationship('User')

class UserLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {'user_id': self.user_id,'latitude': self.latitude,'longitude': self.longitude,'timestamp': self.timestamp.isoformat()}




# -------------------------------
# Helper Functions
# -------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(subject, recipients, body, html=None):
    try:
        msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=recipients)
        msg.body = body
        if html:
            msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def send_sms_alert(to_number, message):
    try:
        if not to_number.startswith("+"):
            to_number = "+91" + to_number
        twilio_client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
        return True
    except Exception as e:
        print("SMS Error:", e)
        return False

# -------------------------------
# Role-based decorators
# -------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('unauthorized'))
        return f(*args, **kwargs)
    return decorated_function

def police_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'police':
            flash("Police access required.", "danger")
            return redirect(url_for('unauthorized'))
        return f(*args, **kwargs)
    return decorated_function

def police_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['police', 'admin']:
            flash("Access denied.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------
# Routes
# -------------------------------
@app.route('/')
def index():
    return redirect(url_for('dashboard')) if current_user.is_authenticated else redirect(url_for('login'))

@app.route('/unauthorized')
def unauthorized():
    return "<h2>Unauthorized Access</h2>", 403

# -------- Register --------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        imei = request.form.get('imei') or None

        if not all([username, email, role, password, confirm_password]):
            flash("All fields are required.", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))
        if imei and User.query.filter_by(imei=imei).first():
            flash("This device (IMEI) is already registered.", "danger")
            return redirect(url_for('register'))

        user = User(username=username, email=email, role=role, name=username, imei=imei)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        send_email(
            subject="Welcome to E-Police FIR System",
            recipients=[user.email],
            body=f"Hello {user.username},\n\nThank you for registering with E-Police FIR system.\n\nRegards,\nE-Police"
        )

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# -------- Login --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        imei = request.form.get('imei') or None

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact admin.', 'danger')
                return redirect(url_for('login'))

            if not user.imei and imei:
                user.imei = imei
                db.session.commit()

            if user.imei and user.imei != imei:
                flash("Login denied: This account is locked to a different device.", "danger")
                return redirect(url_for('login'))

            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

#--------forgot-password--------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        # Basic validations
        if not username or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for('forgot_password'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('forgot_password'))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('forgot_password'))

        # Case-insensitive lookup (handles Admin vs admin)
        user = User.query.filter(func.lower(User.username) == username.lower()).first()

        if not user:
            flash("Username not found.", "danger")
            return redirect(url_for('forgot_password'))

        # Save hashed password using your model helper
        user.set_password(password)
        db.session.commit()

        flash("Password updated successfully! You can now log in with your new password.", "success")
        return redirect(url_for('login'))

    return render_template('forgot_password.html')


# -------- Dashboard --------
@app.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    if current_user.role == 'complainant':
        return redirect(url_for('complainant_dashboard'))
    elif current_user.role == 'police':
        return redirect(url_for('police_dashboard'))
    elif current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        flash("Invalid role. Contact admin.", "danger")
        return redirect(url_for('logout'))


# -------- Complainant Dashboard --------
@app.route('/dashboard/complainant')
@login_required
def complainant_dashboard():
    if current_user.role != 'complainant':
        return redirect(url_for('unauthorized'))
    firs = FIR.query.filter_by(complainant_id=current_user.id).order_by(FIR.timestamp.desc()).all()
    return render_template('complainant_dashboard.html', firs=firs)


# -------- Police Dashboard --------
@app.route('/dashboard/police')
@login_required
@police_or_admin_required
def police_dashboard():
    if current_user.role not in ['police', 'admin']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    # If admin → show all FIRs and evidences
    if current_user.role == 'admin':
        firs = FIR.query.order_by(FIR.timestamp.desc()).all()
        evidences = Evidence.query.order_by(Evidence.id.desc()).all()
    else:
        # Police → only their assigned FIRs and evidences
        firs = FIR.query.filter_by(assigned_police_id=current_user.id).order_by(FIR.timestamp.desc()).all()
        evidences = (
            Evidence.query.join(FIR, Evidence.fir_id == FIR.id)
            .filter(FIR.assigned_police_id == current_user.id)
            .order_by(Evidence.id.desc())
            .all()
        )

    return render_template("police_dashboard.html", firs=firs, evidences=evidences)


# -------- Admin Dashboard --------
@app.route('/dashboard/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    firs = FIR.query.order_by(FIR.timestamp.desc()).all()
    evidences = Evidence.query.order_by(Evidence.timestamp.desc()).all()
    evidence_logs = EvidenceLog.query.order_by(EvidenceLog.timestamp.desc()).all()
    police_officers = User.query.filter_by(role='police').all()
    locations = [loc.to_dict() for loc in UserLocation.query.order_by(UserLocation.timestamp.desc()).all()]

    return render_template(
        'admin_dashboard.html',
        users=users,
        firs=firs,
        evidences=evidences,
        evidence_logs=evidence_logs,
        police_officers=police_officers,
        locations=locations
    )


# -------- Submit FIR --------
@app.route('/submit-fir', methods=['GET', 'POST'])
@login_required
def submit_fir():
    if current_user.role != 'complainant':
        flash('Only complainants can submit FIRs.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Update complainant details
        current_user.name = request.form.get('name')
        current_user.father_name = request.form.get('father_name')
        current_user.mobile = request.form.get('mobile')
        current_user.address = request.form.get('address')
        current_user.district = request.form.get('district')
        current_user.state = request.form.get('state')
        db.session.commit()

        # Get FIR form fields
        subject = request.form.get('subject')
        occurrence_date = request.form.get('occurrence_date')
        place_of_occurrence = request.form.get('place_of_occurrence')
        description = request.form.get('description')
        imei_input = request.form.get('imei')
        files = request.files.getlist('multimedia')

        imei_value = imei_input.strip() if imei_input else current_user.imei

        # Convert date string to Python date (if provided)
        occ_date_obj = None
        if occurrence_date:
            try:
                occ_date_obj = datetime.strptime(occurrence_date, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format for occurrence date. Use YYYY-MM-DD.", "danger")
                
        police_officer = User.query.filter_by(role='police').first()
        if not police_officer:
            flash("No police officer available. FIR saved but not assigned.", "warning")

        # Create FIR entry
        fir = FIR(
            complainant_id=current_user.id,
            subject=subject,
            occurrence_date=occ_date_obj,
            place_of_occurrence=place_of_occurrence,
            description=description,
            imei=imei_value,
            assigned_police_id=police_officer.id if police_officer else None
        )
        db.session.add(fir)
        db.session.commit()

        # Save uploaded files as Evidence
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                ev = Evidence(fir_id=fir.id, file_path=f"uploads/{filename}", uploaded_by=current_user.id)
                db.session.add(ev)

        db.session.commit()

        # Save location if provided
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        if lat and lng:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                loc = UserLocation(user_id=current_user.id, latitude=lat_f, longitude=lng_f)
                db.session.add(loc)
                db.session.commit()
            except ValueError:
                pass

        # Send email confirmation
        send_email(
            subject=f"FIR #{fir.id} Submitted Successfully",
            recipients=[current_user.email] if current_user.email else [],
            body=f"Dear {current_user.name},\n\nYour FIR (ID: {fir.id}) has been submitted successfully.\n\nRegards,\nE-Police"
        )

        flash('FIR submitted successfully!', 'success')
        return redirect(url_for('dashboard'))

    # GET request → render FIR form
    return render_template('submit_fir.html', user=current_user)


# -------- Evidence Verification (Police) --------
@app.route('/verify_evidence/<int:evidence_id>', methods=['POST'])
@login_required
@police_or_admin_required
def verify_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    action = request.form.get('action')
    remarks = request.form.get('remarks', '').strip()

    if not action:
        flash("Invalid action.", "danger")
        return redirect(url_for('police_dashboard'))

    # Allow only assigned police or admin
    if current_user.role == 'police' and (
        not evidence.fir or evidence.fir.assigned_police_id != current_user.id
    ):
        flash("Unauthorized action. You cannot verify this evidence.", "danger")
        return redirect(url_for('police_dashboard'))

    if action == 'verify':
        evidence.status = 'Verified'
        msg = f"Evidence #{evidence.id} verified successfully."
    elif action == 'reject':
        evidence.status = 'Rejected'
        msg = f"Evidence #{evidence.id} rejected."
    else:
        flash("Invalid action.", "danger")
        return redirect(url_for('police_dashboard'))

    evidence.remarks = remarks
    db.session.commit()

    # ✅ Log the action (optional, if EvidenceLog exists)
    try:
        log = EvidenceLog(
            evidence_id=evidence.id,
            action=evidence.status,
            remarks=remarks,
            performed_by_id=current_user.id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print("Log entry skipped:", e)

    # ✅ Notify complainant (if contact info available)
    complainant = evidence.fir.complainant
    if complainant:
        if complainant.email:
            send_email(
                subject=f"Evidence for FIR #{evidence.fir.id} {evidence.status}",
                recipients=[complainant.email],
                body=f"Dear {complainant.name},\n\nYour evidence (ID: {evidence.id}) "
                     f"for FIR #{evidence.fir.id} has been {evidence.status.lower()}.\n"
                     f"Remarks: {remarks or 'N/A'}\n\nRegards,\nE-Police"
            )
        if complainant.mobile:
            send_sms_alert(
                complainant.mobile,
                f"Your evidence (ID {evidence.id}) for FIR #{evidence.fir.id} was {evidence.status}. "
                f"Remarks: {remarks or 'N/A'}"
            )

    flash(msg, "success")
    return redirect(url_for('police_dashboard' if current_user.role == 'police' else 'admin_dashboard'))

@app.route('/admin/override-evidence/<int:evidence_id>', methods=['POST'])
@login_required
@admin_required
def override_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    action = (request.form.get('action') or '').lower()
    remarks = request.form.get('remarks', '')

    if action == "verify":
        evidence.status = "Verified"
    elif action == "reject":
        evidence.status = "Rejected"
    else:
        flash("Invalid action.", "danger")
        return redirect(url_for('admin_dashboard'))

    evidence.remarks = remarks
    db.session.commit()

    # Log admin override
    log = EvidenceLog(
        evidence_id=evidence.id,
        action=f"Admin override: {evidence.status}",
        remarks=remarks,
        performed_by_id=current_user.id
    )
    db.session.add(log)
    db.session.commit()

    # Optionally notify complainant (same pattern as police route)
    try:
        complainant = evidence.fir.complainant
        if complainant and complainant.email:
            send_email(
                subject=f"Evidence for FIR #{evidence.fir.id} {evidence.status}",
                recipients=[complainant.email],
                body=f"Dear {complainant.name},\n\nYour evidence (ID: {evidence.id}) for FIR #{evidence.fir.id} "
                     f"has been {evidence.status.lower()} by admin.\n\nRemarks: {remarks or 'N/A'}\n\nRegards,\nE-Police"
            )
        if complainant and complainant.mobile:
            send_sms_alert(
                complainant.mobile,
                f"Your evidence (ID {evidence.id}) for FIR #{evidence.fir.id} was {evidence.status}. Remarks: {remarks or 'N/A'}"
            )
    except Exception:
        # don't crash if notification fails
        pass

    flash(f"Evidence #{evidence.id} overridden to {evidence.status}.", "success")
    return redirect(url_for('admin_dashboard'))


# -------- View FIR --------
@app.route('/fir/<int:fir_id>', methods=['GET', 'POST'])
@login_required
def view_fir(fir_id):
    fir = FIR.query.get_or_404(fir_id)

    # --- Role-based access ---
    if current_user.role == 'complainant' and fir.complainant_id != current_user.id:
        flash('You can only view your own FIRs.', 'danger')
        return redirect(url_for('dashboard'))
    if current_user.role == 'police' and fir.assigned_police_id != current_user.id:
        flash('You can only view FIRs assigned to you.', 'danger')
        return redirect(url_for('dashboard'))

    # --- Handle POST requests (status update or assignment) ---
    if request.method == 'POST':
        # 1. If admin assigns police
        if current_user.role == 'admin' and request.form.get('police_id'):
            police_id = request.form.get('police_id')
            fir.assigned_police_id = int(police_id)
            db.session.commit()
            flash("Police officer assigned successfully!", "success")
            return redirect(url_for('view_fir', fir_id=fir_id))

        # 2. If police/admin updates FIR status
        if current_user.role not in ['police', 'admin']:
            flash('Unauthorized to update FIR status.', 'danger')
            return redirect(url_for('view_fir', fir_id=fir_id))

        status = request.form.get('status')
        comment = request.form.get('comment')

        if status not in ['pending', 'in-progress', 'closed']:
            flash('Invalid status.', 'danger')
            return redirect(url_for('view_fir', fir_id=fir_id))

        fir.status = status
        update = FIRStatusUpdate(
            fir_id=fir.id,
            updated_by_id=current_user.id,
            status=status,
            comment=comment
        )
        db.session.add(update)
        db.session.commit()

        # --- Notifications ---
        if fir.complainant and fir.complainant.email:
             send_email(
                 subject=f"FIR #{fir.id} status updated",
                 recipients=[fir.complainant.email],
                 body=f"Hello {fir.complainant.username},\n\nYour FIR #{fir.id} status is now: {status.capitalize()}.\n\nRegards,\nE-Police"
             )


        if fir.complainant.mobile:
            send_sms_alert(
                fir.complainant.mobile,
                f"Hello {fir.complainant.username}, your FIR #{fir.id} status updated to '{status}'. Comments: {comment}"
            )

        flash('FIR status updated.', 'success')
        return redirect(url_for('view_fir', fir_id=fir_id))

    # --- GET request: load related data ---
    updates = FIRStatusUpdate.query.filter_by(fir_id=fir.id).order_by(FIRStatusUpdate.timestamp.desc()).all()
    evidences = Evidence.query.filter_by(fir_id=fir.id).all()
    police_officers = User.query.filter_by(role='police').all()  # ✅ Added

    return render_template(
        'view_fir.html',
        fir=fir,
        updates=updates,
        evidences=evidences,
        police_officers=police_officers  # ✅ Pass to template
    )

@app.route('/admin/assign-police/<int:fir_id>', methods=['POST'], endpoint="assign_police_to_fir")
@login_required
def assign_police_to_fir(fir_id):
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    police_id = request.form.get("police_id")
    fir = FIR.query.get_or_404(fir_id)

    if police_id:
        fir.assigned_police_id = police_id
        db.session.commit()
        flash(f"FIR #{fir.id} assigned to police officer {police_id}.", "success")
    else:
        flash("No police officer selected.", "warning")

    return redirect(url_for("police_dashboard"))

# -------- Logout --------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# -------- Admin Routes --------
@app.route('/admin/ban-user/<int:user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash("Cannot ban another admin.", "danger")
        return redirect(url_for('dashboard'))
    user.is_active = False
    db.session.commit()
    flash(f'User {user.username} banned successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/assign-police/<int:fir_id>', methods=['POST'])
@admin_required
def assign_police(fir_id):
    fir = FIR.query.get_or_404(fir_id)
    police_id = request.form.get('police_id')
    police = User.query.filter_by(id=police_id, role='police').first()
    if not police:
        flash('Invalid police officer.', 'danger')
        return redirect(url_for('dashboard'))
    fir.assigned_police_id = police.id
    db.session.commit()
    flash(f'Police assigned to FIR #{fir.id} successfully.', 'success')
    return redirect(url_for('view_fir', fir_id=fir.id))

# -------- Admin Evidence Override --------
@app.route('/evidence/<int:evidence_id>/verify', methods=['POST'])
@login_required
@police_required
def police_verify_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)

    if evidence.fir.assigned_police_id != current_user.id:
        flash("Unauthorized action. You cannot verify this evidence.", "danger")
        return redirect(url_for('police_dashboard'))

    action = request.form.get('action')
    remarks = request.form.get('remarks', '')

    if action == "verify":
        evidence.status = "Verified"
        msg = "Evidence verified successfully!"
    elif action == "reject":
        evidence.status = "Rejected"
        msg = "Evidence rejected successfully!"
    else:
        flash("Invalid action.", "danger")
        return redirect(url_for('police_dashboard'))

    evidence.remarks = remarks
    db.session.commit()

    # ✅ Log police verification/rejection
    log = EvidenceLog(
        evidence_id=evidence.id,
        action=evidence.status,   # "Verified" or "Rejected"
        remarks=remarks,
        performed_by_id=current_user.id
    )
    db.session.add(log)
    db.session.commit()

    # Notify complainant
    complainant = evidence.fir.complainant
    if complainant.email:
        send_email(
            subject=f"Evidence for FIR #{evidence.fir.id} {evidence.status}",
            recipients=[complainant.email],
            body=f"Dear {complainant.name},\n\nYour evidence (ID: {evidence.id}) "
                 f"for FIR #{evidence.fir.id} has been {evidence.status.lower()}.\n"
                 f"Remarks: {remarks or 'N/A'}\n\nRegards,\nE-Police"
        )
    if complainant.mobile:
        send_sms_alert(
            complainant.mobile,
            f"Your evidence (ID {evidence.id}) for FIR #{evidence.fir.id} was {evidence.status}. "
            f"Remarks: {remarks or 'N/A'}"
        )

    flash(msg, "success")
    return redirect(url_for('police_dashboard'))

# -------- Geo-tracking --------
@app.route('/api/submit-location', methods=['POST'])
@login_required
def submit_location():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if None in (latitude, longitude):
        return jsonify({'error': 'Missing latitude or longitude'}), 400
    loc = UserLocation(user_id=current_user.id, latitude=latitude, longitude=longitude)
    db.session.add(loc)
    current_user.location = f"{latitude},{longitude}"
    db.session.commit()
    return jsonify({'message': 'Location saved'}), 200

@app.route('/api/locations', methods=['GET'])
@admin_required
def get_locations():
    # Get the latest timestamp per user
    subs = db.session.query(
        UserLocation.user_id, 
        db.func.max(UserLocation.timestamp).label('ts')
    ).group_by(UserLocation.user_id).all()

    data = []
    for user_id, ts in subs:
        # Get the latest location for this user
        loc = UserLocation.query.filter_by(user_id=user_id).order_by(UserLocation.timestamp.desc()).first()
        if loc:
            data.append({
                'user_id': loc.user_id,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'timestamp': loc.timestamp.isoformat()
            })
    return jsonify(data), 200



@app.route('/admin/locations')
@login_required
@admin_required
def admin_locations():
    # Get latest location timestamp per user
    subs = db.session.query(UserLocation.user_id, func.max(UserLocation.timestamp).label('ts')) \
                     .group_by(UserLocation.user_id).all()

    locations = []
    for user_id, ts in subs:
        loc = UserLocation.query.filter_by(user_id=user_id).order_by(UserLocation.timestamp.desc()).first()
        if loc:
            locations.append({
                'user_id': loc.user_id,
                'latitude': float(loc.latitude),
                'longitude': float(loc.longitude),
                'timestamp': loc.timestamp.isoformat()
            })
    return render_template('admin_locations.html', locations=locations)

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
