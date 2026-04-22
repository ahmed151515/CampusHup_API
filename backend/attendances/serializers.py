from rest_framework import serializers
from .models import Attendance


class AttendanceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["student_id", "is_present", "course_id", "created_at", "date", "id"]
        read_only = "id"
