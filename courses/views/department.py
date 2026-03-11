from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import Department
from ..serializers import DepartmentSerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    CRUD for Departments.
    """
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"
