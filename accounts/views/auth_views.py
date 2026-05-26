from rest_framework import generics, permissions
from accounts.serializers.auth_serializers import (
    TavUserRegisterSerializer,
    LoginSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from accounts.models import TavUser

class RegisterView(generics.CreateAPIView):
    queryset = TavUser.objects.all()
    serializer_class = TavUserRegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]