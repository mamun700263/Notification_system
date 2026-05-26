from rest_framework import generics, permissions
from accounts.models import TavUser
from accounts.serializers.user_serializers import TavUserPublicSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = TavUserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user