from rest_framework import serializers
from .models import Reminder,AirConditioner, Computer, Customer, HardwareService, NetworkDevice, Notification, PortableDevice, Printer, Provider, Purchase, Resource, Scanner, Subscription, User, SoftwareSubscriptions, Utilities, Domain, Servers, Hardware, Warranty
from django.db import transaction
from django.core.validators import validate_email
from simple_history.models import HistoricalRecords
import re  # Regular Expressions for extracting numbers

import logging
logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password','is_active','is_superuser']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])  #  Hash the password before saving
        user.save()
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile_picture','phone_numbers']
        extra_kwargs = {
            'email': {'required': False},  # Allow partial updates
            'username': {'required': False},
            'profile_picture': {'required': False},
            'phone_numbers': {'required': False}
        }

    def update(self, instance, validated_data):
        # Update user fields if provided
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        instance.phone_numbers=validated_data.get('phone_numbers',instance.phone_numbers)
        
        # Update profile picture if provided
        if 'profile_picture' in validated_data:
            instance.profile_picture = validated_data['profile_picture']

        instance.save()
        return instance

class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text="URL-safe base64 encoded user ID")
    token = serializers.CharField(help_text="Password reset token")
    new_password = serializers.CharField(min_length=8, write_only=True, help_text="New password (min. 8 characters)")

    def validate_new_password(self, value):
        """
        Validate that the password meets complexity requirements.
        """
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one digit
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        
        return value

class ProviderSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True) 
    providerName = serializers.CharField(source='provider_name',max_length=255, required=True)
    providerContact = serializers.CharField(source='contact_phone',  required=True)
    providerEmail = serializers.EmailField(source='contact_email',required=True)
    websiteLink = serializers.URLField(source='website',  required=True)
    # category = serializers.ChoiceField(choices=Provider.CATEGORY_CHOICES)
    
    class Meta:
        model = Provider
        fields = [ 'id','providerName', 'providerContact', 'providerEmail', 'websiteLink']
                #   'category']

    def validate_provider_name(self, value):
        """Ensure provider name is unique and not empty."""
        if not value.strip():
            raise serializers.ValidationError("Provider name cannot be empty.")
        
        provider_qs = Provider.objects.filter(provider_name=value)

        # Exclude self if updating
        if self.instance:
            provider_qs = provider_qs.exclude(pk=self.instance.pk)

        if provider_qs.exists():
            raise serializers.ValidationError("Provider name must be unique.")
        
        return value
    
    def validate_provider_contact(self, value):
        """Ensure phone number contains only digits and has a valid length."""
        if value and not re.match(r'^\d{7,15}$', value):
            raise serializers.ValidationError("Phone number must contain only digits and be between 7 to 15 characters long.")
        return value
    
    # def validate_providerEmail(self, value):
    #     """Check if the email is already used"""
    #     if Provider.objects.filter(contact_email=value).exists():
    #         raise serializers.ValidationError("A provider with this email already exists.")
    #     return value

class SubscriptionSerializer(serializers.ModelSerializer):
    # provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.all(),
        required=True  # Ensure provider ID is required
    )

    class Meta:
        model = Subscription
        fields = '__all__'

class SoftwareSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareSubscriptions
        fields = '__all__'

    def validate_software_id(self, value):
        """ Ensure software_id is unique """
        if SoftwareSubscriptions.objects.filter(software_id=value).exists():
            raise serializers.ValidationError("A software subscription with this ID already exists.")
        return value

class UtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilities
        fields = '__all__'

    def validate_consumer_no(self, value):
        """ Ensure consumer_no is unique """
        if Utilities.objects.filter(consumer_no=value).exists():
            raise serializers.ValidationError("This consumer number is already registered.")
        return value

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = '__all__'

    def validate_domain_name(self, value):
        """ Ensure domain_name is unique """
        if Domain.objects.filter(domain_name=value).exists():
            raise serializers.ValidationError("This domain is already registered.")
        return value

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servers
        fields = '__all__'

    def validate_server_name(self, value):
        """ Ensure server_name is unique """
        if Servers.objects.filter(server_name=value).exists():
            raise serializers.ValidationError("This server name is already in use.")
        return value

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

    deleted_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", read_only=True)
    deleted_by_username = serializers.CharField(source='deleted_by.username', read_only=True)
    last_payment_date = serializers.DateField(format="%Y-%m-%d", read_only=True)

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
            # "end_date",
            "billing_cycle",
            "cost",
            "payment_status",
            "next_payment_date",
            "last_payment_date",
            "status",
            "auto_renewal",
            'deleted_by',
            'deleted_by_username' ,
            
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
            "server_capacity",
            "deleted_at",
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
    
class SubscriptionUpdateSerializer(serializers.ModelSerializer):
    # Software Details
    version = serializers.CharField(source="software_detail.version", required=False ,allow_null=True, allow_blank=True,default=None,)
    no_of_users = serializers.IntegerField(source="software_detail.no_of_users", required=False, allow_null=True,default=None,)
    
    # Billing Details
    consumer_no = serializers.IntegerField(source="billing.consumer_no",required=False,allow_null=True,default=None)
    utility_name = serializers.CharField(source="billing.utility_name", required=False)
    
    # Domain Details
    domain_name = serializers.CharField(source="domain.domain_name", required=False)
    domain_type = serializers.CharField(source="domain.domain_type", required=False,allow_null=True,allow_blank=True,default=None)
    ssl_certification = serializers.BooleanField(source="domain.ssl_certification", required=False,allow_null=True,default=None)
    ssl_expiry_date = serializers.DateField(source="domain.ssl_expiry_date", required=False,allow_null=True,default=None)
    whois_protection = serializers.BooleanField(source="domain.whois_protection", required=False,allow_null=True,default=None)
    name_servers = serializers.CharField(source="domain.name_servers", required=False,allow_null=True,allow_blank=True,default=None)
    hosting_provider = serializers.CharField(source="domain.hosting_provider", required=False,allow_null=True,allow_blank=True,default=None)
    
    # Server Details
    server_name = serializers.CharField(source="server.server_name", required=False)
    name_servers = serializers.CharField(source="domain.name_servers", required=False,allow_null=True,allow_blank=True)
    server_capacity = serializers.CharField(source="server.server_capacity", required=False,allow_null=True,allow_blank=True)

    last_payment_date = serializers.DateField(required=False, allow_null=True)
    provider_name = serializers.CharField(source="provider.name",read_only=True)
    provider_id = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all(),source="provider",required=False,allow_null=True)

    class Meta:
        model = Subscription
        fields = [
            # Subscription fields
            "subscription_category", "start_date",  "billing_cycle",
            "cost", "payment_status", "next_payment_date","last_payment_date", "status", "auto_renewal",
            
            # Software fields
            "version", "no_of_users",
            
            # Billing fields
            "consumer_no", "utility_name",
            
            # Domain fields
            "domain_name", "ssl_certification","ssl_expiry_date","whois_protection","domain_type","hosting_provider","name_servers",
            
            # Server fields
            "server_name","name_servers","server_capacity",
            "provider_name" , "provider_id"
        ]
        extra_kwargs = {
            'start_date': {'required': False},
            # 'end_date': {'required': False, 'allow_null': True},
            'billing_cycle': {'required': False},
            'cost': {'required': False, 'min_value': 0},
            'payment_status': {'required': False},
            'next_payment_date': {'required': False, 'allow_null': True},
            'last_payment_date': {'required': False, 'allow_null': True},
            'status': {'required': False},
            'auto_renewal': {'required': False},
        }

    def update(self, instance, validated_data):
        print("Validated data:", validated_data)
        # Extract nested data
        software_data = validated_data.pop('software_detail', {})
        print("Software data to update:", software_data)
        billing_data = validated_data.pop('billing', {})
        print("billing data to update:", billing_data)
        domain_data = validated_data.pop('domain', {})
        print("domain data to update:", domain_data)
        server_data = validated_data.pop('server', {})
        print("server data to update:", server_data)

        # Remove last_payment_date if it is None to prevent unnecessary validation
        if "last_payment_date" in validated_data and validated_data["last_payment_date"] is None:
            validated_data.pop("last_payment_date")

        # Update main model
        instance = super().update(instance, validated_data)

        try:
            if software_data is not None and hasattr(instance, 'software_detail'):
                self._update_related_model(instance.software_detail, software_data)
            
            if billing_data is not None and hasattr(instance, 'billing'):
                self._update_related_model(instance.billing, billing_data)
            
            if domain_data is not None and hasattr(instance, 'domain'):
                self._update_related_model(instance.domain, domain_data)
            
            if server_data is not None and hasattr(instance, 'server'):
                self._update_related_model(instance.server, server_data)
        
        except Exception as e:
            # Rollback the instance update if related model update fails
            instance.refresh_from_db()
            logger.error(f"Failed to update subscription: {str(e)}")
            raise serializers.ValidationError(
                f"Failed to update related models: {str(e)}"
            )

        return instance

    def _update_related_model(self, model_instance, data):
        """Helper method to update related model instances"""
        for attr, value in data.items():
            print(f"Updating {attr} to {value}")
            setattr(model_instance, attr, value)
        if hasattr(model_instance, 'updated_by') and hasattr(self.context['request'], 'user'):
            model_instance.updated_by = self.context['request'].user
        model_instance.save()
        print("after update:",model_instance)     
    
class SubscriptionWarningSerializer(serializers.ModelSerializer):
    providerid = serializers.IntegerField(source="provider.id", read_only=True)
    providerName = serializers.CharField(source="provider.provider_name", read_only=True)
    providerContact = serializers.CharField(source="provider.contact_phone", read_only=True)
    providerEmail = serializers.EmailField(source="provider.contact_email", read_only=True)
    websiteLink = serializers.URLField(source="provider.website", read_only=True)

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
            "websiteLink", "start_date", "billing_cycle", "cost", "payment_status", "next_payment_date",
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
        extra_kwargs = {
            'hardware': {'required': False}  # Since we set it manually
        }

class ComputerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class PortableDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortableDevice
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class NetworkDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkDevice
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class AirConditionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirConditioner
        fields = '__all__'
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = '__all__'
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class ScannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scanner
        fields = '__all__'
        fields = '__all__'
        extra_kwargs = {
            'hardware': {'required': False}  # Allow hardware to be assigned later
        }

class HardwareSerializer(serializers.ModelSerializer):
    purchase = PurchaseSerializer(required=False)
    warranty = WarrantySerializer(required=False)
    services = HardwareServiceSerializer( required=False,many=False)

    computer = ComputerSerializer(required=False)
    portable_device = PortableDeviceSerializer(required=False)
    network_device = NetworkDeviceSerializer(required=False)
    air_conditioner = AirConditionerSerializer(required=False)
    # on_premise_server = HardwareServerSerializer(required=False)
    printer = PrinterSerializer(required=False)
    scanner = ScannerSerializer(required=False)
    
    imei_number = serializers.CharField(source="portable_device.imei_number",required=False,allow_null=True,allow_blank=True)
    os_version = serializers.CharField(source="portable_device.os_version",required=False,allow_null=True,allow_blank=True)
    portable_storage = serializers.CharField(source="portable_device.storage",required=False,allow_null=True,allow_blank=True)
    
    # Add similar mappings for warranty and service fields
    warranty_expiry_date = serializers.DateField(source="warranty.warranty_expiry_date",required=False,allow_null=True)

    purchase_date = serializers.DateField(source="purchase.purchase_date",required=False,allow_null=True)
    purchase_cost = serializers.DecimalField(source="purchase.purchase_cost",max_digits=10,decimal_places=2,required=False,allow_null=True)
    last_service_date = serializers.DateField(source="services.last_service_date",required=False,allow_null=True)
    next_service_date = serializers.DateField(source="services.next_service_date",required=False,allow_null=True)
    service_cost = serializers.DecimalField(source="services.service_cost",max_digits=10,decimal_places=2,required=False,allow_null=True)

    class Meta:
        model = Hardware
        fields = '__all__'

    def create(self, validated_data):
        print("\n*************************************************************************************************************************************")
        logger.info("Validated data before saving: %s", validated_data)
        # Extract nested data
        purchase_data = validated_data.pop('purchase', None)
        warranty_data = validated_data.pop('warranty', None)
        # services_data = validated_data.pop('services', [])
        services_data = validated_data.pop('services', None)
        computer_data = validated_data.pop('computer', None)
        portable_device_data = validated_data.pop('portable_device', None)
        network_device_data = validated_data.pop('network_device', None)
        air_conditioner_data = validated_data.pop('air_conditioner', None)
        # server_data = validated_data.pop('on_premise_server', None)
        printer_data = validated_data.pop('printer', None)
        scanner_data = validated_data.pop('scanner', None)

        try:
            with transaction.atomic():  # Start transaction

                # Create Hardware instance
                hardware = Hardware.objects.create(**validated_data)

                # Create related instances
                if purchase_data:
                    Purchase.objects.create(hardware=hardware, **purchase_data)
                if warranty_data:
                    Warranty.objects.create(hardware=hardware, **warranty_data)
                if services_data :
                    HardwareService.objects.create(hardware=hardware, **services_data)

                if computer_data:
                    computer_data["hardware"] = hardware
                    Computer.objects.create(**computer_data)
                if portable_device_data:
                    portable_device_data["hardware"] = hardware  # Explicitly set hardware reference
                    PortableDevice.objects.create(**portable_device_data)
                if network_device_data:
                    NetworkDevice.objects.create(hardware=hardware, **network_device_data)
                if air_conditioner_data:
                    AirConditioner.objects.create(hardware=hardware, **air_conditioner_data)
                # if server_data:
                #     HardwareServers.objects.create(hardware=hardware, **server_data)
                if printer_data:
                    Printer.objects.create(hardware=hardware, **printer_data)
                if scanner_data:
                    Scanner.objects.create(hardware=hardware, **scanner_data)

                return hardware
        
        except Exception as e:
            logger.error("Error while creating hardware and related objects: %s", str(e))
            raise serializers.ValidationError({"message": "Failed to add hardware. Please try again."})
    
    def to_representation(self, instance):
        """Remove null values and set a single 'name' field."""
        data = super().to_representation(instance)
        
        # Remove null values
        data = {key: value for key, value in data.items() if value is not None}

        # Filter out unrelated device details based on `hardware_type`
        hardware_type_mapping = {
            'Laptop': 'computer',
            'Desktop': 'computer',
            'Mobile Phone': 'portable_device',
            'Tablet': 'portable_device',
            'Network Device': 'network_device',
            'Air Conditioner': 'air_conditioner',
            'On-Premise Server': 'computer',
            'Printer': 'printer',
            'Scanner': 'scanner',
        }

        hardware_type = instance.hardware_type
        relevant_field = hardware_type_mapping.get(hardware_type)

        # Remove other device-specific fields that do not match `hardware_type`
        device_fields = [
            'computer', 'portable_device', 'network_device', 'air_conditioner', 'printer', 'scanner'
            # 'on_premise_server',
        ]

        for field in device_fields:
            if field != relevant_field:
                data.pop(field, None)

        return data
    
    def validate_serial_number(self, value):
        """Ensure serial number is unique and follows format."""
        # If instance exists, exclude it from uniqueness check
        instance = getattr(self, 'instance', None)
        if Hardware.objects.filter(serial_number=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError("Serial number already exists.")
        return value
    def validate_purchase(self, value):
        """Ensure purchase cost is a positive number."""
        if value.get("purchase_cost") is not None and value["purchase_cost"] < 0:
            raise serializers.ValidationError("Purchase cost must be a positive number.")
        return value
    def validate_warranty(self, value):
        """Ensure warranty dates are valid."""
        purchase_date = self.initial_data.get("purchase", {}).get("purchase_date")
        warranty_date = value.get("warranty_expiry_date")

        if purchase_date and warranty_date and purchase_date > warranty_date:
            raise serializers.ValidationError("Warranty expiry date must be after purchase date.")
        
        if value.get("is_extended_warranty") and value.get("extended_warranty_period") is not None:
            if value["extended_warranty_period"] < 0:
                raise serializers.ValidationError("Extended warranty period must be positive.")
        
        return value
    def validate_recipients(self, value):
        """Ensure recipients email is valid."""
        try:
            validate_email(value)
        except:
            raise serializers.ValidationError("Invalid email format for recipients.")
        return value
    
    def validate_services(self, value):
        """Ensure service dates are valid."""
        if value:  # value is now a single dict
            last_date = value.get("last_service_date")
            next_date = value.get("next_service_date")
            if last_date and next_date and last_date > next_date:
                raise serializers.ValidationError(
                    "Next service date must be after last service date."
                )
        return value
    
    def update(self, instance, validated_data):
        # Extract nested data
        purchase_data = validated_data.pop('purchase', None)
        warranty_data = validated_data.pop('warranty', None)
        services_data = validated_data.pop('services', None)
        
        # Hardware type specific data
        computer_data = validated_data.pop('computer', None)
        portable_device_data = validated_data.pop('portable_device', None)
        network_device_data = validated_data.pop('network_device', None)
        air_conditioner_data = validated_data.pop('air_conditioner', None)
        printer_data = validated_data.pop('printer', None)
        scanner_data = validated_data.pop('scanner', None)

        try:
            with transaction.atomic():
                # Update main Hardware instance
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()

                # Update or create related models
                if purchase_data:
                    purchase_instance = getattr(instance, 'purchase', None)
                    if purchase_instance:
                        self._update_related_model(purchase_instance, purchase_data)
                    else:
                        Purchase.objects.create(hardware=instance, **purchase_data)
                if warranty_data and hasattr(instance, 'warranty'):
                    self._update_related_model(instance.warranty, warranty_data)
                elif warranty_data:
                    Warranty.objects.create(hardware=instance, **warranty_data)
                
                if services_data is not None:
                    service_instance = getattr(instance, 'services', None)
                    if service_instance:
                        self._update_related_model(service_instance, services_data)
                    else:
                        HardwareService.objects.create(hardware=instance, **services_data)

                # Update hardware type specific models
                if instance.hardware_type in ['Laptop', 'Desktop']:
                    if computer_data and hasattr(instance, 'computer'):
                        self._update_related_model(instance.computer, computer_data)
                    elif computer_data:
                        Computer.objects.create(hardware=instance, **computer_data)
            
                elif instance.hardware_type in ['Mobile Phone', 'Tablet']:
                    if portable_device_data and hasattr(instance, 'portable_device'):
                        self._update_related_model(instance.portable_device, portable_device_data)
                    elif portable_device_data:
                        PortableDevice.objects.create(hardware=instance, **portable_device_data)
                
                elif instance.hardware_type == 'Network Device':
                    if network_device_data and hasattr(instance, 'network_device'):
                        self._update_related_model(instance.network_device, network_device_data)
                    elif network_device_data:
                        NetworkDevice.objects.create(hardware=instance, **network_device_data)
                
                elif instance.hardware_type == 'Air Conditioner':
                    if air_conditioner_data and hasattr(instance, 'air_conditioner'):
                        self._update_related_model(instance.air_conditioner, air_conditioner_data)
                    elif air_conditioner_data:
                        AirConditioner.objects.create(hardware=instance, **air_conditioner_data)
                
                elif instance.hardware_type == 'Printer':
                    if printer_data and hasattr(instance, 'printer'):
                        self._update_related_model(instance.printer, printer_data)
                    elif printer_data:
                        Printer.objects.create(hardware=instance, **printer_data)
                
                elif instance.hardware_type == 'Scanner':
                    if scanner_data and hasattr(instance, 'scanner'):
                        self._update_related_model(instance.scanner, scanner_data)
                    elif scanner_data:
                        Scanner.objects.create(hardware=instance, **scanner_data)

                return instance
        except Exception as e:
            logger.error(f"Error updating hardware: {str(e)}")
            raise serializers.ValidationError({"message": "Failed to update hardware."})
        
    def _update_related_model(self, model_instance, data):
        """Helper to update a single related model instance"""
        if model_instance is None:
            return
            
        for attr, value in data.items():
            if value is not None:  # Only update non-null values
                setattr(model_instance, attr, value)
        model_instance.save()

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
        fields = ['id','resource_name']

class CustomerBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields= "__all__"

class ResourceAddSerializer(serializers.ModelSerializer):
    # customer = CustomerBasicSerializer(read_only=True)
    
    class Meta:
        model = Resource
        fields = '__all__'
        extra_kwargs = {
            'server': {'required': False},
            'user': {'required': False}
        }

    def validate(self, data):
        """
        Custom validation to set user and check server capacity.
        """
        if data is None:
            raise serializers.ValidationError("Invalid input data")
        
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is missing")
            
        data["status"] = "Active"

        # Convert hosting_location_name to server ID
        hosting_location_name = self.initial_data.get("hosting_location_name")  # Frontend field
        if hosting_location_name:
            try:
                server = Servers.objects.get(server_name=hosting_location_name)
                data["server"] = server
            except Servers.DoesNotExist:
                raise serializers.ValidationError({"hosting_location": "Invalid server name."})
            
        # Check if the server has enough capacity
        server = data.get("server")
        new_resource_capacity = data.get("storage_capacity", 0)

        if server:
            # Convert storage capacity to integer (assuming it's in GB or TB needs conversion)
            total_capacity = self._convert_to_gb(server.server_capacity)
            used_capacity = self._get_used_capacity(server)

            if used_capacity + self._convert_to_gb(new_resource_capacity) > total_capacity:
                raise serializers.ValidationError({"storage_capacity": "Not enough server capacity available."})

        return data

    def to_internal_value(self, data):
        # Mapping frontend fields to backend fields
        field_mapping = {
            "billing_cycle": "billing_cycle",
            "hosting_location": "server",
            "hosting_type": "hosting_type",
            "last_updated_date": "last_updated_date",
            "last_updated_date": "last_payment_date",
            "provisioned_date": "provisioned_date",
            "resource_cost": "resource_cost",
            "resource_name": "resource_name",
            "resource_type": "resource_type",
            "storage_capacity": "storage_capacity",
             "paymentMethod":"payment_method"
            # "hosting_location_name": "hosting_location_name",
            # "user": "user"
        }

        # Convert frontend field names to backend field names
        converted_data = {backend_key: data.get(frontend_key) for frontend_key, backend_key in field_mapping.items() if frontend_key in data}

        # Convert hosting_location (name) to server (ID)
        hosting_location_name = data.get("hosting_location")
        if hosting_location_name:
            try:
                server = Servers.objects.get(server_name=hosting_location_name)  # Convert name to ID
                converted_data["server"] = server.id
            except Servers.DoesNotExist:
                raise serializers.ValidationError({"server": "Invalid server name."})

            return super().to_internal_value(converted_data)

    def _convert_to_gb(self, capacity):
        """ Helper function to convert capacity to GB if necessary. """
        if isinstance(capacity, str):
            if "TB" in capacity:
                return int(capacity.replace("TB", "").strip()) * 1000  # Convert TB to GB
            elif "GB" in capacity:
                return int(capacity.replace("GB", "").strip())  # Already in GB
        return int(capacity)

    def _get_used_capacity(self, server):
        """ Helper function to calculate total used capacity on a server. """
        return sum(self._convert_to_gb(resource.storage_capacity) for resource in server.server_resources.all())
    
class ResourceViewSerializer(serializers.ModelSerializer):
    customer = CustomerBasicSerializer(read_only=True)
    server = ServerSerializer(read_only=True)
    
    class Meta:
        model = Resource
        fields = '__all__'
        extra_kwargs = {
            'server': {'required': False},
            'user': {'required': False}
        }

    def validate(self, data):
        """
        Custom validation to set user and check server capacity.
        """
        request = self.context.get('request')

        # Convert hosting_location_name to server ID
        hosting_location_name = self.initial_data.get("hosting_location_name")  # Frontend field
        if hosting_location_name:
            try:
                server = Servers.objects.get(server_name=hosting_location_name)
                data["server"] = server
            except Servers.DoesNotExist:
                raise serializers.ValidationError({"hosting_location": "Invalid server name."})
            
        # Check if the server has enough capacity
        server = data.get("server")
        new_resource_capacity = data.get("storage_capacity", 0)

        if server:
            # Convert storage capacity to integer (assuming it's in GB or TB needs conversion)
            total_capacity = self._convert_to_gb(server.server_capacity)
            used_capacity = self._get_used_capacity(server)

            if used_capacity + self._convert_to_gb(new_resource_capacity) > total_capacity:
                raise serializers.ValidationError({"storage_capacity": "Not enough server capacity available."})

        return data

    def to_internal_value(self, data):
        # Mapping frontend fields to backend fields
        field_mapping = {
            "billing_cycle": "billing_cycle",
            "hosting_location": "server",
            "hosting_type": "hosting_type",
            "last_updated_date": "last_updated_date",
            "provisioned_date": "provisioned_date",
            "resource_cost": "resource_cost",
            "resource_name": "resource_name",
            "resource_type": "resource_type",
            "storage_capacity": "storage_capacity",
            # "hosting_location_name": "hosting_location_name",
            # "user": "user"
        }

        # Convert frontend field names to backend field names
        converted_data = {backend_key: data.get(frontend_key) for frontend_key, backend_key in field_mapping.items() if frontend_key in data}

        # Convert hosting_location (name) to server (ID)
        hosting_location_name = data.get("hosting_location")
        if hosting_location_name:
            try:
                server = Servers.objects.get(server_name=hosting_location_name)  # Convert name to ID
                converted_data["server"] = server.id
            except Servers.DoesNotExist:
                raise serializers.ValidationError({"server": "Invalid server name."})

        return super().to_internal_value(converted_data)

    def _convert_to_gb(self, capacity):
        """ Helper function to convert capacity to GB if necessary. """
        if isinstance(capacity, str):
            if "TB" in capacity:
                return int(capacity.replace("TB", "").strip()) * 1000  # Convert TB to GB
            elif "GB" in capacity:
                return int(capacity.replace("GB", "").strip())  # Already in GB
        return int(capacity)

    def _get_used_capacity(self, server):
        """ Helper function to calculate total used capacity on a server. """
        return sum(self._convert_to_gb(resource.storage_capacity) for resource in server.server_resources.all())

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "subscription", "message", "is_read", "created_at"]

class ResourceBasicSerializer(serializers.ModelSerializer):
    # Remove the redundant source='hosting_type' since field name matches model field
    hosting_type = serializers.CharField(allow_null=True)
    server_name = serializers.CharField(source='server.server_name', read_only=True)
    
    class Meta:
        model = Resource
        fields = [
            'id',
            'resource_name',
            'resource_type',
            'status',
            'billing_cycle',
            'resource_cost',
            'storage_capacity',
            'provisioned_date',
            'next_payment_date',
            'hosting_type',
            'server_name',
            'created_at',
            'updated_at'
        ]
        extra_kwargs = {
            'created_at': {'format': '%Y-%m-%dT%H:%M:%S%z'},
            'updated_at': {'format': '%Y-%m-%dT%H:%M:%S%z'}
        }

class CustomerSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source='contact_phone')  # Mapping JSON key to model field
    customer_email = serializers.EmailField(source='email')  # Mapping JSON key to model field
    billingCycle = serializers.CharField(source='billing_cycle')
    # lastPaymentDate = serializers.DateField(source='last_payment_date')
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date')
    paymentMethod = serializers.CharField(source='payment_method')
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    resource_id = serializers.IntegerField(write_only=True, required=False)
    resources = ResourceBasicSerializer(many=True,read_only=True)
    deleted_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", read_only=True)
    deleted_by_username = serializers.CharField(source='deleted_by.username', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_email', 'status', "deleted_at","deleted_by_username",
            'paymentMethod', 'startDate', 'endDate', 'billingCycle', 'cost', 'user','resource_id','resources'
        ]

    def create(self, validated_data):
        resource_id = validated_data.pop('resource_id', None)

        print(f"📌 Creating customer with data: {validated_data}")

        customer = Customer.objects.create(**validated_data)

        # Assign resources to this customer
        if resource_id:
            try:
                resource = Resource.objects.get(id=resource_id)
                if resource.customer is not None:
                    raise serializers.ValidationError(
                        {"resource_id": "This resource is already assigned to another customer"}
                    )
                # Assign the resource to the customer
                resource.customer = customer
                resource.save()
                print(f"🔗 Assigned resource: {resource} to customer: {customer.id}")
            except Resource.DoesNotExist:
                raise serializers.ValidationError(
                    {"resource_id": "Invalid resource ID"}
                )
            
        return customer

class ServerUsageSerializer(serializers.ModelSerializer):
    used = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = Servers
        fields = ["server_name", "used", "total", "percentage"]

    def parse_capacity(self, capacity_str):
        """Helper method to parse capacity strings into GB"""
        if not capacity_str:
            return 0
            
        try:
            # Extract numeric value and unit
            match = re.match(r'^(\d+\.?\d*)\s*([TGMK]?B)?$', str(capacity_str).upper())
            if not match:
                return 0
                
            value = float(match.group(1))
            unit = match.group(2) or 'GB'  # Default to GB if no unit specified
            
            # Convert to GB
            if unit == 'TB':
                return value * 1024
            elif unit == 'MB':
                return value / 1024
            elif unit == 'KB':
                return value / (1024 * 1024)
            return value
        except (ValueError, TypeError):
            return 0

    def get_used(self, obj):
        """Calculate total used capacity from related resources in GB"""
        total_used = 0
        # for resource in obj.server_resources.all():
        for resource in obj.server_resources.filter(is_deleted=False):  
            total_used += self.parse_capacity(resource.storage_capacity)
        return round(total_used, 2)

    def get_total(self, obj):
        """Get total server capacity in GB"""
        return round(self.parse_capacity(obj.server_capacity), 2)

    def get_percentage(self, obj):
        """Calculate the percentage usage safely"""
        total = self.get_total(obj)
        used = self.get_used(obj)
        
        if total <= 0:
            return 0
            
        percentage = (used / total) * 100
        return round(min(percentage, 100), 2)  # Cap at 100%
    
class OnPremServerUsageSerializer(serializers.ModelSerializer):
    used = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = Computer
        fields = ["hardware_server_name", "used", "total", "percentage"]

    def get_server_name(self, obj):
        return obj.hardware_server_name  # Assuming `name` field stores the server name

    def parse_capacity(self, capacity_str):
        """Helper method to parse capacity strings into GB"""
        if not capacity_str:
            return 0
            
        try:
            match = re.match(r'^(\d+\.?\d*)\s*([TGMK]?B)?$', str(capacity_str).upper())
            if not match:
                return 0
                
            value = float(match.group(1))
            unit = match.group(2) or 'GB'  # Default to GB if no unit specified
            
            if unit == 'TB':
                return value * 1024
            elif unit == 'MB':
                return value / 1024
            elif unit == 'KB':
                return value / (1024 * 1024)
            return value
        except (ValueError, TypeError):
            return 0

    def get_used(self, obj):
        """Calculate total used capacity"""
        return round(self.parse_capacity(obj.used_capacity), 2)  # Assuming `used_capacity` exists

    def get_total(self, obj):
        """Get total capacity"""
        return round(self.parse_capacity(obj.total_capacity), 2)  # Assuming `total_capacity` exists

    def get_percentage(self, obj):
        """Calculate the percentage usage safely"""
        total = self.get_total(obj)
        used = self.get_used(obj)
        
        if total <= 0:
            return 0
            
        percentage = (used / total) * 100
        return round(min(percentage, 100), 2)  # Cap at 100%

class UserStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']

class SubscriptionHistorySerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='history_user.username')
    change_reason = serializers.CharField(source='history_change_reason')
    history_date = serializers.DateTimeField()

    class Meta:
        model = Subscription.history.model
        fields = '__all__'
