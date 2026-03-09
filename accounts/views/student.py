from rest_framework import viewsets
from ..models import User
from ..serializers import StudentSerializer
from ..permissions import IsAdmin


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    lookup_field = "college_id"
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.filter(
            role="student",
            is_active=True,
        ).select_related("student_profile")

    def perform_create(self, serializer):

        data = serializer.validated_data

        user = User.objects.create_student(data.copy())
        return user

    def perform_destroy(self, instance):
        # soft delete — never hard delete
        instance.is_active = False
        instance.save()
