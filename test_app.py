import json
from unittest.mock import patch

import pandas as pd
import pytest

from app import app, clean_course_info, create_timetable


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_timetable_data():
    """Sample timetable data for testing."""
    return pd.DataFrame(
        {
            "Course Number": ["CS101", "MATH201", "PHY301"],
            "Course Name": [
                "Intro to Computer Science",
                "Calculus II",
                "Quantum Physics",
            ],
            "Credit": [3, 4, 3],
            "Lecture Time": ["T1,T2", "T3", "T4"],
            "Tutorial Time": ["T5", "T6", ""],
            "Lab Time": ["", "T7", "T8"],
            "Lecture Location": ["Room 101", "Room 202", "Lab 303"],
            "Tutorial Location": ["Room 104", "Room 205", ""],
            "Lab Location": ["", "Lab 201", "Lab 304"],
        }
    )


@pytest.fixture
def sample_time_slots():
    """Sample time slots data for testing."""
    return pd.DataFrame(
        {
            "Time Slot": ["08:00-09:00", "09:00-10:00", "10:00-11:00"],
            "Monday": ["T1", "T2", "T3"],
            "Tuesday": ["T4", "T5", "T6"],
            "Wednesday": ["T7", "T8", ""],
        }
    )


class TestCleanCourseInfo:
    """Test cases for the clean_course_info function."""

    def test_clean_course_info_basic(self):
        """Test basic cleaning of course information."""
        content = "CS101\nIntro to Computer Science\nLecture\nRoom 101"
        result = clean_course_info(content)
        assert result == "Intro to Computer Science, Lecture, Room 101"

    def test_clean_course_info_with_commas_in_location(self):
        """Test cleaning when location contains commas."""
        content = "CS101\nData Analysis\nTutorial\n7104, 7/105"
        result = clean_course_info(content)
        assert result == "Data Analysis, Tutorial, 7104 7/105"

    def test_clean_course_info_empty_content(self):
        """Test cleaning with empty or invalid content."""
        assert clean_course_info("") is None
        assert clean_course_info("nan") is None
        assert clean_course_info("T1") is None
        assert clean_course_info("O2") is None

    def test_clean_course_info_with_brackets(self):
        """Test cleaning content with brackets."""
        content = "CS101 (Section A)\nProgramming\nLecture\nRoom 101"
        result = clean_course_info(content)
        assert result == "Programming, Lecture, Room 101"

    def test_clean_course_info_course_code_filtering(self):
        """Test that course numbers are filtered out."""
        content = "CS101\nProgramming\nCS102\nLecture\nRoom 101"
        result = clean_course_info(content)
        assert result == "Programming, Lecture, Room 101"


class TestFlaskRoutes:
    """Test cases for Flask routes."""

    def test_index_route(self, client):
        """Test the index route returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data or b"<!DOCTYPE" in response.data.lower()

    @patch("app.timetable_data")
    def test_get_courses_success(self, mock_timetable_data, client):
        """Test successful retrieval of courses."""
        mock_timetable_data.iterrows.return_value = [
            (0, {"Course Number": "CS101", "Course Name": "Programming", "Credit": 3}),
            (1, {"Course Number": "MATH201", "Course Name": "Calculus", "Credit": 4}),
        ]

        with patch("app.time_slots") as mock_time_slots:
            mock_time_slots.empty = False
            mock_time_slots.columns = ["Monday", "Tuesday", "Wednesday"]

            with patch("app.time_labels", ["08:00-09:00", "09:00-10:00"]):
                response = client.get("/api/courses")
                assert response.status_code == 200

                data = json.loads(response.data)
                assert "courses" in data
                assert "days" in data
                assert "timeLabels" in data
                assert len(data["courses"]) == 2
                assert data["courses"][0]["code"] == "CS101"

    def test_get_courses_error_handling(self, client):
        """Test error handling in get_courses route."""
        with patch("app.timetable_data") as mock_data:
            mock_data.iterrows.side_effect = Exception("Database error")

            response = client.get("/api/courses")
            assert response.status_code == 500

            data = json.loads(response.data)
            assert "error" in data

    def test_get_timetable_no_courses(self, client):
        """Test timetable generation with no courses selected."""
        response = client.post(
            "/api/timetable",
            data=json.dumps({"courses": []}),
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "No courses selected" in data["error"]

    def test_get_timetable_no_json(self, client):
        """Test timetable generation with no JSON data."""
        response = client.post("/api/timetable")
        assert response.status_code == 400

    @patch("app.create_timetable")
    @patch("app.time_labels", ["08:00-09:00", "09:00-10:00"])
    def test_get_timetable_success(self, mock_create_timetable, client):
        """Test successful timetable generation."""
        mock_timetable = pd.DataFrame(
            {
                "Monday": ["CS101\nProgramming\nLecture\nRoom 101", ""],
                "Tuesday": ["", "MATH201\nCalculus\nTutorial\nRoom 202"],
            }
        )
        mock_create_timetable.return_value = mock_timetable

        response = client.post(
            "/api/timetable",
            data=json.dumps({"courses": ["CS101", "MATH201"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert len(data) > 0

    @patch("app.create_timetable")
    def test_get_timetable_error_handling(self, mock_create_timetable, client):
        """Test error handling in timetable generation."""
        mock_create_timetable.side_effect = Exception("Timetable generation error")

        response = client.post(
            "/api/timetable",
            data=json.dumps({"courses": ["CS101"]}),
            content_type="application/json",
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data


class TestCreateTimetable:
    """Test cases for the create_timetable function."""

    @patch("app.timetable_data")
    @patch("app.time_slots")
    def test_create_timetable_basic(self, mock_time_slots, mock_timetable_data):
        """Test basic timetable creation."""
        mock_timetable_data.iterrows.return_value = [
            (
                0,
                {
                    "Course Number": "CS101",
                    "Course Name": "Programming",
                    "Lecture Time": "T1,T2",
                    "Tutorial Time": "T3",
                    "Lab Time": "",
                    "Lecture Location": "Room 101",
                    "Tutorial Location": "Room 102",
                    "Lab Location": "",
                },
            )
        ]

        mock_time_slots_df = pd.DataFrame(
            {"Monday": ["T1", "T2", "T3"], "Tuesday": ["T4", "T5", "T6"]}
        )
        mock_time_slots.copy.return_value = mock_time_slots_df
        mock_time_slots.columns = ["Monday", "Tuesday"]

        result = create_timetable(["CS101"])
        assert isinstance(result, pd.DataFrame)
        assert "Monday" in result.columns
        assert "Tuesday" in result.columns

    @patch("app.timetable_data")
    @patch("app.time_slots")
    def test_create_timetable_clash_detection(
        self, mock_time_slots, mock_timetable_data
    ):
        """Test timetable creation with class clashes."""
        mock_timetable_data.iterrows.return_value = [
            (
                0,
                {
                    "Course Number": "CS101",
                    "Course Name": "Programming",
                    "Lecture Time": "T1",
                    "Tutorial Time": "",
                    "Lab Time": "",
                    "Lecture Location": "Room 101",
                    "Tutorial Location": "",
                    "Lab Location": "",
                },
            ),
            (
                1,
                {
                    "Course Number": "MATH201",
                    "Course Name": "Calculus",
                    "Lecture Time": "T1",
                    "Tutorial Time": "",
                    "Lab Time": "",
                    "Lecture Location": "Room 202",
                    "Tutorial Location": "",
                    "Lab Location": "",
                },
            ),
        ]

        mock_time_slots_df = pd.DataFrame({"Monday": ["T1", "T2", "T3"]})
        mock_time_slots.copy.return_value = mock_time_slots_df
        mock_time_slots.columns = ["Monday"]

        result = create_timetable(["CS101", "MATH201"])
        assert isinstance(result, pd.DataFrame)
        monday_t1 = str(result.iloc[0]["Monday"])
        assert "Clash" in monday_t1 or "/" in monday_t1


class TestIntegration:
    """Integration tests for the complete application."""

    def test_app_runs_without_csv_files(self, client):
        """Test that the app handles missing CSV files gracefully."""
        response = client.get("/")
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.get("/api/courses")
        assert "Access-Control-Allow-Origin" in response.headers

    def test_json_response_format(self, client):
        """Test that API endpoints return proper JSON."""
        with patch("app.timetable_data") as mock_data:
            mock_data.iterrows.return_value = []
            mock_data.empty = True

            response = client.get("/api/courses")
            assert response.content_type == "application/json"

            data = json.loads(response.data)
            assert isinstance(data, dict)
