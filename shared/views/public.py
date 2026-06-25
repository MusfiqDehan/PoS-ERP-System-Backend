"""Base view for unauthenticated public-schema endpoints."""

from typing import ClassVar

from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class PublicAPIView(APIView):
    """Skip JWT parsing so stale collection Authorization headers do not break login."""

    authentication_classes: ClassVar[list[type[BaseAuthentication]]] = []
    permission_classes = [AllowAny]
