from django.urls import path

from accounts.views.auth_views import RegisterView, LoginView
from accounts.views.user_views import MeView
from accounts.views.profile_views import ProfileView
from accounts.views.admin_views import (
    AdminUserListView,
    AdminUserDetailView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # AUTH
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    
    # JWT REFRESH
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # USER
    path("me/", MeView.as_view(), name="me"),

    # PROFILE
    # path("me/profile/", ProfileView.as_view(), name="profile"),

    # ADMIN
    # path("admin/users/", AdminUserListView.as_view(), name="admin-users"),
    # path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]