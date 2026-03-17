from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrReadOnly
from ..models import Department
from ..serializers import DepartmentSerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    CRUD for Departments.
    """
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "code"
