from rest_framework import serializers
# from django.contrib.auth import get_user_model

# User = get_user_model()
from .models import Provider, Subscription, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])  #  Hash the password before saving
        user.save()
        return user

class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text="URL-safe base64 encoded user ID")
    token = serializers.CharField(help_text="Password reset token")
    new_password = serializers.CharField(min_length=8, write_only=True, help_text="New password (min. 8 characters)")

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = '__all__'

class SubscriptionSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())

    class Meta:
        model = Subscription
        fields = '__all__'