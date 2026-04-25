from django.core.management.base import BaseCommand
from courses.models import Course, CourseFaculty, Enrollment, Timetable
from accounts.models import Department, User, StudentProfile, FacultyProfile
import datetime

class Command(BaseCommand):
    help = "Seed database with init data for courses"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dev",
            action="store_true",
            help="Seed additional dev/test data (course, assignments, enrollments)",
        )

    def handle(self, *args, **options):
        is_dev = options.get("dev", False)
        if is_dev:
            self.seed_course()
            self.seed_course_faculty()
            self.seed_enrollment()
            self.seed_timetable()
        else:
            self.stdout.write(self.style.WARNING("No data to seed without --dev flag for courses."))

    def seed_course(self):
        admin_user = User.objects.filter(college_id="su").first()
        dept = Department.objects.filter(code="03").first()
        if not dept:
            self.stdout.write(self.style.ERROR("Department 03 not found. Run 'py manage.py seed' for accounts first."))
            return

        data = {
            "course_code": "CS101",
            "course_name": "Introduction to Computer Science",
            "description": "Basic concepts of programming and computer science.",
            "credit_hours": 3,
            "department": dept,
            "semester": 1,
            "is_active": True,
            "created_by": admin_user,
        }
        try:
            course, created = Course.objects.update_or_create(course_code=data["course_code"], defaults=data)
            self.print_data(
                {"course_code": data["course_code"], "course_name": data["course_name"]}, 
                "course"
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"course error: {e}"))

    def seed_course_faculty(self):
        course = Course.objects.filter(course_code="CS101").first()
        faculty = FacultyProfile.objects.filter(user__college_id="dr001").first()
        if not course or not faculty:
            self.stdout.write(self.style.ERROR("Course CS101 or Faculty dr001 not found."))
            return

        data = {
            "course": course,
            "faculty": faculty,
            "role": "lecturer",
        }
        try:
            CourseFaculty.objects.update_or_create(course=course, faculty=faculty, defaults=data)
            self.print_data({"course_code": "CS101", "faculty_id": "dr001", "role": "lecturer"}, "course faculty")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"course faculty error: {e}"))

    def seed_enrollment(self):
        course = Course.objects.filter(course_code="CS101").first()
        student = StudentProfile.objects.filter(user__college_id="2022030001").first()
        if not course or not student:
            self.stdout.write(self.style.ERROR("Course CS101 or Student 2022030001 not found."))
            return

        data = {
            "student": student,
            "course": course,
            "status": "active",
        }
        try:
            Enrollment.objects.update_or_create(student=student, course=course, defaults=data)
            self.print_data({"student_id": "2022030001", "course_code": "CS101", "status": "active"}, "enrollment")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"enrollment error: {e}"))

    def seed_timetable(self):
        course = Course.objects.filter(course_code="CS101").first()
        faculty = FacultyProfile.objects.filter(user__college_id="dr001").first()
        if not course or not faculty:
            return

        data = {
            "course": course,
            "faculty": faculty,
            "day_of_week": "Mon",
            "start_time": datetime.time(9, 0),
            "end_time": datetime.time(11, 0),
            "room": "Hall A",
            "semester": "Fall 2026",
        }
        try:
            Timetable.objects.update_or_create(course=course, faculty=faculty, day_of_week="Mon", defaults=data)
            self.print_data({"course_code": "CS101", "faculty_id": "dr001", "day": "Mon"}, "timetable")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"timetable error: {e}"))

    def print_data(self, data, model):
        self.stdout.write(
            self.style.SUCCESS(f"the data of seed of {model} is \n {data}")
        )
