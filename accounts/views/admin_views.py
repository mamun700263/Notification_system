from rest_framework import generics, permissions
from accounts.models import TavUser
from accounts.serializers.admin_user_serializers import TavUserAdminSerializer

class AdminUserListView(generics.ListAPIView):
    queryset = TavUser.objects.all()
    serializer_class = TavUserAdminSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TavUser.objects.all()
    serializer_class = TavUserAdminSerializer
    permission_classes = [permissions.IsAdminUser]