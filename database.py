import sqlite3

connection = sqlite3.connect("careertrack.db")

cursor = connection.cursor()


# USERS TABLE

cursor.execute("""
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

    skills TEXT
)
""")


# JOBS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    company TEXT NOT NULL,

    position TEXT NOT NULL,

    location TEXT,

    salary TEXT,

    job_date TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")


# INTERNSHIPS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS internships (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    company TEXT NOT NULL,

    position TEXT NOT NULL,

    location TEXT,

    stipend TEXT,

    duration TEXT,

    internship_date TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")


# APPLICATIONS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    company TEXT NOT NULL,

    position TEXT NOT NULL,

    status TEXT NOT NULL,

    application_date TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")


# ASSESSMENTS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS assessments (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    company TEXT NOT NULL,

    assessment_name TEXT NOT NULL,

    assessment_type TEXT NOT NULL,

    scheduled_date TEXT NOT NULL,

    end_date TEXT NOT NULL,

    status TEXT NOT NULL,

    notes TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")


connection.commit()

connection.close()

print("Database created successfully!")