import os
import secrets
import json
from datetime import datetime, timedelta

from flask import (Flask, render_template, redirect, url_for, request,
                   flash, session, jsonify)
from models import db, Admin, Teacher, Student, Class, AttendanceSession, Attendance
from qr_generator import generate_student_qr_b64, generate_session_qr_b64
from location_verify import is_within_radius

# ─────────────────────────── App Setup ──────────────────────────────────────

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Render gives postgres:// but SQLAlchemy needs postgresql://
database_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

db.init_app(app)

# ─────────────────────────── DB Init / Seed ─────────────────────────────────

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(name="Super Admin", email="admin@attend.com")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created: admin@attend.com / admin123")

# ─────────────────────────── Helpers ─────────────────────────────────────────

def login_required(role):
    """Decorator factory — ensures user is logged in with the correct role."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ─────────────────────────── Auth Routes ─────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        user = None
        if role == "admin":
            user = Admin.query.filter_by(email=email).first()
        elif role == "teacher":
            user = Teacher.query.filter_by(email=email).first()
        elif role == "student":
            user = Student.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.permanent = True
            session["user_id"] = user.id
            session["role"] = role
            session["name"] = user.name
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for(f"{role}_dashboard"))
        flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ─────────────────────────── Admin Routes ─────────────────────────────────────

@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    teachers = Teacher.query.all()
    students = Student.query.all()
    classes = Class.query.all()
    attendance_records = Attendance.query.order_by(Attendance.timestamp.desc()).limit(100).all()
    return render_template("admin_dashboard.html",
                           teachers=teachers, students=students,
                           classes=classes, attendance_records=attendance_records)


@app.route("/admin/add-teacher", methods=["POST"])
@login_required("admin")
def add_teacher():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not all([name, email, password]):
        flash("All fields are required.", "danger")
    elif Teacher.query.filter_by(email=email).first():
        flash("A teacher with that email already exists.", "warning")
    else:
        t = Teacher(name=name, email=email)
        t.set_password(password)
        db.session.add(t)
        db.session.commit()
        flash(f"Teacher '{name}' added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-teacher/<int:tid>", methods=["POST"])
@login_required("admin")
def delete_teacher(tid):
    t = Teacher.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    flash("Teacher deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/add-student", methods=["POST"])
@login_required("admin")
def add_student():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    roll = request.form.get("roll_number", "").strip()
    password = request.form.get("password", "")
    if not all([name, email, roll, password]):
        flash("All fields are required.", "danger")
    elif Student.query.filter_by(email=email).first():
        flash("A student with that email already exists.", "warning")
    elif Student.query.filter_by(roll_number=roll).first():
        flash("Roll number already exists.", "warning")
    else:
        s = Student(name=name, email=email, roll_number=roll)
        s.set_password(password)
        db.session.add(s)
        db.session.commit()
        flash(f"Student '{name}' added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-student/<int:sid>", methods=["POST"])
@login_required("admin")
def delete_student(sid):
    s = Student.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash("Student deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/add-class", methods=["POST"])
@login_required("admin")
def add_class():
    class_name = request.form.get("class_name", "").strip()
    subject = request.form.get("subject", "").strip()
    section = request.form.get("section", "").strip()
    teacher_id = request.form.get("teacher_id", "")
    if not all([class_name, subject, section, teacher_id]):
        flash("All fields are required.", "danger")
    else:
        c = Class(class_name=class_name, subject=subject,
                  section=section, teacher_id=int(teacher_id))
        db.session.add(c)
        db.session.commit()
        flash(f"Class '{class_name}' created.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-class/<int:cid>", methods=["POST"])
@login_required("admin")
def delete_class(cid):
    c = Class.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash("Class deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/attendance-report")
@login_required("admin")
def attendance_report():
    records = (Attendance.query
               .join(Student, Attendance.student_id == Student.id)
               .join(Class, Attendance.class_id == Class.id)
               .order_by(Attendance.timestamp.desc()).all())
    return render_template("attendance_report.html", records=records, is_admin=True)

# ─────────────────────────── Teacher Routes ───────────────────────────────────

@app.route("/teacher")
@login_required("teacher")
def teacher_dashboard():
    teacher_id = session["user_id"]
    classes = Class.query.filter_by(teacher_id=teacher_id).all()
    active_session = (AttendanceSession.query
                      .join(Class, AttendanceSession.class_id == Class.id)
                      .filter(Class.teacher_id == teacher_id,
                              AttendanceSession.active == True).first())
    
    # Fetch past 10 expired sessions for the teacher
    past_sessions = (AttendanceSession.query
                     .join(Class, AttendanceSession.class_id == Class.id)
                     .filter(Class.teacher_id == teacher_id,
                             AttendanceSession.active == False)
                     .order_by(AttendanceSession.start_time.desc())
                     .limit(10).all())

    return render_template("teacher_dashboard.html",
                           classes=classes, 
                           active_session=active_session,
                           past_sessions=past_sessions)


@app.route("/teacher/update-location/<int:class_id>", methods=["POST"])
@login_required("teacher")
def update_class_location(class_id):
    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403
    cls.latitude = lat
    cls.longitude = lon
    db.session.commit()
    return jsonify({"success": True, "lat": lat, "lon": lon})


@app.route("/teacher/start-session", methods=["POST"])
@login_required("teacher")
def start_session():
    data = request.get_json()
    class_id = data.get("class_id")
    duration = int(data.get("duration", 30))
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    # Deactivate any previous active sessions for this class
    AttendanceSession.query.filter_by(class_id=class_id, active=True).update({"active": False})
    db.session.commit()

    token = secrets.token_hex(16)
    sess = AttendanceSession(class_id=class_id,
                             session_token=token,
                             duration_seconds=duration)
    db.session.add(sess)
    db.session.commit()

    qr_b64 = generate_session_qr_b64(cls.id, sess.id)
    return jsonify({
        "success": True,
        "session_id": sess.id,
        "token": token,
        "qr_b64": qr_b64,
        "duration": duration,
    })


@app.route("/teacher/end-session/<int:session_id>", methods=["POST"])
@login_required("teacher")
def end_session(session_id):
    sess = AttendanceSession.query.get_or_404(session_id)
    sess.active = False
    db.session.commit()
    return jsonify({"success": True})


@app.route("/teacher/attendance-report/<int:class_id>")
@login_required("teacher")
def teacher_attendance_report(class_id):
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != session["user_id"]:
        flash("Unauthorized.", "danger")
        return redirect(url_for("teacher_dashboard"))
    records = (Attendance.query
               .filter_by(class_id=class_id)
               .order_by(Attendance.timestamp.desc()).all())
    return render_template("attendance_report.html",
                           records=records, cls=cls, is_admin=False)


@app.route("/teacher/session-report/<int:session_id>")
@login_required("teacher")
def teacher_session_report(session_id):
    sess = AttendanceSession.query.get_or_404(session_id)
    if sess.cls.teacher_id != session["user_id"]:
        flash("Unauthorized.", "danger")
        return redirect(url_for("teacher_dashboard"))
    
    records = (Attendance.query
               .filter_by(session_id=session_id)
               .order_by(Attendance.timestamp.desc()).all())
    return render_template("attendance_report.html",
                           records=records, cls=sess.cls, sess=sess, is_admin=False)

# ─────────────────────────── Student Routes ───────────────────────────────────

@app.route("/student")
@login_required("student")
def student_dashboard():
    # Find active sessions for ALL classes
    active_sessions = (AttendanceSession.query
                       .filter_by(active=True)
                       .order_by(AttendanceSession.start_time.desc()).all())
                       
    # Find past attendance history for this student
    past_records = (Attendance.query
                    .filter_by(student_id=session["user_id"])
                    .order_by(Attendance.timestamp.desc())
                    .limit(20).all())

    return render_template("student_dashboard.html",
                           active_sessions=active_sessions,
                           past_records=past_records)

@app.route("/student/generate-qr", methods=["POST"])
@login_required("student")
def generate_student_qr():
    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")
    session_id = data.get("session_id")
    student_id = session["user_id"]

    att_sess = AttendanceSession.query.get_or_404(session_id)
    if not att_sess.active or att_sess.is_expired():
        att_sess.active = False
        db.session.commit()
        return jsonify({"error": "Session expired or inactive."}), 400

    already = Attendance.query.filter_by(
        student_id=student_id, session_id=session_id).first()
    if already:
        return jsonify({"error": "You have already marked attendance for this session."}), 400

    qr_b64 = generate_student_qr_b64(student_id, att_sess.class_id, session_id, lat, lon)
    return jsonify({"success": True, "qr_b64": qr_b64})

# ─────────────────────────── Mark Attendance API ──────────────────────────────

@app.route("/api/mark-attendance", methods=["POST"])
@login_required("teacher")
def mark_attendance():
    """Teacher scanner calls this endpoint after reading student QR."""
    data = request.get_json()
    try:
        payload = data if isinstance(data, dict) else json.loads(data)
    except Exception:
        return jsonify({"error": "Invalid QR payload"}), 400

    if payload.get("type") != "student":
        return jsonify({"error": "Not a student QR code"}), 400

    student_id = payload.get("student_id")
    class_id = payload.get("class_id")
    sess_id = payload.get("session_id")
    student_lat = payload.get("lat")
    student_lon = payload.get("lon")

    # Validate session
    att_sess = AttendanceSession.query.get(sess_id)
    if not att_sess or not att_sess.active:
        return jsonify({"error": "Session is not active."}), 400
    if att_sess.is_expired():
        att_sess.active = False
        db.session.commit()
        return jsonify({"error": "Attendance window has expired."}), 400
    if att_sess.class_id != class_id:
        return jsonify({"error": "Class mismatch."}), 400

    # Validate class → teacher ownership
    cls = Class.query.get(class_id)
    if not cls or cls.teacher_id != session["user_id"]:
        return jsonify({"error": "Unauthorised teacher."}), 403

    # Duplicate check
    existing = Attendance.query.filter_by(
        student_id=student_id, session_id=sess_id).first()
    if existing:
        return jsonify({"error": "Attendance already marked for this student.", "status": existing.status}), 400

    # Location check
    if cls.latitude is None or cls.longitude is None:
        return jsonify({"error": "Classroom location not set."}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found."}), 404

    within, dist = is_within_radius(student_lat, student_lon, cls.latitude, cls.longitude)
    status = "Present" if within else "Rejected"

    record = Attendance(
        student_id=student_id,
        class_id=class_id,
        session_id=sess_id,
        status=status,
        distance_m=dist,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "success": True,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "status": status,
        "distance_m": dist,
    })


@app.route("/api/session-status/<int:session_id>")
def session_status(session_id):
    sess = AttendanceSession.query.get(session_id)
    if not sess:
        return jsonify({"active": False})
    expired = sess.is_expired()
    if expired and sess.active:
        sess.active = False
        db.session.commit()
    elapsed = (datetime.utcnow() - sess.start_time).total_seconds()
    remaining = max(0, sess.duration_seconds - int(elapsed))
    return jsonify({
        "active": sess.active and not expired,
        "remaining": remaining,
        "duration": sess.duration_seconds,
    })


# ─────────────────────────── Run ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
