from rest_framework import serializers
from .models import User, StudentProfile, FacultyProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ["department", "join_date_year", "gpa"]
        extra_kwargs = {
            "department": {"required": True},
            "join_date_year": {"required": True},
            "gpa": {"read_only": True, "write_only": True},
        }


class FacultyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyProfile
        fields = ["department", "name"]
        extra_kwargs = {
            "department": {"required": True},
            "name": {"required": True},
        }


class StudentSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(source="student_profile")

    class Meta:
        model = User
        fields = [
            "id",
            "college_id",
            "first_name",
            "last_name",
            "email",
            "role",
            "date_joined",
            "student_profile",
        ]
        read_only_fields = ["id", "role", "date_joined"]
        extra_kwargs = {
            "college_id": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("student_profile", None)

        # update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # update profile fields
        if profile_data:
            profile = instance.student_profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class FacultySerializer(serializers.ModelSerializer):
    faculty_profile = FacultyProfileSerializer(source="faculty_profile")

    class Meta:
        model = User
        fields = [
            "id",
            "college_id",
            "first_name",
            "last_name",
            "email",
            "role",
            "date_joined",
            "faculty_profile",
        ]
        read_only_fields = ["id", "role", "date_joined"]
        extra_kwargs = {
            "college_id": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("faculty_profile", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile = instance.faculty_profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance
