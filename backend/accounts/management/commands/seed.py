from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.utils import IntegrityError
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
        is_dev = options.get("dev", False)
        self.seed_department(is_dev=is_dev)
        self.seed_admin()
        if is_dev:
            self.seed_student()
            self.seed_faculty()
            
        call_command("seed_courses", dev=is_dev)

    def seed_student(self):

        data = {
            "college_id": "2022030001",
            "first_name": "st_test",
            "last_name": "st_test",
            "email": "st_test@example.com",
            "student_profile": {"join_date_year": 2022},
            "department_id": "03",
        }

        try:
            User.objects.create_student(data)
            self.print_data(data, "user student")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"student already exists or error: {e}"))

    def seed_faculty(self):
        data = {
            "college_id": "dr001",
            "first_name": "test",
            "last_name": "test",
            "email": "drtest1@admin.com",
            "department_id": "03",
            "faculty_profile": {},
        }

        try:
            User.objects.create_faculty(data)
            self.print_data(data, "user faculty")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"faculty already exists or error: {e}"))

    def seed_admin(self):
        data = {
            "college_id": "su",
            "password": "su",
            "first_name": "su",
            "last_name": "su",
            "email": "su@admin.com",
        }

        try:
            User.objects.create_superuser(**data)
            self.print_data(data, "user admin")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"admin already exists or error: {e}"))

    def seed_department(self, is_dev):
        data = [
            {"name": "staff", "code": "05", "description": "staff"},
        ]
        if is_dev:
            data += [
                {"name": "cs", "code": "03", "description": "computer science"},
            ]
        for d in data:
            try:
                dept = Department(**d)
                dept.save()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"department already exists or error: {e}"))
        self.print_data(data, "department")

    def print_data(self, data, model):
        self.stdout.write(
            self.style.SUCCESS(f"the data of seed of {model} is \n {data}")
        )
