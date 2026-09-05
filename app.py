from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory
)

import sqlite3
import re
import os

from datetime import date, datetime

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "careertrack_secret_key"


# ============================================================
# RESUME FEATURE - UPLOAD CONFIGURATION
# ============================================================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads",
    "resumes"
)

ALLOWED_RESUME_EXTENSIONS = {
    "pdf",
    "doc",
    "docx"
}

MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_RESUME_SIZE


# ============================================================
# DATABASE
# ============================================================

def get_database():

    connection = sqlite3.connect(
        "careertrack.db",
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA busy_timeout = 10000"
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# APPLICATION STATUSES
# ============================================================

APPLICATION_STATUSES = [
    "Applied",
    "Shortlisted",
    "Assessment",
    "Interview",
    "Selected",
    "Rejected",
    "Withdrawn"
]


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

def create_tables():

    connection = get_database()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            college TEXT,
            degree TEXT,
            branch TEXT,
            graduation_year TEXT,
            skills TEXT,
            career_status TEXT,
            current_year TEXT,
            experience TEXT,
            preferred_role TEXT,
            preferred_location TEXT,
            career_goal TEXT
        )
    """)

    # --------------------------------------------------------
    # JOBS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT,
            position TEXT,
            location TEXT,
            salary TEXT,
            job_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # INTERNSHIPS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT,
            position TEXT,
            location TEXT,
            stipend TEXT,
            duration TEXT,
            internship_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # ASSESSMENTS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT,
            assessment_name TEXT,
            assessment_type TEXT,
            scheduled_date TEXT,
            end_date TEXT,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # APPLICATIONS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT,
            position TEXT,
            status TEXT,
            application_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # APPLICATION HISTORY
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS application_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            changed_date TEXT NOT NULL,
            FOREIGN KEY (application_id)
                REFERENCES applications(id)
        )
    """)

    # --------------------------------------------------------
    # FIX OLD APPLICATION HISTORY TABLE
    # --------------------------------------------------------

    columns = connection.execute("""
        PRAGMA table_info(application_history)
    """).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "changed_date" not in column_names:

        connection.execute("""
            ALTER TABLE application_history
            ADD COLUMN changed_date TEXT
        """)

        if "changed_at" in column_names:

            connection.execute("""
                UPDATE application_history
                SET changed_date = changed_at
                WHERE changed_date IS NULL
            """)

        else:

            connection.execute("""
                UPDATE application_history
                SET changed_date = ?
                WHERE changed_date IS NULL
            """, (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ))

    # --------------------------------------------------------
    # INTERVIEWS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            interview_round TEXT NOT NULL,
            interview_date TEXT NOT NULL,
            interview_time TEXT,
            mode TEXT,
            meeting_link TEXT,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ========================================================
    # RESUME FEATURE - RESUMES TABLE
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            uploaded_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


create_tables()


# ============================================================
# LOGIN CHECK
# ============================================================

def login_required():

    return "user_id" in session


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def validate_password(password):

    if len(password) < 8:
        return "Password must contain at least 8 characters."

    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."

    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one special character."

    return None


# ============================================================
# RESUME FEATURE - FILE VALIDATION
# ============================================================

def allowed_resume_file(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_RESUME_EXTENSIONS


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template("index.html")


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        if password != confirm_password:
            return "Passwords do not match."

        college = request.form.get(
            "college",
            ""
        ).strip()

        degree = request.form.get(
            "degree",
            ""
        ).strip()

        branch = request.form.get(
            "branch",
            ""
        ).strip()

        graduation_year = request.form.get(
            "graduation_year",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        career_status = request.form.get(
            "career_status",
            ""
        ).strip()

        current_year = request.form.get(
            "current_year",
            ""
        ).strip()

        experience = request.form.get(
            "experience",
            ""
        ).strip()

        preferred_role = request.form.get(
            "preferred_role",
            ""
        ).strip()

        preferred_location = request.form.get(
            "preferred_location",
            ""
        ).strip()

        career_goal = request.form.get(
            "career_goal",
            ""
        ).strip()

        password_error = validate_password(password)

        if password_error:
            return password_error

        hashed_password = generate_password_hash(password)

        connection = get_database()

        try:

            connection.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    phone,
                    password,
                    college,
                    degree,
                    branch,
                    graduation_year,
                    skills,
                    career_status,
                    current_year,
                    experience,
                    preferred_role,
                    preferred_location,
                    career_goal
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                phone,
                hashed_password,
                college,
                degree,
                branch,
                graduation_year,
                skills,
                career_status,
                current_year,
                experience,
                preferred_role,
                preferred_location,
                career_goal
            ))

            connection.commit()

        except sqlite3.IntegrityError:

            connection.close()

            return "Email already registered."

        connection.close()

        return redirect("/login")

    return render_template("register.html")


# ============================================================
# CHECK EMAIL
# ============================================================

@app.route("/check-email")
def check_email():

    email = request.args.get(
        "email",
        ""
    ).strip()

    if not email:

        return {
            "exists": False
        }

    connection = get_database()

    user = connection.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    connection.close()

    return {
        "exists": user is not None
    }


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        connection = get_database()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        connection.close()

        if user:

            try:

                password_correct = check_password_hash(
                    user["password"],
                    password
                )

            except ValueError:

                password_correct = False

            if password_correct:

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]

                return redirect("/dashboard")

        return "Invalid email or password."

    return render_template("login.html")


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        ).strip()

        password_error = validate_password(
            new_password
        )

        if password_error:
            return password_error

        connection = get_database()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        if user:

            hashed_password = generate_password_hash(
                new_password
            )

            connection.execute("""
                UPDATE users
                SET password = ?
                WHERE email = ?
            """, (
                hashed_password,
                email
            ))

            connection.commit()
            connection.close()

            return redirect("/login")

        connection.close()

        return "Email not found."

    return render_template(
        "forgot_password.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    # --------------------------------------------------------
    # TOTAL COUNTS
    # --------------------------------------------------------

    total_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    total_jobs = connection.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    total_internships = connection.execute("""
        SELECT COUNT(*)
        FROM internships
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    total_assessments = connection.execute("""
        SELECT COUNT(*)
        FROM assessments
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    total_interviews = connection.execute("""
        SELECT COUNT(*)
        FROM interviews
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    # --------------------------------------------------------
    # APPLICATION STATUS COUNTS
    # --------------------------------------------------------

    applied_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Applied'
    """, (user_id,)).fetchone()[0]

    shortlisted_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Shortlisted'
    """, (user_id,)).fetchone()[0]

    assessment_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Assessment'
    """, (user_id,)).fetchone()[0]

    interview_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Interview'
    """, (user_id,)).fetchone()[0]

    selected_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Selected'
    """, (user_id,)).fetchone()[0]

    rejected_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Rejected'
    """, (user_id,)).fetchone()[0]

    withdrawn_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE user_id = ?
        AND status = 'Withdrawn'
    """, (user_id,)).fetchone()[0]

    # --------------------------------------------------------
    # RECENT APPLICATIONS
    # --------------------------------------------------------

    recent_applications = connection.execute("""
        SELECT *
        FROM applications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    # --------------------------------------------------------
    # UPCOMING ASSESSMENTS
    # --------------------------------------------------------

    upcoming_assessments = connection.execute("""
        SELECT *
        FROM assessments
        WHERE user_id = ?
        AND scheduled_date >= date('now')
        ORDER BY scheduled_date ASC
        LIMIT 5
    """, (user_id,)).fetchall()

    # --------------------------------------------------------
    # UPCOMING INTERVIEWS
    # --------------------------------------------------------

    upcoming_interviews = connection.execute("""
        SELECT *
        FROM interviews
        WHERE user_id = ?
        AND interview_date >= date('now')
        AND status IN ('Scheduled', 'Rescheduled')
        ORDER BY interview_date ASC, interview_time ASC
        LIMIT 5
    """, (user_id,)).fetchall()

    # --------------------------------------------------------
    # INTERVIEW TOMORROW
    # --------------------------------------------------------

    interview_tomorrow = connection.execute("""
        SELECT *
        FROM interviews
        WHERE user_id = ?
        AND interview_date = date('now', '+1 day')
        AND status IN ('Scheduled', 'Rescheduled')
        ORDER BY interview_time ASC
    """, (user_id,)).fetchall()

    # --------------------------------------------------------
    # INTERVIEW IN TWO DAYS
    # --------------------------------------------------------

    interview_in_two_days = connection.execute("""
        SELECT *
        FROM interviews
        WHERE user_id = ?
        AND interview_date = date('now', '+2 day')
        AND status IN ('Scheduled', 'Rescheduled')
        ORDER BY interview_time ASC
    """, (user_id,)).fetchall()

    # ========================================================
    # NOTIFICATIONS
    # ========================================================

    notifications = []

    # --------------------------------------------------------
    # ASSESSMENTS TODAY
    # --------------------------------------------------------

    assessments_today = connection.execute("""
        SELECT *
        FROM assessments
        WHERE user_id = ?
        AND scheduled_date = date('now')
    """, (user_id,)).fetchall()

    for assessment in assessments_today:

        notifications.append({
            "message":
                "Your "
                + assessment["company"]
                + " "
                + assessment["assessment_name"]
                + " is today!",

            "url": "/assessments"
        })

    # --------------------------------------------------------
    # INTERVIEWS TODAY
    # --------------------------------------------------------

    interviews_today = connection.execute("""
        SELECT *
        FROM interviews
        WHERE user_id = ?
        AND interview_date = date('now')
        AND status IN ('Scheduled', 'Rescheduled')
        ORDER BY interview_time ASC
    """, (user_id,)).fetchall()

    for interview in interviews_today:

        notifications.append({
            "message":
                "Your "
                + interview["company"]
                + " interview is today!",

            "url": "/interviews"
        })

    # --------------------------------------------------------
    # ASSESSMENTS TOMORROW
    # --------------------------------------------------------

    assessments_tomorrow = connection.execute("""
        SELECT *
        FROM assessments
        WHERE user_id = ?
        AND scheduled_date = date('now', '+1 day')
    """, (user_id,)).fetchall()

    for assessment in assessments_tomorrow:

        notifications.append({
            "message":
                "Your "
                + assessment["company"]
                + " "
                + assessment["assessment_name"]
                + " is tomorrow.",

            "url": "/assessments"
        })

    # --------------------------------------------------------
    # ASSESSMENTS IN TWO DAYS
    # --------------------------------------------------------

    assessments_in_two_days = connection.execute("""
        SELECT *
        FROM assessments
        WHERE user_id = ?
        AND scheduled_date = date('now', '+2 day')
    """, (user_id,)).fetchall()

    for assessment in assessments_in_two_days:

        notifications.append({
            "message":
                "Your "
                + assessment["company"]
                + " "
                + assessment["assessment_name"]
                + " is in 2 days.",

            "url": "/assessments"
        })

    # --------------------------------------------------------
    # INTERVIEWS TOMORROW
    # --------------------------------------------------------

    for interview in interview_tomorrow:

        notifications.append({
            "message":
                "Your "
                + interview["company"]
                + " interview is tomorrow.",

            "url": "/interviews"
        })

    # --------------------------------------------------------
    # INTERVIEWS IN TWO DAYS
    # --------------------------------------------------------

    for interview in interview_in_two_days:

        notifications.append({
            "message":
                "Your "
                + interview["company"]
                + " interview is in 2 days.",

            "url": "/interviews"
        })

    # --------------------------------------------------------
    # PENDING APPLICATIONS
    # --------------------------------------------------------

    pending_applications = connection.execute("""
        SELECT *
        FROM applications
        WHERE user_id = ?
        AND status = 'Applied'
        ORDER BY id DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    for application in pending_applications:

        notifications.append({
            "message":
                "Your "
                + application["company"]
                + " application is still pending.",

            "url":
                "/application/"
                + str(application["id"])
        })

    connection.close()

    return render_template(
        "dashboard.html",
        user=user,
        total_applications=total_applications,
        total_jobs=total_jobs,
        total_internships=total_internships,
        total_assessments=total_assessments,
        total_interviews=total_interviews,
        applied_count=applied_count,
        shortlisted_count=shortlisted_count,
        assessment_count=assessment_count,
        interview_count=interview_count,
        selected_count=selected_count,
        rejected_count=rejected_count,
        withdrawn_count=withdrawn_count,
        recent_applications=recent_applications,
        upcoming_assessments=upcoming_assessments,
        upcoming_interviews=upcoming_interviews,
        interview_tomorrow=interview_tomorrow,
        interview_in_two_days=interview_in_two_days,
        notifications=notifications
    )


# ============================================================
# JOBS - SEARCH + FILTER + ADD
# ============================================================

@app.route(
    "/jobs",
    methods=["GET", "POST"]
)
def jobs():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    # --------------------------------------------------------
    # ADD JOB
    # --------------------------------------------------------

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        salary = request.form.get(
            "salary",
            ""
        ).strip()

        job_date = request.form.get(
            "job_date",
            ""
        ).strip()

        if company and position:

            connection.execute("""
                INSERT INTO jobs
                (
                    user_id,
                    company,
                    position,
                    location,
                    salary,
                    job_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                company,
                position,
                location,
                salary,
                job_date
            ))

            connection.commit()

        connection.close()

        return redirect("/jobs")

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = request.args.get(
        "search",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    sort = request.args.get(
        "sort",
        "newest"
    ).strip()

    # --------------------------------------------------------
    # BUILD QUERY
    # --------------------------------------------------------

    query = """
        SELECT *
        FROM jobs
        WHERE user_id = ?
    """

    parameters = [user_id]

    if search:

        query += """
            AND (
                LOWER(company) LIKE ?
                OR LOWER(position) LIKE ?
            )
        """

        search_value = "%" + search.lower() + "%"

        parameters.append(search_value)
        parameters.append(search_value)

    if location:

        query += """
            AND LOWER(location) LIKE ?
        """

        location_value = "%" + location.lower() + "%"

        parameters.append(location_value)

    if sort == "oldest":

        query += """
            ORDER BY job_date ASC, id ASC
        """

    elif sort == "company":

        query += """
            ORDER BY company ASC
        """

    else:

        query += """
            ORDER BY job_date DESC, id DESC
        """

    jobs_list = connection.execute(
        query,
        parameters
    ).fetchall()

    total_jobs = connection.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    connection.close()

    return render_template(
        "jobs.html",
        jobs=jobs_list,
        search=search,
        location=location,
        sort=sort,
        total_jobs=total_jobs,
        today=date.today().isoformat()
    )


# ============================================================
# VIEW JOB DETAILS
# ============================================================

@app.route("/job/<int:id>")
def job_details(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    job = connection.execute("""
        SELECT *
        FROM jobs
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    connection.close()

    if job is None:
        return redirect("/jobs")

    return render_template(
        "job_details.html",
        job=job
    )


# ============================================================
# EDIT JOB
# ============================================================

@app.route(
    "/edit-job/<int:id>",
    methods=["GET", "POST"]
)
def edit_job(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    job = connection.execute("""
        SELECT *
        FROM jobs
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if job is None:

        connection.close()

        return redirect("/jobs")

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        salary = request.form.get(
            "salary",
            ""
        ).strip()

        job_date = request.form.get(
            "job_date",
            ""
        ).strip()

        connection.execute("""
            UPDATE jobs
            SET
                company = ?,
                position = ?,
                location = ?,
                salary = ?,
                job_date = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            company,
            position,
            location,
            salary,
            job_date,
            id,
            user_id
        ))

        connection.commit()
        connection.close()

        return redirect("/jobs")

    connection.close()

    return render_template(
        "edit_job.html",
        job=job
    )


# ============================================================
# DELETE JOB
# ============================================================

@app.route(
    "/delete-job/<int:id>",
    methods=["GET", "POST"]
)
def delete_job(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    connection.execute("""
        DELETE FROM jobs
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/jobs")


# ============================================================
# INTERNSHIPS
# ============================================================

@app.route(
    "/internships",
    methods=["GET", "POST"]
)
def internships():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        stipend = request.form.get(
            "stipend",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        internship_date = request.form.get(
            "internship_date",
            ""
        ).strip()

        connection.execute("""
            INSERT INTO internships
            (
                user_id,
                company,
                position,
                location,
                stipend,
                duration,
                internship_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            company,
            position,
            location,
            stipend,
            duration,
            internship_date
        ))

        connection.commit()
        connection.close()

        return redirect("/internships")

    internships_list = connection.execute("""
        SELECT *
        FROM internships
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    connection.close()

    return render_template(
        "internships.html",
        internships=internships_list
    )


# ============================================================
# EDIT INTERNSHIP
# ============================================================

@app.route(
    "/edit-internship/<int:id>",
    methods=["GET", "POST"]
)
def edit_internship(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    internship = connection.execute("""
        SELECT *
        FROM internships
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if internship is None:

        connection.close()

        return redirect("/internships")

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        stipend = request.form.get(
            "stipend",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        internship_date = request.form.get(
            "internship_date",
            ""
        ).strip()

        connection.execute("""
            UPDATE internships
            SET
                company = ?,
                position = ?,
                location = ?,
                stipend = ?,
                duration = ?,
                internship_date = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            company,
            position,
            location,
            stipend,
            duration,
            internship_date,
            id,
            user_id
        ))

        connection.commit()
        connection.close()

        return redirect("/internships")

    connection.close()

    return render_template(
        "edit_internship.html",
        internship=internship
    )


# ============================================================
# DELETE INTERNSHIP
# ============================================================

@app.route(
    "/delete-internship/<int:id>",
    methods=["GET", "POST"]
)
def delete_internship(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    connection.execute("""
        DELETE FROM internships
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/internships")


# ============================================================
# ASSESSMENTS
# ============================================================

@app.route(
    "/assessments",
    methods=["GET", "POST"]
)
def assessments():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        assessment_name = request.form.get(
            "assessment_name",
            ""
        ).strip()

        assessment_type = request.form.get(
            "assessment_type",
            ""
        ).strip()

        scheduled_date = request.form.get(
            "scheduled_date",
            ""
        ).strip()

        end_date = request.form.get(
            "end_date",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        connection.execute("""
            INSERT INTO assessments
            (
                user_id,
                company,
                assessment_name,
                assessment_type,
                scheduled_date,
                end_date,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            company,
            assessment_name,
            assessment_type,
            scheduled_date,
            end_date,
            status,
            notes
        ))

        connection.commit()
        connection.close()

        return redirect("/assessments")

    assessments_list = connection.execute("""
        SELECT *
        FROM assessments
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    connection.close()

    return render_template(
        "assessments.html",
        assessments=assessments_list
    )


# ============================================================
# EDIT ASSESSMENT
# ============================================================

@app.route(
    "/edit-assessment/<int:id>",
    methods=["GET", "POST"]
)
def edit_assessment(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    assessment = connection.execute("""
        SELECT *
        FROM assessments
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if assessment is None:

        connection.close()

        return redirect("/assessments")

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        assessment_name = request.form.get(
            "assessment_name",
            ""
        ).strip()

        assessment_type = request.form.get(
            "assessment_type",
            ""
        ).strip()

        scheduled_date = request.form.get(
            "scheduled_date",
            ""
        ).strip()

        end_date = request.form.get(
            "end_date",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        connection.execute("""
            UPDATE assessments
            SET
                company = ?,
                assessment_name = ?,
                assessment_type = ?,
                scheduled_date = ?,
                end_date = ?,
                status = ?,
                notes = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            company,
            assessment_name,
            assessment_type,
            scheduled_date,
            end_date,
            status,
            notes,
            id,
            user_id
        ))

        connection.commit()
        connection.close()

        return redirect("/assessments")

    connection.close()

    return render_template(
        "edit_assessment.html",
        assessment=assessment
    )


# ============================================================
# DELETE ASSESSMENT
# ============================================================

@app.route(
    "/delete-assessment/<int:id>",
    methods=["GET", "POST"]
)
def delete_assessment(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    connection.execute("""
        DELETE FROM assessments
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/assessments")


# ============================================================
# ADD APPLICATION
# ============================================================

@app.route(
    "/add-application",
    methods=["GET", "POST"]
)
def add_application():

    if not login_required():
        return redirect("/login")

    if request.method == "POST":

        user_id = session["user_id"]

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Applied"
        ).strip()

        application_date = request.form.get(
            "application_date",
            ""
        ).strip()

        if status not in APPLICATION_STATUSES:

            status = "Applied"

        connection = get_database()

        # ----------------------------------------------------
        # CREATE APPLICATION
        # ----------------------------------------------------

        connection.execute("""
            INSERT INTO applications
            (
                user_id,
                company,
                position,
                status,
                application_date
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            company,
            position,
            status,
            application_date
        ))

        application_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        # ----------------------------------------------------
        # CREATE FIRST TIMELINE ENTRY
        # ----------------------------------------------------

        changed_date = application_date

        if not changed_date:

            changed_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        connection.execute("""
            INSERT INTO application_history
            (
                application_id,
                status,
                changed_date
            )
            VALUES (?, ?, ?)
        """, (
            application_id,
            status,
            changed_date
        ))

        connection.commit()
        connection.close()

        return redirect("/applications")

    return render_template(
        "add_application.html",
        application_statuses=APPLICATION_STATUSES
    )


# ============================================================
# APPLICATIONS
# ============================================================

@app.route("/applications")
def applications():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    applications_list = connection.execute("""
        SELECT *
        FROM applications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    connection.close()

    return render_template(
        "applications.html",
        applications=applications_list
    )


# ============================================================
# APPLICATION DETAILS + TIMELINE
# ============================================================

@app.route("/application/<int:id>")
def application_details(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    application = connection.execute("""
        SELECT *
        FROM applications
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if application is None:

        connection.close()

        return redirect("/applications")

    history = connection.execute("""
        SELECT *
        FROM application_history
        WHERE application_id = ?
        ORDER BY id ASC
    """, (id,)).fetchall()

    connection.close()

    return render_template(
        "application_details.html",
        application=application,
        history=history
    )


# ============================================================
# EDIT APPLICATION
# ============================================================

@app.route(
    "/edit-application/<int:id>",
    methods=["GET", "POST"]
)
def edit_application(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    application = connection.execute("""
        SELECT *
        FROM applications
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if application is None:

        connection.close()

        return redirect("/applications")

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Applied"
        ).strip()

        application_date = request.form.get(
            "application_date",
            ""
        ).strip()

        if status not in APPLICATION_STATUSES:

            status = "Applied"

        old_status = application["status"]

        # ----------------------------------------------------
        # UPDATE APPLICATION
        # ----------------------------------------------------

        connection.execute("""
            UPDATE applications
            SET
                company = ?,
                position = ?,
                status = ?,
                application_date = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            company,
            position,
            status,
            application_date,
            id,
            user_id
        ))

        # ----------------------------------------------------
        # ADD TIMELINE ENTRY ONLY WHEN STATUS CHANGES
        # ----------------------------------------------------

        if old_status != status:

            connection.execute("""
                INSERT INTO application_history
                (
                    application_id,
                    status,
                    changed_date
                )
                VALUES (?, ?, ?)
            """, (
                id,
                status,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

        connection.commit()
        connection.close()

        return redirect("/applications")

    connection.close()

    return render_template(
        "edit_application.html",
        application=application,
        application_statuses=APPLICATION_STATUSES
    )


# ============================================================
# DELETE APPLICATION
# ============================================================

@app.route(
    "/delete-application/<int:id>",
    methods=["GET", "POST"]
)
def delete_application(id):

    if not login_required():
        return redirect("/applications")

    user_id = session["user_id"]

    connection = get_database()

    # --------------------------------------------------------
    # CHECK APPLICATION BELONGS TO USER
    # --------------------------------------------------------

    application = connection.execute("""
        SELECT id
        FROM applications
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if application is None:

        connection.close()

        return redirect("/applications")

    # --------------------------------------------------------
    # DELETE TIMELINE
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM application_history
        WHERE application_id = ?
    """, (id,))

    # --------------------------------------------------------
    # DELETE APPLICATION
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM applications
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/applications")


# ============================================================
# INTERVIEWS
# ============================================================

@app.route("/interviews")
def interviews():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    interviews_list = connection.execute("""
        SELECT *
        FROM interviews
        WHERE user_id = ?
        ORDER BY interview_date ASC, interview_time ASC
    """, (user_id,)).fetchall()

    connection.close()

    return render_template(
        "interviews.html",
        interviews=interviews_list
    )


# ============================================================
# ADD INTERVIEW
# ============================================================

@app.route(
    "/add-interview",
    methods=["GET", "POST"]
)
def add_interview():

    if not login_required():
        return redirect("/login")

    if request.method == "POST":

        user_id = session["user_id"]

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        interview_round = request.form.get(
            "interview_round",
            ""
        ).strip()

        interview_date = request.form.get(
            "interview_date",
            ""
        ).strip()

        interview_time = request.form.get(
            "interview_time",
            ""
        ).strip()

        mode = request.form.get(
            "mode",
            ""
        ).strip()

        meeting_link = request.form.get(
            "meeting_link",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        connection = get_database()

        connection.execute("""
            INSERT INTO interviews
            (
                user_id,
                company,
                position,
                interview_round,
                interview_date,
                interview_time,
                mode,
                meeting_link,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            company,
            position,
            interview_round,
            interview_date,
            interview_time,
            mode,
            meeting_link,
            status,
            notes
        ))

        connection.commit()
        connection.close()

        return redirect("/interviews")

    return render_template(
        "add_interview.html"
    )


# ============================================================
# EDIT INTERVIEW
# ============================================================

@app.route(
    "/edit-interview/<int:id>",
    methods=["GET", "POST"]
)
def edit_interview(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    interview = connection.execute("""
        SELECT *
        FROM interviews
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if interview is None:

        connection.close()

        return redirect("/interviews")

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        position = request.form.get(
            "position",
            ""
        ).strip()

        interview_round = request.form.get(
            "interview_round",
            ""
        ).strip()

        interview_date = request.form.get(
            "interview_date",
            ""
        ).strip()

        interview_time = request.form.get(
            "interview_time",
            ""
        ).strip()

        mode = request.form.get(
            "mode",
            ""
        ).strip()

        meeting_link = request.form.get(
            "meeting_link",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        connection.execute("""
            UPDATE interviews
            SET
                company = ?,
                position = ?,
                interview_round = ?,
                interview_date = ?,
                interview_time = ?,
                mode = ?,
                meeting_link = ?,
                status = ?,
                notes = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            company,
            position,
            interview_round,
            interview_date,
            interview_time,
            mode,
            meeting_link,
            status,
            notes,
            id,
            user_id
        ))

        connection.commit()
        connection.close()

        return redirect("/interviews")

    connection.close()

    return render_template(
        "edit_interview.html",
        interview=interview
    )


# ============================================================
# DELETE INTERVIEW
# ============================================================

@app.route(
    "/delete-interview/<int:id>",
    methods=["GET", "POST"]
)
def delete_interview(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    connection.execute("""
        DELETE FROM interviews
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/interviews")


# ============================================================
# RESUME FEATURE - RESUMES
# ============================================================

@app.route(
    "/resumes",
    methods=["GET", "POST"]
)
def resumes():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    # --------------------------------------------------------
    # UPLOAD RESUME
    # --------------------------------------------------------

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        resume_file = request.files.get(
            "resume"
        )

        # ----------------------------------------------------
        # VALIDATE COMPANY
        # ----------------------------------------------------

        if not company:

            connection.close()

            return "Company name is required."

        # ----------------------------------------------------
        # VALIDATE FILE
        # ----------------------------------------------------

        if resume_file is None:

            connection.close()

            return "Please select a resume file."

        if resume_file.filename == "":

            connection.close()

            return "Please select a resume file."

        if not allowed_resume_file(
            resume_file.filename
        ):

            connection.close()

            return (
                "Only PDF, DOC and DOCX files are allowed."
            )

        # ----------------------------------------------------
        # CREATE SAFE ORIGINAL FILE NAME
        # ----------------------------------------------------

        original_filename = secure_filename(
            resume_file.filename
        )

        if not original_filename:

            connection.close()

            return "Invalid file name."

        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()

        # ----------------------------------------------------
        # CREATE UNIQUE STORED FILE NAME
        # ----------------------------------------------------

        unique_filename = (
            "resume_"
            + str(user_id)
            + "_"
            + datetime.now().strftime(
                "%Y%m%d%H%M%S%f"
            )
            + "."
            + extension
        )

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            unique_filename
        )

        # ----------------------------------------------------
        # SAVE FILE
        # ----------------------------------------------------

        resume_file.save(
            file_path
        )

        # ----------------------------------------------------
        # SAVE DATABASE RECORD
        # ----------------------------------------------------

        uploaded_date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        connection.execute("""
            INSERT INTO resumes
            (
                user_id,
                company,
                original_filename,
                stored_filename,
                uploaded_date
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            company,
            original_filename,
            unique_filename,
            uploaded_date
        ))

        connection.commit()
        connection.close()

        return redirect("/resumes")

    # --------------------------------------------------------
    # GET USER RESUMES
    # --------------------------------------------------------

    resumes_list = connection.execute("""
        SELECT *
        FROM resumes
        WHERE user_id = ?
        ORDER BY uploaded_date DESC, id DESC
    """, (
        user_id,
    )).fetchall()

    connection.close()

    return render_template(
        "resumes.html",
        resumes=resumes_list
    )


# ============================================================
# RESUME FEATURE - DOWNLOAD
# ============================================================

@app.route(
    "/resume/<int:id>/download"
)
def download_resume(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    resume = connection.execute("""
        SELECT *
        FROM resumes
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    connection.close()

    if resume is None:
        return redirect("/resumes")

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        resume["stored_filename"],
        as_attachment=True,
        download_name=resume["original_filename"]
    )


# ============================================================
# RESUME FEATURE - DELETE
# ============================================================

@app.route(
    "/delete-resume/<int:id>",
    methods=["GET", "POST"]
)
def delete_resume(id):

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    resume = connection.execute("""
        SELECT *
        FROM resumes
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    )).fetchone()

    if resume is None:

        connection.close()

        return redirect("/resumes")

    # --------------------------------------------------------
    # DELETE PHYSICAL FILE
    # --------------------------------------------------------

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        resume["stored_filename"]
    )

    if os.path.exists(file_path):

        os.remove(file_path)

    # --------------------------------------------------------
    # DELETE DATABASE RECORD
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM resumes
        WHERE id = ?
        AND user_id = ?
    """, (
        id,
        user_id
    ))

    connection.commit()
    connection.close()

    return redirect("/resumes")


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    connection = get_database()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    connection.close()

    return render_template(
        "profile.html",
        user=user
    )


# ============================================================
# DELETE ACCOUNT
# ============================================================

@app.route(
    "/delete-account",
    methods=["GET", "POST"]
)
def delete_account():

    if not login_required():
        return redirect("/login")

    if request.method == "POST":

        user_id = session["user_id"]

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        connection = get_database()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

        if user is None or user["email"] != email:

            connection.close()

            return "Invalid email."

        try:

            password_correct = check_password_hash(
                user["password"],
                password
            )

        except ValueError:

            password_correct = False

        if not password_correct:

            connection.close()

            return "Incorrect password."

        # ----------------------------------------------------
        # DELETE APPLICATION HISTORY
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM application_history
            WHERE application_id IN (
                SELECT id
                FROM applications
                WHERE user_id = ?
            )
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE APPLICATIONS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM applications
            WHERE user_id = ?
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE JOBS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM jobs
            WHERE user_id = ?
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE INTERNSHIPS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM internships
            WHERE user_id = ?
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE ASSESSMENTS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM assessments
            WHERE user_id = ?
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE INTERVIEWS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM interviews
            WHERE user_id = ?
        """, (user_id,))

        # ====================================================
        # RESUME FEATURE - DELETE USER RESUME FILES
        # ====================================================

        resumes_to_delete = connection.execute("""
            SELECT stored_filename
            FROM resumes
            WHERE user_id = ?
        """, (user_id,)).fetchall()

        for resume in resumes_to_delete:

            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                resume["stored_filename"]
            )

            if os.path.exists(file_path):

                os.remove(file_path)

        # ----------------------------------------------------
        # DELETE RESUME RECORDS
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM resumes
            WHERE user_id = ?
        """, (user_id,))

        # ----------------------------------------------------
        # DELETE USER
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM users
            WHERE id = ?
        """, (user_id,))

        connection.commit()
        connection.close()

        session.clear()

        return redirect("/")

    return render_template(
        "delete_account.html"
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(debug=True)