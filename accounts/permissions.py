
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        # Allow read-only permissions for any authenticated user
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.is_authenticated
        
        # Write permissions are only allowed to admins
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )