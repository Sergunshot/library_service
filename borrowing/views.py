from django.db.transaction import atomic
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.models import Borrowing
from borrowing.serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all().select_related("book", "user")
    serializer_class = BorrowingSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "return_borrowing":
            return BorrowingReturnSerializer
        return BorrowingSerializer

    def get_queryset(self):
        queryset = self.queryset
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")
        user = self.request.user

        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            if is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)

        if user_id and user.is_staff:
            queryset = queryset.filter(user__id=user_id)

        if not user.is_staff:
            return queryset.filter(user=user).select_related("user")

        return queryset

    @extend_schema(
        description="Create new borrowing." "Validate no pending and expired payments.",
    )
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

    @extend_schema(
        description="Return borrowing by add actual_return_date."
        "Check borrowing overdue and if exist add overdue payments.",
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="return",
    )
    @atomic
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()
        serializer = BorrowingReturnSerializer(
            borrowing,
            data=request.data,
            context={"request": request},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.STR,
                description="Filter by user ID (ex. ?user_id=10). For admin only.",
                required=False,
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.STR,
                description="Filter by active/returned borrowing status."
                "(ex. ?is_active=true for active "
                "and ?is_active=false for returned borrowings)",
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
