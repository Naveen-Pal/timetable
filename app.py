import os
import re
import uuid
from datetime import datetime, timedelta

import pandas as pd
from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from icalendar import Calendar, Event

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST"])

# Load data
try:
    time_slots = pd.read_csv("Time Slots.csv")
    timetable_data = pd.read_csv("Updated_Processed_Timetable.csv")
    time_labels = pd.read_csv("Time Slots.csv").iloc[:, 0].tolist()
except Exception:
    time_slots = pd.DataFrame()
    timetable_data = pd.DataFrame()
    time_labels = []


@app.route("/")
def index():
    return render_template("index.html", session_id=str(uuid.uuid4()))


@app.route("/api/courses")
def get_courses():
    try:
        courses = [
            {
                "code": row["Course Number"],
                "name": row["Course Name"],
                "credits": row["Credit"],
            }
            for _, row in timetable_data.iterrows()
            if not pd.isna(row["Credit"])
        ]

        return jsonify(
            {
                "courses": courses,
                "days": list(time_slots.columns) if not time_slots.empty else [],
                "timeLabels": time_labels,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to load courses: {str(e)}"}), 500


@app.route("/api/timetable", methods=["POST"])
def get_timetable():
    try:
        # Check if request has JSON data
        try:
            json_data = request.get_json()
        except Exception:
            return (
                jsonify({"error": "No JSON data provided or invalid content type"}),
                400,
            )

        if not json_data:
            return jsonify({"error": "No JSON data provided"}), 400

        selected_courses = json_data.get("courses", [])
        if not selected_courses:
            return jsonify({"error": "No courses selected"}), 400

        # Create timetable structure
        timetable = create_timetable(selected_courses)
        clean_timetable = {}
        days = [col for col in timetable.columns if col != "Time Slot"]

        # Initialize days
        for day in days:
            clean_timetable[day.lower()] = []

        # Process each time slot
        for idx, row in timetable.iterrows():
            time_slot = (
                time_labels[idx] if idx < len(time_labels) else f"Slot {idx + 1}"
            )

            for day in days:
                content = str(row[day]) if pd.notna(row[day]) else ""
                clean_info = clean_course_info(content)

                if clean_info:
                    clean_timetable[day.lower()].append(
                        {"time": time_slot, "class": clean_info}
                    )

        # Remove empty days
        return jsonify(
            {day: classes for day, classes in clean_timetable.items() if classes}
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate timetable: {str(e)}"}), 500


@app.route("/api/download-ics", methods=["POST"])
def download_ics():
    try:
        json_data = request.get_json()
        if not json_data or not json_data.get("courses"):
            return jsonify({"error": "No courses selected"}), 400

        selected_courses = json_data.get("courses", [])
        
        # Create ICS calendar
        cal = Calendar()
        cal.add('prodid', '-//IIT Gandhinagar//Timetable//EN')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'IIT Gandhinagar Timetable')

        # Generate timetable data
        timetable = create_timetable(selected_courses)
        day_columns = [col for col in timetable.columns if col != "Time Slot"]
        
        # Semester start date
        semester_start = datetime(2025, 8, 4)
        
        # Process each time slot
        for idx, row in timetable.iterrows():
            time_slot = time_labels[idx] if idx < len(time_labels) else f"Slot {idx + 1}"
            
            # Parse time (format: "08:30 - 09:50")
            if '-' not in time_slot:
                continue
            start_time, end_time = time_slot.split('-')
            try:
                start_hour, start_min = map(int, start_time.strip().split(':'))
                end_hour, end_min = map(int, end_time.strip().split(':'))
            except:
                continue
            
            for day_name in day_columns:
                content = str(row[day_name]) if pd.notna(row[day_name]) else ""
                if not content or content == 'nan':
                    continue
                
                # Use cleaned content from clean_course_info function
                clean_info = clean_course_info(content)
                if not clean_info:
                    continue
                
                
                parts = [p.strip() for p in clean_info.split(',')]
                if len(parts) < 3:
                    continue
                    
                course_code = parts[0]
                course_name = parts[1][:20] + "..." if len(parts[1]) > 20 else parts[1]  # Slice if long
                session_type = parts[2]
                location = parts[3] if len(parts) > 3 else "IIT Gandhinagar"
                
                # Calculate first occurrence date
                days_until = (day_columns.index(day_name) - semester_start.weekday()) % 7
                first_date = semester_start + timedelta(days=days_until)
                
                # Create recurring event
                event = Event()
                event.add('summary', f"{course_name} ({session_type})")
                event.add('dtstart', datetime.combine(first_date, datetime.min.time().replace(hour=start_hour, minute=start_min)))
                event.add('dtend', datetime.combine(first_date, datetime.min.time().replace(hour=end_hour, minute=end_min)))
                event.add('location', location)
                event.add('rrule', {'freq': 'weekly', 'count': 16})  # 16 weeks
                event.add('uid', f'{uuid.uuid4()}@iitgn.ac.in')
                
                cal.add_component(event)

        return Response(
            cal.to_ical().decode('utf-8'),
            mimetype='text/calendar',
            headers={'Content-Disposition': 'attachment; filename=timetable.ics'}
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate ICS: {str(e)}"}), 500


def clean_course_info(content):
    """Clean and format course information"""
    if (
        not content
        or content.strip() in ["", "nan"]
        or re.match(r"^[A-Z]\d+$", content.strip())
    ):
        return None

    if content.strip() in ["T1", "T2", "T3", "O1", "O2"]:
        return None

    # Remove brackets first, then replace commas with single space, then process newlines
    content = re.sub(r"\([^)]*\)", "", content)
    content = re.sub(
        r",\s*", " ", content
    )  # Replace comma and any following spaces with single space
    content = content.replace("\n", ", ")  # Replace newlines with comma-space
    parts = [part.strip() for part in content.split(",") if part.strip()]

    # Filter out Course Numbers (pattern: letters followed by numbers)
    clean_parts = []
    for part in parts:
        # Skip if it matches Course Number pattern (e.g., CS101, MATH201)
        if not re.match(r"^[A-Z]{1,4}\d+$", part.strip()):
            clean_parts.append(part)

    return ", ".join(clean_parts) if clean_parts else None


def create_timetable(selected_courses):
    """Create timetable data structure"""
    course_info = {}
    for _, row in timetable_data.iterrows():
        if row["Course Number"] in selected_courses:
            course_info[row["Course Number"]] = {
                "name": row["Course Name"],
                "Lecture": str(row.get("Lecture Time", "")),
                "Tutorial": str(row.get("Tutorial Time", "")),
                "Lab": str(row.get("Lab Time", "")),
                "Lecture_Location": str(row.get("Lecture Location", "")),
                "Tutorial_Location": str(row.get("Tutorial Location", "")),
                "Lab_Location": str(row.get("Lab Location", "")),
            }

    timetable = time_slots.copy().reset_index(drop=True)

    for slot in timetable.index:
        for day in timetable.columns:
            entries = []
            for code, info in course_info.items():
                for session_type in ["Lecture", "Tutorial", "Lab"]:
                    times = info.get(session_type, "")
                    if pd.isna(times) or times == "nan":
                        continue

                    if timetable.at[slot, day] in [
                        t.strip() for t in times.split(",") if t.strip()
                    ]:
                        location = info.get(f"{session_type}_Location", "")
                        location_text = (
                            f"\n{location}" if location and location != "nan" else ""
                        )
                        entries.append(
                            f"{code}\n{info['name']}\n{session_type}{location_text}"
                        )

            if len(entries) > 1:
                display = (
                    "/ ".join([e.split("\n")[0].strip() for e in entries]) + "\n(Clash)"
                )
                timetable.at[slot, day] = display
            elif entries:
                timetable.at[slot, day] = entries[0]

    return timetable


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
