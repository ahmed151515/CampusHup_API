from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..serializers import StudentSerializer, FacultySerializer
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer


@extend_schema(
    summary="Get current user's profile",
    description="Returns the profile information of the currently authenticated user.",
    request=None,
    responses={
        200: PolymorphicProxySerializer(
            component_name="UserProfile",
            serializers=[
                StudentSerializer,
                FacultySerializer,
            ],
            resource_type_field_name=None,
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
        pass  # admin or other roles, can be extended in the future

    return Response(serializer.data)
