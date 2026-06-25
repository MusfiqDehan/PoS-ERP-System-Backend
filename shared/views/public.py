"""Base view for unauthenticated public-schema endpoints."""

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class PublicAPIView(APIView):
    """Skip JWT parsing so stale collection Authorization headers do not break login."""

    authentication_classes = []
    permission_classes = [AllowAny]
