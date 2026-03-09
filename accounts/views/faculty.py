from rest_framework import viewsets
from ..permissions import IsAdmin
from ..models import User
from ..serializers import FacultySerializer


class FacultyViewSet(viewsets.ModelViewSet):
    serializer_class = FacultySerializer
    lookup_field = "college_id"
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.filter(
            role="faculty",
            is_active=True,
        ).select_related("faculty_profile")

    def perform_create(self, serializer):

        data = serializer.validated_data

        user = User.objects.create_faculty(data.copy())
        return user

    def perform_destroy(self, instance):
        # soft delete — never hard delete
        instance.is_active = False
        instance.save()
