from django.core.management.base import BaseCommand
from accounts.models import (
    Department,
    User,
)


class Command(BaseCommand):

    help = "Seed database with init data and data to test in dev"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dev",
            action="store_true",
            help="Seed additional dev/test data (students, faculty, extra departments)",
        )

    def handle(self, *args, **options):
        is_dev = True
        self.seed_department(is_dev=is_dev)
        self.seed_admin()
        if is_dev:
            self.seed_student()
            self.seed_faculty()

    def seed_student(self):

        data = {
            "college_id": "2022030001",
            "first_name": "st_test",
            "last_name": "st_test",
            "email": "st_test@example.com",
            "student_profile": {"join_date_year": 2022},
            "department_id": "03",
        }

        User.objects.create_student(data)
        self.print_data(data, "user student")

    def seed_faculty(self):
        data = {
            "college_id": "dr001",
            "first_name": "test",
            "last_name": "test",
            "email": "drtest1@admin.com",
            "department_id": "03",
            "faculty_profile": {},
        }

        User.objects.create_faculty(data)
        self.print_data(data, "user faculty")

    def seed_admin(self):
        data = {
            "college_id": "su",
            "password": "su",
            "first_name": "su",
            "last_name": "su",
            "email": "su@admin.com",
        }

        User.objects.create_superuser(**data)
        self.print_data(data, "user admin")

    def seed_department(self, is_dev):
        data = [
            {"name": "staff", "code": "05", "description": "staff"},
        ]
        if is_dev:
            data += [
                {"name": "cs", "code": "03", "description": "computer science"},
            ]
        for d in data:
            dept = Department(**d)
            dept.save()
        self.print_data(data, "department")

    def print_data(self, data, model):
        self.stdout.write(
            self.style.SUCCESS(f"the data of seed of {model} is \n {data}")
        )
