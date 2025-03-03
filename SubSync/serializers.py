from rest_framework import serializers
# from django.contrib.auth import get_user_model
# User = get_user_model()
from .models import HardwareService, Provider, Purchase, Subscription, User, SoftwareSubscriptions, Utilities, Domain, Servers, Hardware, Warranty

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

from rest_framework import serializers
from .models import User

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile_picture']
        extra_kwargs = {
            'email': {'required': False},  # Allow partial updates
            'username': {'required': False},
            'profile_picture': {'required': False}
        }

    def update(self, instance, validated_data):
        # Update user fields if provided
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        
        # Update profile picture if provided
        if 'profile_picture' in validated_data:
            instance.profile_picture = validated_data['profile_picture']

        instance.save()
        return instance

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

class SubscriptionFilterSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())

    software_name = serializers.CharField(source="software_detail.software_name", read_only=True)
    server_name = serializers.CharField(source="server.server_name", read_only=True)
    domain_name = serializers.CharField(source="domain.domain_name", read_only=True)
    utility_name = serializers.CharField(source="billing.utility_type", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "subscription_category",
            "provider",
            "start_date",
            "end_date",
            "billing_cycle",
            "cost",
            "payment_status",
            "next_payment_date",
            "status",
            "auto_renewal",
            "software_name",
            "server_name",
            "domain_name",
            "utility_name",
        ]

    
class SoftwareSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareSubscriptions
        fields = '__all__'

class UtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilities
        fields = '__all__'

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = '__all__'

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servers
        fields = '__all__'

class WarrantySerializer(serializers.ModelSerializer):
    class Meta:
        model = Warranty
        exclude = ['hardware']  # Exclude hardware because we'll set it manually

class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        exclude = ['hardware']

class HardwareServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareService
        exclude = ['hardware']

class HardwareSerializer(serializers.ModelSerializer):
    warranty = WarrantySerializer(required=False)
    purchase = PurchaseSerializer(required=False)
    service = HardwareServiceSerializer(required=False)

    class Meta:
        model = Hardware
        fields = '__all__'
        extra_kwargs = {'user': {'read_only': True}}

    def create(self, validated_data):
        """Create Hardware first, then assign its ID to related models"""

        user = validated_data.pop('user', None)
        if user is None:
            raise serializers.ValidationError({"user": "User is required."})

        # user = request.user if request else None

        # if not user or not user.is_authenticated:
        #     raise serializers.ValidationError({"user": ["Authentication required."]})

        # Extract nested data
        warranty_data = validated_data.pop('warranty', None)
        purchase_data = validated_data.pop('purchase', None)
        service_data = validated_data.pop('service', None)

        # Ensure unique serial number
        if Hardware.objects.filter(serial_number=validated_data.get('serial_number')).exists():
            raise serializers.ValidationError({"serial_number": ["A hardware with this serial number already exists."]})

        # Create Hardware
        hardware = Hardware.objects.create(user=user,**validated_data)

        # Assign Foreign Key hardware to related tables
        if warranty_data:
            Warranty.objects.create(hardware=hardware, **warranty_data)
        if purchase_data:
            Purchase.objects.create(hardware=hardware, **purchase_data)
        if service_data:
            HardwareService.objects.create(hardware=hardware, **service_data)

        return hardware
    
    def update(self, instance, validated_data):
        # Update Hardware fields
        warranty_data = validated_data.pop('warranty', None)
        purchase_data = validated_data.pop('purchase', None)
        service_data = validated_data.pop('service', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle Warranty Update
        if warranty_data:
            warranty, _ = Warranty.objects.update_or_create(hardware=instance, defaults=warranty_data)

        # Handle Purchase Update
        if purchase_data:
            purchase, _ = Purchase.objects.update_or_create(hardware=instance, defaults=purchase_data)

        # Handle Service Update
        if service_data:
            service, _ = HardwareService.objects.update_or_create(hardware=instance, defaults=service_data)

        return instance