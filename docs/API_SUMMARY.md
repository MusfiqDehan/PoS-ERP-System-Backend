# Sortorium Backend — API Summary

> Auto-generated from the live OpenAPI schema (`drf-spectacular`) and URL routing. Last updated: 2026-06-24.

## Overview

Sortorium Backend exposes a versioned REST API under `/api/v1/`. The platform uses **django-tenants** with two PostgreSQL schema contexts:

| Schema | URL conf | Purpose |
|--------|----------|---------|
| **Public** | `config.public_urls` | Tenant registration, authentication, platform admin, billing catalog, payment callbacks |
| **Tenant** | `config.urls` | Per-tenant operations: users, RBAC, branches, subscriptions, branding |

Interactive documentation is served at `/api/v1/docs/` (Swagger UI) and `/api/v1/redoc/` on the public schema.

### Conventions

- **Authentication**: JWT Bearer tokens (`Authorization: Bearer <access_token>`) unless marked *Public*.
- **Response envelope**: All DRF endpoints return `{ success, message, data, error_code? }`.
- **Pagination**: Cursor-based pagination where applicable (`CursorPagination`, page size 20).
- **Multi-tenancy**: Tenant-scoped endpoints resolve the tenant from the request host/subdomain.

### Totals

- **88** documented API operations across **10** tag groups
- **15** public (unauthenticated) operations
- **73** JWT-authenticated operations

---

## Health

Infrastructure health and readiness probes available on both public and tenant schemas.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/health/ready/` | Readiness health check | Public (no auth) | public + tenant |
| `GET` | `/api/v1/health/tenant/` | Tenant health check | Public (no auth) | public + tenant |

<details>
<summary>Endpoint details (2 operations)</summary>

### `GET` `/api/v1/health/ready/`

**Readiness health check**

Probes database and Redis connectivity. Returns HTTP 200 when all checks pass, HTTP 503 otherwise. No authentication required.

### `GET` `/api/v1/health/tenant/`

**Tenant health check**

Returns schema name, tenant name, host, and scope (public or tenant) for the current request context. No authentication required.

</details>

---

## Tenancy - Public

Unauthenticated public-schema tenant onboarding, auth, and password flows.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `POST` | `/api/v1/tenancy/auth/login/` | Authenticate a tenant user | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/auth/refresh/` | Refresh JWT access token | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/password/reset/confirm/` | Confirm password reset using reset token | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/password/reset/request/` | Request a tenant password reset email | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/password/setup/` | Set password using invitation or verification token | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/register/` | Register a new tenant (self-service) | Public (no auth) | public |
| `POST` | `/api/v1/tenancy/tokens/validate/` | Validate an invitation or verification token | Public (no auth) | public |

<details>
<summary>Endpoint details (7 operations)</summary>

### `POST` `/api/v1/tenancy/auth/login/`

**Authenticate a tenant user**

Authenticates a tenant user on the public schema using email, password, and tenant domain or subdomain. Returns JWT access and refresh tokens plus tenant metadata on success. Rate limited to 30 requests per minute.

### `POST` `/api/v1/tenancy/auth/refresh/`

**Refresh JWT access token**

Exchanges a valid refresh token for a new access token pair. No authentication header is required; supply the refresh token in the request body.

### `POST` `/api/v1/tenancy/password/reset/confirm/`

**Confirm password reset using reset token**

Confirms a password reset by setting a new password with a valid reset token. Uses the same payload contract as password setup. Rate limited to 20 requests per hour.

### `POST` `/api/v1/tenancy/password/reset/request/`

**Request a tenant password reset email**

Requests a password reset email for a tenant user. Always returns a generic success message to avoid account enumeration. Rate limited to 10 requests per hour.

### `POST` `/api/v1/tenancy/password/setup/`

**Set password using invitation or verification token**

Sets the initial password for a user using a valid invitation or verification token. Rate limited to 20 requests per hour.

### `POST` `/api/v1/tenancy/register/`

**Register a new tenant (self-service)**

Starts self-service tenant registration on the public schema. Creates a pending tenant workspace and sends a verification email. Rate limited to 10 requests per hour.

### `POST` `/api/v1/tenancy/tokens/validate/`

**Validate an invitation or verification token**

Validates an invitation, email verification, or setup token on the public schema. Returns invitation metadata when the token is valid and the tenant workspace allows user entry.

</details>

---

## Tenancy - Tenant

Authenticated tenant-scoped user, branding, and settings operations.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/tenancy/me/` | Get current tenant user profile | JWT Bearer | tenant |
| `GET` | `/api/v1/tenancy/me/features/` | List enabled features for the current tenant | JWT Bearer | tenant |
| `DELETE` | `/api/v1/tenancy/me/profile-picture/` | Remove authenticated user profile picture | JWT Bearer | tenant |
| `PATCH` | `/api/v1/tenancy/me/profile-picture/` | Upload or replace authenticated user profile picture | JWT Bearer | tenant |
| `PUT` | `/api/v1/tenancy/me/profile-picture/` | Upload or replace authenticated user profile picture | JWT Bearer | tenant |
| `POST` | `/api/v1/tenancy/password/change/` | Change password for the authenticated user | JWT Bearer | tenant |
| `GET` | `/api/v1/tenancy/settings/branding/` | Read current tenant branding settings | JWT Bearer | tenant |
| `DELETE` | `/api/v1/tenancy/settings/branding/logo/` | Remove current tenant company logo | JWT Bearer | tenant |
| `PATCH` | `/api/v1/tenancy/settings/branding/logo/` | Upload or replace current tenant company logo | JWT Bearer | tenant |
| `PUT` | `/api/v1/tenancy/settings/branding/logo/` | Upload or replace current tenant company logo | JWT Bearer | tenant |
| `GET` | `/api/v1/tenancy/users/` | List tenant users (branch-scoped) | JWT Bearer | tenant |

<details>
<summary>Endpoint details (11 operations)</summary>

### `GET` `/api/v1/tenancy/me/`

**Get current tenant user profile**

Returns the authenticated user's profile within the resolved tenant schema. Requires a valid JWT bearer token.

### `GET` `/api/v1/tenancy/me/features/`

**List enabled features for the current tenant**

Returns feature keys enabled for the tenant resolved from the request host. Requires authentication; returns an empty feature list when no tenant context is available.

### `DELETE` `/api/v1/tenancy/me/profile-picture/`

**Remove authenticated user profile picture**

Removes the authenticated user's profile picture attachment. Requires a valid JWT bearer token.

### `PATCH` `/api/v1/tenancy/me/profile-picture/`

**Upload or replace authenticated user profile picture**

Uploads or replaces the authenticated user's profile picture using multipart form data. Requires a valid JWT bearer token.

### `PUT` `/api/v1/tenancy/me/profile-picture/`

**Upload or replace authenticated user profile picture**

Uploads or replaces the authenticated user's profile picture using multipart form data. Requires a valid JWT bearer token.

### `POST` `/api/v1/tenancy/password/change/`

**Change password for the authenticated user**

Changes the password for the currently authenticated tenant user. Requires the current password and a validated new password.

### `GET` `/api/v1/tenancy/settings/branding/`

**Read current tenant branding settings**

Returns branding settings for the resolved tenant, including company display metadata. Requires CanManageTenantBranding permission.

### `DELETE` `/api/v1/tenancy/settings/branding/logo/`

**Remove current tenant company logo**

Removes the current tenant company logo attachment. Requires CanManageTenantBranding permission.

### `PATCH` `/api/v1/tenancy/settings/branding/logo/`

**Upload or replace current tenant company logo**

Uploads or replaces the tenant company logo using multipart form data. Requires CanManageTenantBranding permission.

### `PUT` `/api/v1/tenancy/settings/branding/logo/`

**Upload or replace current tenant company logo**

Uploads or replaces the tenant company logo using multipart form data. Requires CanManageTenantBranding permission.

### `GET` `/api/v1/tenancy/users/`

**List tenant users (branch-scoped)**

Lists active tenant users visible to the caller based on branch access rules. Supports an optional branch query filter. Requires CanViewTenantUsers permission.

</details>

---

## Tenancy - Platform Admin

Platform administrator operations for tenant lifecycle and feature overrides.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/tenancy/admin/tenants/` | List tenants (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/tenancy/admin/tenants/{tenant_id}/features/` | Read tenant feature overrides (platform admin) | JWT Bearer | public |
| `PATCH` | `/api/v1/tenancy/admin/tenants/{tenant_id}/features/` | Update tenant feature overrides (platform admin) | JWT Bearer | public |

<details>
<summary>Endpoint details (3 operations)</summary>

### `GET` `/api/v1/tenancy/admin/tenants/`

**List tenants (platform admin)**

Returns a cursor-paginated list of tenants for platform administrators. Requires platform.tenants view permission.

### `GET` `/api/v1/tenancy/admin/tenants/{tenant_id}/features/`

**Read tenant feature overrides (platform admin)**

Returns per-tenant feature override map for a platform administrator. Requires platform.tenants edit permission.

### `PATCH` `/api/v1/tenancy/admin/tenants/{tenant_id}/features/`

**Update tenant feature overrides (platform admin)**

Patches per-tenant feature overrides for a platform administrator. Requires a features object in the request body and platform.tenants edit permission.

</details>

---

## Access - Tenant

Tenant-scoped role-based access control for roles, permissions, and assignments.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/access/features/` | List tenant feature catalog | JWT Bearer | tenant |
| `GET` | `/api/v1/access/me/` | Get current user permissions | JWT Bearer | tenant |
| `GET` | `/api/v1/access/roles/` | List tenant roles | JWT Bearer | tenant |
| `POST` | `/api/v1/access/roles/` | Create tenant role | JWT Bearer | tenant |
| `DELETE` | `/api/v1/access/roles/{id}/` | Delete tenant role | JWT Bearer | tenant |
| `GET` | `/api/v1/access/roles/{id}/` | Retrieve tenant role | JWT Bearer | tenant |
| `PATCH` | `/api/v1/access/roles/{id}/` | Update tenant role | JWT Bearer | tenant |
| `PUT` | `/api/v1/access/roles/{id}/` | Replace tenant role | JWT Bearer | tenant |
| `GET` | `/api/v1/access/roles/{role_id}/permissions/` | List permissions for a role | JWT Bearer | tenant |
| `PUT` | `/api/v1/access/roles/{role_id}/permissions/` | Replace permissions for a role | JWT Bearer | tenant |
| `GET` | `/api/v1/access/user-roles/` | List user role assignments | JWT Bearer | tenant |
| `POST` | `/api/v1/access/user-roles/` | Create user role assignment | JWT Bearer | tenant |
| `DELETE` | `/api/v1/access/user-roles/{id}/` | Delete user role assignment | JWT Bearer | tenant |
| `GET` | `/api/v1/access/user-roles/{id}/` | Retrieve user role assignment | JWT Bearer | tenant |
| `PATCH` | `/api/v1/access/user-roles/{id}/` | Update user role assignment | JWT Bearer | tenant |
| `PUT` | `/api/v1/access/user-roles/{id}/` | Replace user role assignment | JWT Bearer | tenant |

<details>
<summary>Endpoint details (16 operations)</summary>

### `GET` `/api/v1/access/features/`

**List tenant feature catalog**

Returns the tenant feature catalog used when configuring role permissions. Requires role administrator permission.

### `GET` `/api/v1/access/me/`

**Get current user permissions**

Returns the authenticated user's effective permission map, assigned roles, and enabled tenant features. Responses may be cached per tenant user.

### `GET` `/api/v1/access/roles/`

**List tenant roles**

Lists custom and system roles in the current tenant. Requires role administrator permission.

### `POST` `/api/v1/access/roles/`

**Create tenant role**

Creates a custom tenant role when capacity allows. Requires role administrator permission.

### `DELETE` `/api/v1/access/roles/{id}/`

**Delete tenant role**

Deletes a non-system role by ID. Requires role administrator permission.

### `GET` `/api/v1/access/roles/{id}/`

**Retrieve tenant role**

Returns a single role by ID. Requires role administrator permission.

### `PATCH` `/api/v1/access/roles/{id}/`

**Update tenant role**

Partially updates a role by ID. Requires role administrator permission.

### `PUT` `/api/v1/access/roles/{id}/`

**Replace tenant role**

Replaces a role by ID. Requires role administrator permission.

### `GET` `/api/v1/access/roles/{role_id}/permissions/`

**List permissions for a role**

Returns feature permission levels assigned to a role. Requires role administrator permission.

### `PUT` `/api/v1/access/roles/{role_id}/permissions/`

**Replace permissions for a role**

Replaces the full permission set for a role. Requires role administrator permission.

### `GET` `/api/v1/access/user-roles/`

**List user role assignments**

Lists user-to-role assignments scoped by branch access. Supports an optional branch query filter. Requires role administrator permission.

### `POST` `/api/v1/access/user-roles/`

**Create user role assignment**

Assigns a role to a user when capacity allows. Requires role administrator permission.

### `DELETE` `/api/v1/access/user-roles/{id}/`

**Delete user role assignment**

Removes a user role assignment by ID. Requires role administrator permission.

### `GET` `/api/v1/access/user-roles/{id}/`

**Retrieve user role assignment**

Returns a single user role assignment by ID. Requires role administrator permission.

### `PATCH` `/api/v1/access/user-roles/{id}/`

**Update user role assignment**

Partially updates a user role assignment by ID. Requires role administrator permission.

### `PUT` `/api/v1/access/user-roles/{id}/`

**Replace user role assignment**

Replaces a user role assignment by ID. Requires role administrator permission.

</details>

---

## Branch - Public

Unauthenticated read-only branch listings for tenant storefronts.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/branches/public/` | List public branches | Public (no auth) | tenant |
| `GET` | `/api/v1/branches/public/minimal/` | List public branches (minimal) | Public (no auth) | tenant |

<details>
<summary>Endpoint details (2 operations)</summary>

### `GET` `/api/v1/branches/public/`

**List public branches**

Returns active branches for the resolved tenant schema without authentication. Supports homepage=true to filter branches shown on the storefront.

### `GET` `/api/v1/branches/public/minimal/`

**List public branches (minimal)**

Returns a minimal active branch listing for the resolved tenant schema without authentication.

</details>

---

## Branch - Tenant

Authenticated tenant branch management, summaries, and manager assignment.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/branches/` | List branches | JWT Bearer | tenant |
| `POST` | `/api/v1/branches/` | Create branch | JWT Bearer | tenant |
| `GET` | `/api/v1/branches/summary/` | Get branch summary metrics | JWT Bearer | tenant |
| `DELETE` | `/api/v1/branches/{id}/` | Delete branch | JWT Bearer | tenant |
| `GET` | `/api/v1/branches/{id}/` | Retrieve branch | JWT Bearer | tenant |
| `PATCH` | `/api/v1/branches/{id}/` | Update branch | JWT Bearer | tenant |
| `PUT` | `/api/v1/branches/{id}/` | Replace branch | JWT Bearer | tenant |
| `POST` | `/api/v1/branches/{id}/assign-manager/` | Assign branch manager | JWT Bearer | tenant |

<details>
<summary>Endpoint details (8 operations)</summary>

### `GET` `/api/v1/branches/`

**List branches**

Lists branches visible to the caller based on branch access rules. Requires branches view permission.

### `POST` `/api/v1/branches/`

**Create branch**

Creates a branch when tenant capacity allows. Requires branches edit permission.

### `GET` `/api/v1/branches/summary/`

**Get branch summary metrics**

Returns branch summary metrics including staff and user counts. Only tenant administrators can access this endpoint.

### `DELETE` `/api/v1/branches/{id}/`

**Delete branch**

Deletes a branch by ID. Requires branches edit permission.

### `GET` `/api/v1/branches/{id}/`

**Retrieve branch**

Returns a single branch by ID. Requires branches view permission.

### `PATCH` `/api/v1/branches/{id}/`

**Update branch**

Partially updates a branch by ID. Requires branches edit permission.

### `PUT` `/api/v1/branches/{id}/`

**Replace branch**

Replaces a branch by ID. Requires branches edit permission.

### `POST` `/api/v1/branches/{id}/assign-manager/`

**Assign branch manager**

Assigns a tenant user as the manager for a branch. Requires branches edit permission.

</details>

---

## Billing - Public

Unauthenticated payment gateway callbacks and subscription redirect handlers.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/billing/subscription/cancel/` | Handle cancelled subscription payment redirect | Public (no auth) | public |
| `GET` | `/api/v1/billing/subscription/fail/` | Handle failed subscription payment redirect | Public (no auth) | public |
| `POST` | `/api/v1/billing/subscription/ipn/` | Process subscription payment IPN callback | Public (no auth) | public |
| `GET` | `/api/v1/billing/subscription/success/` | Handle successful subscription payment redirect | Public (no auth) | public |

<details>
<summary>Endpoint details (4 operations)</summary>

### `GET` `/api/v1/billing/subscription/cancel/`

**Handle cancelled subscription payment redirect**

Browser redirect handler for cancelled subscription payments on the public schema. Accepts tran_id as a query parameter and marks the invoice as cancelled.

### `GET` `/api/v1/billing/subscription/fail/`

**Handle failed subscription payment redirect**

Browser redirect handler for failed subscription payments on the public schema. Accepts tran_id as a query parameter and marks the invoice as failed.

### `POST` `/api/v1/billing/subscription/ipn/`

**Process subscription payment IPN callback**

Receives instant payment notification callbacks from the payment gateway on the public schema. No authentication is required; gateway validation is handled server-side.

### `GET` `/api/v1/billing/subscription/success/`

**Handle successful subscription payment redirect**

Browser redirect handler for successful subscription payments on the public schema. Accepts tran_id as a query parameter and activates the subscription when payment succeeded.

</details>

---

## Billing - Tenant

Tenant administrator subscription, invoice, and gateway configuration operations.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `DELETE` | `/api/v1/billing/payments/gateways/` | Delete tenant payment gateway configuration | JWT Bearer | tenant |
| `GET` | `/api/v1/billing/payments/gateways/` | List or retrieve tenant payment gateway configuration | JWT Bearer | tenant |
| `POST` | `/api/v1/billing/payments/gateways/` | Create or update tenant payment gateway configuration | JWT Bearer | tenant |
| `DELETE` | `/api/v1/billing/payments/gateways/{slug}/` | Delete tenant payment gateway configuration | JWT Bearer | tenant |
| `GET` | `/api/v1/billing/payments/gateways/{slug}/` | List or retrieve tenant payment gateway configuration | JWT Bearer | tenant |
| `POST` | `/api/v1/billing/payments/gateways/{slug}/` | Create or update tenant payment gateway configuration | JWT Bearer | tenant |
| `POST` | `/api/v1/billing/subscription/initiate-change/` | Initiate tenant subscription change | JWT Bearer | public |
| `POST` | `/api/v1/billing/subscription/initiate-change/` | Initiate tenant subscription change | JWT Bearer | tenant |
| `GET` | `/api/v1/billing/subscription/invoices/` | List tenant subscription invoices (tenant admin) | JWT Bearer | tenant |
| `GET` | `/api/v1/billing/subscription/invoices/{id}/pdf/` | Download tenant subscription invoice PDF | JWT Bearer | tenant |
| `GET` | `/api/v1/billing/subscription/summary/` | Get tenant subscription summary | JWT Bearer | public |
| `GET` | `/api/v1/billing/subscription/summary/` | Get tenant subscription summary | JWT Bearer | tenant |

<details>
<summary>Endpoint details (12 operations)</summary>

### `DELETE` `/api/v1/billing/payments/gateways/`

**Delete tenant payment gateway configuration**

Removes tenant-scoped gateway credentials for the slug provided in the URL. Requires authentication.

### `GET` `/api/v1/billing/payments/gateways/`

**List or retrieve tenant payment gateway configuration**

Lists all tenant gateway configurations or returns one configuration when slug is provided. Requires authentication.

### `POST` `/api/v1/billing/payments/gateways/`

**Create or update tenant payment gateway configuration**

Creates or updates tenant-scoped gateway credentials for the slug provided in the URL. Requires authentication.

### `DELETE` `/api/v1/billing/payments/gateways/{slug}/`

**Delete tenant payment gateway configuration**

Removes tenant-scoped gateway credentials for the slug provided in the URL. Requires authentication.

### `GET` `/api/v1/billing/payments/gateways/{slug}/`

**List or retrieve tenant payment gateway configuration**

Lists all tenant gateway configurations or returns one configuration when slug is provided. Requires authentication.

### `POST` `/api/v1/billing/payments/gateways/{slug}/`

**Create or update tenant payment gateway configuration**

Creates or updates tenant-scoped gateway credentials for the slug provided in the URL. Requires authentication.

### `POST` `/api/v1/billing/subscription/initiate-change/`

**Initiate tenant subscription change**

Starts a subscription plan change for the current tenant and returns a payment gateway redirect URL plus invoice metadata. Only tenant administrators can access this endpoint.

### `POST` `/api/v1/billing/subscription/initiate-change/`

**Initiate tenant subscription change**

Starts a subscription plan change for the current tenant and returns a payment gateway redirect URL plus invoice metadata. Only tenant administrators can access this endpoint.

### `GET` `/api/v1/billing/subscription/invoices/`

**List tenant subscription invoices (tenant admin)**

Lists subscription invoices for the current tenant. Only tenant administrators can access this endpoint.

### `GET` `/api/v1/billing/subscription/invoices/{id}/pdf/`

**Download tenant subscription invoice PDF**

Downloads a subscription invoice PDF for the current tenant. Returns binary application/pdf content. Only tenant administrators can access this endpoint.

### `GET` `/api/v1/billing/subscription/summary/`

**Get tenant subscription summary**

Returns active subscriptions, effective plan limits, and payment totals for the current tenant. Only tenant administrators can access this endpoint.

### `GET` `/api/v1/billing/subscription/summary/`

**Get tenant subscription summary**

Returns active subscriptions, effective plan limits, and payment totals for the current tenant. Only tenant administrators can access this endpoint.

</details>

---

## Billing - Platform Admin

Platform administrator billing catalog, gateways, packages, and invoice management.

| Method | Endpoint | Summary | Auth | Schema |
|--------|----------|---------|------|--------|
| `GET` | `/api/v1/billing/gateways/` | List payment gateways (platform admin) | JWT Bearer | public |
| `POST` | `/api/v1/billing/gateways/` | Create payment gateway (platform admin) | JWT Bearer | public |
| `DELETE` | `/api/v1/billing/gateways/{slug}/` | Delete payment gateway (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/gateways/{slug}/` | Retrieve payment gateway (platform admin) | JWT Bearer | public |
| `PATCH` | `/api/v1/billing/gateways/{slug}/` | Update payment gateway (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/packages/` | List packages (platform admin) | JWT Bearer | public |
| `POST` | `/api/v1/billing/packages/` | Create package (platform admin) | JWT Bearer | public |
| `DELETE` | `/api/v1/billing/packages/{id}/` | Delete package (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/packages/{id}/` | Retrieve package (platform admin) | JWT Bearer | public |
| `PATCH` | `/api/v1/billing/packages/{id}/` | Update package (platform admin) | JWT Bearer | public |
| `PUT` | `/api/v1/billing/packages/{id}/` | Replace package (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/packages/{id}/features/` | List features assigned to a package | JWT Bearer | public |
| `PUT` | `/api/v1/billing/packages/{id}/features/` | Replace features assigned to a package | JWT Bearer | public |
| `GET` | `/api/v1/billing/products/` | List software products (platform admin) | JWT Bearer | public |
| `POST` | `/api/v1/billing/products/` | Create software product (platform admin) | JWT Bearer | public |
| `DELETE` | `/api/v1/billing/products/{id}/` | Delete software product (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/products/{id}/` | Retrieve software product (platform admin) | JWT Bearer | public |
| `PATCH` | `/api/v1/billing/products/{id}/` | Update software product (platform admin) | JWT Bearer | public |
| `PUT` | `/api/v1/billing/products/{id}/` | Replace software product (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/subscription/invoices/` | List subscription invoices across tenants (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/subscription/invoices/{id}/` | Retrieve subscription invoice (platform admin) | JWT Bearer | public |
| `PATCH` | `/api/v1/billing/subscription/invoices/{id}/` | Update subscription invoice (platform admin) | JWT Bearer | public |
| `GET` | `/api/v1/billing/subscription/invoices/{id}/pdf/` | Download subscription invoice PDF (platform admin) | JWT Bearer | public |

<details>
<summary>Endpoint details (23 operations)</summary>

### `GET` `/api/v1/billing/gateways/`

**List payment gateways (platform admin)**

Lists configured payment gateways for the platform. Requires platform.billing view permission.

### `POST` `/api/v1/billing/gateways/`

**Create payment gateway (platform admin)**

Creates a payment gateway definition. Requires platform.billing edit permission.

### `DELETE` `/api/v1/billing/gateways/{slug}/`

**Delete payment gateway (platform admin)**

Deletes a payment gateway by slug. Requires platform.billing edit permission.

### `GET` `/api/v1/billing/gateways/{slug}/`

**Retrieve payment gateway (platform admin)**

Returns a payment gateway by slug. Requires platform.billing view permission.

### `PATCH` `/api/v1/billing/gateways/{slug}/`

**Update payment gateway (platform admin)**

Partially updates a payment gateway by slug. Requires platform.billing edit permission.

### `GET` `/api/v1/billing/packages/`

**List packages (platform admin)**

Lists subscription packages in the platform catalog. Requires platform.packages view permission.

### `POST` `/api/v1/billing/packages/`

**Create package (platform admin)**

Creates a subscription package. Requires platform.packages edit permission.

### `DELETE` `/api/v1/billing/packages/{id}/`

**Delete package (platform admin)**

Deletes a package by ID. Requires platform.packages edit permission.

### `GET` `/api/v1/billing/packages/{id}/`

**Retrieve package (platform admin)**

Returns a single package by ID. Requires platform.packages view permission.

### `PATCH` `/api/v1/billing/packages/{id}/`

**Update package (platform admin)**

Partially updates a package by ID. Requires platform.packages edit permission.

### `PUT` `/api/v1/billing/packages/{id}/`

**Replace package (platform admin)**

Replaces a package by ID. Requires platform.packages edit permission.

### `GET` `/api/v1/billing/packages/{id}/features/`

**List features assigned to a package**

Returns feature IDs currently assigned to a package. Requires platform.packages view permission.

### `PUT` `/api/v1/billing/packages/{id}/features/`

**Replace features assigned to a package**

Replaces the full feature assignment set for a package. Requires platform.packages edit permission.

### `GET` `/api/v1/billing/products/`

**List software products (platform admin)**

Lists software products in the platform billing catalog. Requires platform.billing view permission.

### `POST` `/api/v1/billing/products/`

**Create software product (platform admin)**

Creates a software product in the platform billing catalog. Requires platform.billing edit permission.

### `DELETE` `/api/v1/billing/products/{id}/`

**Delete software product (platform admin)**

Deletes a software product by ID. Requires platform.billing edit permission.

### `GET` `/api/v1/billing/products/{id}/`

**Retrieve software product (platform admin)**

Returns a single software product by ID. Requires platform.billing view permission.

### `PATCH` `/api/v1/billing/products/{id}/`

**Update software product (platform admin)**

Partially updates a software product by ID. Requires platform.billing edit permission.

### `PUT` `/api/v1/billing/products/{id}/`

**Replace software product (platform admin)**

Replaces a software product by ID. Requires platform.billing edit permission.

### `GET` `/api/v1/billing/subscription/invoices/`

**List subscription invoices across tenants (platform admin)**

Returns paginated subscription invoices across all tenants with aggregate payment statistics. Requires platform.billing view permission.

### `GET` `/api/v1/billing/subscription/invoices/{id}/`

**Retrieve subscription invoice (platform admin)**

Returns a single subscription invoice by ID. Requires platform.billing view permission.

### `PATCH` `/api/v1/billing/subscription/invoices/{id}/`

**Update subscription invoice (platform admin)**

Partially updates a subscription invoice record. Requires platform.billing edit permission.

### `GET` `/api/v1/billing/subscription/invoices/{id}/pdf/`

**Download subscription invoice PDF (platform admin)**

Downloads a subscription invoice PDF for any tenant. Returns binary application/pdf content. Requires platform.billing view permission.

</details>

---

## Module Map

| App | Base path | Views module |
|-----|-----------|--------------|
| Tenancy | `/api/v1/tenancy/` | `apps.tenancy.views` |
| Access | `/api/v1/access/` | `apps.access.views` |
| Branch | `/api/v1/branches/` | `apps.branch.views.branches` |
| Billing | `/api/v1/billing/` | `apps.billing.views` |
| Health | `/api/v1/health/` | `config.health` |

## Related Resources

- **Swagger UI**: `/api/v1/docs/`
- **ReDoc**: `/api/v1/redoc/`
- **OpenAPI schema**: `/api/v1/schema/`
- **Postman collection**: `Sortorium` (GeekSSort workspace)
