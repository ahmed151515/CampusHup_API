from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..serializers import StudentSerializer, FacultySerializer, UserSerializer
from drf_spectacular.utils import (
    extend_schema,
    PolymorphicProxySerializer,
    OpenApiResponse,
)


@extend_schema(
    tags=["Me"],
    summary="Get current user's profile",
    description=(
        "Returns the profile of the currently authenticated user.\n\n"
        "The response shape depends on the caller's role:\n"
        "- **student** → `StudentSerializer` (includes `student_profile`)\n"
        "- **faculty** → `FacultySerializer` (includes `faculty_profile`)\n\n"
        "Other roles (e.g. admin) `UserSerializer`."
    ),
    request=None,
    responses={
        200: PolymorphicProxySerializer(
            component_name="UserProfile",
            serializers=[
                StudentSerializer,
                FacultySerializer,
                UserSerializer,
            ],
            resource_type_field_name=None,
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided or are invalid."
        ),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if user.role == "student":
        serializer = StudentSerializer(user)
    elif user.role == "faculty":
        serializer = FacultySerializer(user)
    else:
        serializer = UserSerializer(user)

    return Response(serializer.data)
