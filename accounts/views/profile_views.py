from rest_framework import generics, permissions
from accounts.models import Account
from accounts.serializers.profile_serializers import AccountSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.account

