from apps.tenancy.views.auth import (
    ChangePasswordView,
    MeView,
    TenantAuthenticationView,
    TokenRefreshView,
)
from apps.tenancy.views.password import (
    InvitationValidationView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordSetupView,
)
from apps.tenancy.views.platform_admin import CurrentTenantFeaturesView
from apps.tenancy.views.profile_assets import ProfilePictureView
from apps.tenancy.views.register import TenantSelfRegistrationView
from apps.tenancy.views.settings import TenantBrandingView, TenantCompanyLogoView
from apps.tenancy.views.employee_invitation import (
    TenantEmployeeInvitationAcceptView,
    TenantEmployeeInvitationListCreateView,
    TenantEmployeeInvitationRevokeView,
    TenantEmployeeInvitationValidateView,
)
from apps.tenancy.views.tenant_user_management import (
    TenantUserDeactivateView,
    TenantUserDetailView,
    TenantUserRolesView,
)

from apps.tenancy.views.users import TenantUserListView

__all__ = [
    "ChangePasswordView",
    "CurrentTenantFeaturesView",
    "InvitationValidationView",
    "MeView",
    "PasswordResetConfirmView",
    "PasswordResetRequestView",
    "PasswordSetupView",
    "ProfilePictureView",
    "TenantBrandingView",
    "TenantCompanyLogoView",
    "TenantEmployeeInvitationAcceptView",
    "TenantEmployeeInvitationListCreateView",
    "TenantEmployeeInvitationRevokeView",
    "TenantEmployeeInvitationValidateView",
    "TenantAuthenticationView",
    "TenantSelfRegistrationView",
    "TenantUserDeactivateView",
    "TenantUserDetailView",
    "TenantUserListView",
    "TenantUserRolesView",
    "TokenRefreshView",
]
