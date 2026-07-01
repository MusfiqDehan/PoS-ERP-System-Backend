"""Inventory dashboard aggregation service."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce

from apps.branch.models import Branch
from apps.inventory.models import (
    Product,
    PurchaseOrder,
    Sale,
    StockLevel,
    StockRequest,
    StockTransfer,
    Warehouse,
)
from shared.tenancy.helpers import (
    get_user_branch_scope_ids,
    scope_queryset_by_branch_access,
)


class DashboardService:
    @classmethod
    def _scope_sales(cls, user, branch_filter_id=None):
        qs = Sale.objects.filter(status=Sale.STATUS_COMPLETED)
        return scope_queryset_by_branch_access(
            qs,
            user,
            branch_field="branch_id",
            branch_filter_id=branch_filter_id,
        )

    @classmethod
    def _scope_stock(cls, user, branch_filter_id=None):
        return scope_queryset_by_branch_access(
            StockLevel.objects.all(),
            user,
            branch_field="branch_id",
            branch_filter_id=branch_filter_id,
        )

    @classmethod
    def summary(
        cls,
        *,
        user,
        scope: str = "business",
        branch_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        branch_filter_id=None,
    ) -> dict:
        branch_param = str(branch_id) if branch_id else branch_filter_id
        sales_qs = cls._scope_sales(user, branch_param)
        stock_qs = cls._scope_stock(user, branch_param)

        if scope == "branch" and branch_id:
            sales_qs = sales_qs.filter(branch_id=branch_id)
            stock_qs = stock_qs.filter(
                location_type=StockLevel.LOCATION_BRANCH, branch_id=branch_id
            )
        elif scope == "warehouse" and warehouse_id:
            stock_qs = stock_qs.filter(
                location_type=StockLevel.LOCATION_WAREHOUSE,
                warehouse_id=warehouse_id,
            )
            sales_qs = sales_qs.none()
        elif branch_id:
            sales_qs = sales_qs.filter(branch_id=branch_id)
            stock_qs = stock_qs.filter(
                Q(location_type=StockLevel.LOCATION_BRANCH, branch_id=branch_id)
            )

        sales_agg = sales_qs.aggregate(
            total_sales=Coalesce(Sum("total"), Decimal("0")),
            order_count=Count("id"),
        )
        stock_agg = stock_qs.aggregate(
            total_quantity=Coalesce(Sum("quantity"), Decimal("0")),
            sku_count=Count("id", distinct=True),
        )
        low_stock_count = stock_qs.filter(quantity__lte=F("qty_alert")).count()

        scope_ids = get_user_branch_scope_ids(user)
        if scope_ids is not None:
            branch_count = len(scope_ids)
        else:
            branch_count = Branch.objects.filter(is_active=True).count()

        return {
            "scope": scope,
            "branch_id": str(branch_id) if branch_id else None,
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
            "total_sales": str(sales_agg["total_sales"]),
            "order_count": sales_agg["order_count"],
            "total_stock_quantity": str(stock_agg["total_quantity"]),
            "stock_sku_count": stock_agg["sku_count"],
            "low_stock_count": low_stock_count,
            "product_count": Product.objects.filter(is_active=True).count(),
            "branch_count": branch_count,
            "warehouse_count": Warehouse.objects.filter(is_active=True).count(),
        }

    @classmethod
    def low_stock(
        cls,
        *,
        user,
        branch_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        branch_filter_id=None,
    ) -> list[dict]:
        branch_param = str(branch_id) if branch_id else branch_filter_id
        qs = scope_queryset_by_branch_access(
            StockLevel.objects.select_related(
                "product", "variant", "branch", "warehouse"
            ).filter(quantity__lte=F("qty_alert")),
            user,
            branch_field="branch_id",
            branch_filter_id=branch_param,
        )
        if branch_id:
            qs = qs.filter(
                location_type=StockLevel.LOCATION_BRANCH, branch_id=branch_id
            )
        if warehouse_id:
            qs = qs.filter(
                location_type=StockLevel.LOCATION_WAREHOUSE,
                warehouse_id=warehouse_id,
            )
        return [
            {
                "id": str(row.id),
                "product_sku": row.product.sku,
                "product_name": row.product.name,
                "quantity": str(row.quantity),
                "qty_alert": str(row.qty_alert),
                "branch_id": str(row.branch_id) if row.branch_id else None,
                "warehouse_id": str(row.warehouse_id) if row.warehouse_id else None,
            }
            for row in qs[:100]
        ]

    @classmethod
    def pending_actions(
        cls,
        *,
        user,
        branch_id: UUID | None = None,
        branch_filter_id=None,
    ) -> dict:
        branch_param = str(branch_id) if branch_id else branch_filter_id
        transfers = scope_queryset_by_branch_access(
            StockTransfer.objects.filter(
                status__in=[
                    StockTransfer.STATUS_PENDING,
                    StockTransfer.STATUS_IN_TRANSIT,
                ]
            ),
            user,
            branch_field="source_branch_id",
            branch_filter_id=branch_param,
        )
        requests = scope_queryset_by_branch_access(
            StockRequest.objects.filter(
                status__in=[StockRequest.STATUS_PENDING, StockRequest.STATUS_APPROVED]
            ),
            user,
            branch_field="requesting_branch_id",
            branch_filter_id=branch_param,
        )
        purchase_orders = PurchaseOrder.objects.filter(
            status=PurchaseOrder.STATUS_SENT
        )
        if branch_id:
            transfers = transfers.filter(
                Q(source_branch_id=branch_id) | Q(target_branch_id=branch_id)
            )
            requests = requests.filter(requesting_branch_id=branch_id)
        return {
            "pending_transfers": transfers.count(),
            "pending_requests": requests.count(),
            "pending_purchase_orders": purchase_orders.count(),
        }

    @classmethod
    def replenishment_options(
        cls,
        *,
        product_id: UUID,
        branch_id: UUID,
        user=None,
        include_other_branches: bool = True,
    ) -> list[dict]:
        options: list[dict] = []
        same_branch = (
            StockLevel.objects.filter(
                location_type=StockLevel.LOCATION_BRANCH,
                branch_id=branch_id,
                product_id=product_id,
                quantity__gt=0,
            )
            .select_related("branch")
            .first()
        )
        if same_branch:
            options.append(
                {
                    "source_type": "branch",
                    "source_id": str(branch_id),
                    "source_name": same_branch.branch.name,
                    "quantity": str(same_branch.quantity),
                    "priority": 1,
                }
            )

        if include_other_branches:
            other_branches = StockLevel.objects.filter(
                location_type=StockLevel.LOCATION_BRANCH,
                product_id=product_id,
                quantity__gt=0,
            ).exclude(branch_id=branch_id).select_related("branch")[:5]
            for idx, row in enumerate(other_branches, start=2):
                options.append(
                    {
                        "source_type": "branch",
                        "source_id": str(row.branch_id),
                        "source_name": row.branch.name,
                        "quantity": str(row.quantity),
                        "priority": idx,
                    }
                )

        warehouses = StockLevel.objects.filter(
            location_type=StockLevel.LOCATION_WAREHOUSE,
            product_id=product_id,
            quantity__gt=0,
        ).select_related("warehouse").order_by("-warehouse__is_central")[:5]
        for idx, row in enumerate(warehouses, start=10):
            options.append(
                {
                    "source_type": "warehouse",
                    "source_id": str(row.warehouse_id),
                    "source_name": row.warehouse.name,
                    "quantity": str(row.quantity),
                    "priority": idx,
                    "is_central": row.warehouse.is_central,
                }
            )
        return options
