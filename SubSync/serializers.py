from rest_framework import serializers
# from django.contrib.auth import get_user_model
# User = get_user_model()
from .models import AirConditioner, Computer, HardwareServers, HardwareService, NetworkDevice, Notification, PortableDevice, Printer, Provider, Purchase, Resource, Scanner, Subscription, User, SoftwareSubscriptions, Utilities, Domain, Servers, Hardware, Warranty

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
    # class Meta:
    #     model = Provider
    #     fields = '__all__'
    id = serializers.IntegerField()  # Include the provider ID
    providerName = serializers.CharField(source='provider_name')
    providerContact = serializers.CharField(source='contact_phone', allow_blank=True, required=False)
    providerEmail = serializers.EmailField(source='contact_email')
    websiteLink = serializers.URLField(source='website', allow_blank=True, required=False)

    class Meta:
        model = Provider
        fields = ['id','providerName', 'providerContact', 'providerEmail', 'websiteLink']

class SubscriptionSerializer(serializers.ModelSerializer):
    # provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(),
        required=True  # Ensure provider ID is required
    )

    class Meta:
        model = Subscription
        fields = '__all__'

# class SubscriptionFilterSerializer(serializers.ModelSerializer):
#     provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())

#     software_name = serializers.CharField(source="software_detail.software_name", read_only=True)
#     server_name = serializers.CharField(source="server.server_name", read_only=True)
#     domain_name = serializers.CharField(source="domain.domain_name", read_only=True)
#     utility_name = serializers.CharField(source="billing.utility_type", read_only=True)

#     class Meta:
#         model = Subscription
#         fields = [
#             "id",
#             "subscription_category",
#             "provider",
#             "start_date",
#             "end_date",
#             "billing_cycle",
#             "cost",
#             "payment_status",
#             "next_payment_date",
#             "status",
#             "auto_renewal",
#             "software_name",
#             "server_name",
#             "domain_name",
#             "utility_name",
#         ]

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

# class SubscriptionDetailSerializer(serializers.ModelSerializer):
#     # provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
#     provider = ProviderSerializer(read_only=True)
#     software_detail = SoftwareSubscriptionSerializer(read_only=True)
#     billing = UtilitySerializer(read_only=True)
#     domain = DomainSerializer(read_only=True)
#     server = ServerSerializer(read_only=True)

#     class Meta:
#         model = Subscription
#         fields = [
#             "id",
#             "subscription_category",
#             "provider",
#             "start_date",
#             "end_date",
#             "billing_cycle",
#             "cost",
#             "payment_status",
#             "next_payment_date",
#             "status",
#             "auto_renewal",
#             "software_detail",
#             "billing",
#             "domain",
#             "server",
#         ]
class SubscriptionDetailSerializer(serializers.ModelSerializer):
    providerid = serializers.IntegerField(source="provider.id", read_only=True)
    providerName = serializers.CharField(source="provider.provider_name", read_only=True)
    providerContact = serializers.CharField(source="provider.contact_phone", read_only=True)
    providerEmail = serializers.EmailField(source="provider.contact_email", read_only=True)
    websiteLink = serializers.URLField(source="provider.website", read_only=True)

    billingid = serializers.IntegerField(source="billing.id", read_only=True)
    consumer_no = serializers.IntegerField(source="billing.consumer_no", read_only=True)
    utility_name = serializers.CharField(source="billing.utility_name", read_only=True)
    utility_type = serializers.CharField(source="billing.utility_type", read_only=True)
    subscription = serializers.IntegerField(source="billing.subscription.id", read_only=True)

    software_id = serializers.CharField(source="software_detail.software_id", read_only=True)
    software_name = serializers.CharField(source="software_detail.software_name", read_only=True)
    software_version = serializers.CharField(source="software_detail.version", read_only=True)
    software_no_of_users = serializers.IntegerField(source="software_detail.no_of_users", read_only=True)

    domain_id = serializers.IntegerField(source="domain.domain_id", read_only=True)
    domain_name = serializers.CharField(source="domain.domain_name", read_only=True)
    domain_type = serializers.CharField(source="domain.domain_type", read_only=True)
    ssl_certification = serializers.BooleanField(source="domain.ssl_certification", read_only=True)
    ssl_expiry_date = serializers.DateField(source="domain.ssl_expiry_date", read_only=True)
    whois_protection = serializers.BooleanField(source="domain.whois_protection", read_only=True)
    name_servers = serializers.CharField(source="domain.name_servers", read_only=True)
    hosting_provider = serializers.CharField(source="domain.hosting_provider", read_only=True)

    server_id = serializers.CharField(source="server.id", read_only=True)
    server_name = serializers.CharField(source="server.server_name", read_only=True)
    server_type = serializers.CharField(source="server.server_type", read_only=True)
    server_capacity = serializers.CharField(source="server.server_capacity", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "subscription_category",
            
            # Provider details (flattened)
            "providerid",
            "providerName",
            "providerContact",
            "providerEmail",
            "websiteLink",
            
            "start_date",
            "end_date",
            "billing_cycle",
            "cost",
            "payment_status",
            "next_payment_date",
            "status",
            "auto_renewal",
            
            # Software details (flattened)
            "software_id",
            "software_name",
            "software_version",
            "software_no_of_users",
            
            # Billing details (flattened)
            "billingid",
            "consumer_no",
            "utility_name",
            "utility_type",
            "subscription",
            
            # Domain details (flattened)
            "domain_id",
            "domain_name",
            "ssl_certification",
            "ssl_expiry_date",
            "whois_protection",
            "domain_type",
            "name_servers",
            "hosting_provider",
            
            # Server details (flattened)
            "server_id",
            "server_name",
            "server_type",
            "server_capacity"
        ]

    def to_representation(self, instance):
        """Remove null values and set a single 'name' field."""
        data = super().to_representation(instance)
        
        # Remove null values
        data = {key: value for key, value in data.items() if value is not None}
        
        # Determine 'name' field dynamically
        name_fields = ["utility_name", "software_name", "domain_name", "server_name"]
        for field in name_fields:
            if field in data:
                data["name"] = data.pop(field)  # Rename first found non-null name field
                break
        
        return data
    
class SubscriptionWarningSerializer(serializers.ModelSerializer):
    providerid = serializers.IntegerField(source="provider.id", read_only=True)
    providerName = serializers.CharField(source="provider.providerName", read_only=True)
    providerContact = serializers.CharField(source="provider.providerContact", read_only=True)
    providerEmail = serializers.EmailField(source="provider.providerEmail", read_only=True)
    websiteLink = serializers.URLField(source="provider.websiteLink", read_only=True)

    software_id = serializers.CharField(source="software_detail.software_id", read_only=True)
    software_name = serializers.CharField(source="software_detail.software_name", read_only=True)
    software_version = serializers.CharField(source="software_detail.version", read_only=True)
    software_no_of_users = serializers.IntegerField(source="software_detail.no_of_users", read_only=True)
   
    server_id = serializers.CharField(source="server.id", read_only=True)
    server_name = serializers.CharField(source="server.server_name", read_only=True)
    server_type = serializers.CharField(source="server.server_type", read_only=True)
    server_capacity = serializers.CharField(source="server.server_capacity", read_only=True)

    billingid = serializers.IntegerField(source="billing.id", read_only=True)
    consumer_no = serializers.IntegerField(source="billing.consumer_no", read_only=True)
    utility_name = serializers.CharField(source="billing.utility_name", read_only=True)
    utility_type = serializers.CharField(source="billing.utility_type", read_only=True)

    domain_id = serializers.IntegerField(source="domain.domain_id", read_only=True)
    domain_name = serializers.CharField(source="domain.domain_name", read_only=True)
    domain_type = serializers.CharField(source="domain.domain_type", read_only=True)
    ssl_certification = serializers.BooleanField(source="domain.ssl_certification", read_only=True)
    ssl_expiry_date = serializers.DateField(source="domain.ssl_expiry_date", read_only=True)
    whois_protection = serializers.BooleanField(source="domain.whois_protection", read_only=True)
    name_servers = serializers.CharField(source="domain.name_servers", read_only=True)
    hosting_provider = serializers.CharField(source="domain.hosting_provider", read_only=True)


    class Meta:
        model = Subscription
        fields = [
            "id", "subscription_category", "providerid", "providerName", "providerContact", "providerEmail",
            "websiteLink", "start_date", "end_date", "billing_cycle", "cost", "payment_status", "next_payment_date",
            "status", "auto_renewal", "software_id", "software_no_of_users","software_name","software_version", "server_id", "server_type",
            "server_capacity","server_name", "billingid", "consumer_no", "utility_type","utility_name","domain_id",
            "domain_name","ssl_certification","ssl_expiry_date","whois_protection","domain_type","name_servers","hosting_provider",

        ]
    def to_representation(self, instance):
        """Remove null values and set a single 'name' field."""
        data = super().to_representation(instance)
        
        # Remove null values
        data = {key: value for key, value in data.items() if value is not None}
        
        # Determine 'name' field dynamically
        name_fields = ["utility_name", "software_name", "domain_name", "server_name"]
        for field in name_fields:
            if field in data:
                data["name"] = data.pop(field)  # Rename first found non-null name field
                break
        
        return data

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

class ComputerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = '__all__'

class PortableDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortableDevice
        fields = '__all__'

class NetworkDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkDevice
        fields = '__all__'

class AirConditionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirConditioner
        fields = '__all__'

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareServers
        fields = '__all__'

class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = '__all__'

class ScannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scanner
        fields = '__all__'

class HardwareSerializer(serializers.ModelSerializer):
    purchase = PurchaseSerializer(required=False)
    warranty = WarrantySerializer(required=False)
    services = HardwareServiceSerializer(many=True, required=False)
    computer = ComputerSerializer(required=False)
    portable_device = PortableDeviceSerializer(required=False)
    network_device = NetworkDeviceSerializer(required=False)
    air_conditioner = AirConditionerSerializer(required=False)
    server = ServerSerializer(required=False)
    printer = PrinterSerializer(required=False)
    scanner = ScannerSerializer(required=False)

    class Meta:
        model = Hardware
        fields = '__all__'

    def create(self, validated_data):
        # Extract nested data
        purchase_data = validated_data.pop('purchase', None)
        warranty_data = validated_data.pop('warranty', None)
        services_data = validated_data.pop('services', [])
        computer_data = validated_data.pop('computer', None)
        portable_device_data = validated_data.pop('portable_device', None)
        network_device_data = validated_data.pop('network_device', None)
        air_conditioner_data = validated_data.pop('air_conditioner', None)
        server_data = validated_data.pop('server', None)
        printer_data = validated_data.pop('printer', None)
        scanner_data = validated_data.pop('scanner', None)

        # Create Hardware instance
        hardware = Hardware.objects.create(**validated_data)

        # Create related instances
        if purchase_data:
            Purchase.objects.create(hardware=hardware, **purchase_data)
        if warranty_data:
            Warranty.objects.create(hardware=hardware, **warranty_data)
        for service_data in services_data:
            HardwareService.objects.create(hardware=hardware, **service_data)
        if computer_data:
            Computer.objects.create(hardware=hardware, **computer_data)
        if portable_device_data:
            PortableDevice.objects.create(hardware=hardware, **portable_device_data)
        if network_device_data:
            NetworkDevice.objects.create(hardware=hardware, **network_device_data)
        if air_conditioner_data:
            AirConditioner.objects.create(hardware=hardware, **air_conditioner_data)
        if server_data:
            HardwareServers.objects.create(hardware=hardware, **server_data)
        if printer_data:
            Printer.objects.create(hardware=hardware, **printer_data)
        if scanner_data:
            Scanner.objects.create(hardware=hardware, **scanner_data)

        return hardware
    
# class HardwareSerializer(serializers.ModelSerializer):
#     warranty = WarrantySerializer(required=False)
#     purchase = PurchaseSerializer(required=False)
#     service = HardwareServiceSerializer(required=False)

#     class Meta:
#         model = Hardware
#         fields = '__all__'
#         extra_kwargs = {'user': {'read_only': True}}

#     def create(self, validated_data):
#         """Create Hardware first, then assign its ID to related models"""

#         user = validated_data.pop('user', None)
#         if user is None:
#             raise serializers.ValidationError({"user": "User is required."})

#         # user = request.user if request else None

#         # if not user or not user.is_authenticated:
#         #     raise serializers.ValidationError({"user": ["Authentication required."]})

#         # Extract nested data
#         warranty_data = validated_data.pop('warranty', None)
#         purchase_data = validated_data.pop('purchase', None)
#         service_data = validated_data.pop('service', None)

#         # Ensure unique serial number
#         if Hardware.objects.filter(serial_number=validated_data.get('serial_number')).exists():
#             raise serializers.ValidationError({"serial_number": ["A hardware with this serial number already exists."]})

#         # Create Hardware
#         hardware = Hardware.objects.create(user=user,**validated_data)

#         # Assign Foreign Key hardware to related tables
#         if warranty_data:
#             Warranty.objects.create(hardware=hardware, **warranty_data)
#         if purchase_data:
#             Purchase.objects.create(hardware=hardware, **purchase_data)
#         if service_data:
#             HardwareService.objects.create(hardware=hardware, **service_data)

#         return hardware
    
#     def update(self, instance, validated_data):
#         # Update Hardware fields
#         warranty_data = validated_data.pop('warranty', None)
#         purchase_data = validated_data.pop('purchase', None)
#         service_data = validated_data.pop('service', None)

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()

#         # Handle Warranty Update
#         if warranty_data:
#             warranty, _ = Warranty.objects.update_or_create(hardware=instance, defaults=warranty_data)

#         # Handle Purchase Update
#         if purchase_data:
#             purchase, _ = Purchase.objects.update_or_create(hardware=instance, defaults=purchase_data)

#         # Handle Service Update
#         if service_data:
#             service, _ = HardwareService.objects.update_or_create(hardware=instance, defaults=service_data)

#         return instance
    
from rest_framework import serializers
from .models import Reminder

class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = '__all__'

    def validate(self, data):
        """Custom validation for reminder logic."""
        print("Received Data:", data) 
        cycle = data.get('subscription_cycle')
        days_in_advance = data.get('days_in_advance')
        reminder_months_before = data.get('reminder_months_before')
        reminder_day_of_month = data.get('reminder_day_of_month')

        if cycle in ["weekly", "monthly"]:
            if reminder_months_before or reminder_day_of_month:
                raise serializers.ValidationError("Months in advance and reminder day are not allowed for weekly/monthly cycles.")
            if days_in_advance is None:
                raise serializers.ValidationError("Days in advance is required for weekly/monthly cycles.")

        elif cycle in ["quarterly", "semi-annual", "annual", "biennial", "triennial"]:
            if reminder_months_before is None:
                raise serializers.ValidationError("Months in advance is required for these cycles.")
            if reminder_day_of_month and (reminder_day_of_month < 1 or reminder_day_of_month > 31):
                raise serializers.ValidationError("Reminder day of the month must be between 1 and 31.")

        return data

class ResourceNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['resource_name']

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__' 

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "subscription", "message", "is_read", "created_at"]