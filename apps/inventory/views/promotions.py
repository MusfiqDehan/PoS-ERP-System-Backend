"""Promotion and customer views."""

from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.inventory.models import (
    Coupon,
    Customer,
    GiftVoucher,
    LoyaltyAccount,
    Promotion,
)
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.inventory.openapi import (
    INVENTORY_TENANT_TAG,
    document_crud_view,
    document_inventory_post_api_view,
    inventory_get_responses,
    inventory_post_responses,
)
from apps.inventory.openapi_schemas import (
    CouponValidateRequestSerializer,
    CouponValidateResponseSerializer,
    GiftVoucherValidateRequestSerializer,
    GiftVoucherValidateResponseSerializer,
    LoyaltyPointsPatchSerializer,
)
from apps.inventory.serializers.promotions import (
    CouponSerializer,
    CustomerSerializer,
    GiftVoucherSerializer,
    LoyaltyAccountSerializer,
    PromotionSerializer,
)
from apps.inventory.services.promotion import PromotionService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import (
    get_user_branch_scope_ids,
    scope_queryset_by_branch_access,
)
from shared.views import ModelCRUDView


def _scoped_promotion_queryset(user, branch_filter_id=None):
    qs = Promotion.objects.all()
    scope_ids = get_user_branch_scope_ids(user)
    if scope_ids is None:
        return scope_queryset_by_branch_access(
            qs,
            user,
            branch_field="branch_id",
            branch_filter_id=branch_filter_id,
        )
    if not scope_ids:
        return qs.none()
    return qs.filter(Q(branch__isnull=True) | Q(branch_id__in=scope_ids))


class _CustomerBaseView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("customers", "view")]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("customers", "edit")()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Customer.objects.order_by("name")
        return scope_queryset_by_branch_access(
            qs,
            self.request.user,
            branch_field="branch_id",
            branch_filter_id=self.request.query_params.get("branch"),
        )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "List customers", "description": "Lists POS customers."},
        "POST": {"summary": "Create customer", "description": "Creates a customer."},
    },
)
class CustomerListCreateView(_CustomerBaseView):
    queryset = Customer.objects.order_by("name")
    serializer_class = CustomerSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve customer", "description": "Returns a customer."},
        "PATCH": {"summary": "Update customer", "description": "Updates a customer."},
        "DELETE": {"summary": "Delete customer", "description": "Deletes a customer."},
    },
)
class CustomerDetailView(_CustomerBaseView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("customers", "view")()]
        return [HasFeaturePermission.require("customers", "edit")()]

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


@extend_schema_view(
    get=extend_schema(
        tags=[INVENTORY_TENANT_TAG],
        summary="Get customer loyalty",
        description="Returns loyalty points balance for a customer.",
        responses=inventory_get_responses(
            LoyaltyAccountSerializer,
            include_not_found=True,
        ),
    ),
    patch=extend_schema(
        tags=[INVENTORY_TENANT_TAG],
        summary="Update customer loyalty",
        description="Adjusts loyalty points balance. Requires customers edit permission.",
        request=LoyaltyPointsPatchSerializer,
        responses=inventory_post_responses(
            LoyaltyAccountSerializer,
            include_forbidden=True,
        ),
    ),
)
class CustomerLoyaltyView(APIView):
    permission_classes = [HasFeaturePermission.require("customers", "view")]

    def get(self, request, pk):
        customer = (
            scope_queryset_by_branch_access(
                Customer.objects.all(),
                request.user,
                branch_field="branch_id",
                branch_filter_id=request.query_params.get("branch"),
            )
            .filter(pk=pk)
            .first()
        )
        if customer is None:
            return error_response(
                message="Customer not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        account = LoyaltyAccount.objects.filter(customer_id=pk).first()
        if account is None:
            return error_response(
                message="Loyalty account not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data=LoyaltyAccountSerializer(account).data,
            message="Loyalty account retrieved.",
        )

    def patch(self, request, pk):
        if not HasFeaturePermission.require("customers", "edit")().has_permission(
            request, self
        ):
            return error_response(
                message="Permission denied.",
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        customer = (
            scope_queryset_by_branch_access(
                Customer.objects.all(),
                request.user,
                branch_field="branch_id",
                branch_filter_id=request.query_params.get("branch"),
            )
            .filter(pk=pk)
            .first()
        )
        if customer is None:
            return error_response(
                message="Customer not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        account, _ = LoyaltyAccount.objects.get_or_create(customer_id=pk)
        points = request.data.get("points_balance")
        if points is not None:
            account.points_balance = int(points)
            account.save(update_fields=["points_balance", "updated_at"])
        return success_response(
            data=LoyaltyAccountSerializer(account).data,
            message="Loyalty account updated.",
        )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "List promotions", "description": "Lists promotions."},
        "POST": {"summary": "Create promotion", "description": "Creates a promotion."},
    },
)
class PromotionListCreateView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("pos", "edit")]
    queryset = Promotion.objects.order_by("name")
    serializer_class = PromotionSerializer
    pagination_class = None

    def get_queryset(self):
        return _scoped_promotion_queryset(
            self.request.user,
            self.request.query_params.get("branch"),
        ).order_by("name")


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve promotion", "description": "Returns a promotion."},
        "PATCH": {"summary": "Update promotion", "description": "Updates a promotion."},
        "DELETE": {
            "summary": "Delete promotion",
            "description": "Deletes a promotion.",
        },
    },
)
class PromotionDetailView(PromotionListCreateView):
    def get_queryset(self):
        return _scoped_promotion_queryset(
            self.request.user,
            self.request.query_params.get("branch"),
        )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "List coupons", "description": "Lists coupons."},
        "POST": {"summary": "Create coupon", "description": "Creates a coupon."},
    },
)
class CouponListCreateView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("pos", "edit")]
    queryset = Coupon.objects.select_related("promotion").order_by("code")
    serializer_class = CouponSerializer
    pagination_class = None

    def get_queryset(self):
        promo_ids = _scoped_promotion_queryset(
            self.request.user,
            self.request.query_params.get("branch"),
        ).values_list("id", flat=True)
        return (
            Coupon.objects.select_related("promotion")
            .filter(promotion_id__in=promo_ids)
            .order_by("code")
        )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve coupon", "description": "Returns a coupon."},
        "PATCH": {"summary": "Update coupon", "description": "Updates a coupon."},
        "DELETE": {"summary": "Delete coupon", "description": "Deletes a coupon."},
    },
)
class CouponDetailView(CouponListCreateView):
    pass


@document_inventory_post_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Validate coupon",
    description="Validates a coupon code and returns discount preview.",
    request_serializer=CouponValidateRequestSerializer,
    response_serializer=CouponValidateResponseSerializer,
    include_not_found=False,
)
class CouponValidateView(APIView):
    permission_classes = [HasFeaturePermission.require("pos", "view")]

    def post(self, request):
        code = request.data.get("code", "")
        coupon, discount = PromotionService.validate_coupon(code)
        return success_response(
            data={"coupon": CouponSerializer(coupon).data, "discount": str(discount)},
            message="Coupon is valid.",
        )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "List gift vouchers", "description": "Lists gift vouchers."},
        "POST": {"summary": "Create voucher", "description": "Creates a gift voucher."},
    },
)
class GiftVoucherListCreateView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("pos", "edit")]
    queryset = GiftVoucher.objects.order_by("code")
    serializer_class = GiftVoucherSerializer
    pagination_class = None


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve voucher", "description": "Returns a voucher."},
        "PATCH": {"summary": "Update voucher", "description": "Updates a voucher."},
        "DELETE": {"summary": "Delete voucher", "description": "Deletes a voucher."},
    },
)
class GiftVoucherDetailView(GiftVoucherListCreateView):
    queryset = GiftVoucher.objects.all()


@document_inventory_post_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Validate gift voucher",
    description="Validates voucher code and available balance.",
    request_serializer=GiftVoucherValidateRequestSerializer,
    response_serializer=GiftVoucherValidateResponseSerializer,
    include_not_found=False,
)
class GiftVoucherValidateView(APIView):
    permission_classes = [HasFeaturePermission.require("pos", "view")]

    def post(self, request):
        from decimal import Decimal

        code = request.data.get("code", "")
        amount = Decimal(str(request.data.get("amount", "0")))
        voucher, applied = PromotionService.validate_voucher(code, amount)
        return success_response(
            data={
                "voucher": GiftVoucherSerializer(voucher).data,
                "applicable_amount": str(applied),
            },
            message="Voucher is valid.",
        )
