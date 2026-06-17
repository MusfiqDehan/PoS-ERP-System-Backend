"""Reusable DRF view classes and mixins."""

from shared.views.crud import ModelCRUDView

__all__ = [
    "BranchScopedListMixin",
    "BranchScopedQuerysetMixin",
    "ModelCRUDView",
    "SearchFilterSortPaginationMixin",
]


def __getattr__(name: str):
    if name in {
        "BranchScopedListMixin",
        "BranchScopedQuerysetMixin",
        "SearchFilterSortPaginationMixin",
    }:
        from shared.views import list_mixins

        return getattr(list_mixins, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
