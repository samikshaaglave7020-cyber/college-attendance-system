from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

import os

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll_no TEXT UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            subject TEXT,
            status TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()
init_db()
@app.route("/")
def home():

    conn = get_db()

    # Total students
    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    # Total attendance records
    total_attendance = conn.execute(
        "SELECT COUNT(*) FROM attendance"
    ).fetchone()[0]

    # Total present
    total_present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status = 'P'"
    ).fetchone()[0]

    # Total absent
    total_absent = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status = 'A'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        total_attendance=total_attendance,
        total_present=total_present,
        total_absent=total_absent
    )


@app.route("/add_student", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        name = request.form["name"]
        roll_no = request.form["roll_no"]

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO students (name, roll_no) VALUES (?, ?)",
                (name, roll_no)
            )

            conn.commit()
            conn.close()

            return redirect("/")

        except sqlite3.IntegrityError:

            conn.close()

            return """
            <h2>Roll Number Already Exists</h2>
            <p>Please enter a different roll number.</p>
            <a href="/add_student">Go Back</a>
            """

    return render_template("add_student.html")

@app.route("/students")
def view_students():

    conn = get_db()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students
    )
    
@app.route("/mark_attendance", methods=["GET", "POST"])
def mark_attendance():

    conn = get_db()

    students = conn.execute(
        "SELECT name, roll_no FROM students ORDER BY roll_no"
    ).fetchall()

    if request.method == "POST":

        roll_no = request.form["roll_no"]
        subject = request.form["subject"].strip().upper()
        date = request.form["date"]
        status = request.form["status"].upper()

        existing = conn.execute("""
            SELECT * FROM attendance
            WHERE roll_no = ?
            AND subject = ?
            AND date = ?
        """, (roll_no, subject, date)).fetchone()

        if existing:

            conn.close()

            return """
            <h2>Attendance Already Marked</h2>
            <p>Attendance for this student, subject and date already exists.</p>
            <a href="/mark_attendance">Go Back</a>
            """

        conn.execute("""
            INSERT INTO attendance
            (roll_no, subject, status, date)
            VALUES (?, ?, ?, ?)
        """, (roll_no, subject, status, date))

        conn.commit()
        conn.close()

        return """
        <h2>Attendance Saved Successfully!</h2>
        <a href="/">Back to Home</a>
        """

    conn.close()

    return render_template(
        "mark_attendance.html",
        students=students
    )
@app.route("/attendance_report")
def attendance_report():

    conn = get_db()

    records = conn.execute("""
        SELECT
            attendance.roll_no,
            students.name,
            attendance.subject,
            attendance.date,
            attendance.status
        FROM attendance
        JOIN students
        ON attendance.roll_no = students.roll_no
        ORDER BY attendance.roll_no,
                 attendance.subject,
                 attendance.date
    """).fetchall()

    conn.close()

    report = {}

    for record in records:

        key = (record["roll_no"], record["subject"])

        if key not in report:
            report[key] = {
                "name": record["name"],
                "roll_no": record["roll_no"],
                "subject": record["subject"],
                "total": 0,
                "present": 0,
                "absent": 0,
                "records": []
            }

        report[key]["total"] += 1

        if record["status"] == "P":
            report[key]["present"] += 1
        else:
            report[key]["absent"] += 1

        report[key]["records"].append(record)

    for item in report.values():

        if item["total"] > 0:
            item["percentage"] = (
                item["present"] / item["total"]
            ) * 100
        else:
            item["percentage"] = 0

    return render_template(
        "attendance_report.html",
        reports=report.values()
    )

@app.route("/search_student", methods=["GET", "POST"])
def search_student():

    student = None
    attendance = []

    if request.method == "POST":

        roll_no = request.form["roll_no"]

        conn = get_db()

        student = conn.execute(
            "SELECT * FROM students WHERE roll_no = ?",
            (roll_no,)
        ).fetchone()

        if student:
            attendance = conn.execute("""
                SELECT subject, date, status
                FROM attendance
                WHERE roll_no = ?
                ORDER BY date
            """, (roll_no,)).fetchall()

        conn.close()

    return render_template(
        "search_student.html",
        student=student,
        attendance=attendance
    )
@app.route("/delete_student", methods=["GET", "POST"])
def delete_student():

    message = ""

    if request.method == "POST":

        roll_no = request.form["roll_no"]

        conn = get_db()

        student = conn.execute(
            "SELECT * FROM students WHERE roll_no = ?",
            (roll_no,)
        ).fetchone()

        if student:

            # Delete attendance records first
            conn.execute(
                "DELETE FROM attendance WHERE roll_no = ?",
                (roll_no,)
            )

            # Delete student
            conn.execute(
                "DELETE FROM students WHERE roll_no = ?",
                (roll_no,)
            )

            conn.commit()

            message = "Student deleted successfully!"

        else:

            message = "Student not found!"

        conn.close()

    return render_template(
        "delete_student.html",
        message=message
    )

@app.route("/update_student", methods=["GET", "POST"])
def update_student():

    message = ""

    if request.method == "POST":

        old_roll_no = request.form["old_roll_no"]
        name = request.form["name"]
        new_roll_no = request.form["new_roll_no"]

        conn = get_db()

        student = conn.execute(
            "SELECT * FROM students WHERE roll_no = ?",
            (old_roll_no,)
        ).fetchone()

        if student:

            try:
                conn.execute(
                    """
                    UPDATE students
                    SET name = ?, roll_no = ?
                    WHERE roll_no = ?
                    """,
                    (name, new_roll_no, old_roll_no)
                )

                # Update attendance roll number also
                conn.execute(
                    """
                    UPDATE attendance
                    SET roll_no = ?
                    WHERE roll_no = ?
                    """,
                    (new_roll_no, old_roll_no)
                )

                conn.commit()

                message = "Student updated successfully!"

            except sqlite3.IntegrityError:

                message = "New roll number already exists!"

        else:

            message = "Student not found!"

        conn.close()

    return render_template(
        "update_student.html",
        message=message
    )
    
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
      )
