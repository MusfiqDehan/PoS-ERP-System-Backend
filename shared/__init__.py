"""Shared cross-cutting utilities for the Sortorium backend.

Package layout:
- ``models``     — abstract base models (UUID v7 PK, soft delete)
- ``views``      — DRF CRUD views and list mixins
- ``responses``  — global API success/error envelopes
- ``pagination`` — cursor pagination
- ``filters``    — list filter backends
- ``middleware`` — Django middleware
- ``cache``      — cache helpers and signals
- ``tenancy``    — tenant/branch scoping and limits
- ``db``         — queryset optimizations
- ``api``        — throttling and API utilities
- ``platform``   — currency and platform settings helpers
"""
