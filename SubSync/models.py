from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta  # For date calculations
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Provider(models.Model):
    provider_name = models.CharField(max_length=255, unique=True)
    contact_email = models.EmailField(unique=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.provider_name

class Subscription(models.Model):
    # CATEGORY_CHOICES = [
    #     ('software', 'Software'),
    #     ('billing', 'Billing'),
    #     ('server', 'Server'),
    #     ('domain', 'Domain'),
    # ]

    # PAYMENT_STATUS_CHOICES = [
    #     ('paid', 'Paid'),
    #     ('pending', 'Pending'),
    #     ('unpaid', 'Unpaid'),
    # ]

    # STATUS_CHOICES = [
    #     ('active', 'Active'),
    #     ('expired', 'Expired'),
    #     ('canceled', 'Canceled'),
    # ]

    CATEGORY_CHOICES = ['Software', 'Billing', 'Server', 'Domain']
    PAYMENT_STATUS_CHOICES = ['Paid', 'Pending', 'Unpaid']
    STATUS_CHOICES = ['Active', 'Expired', 'Canceled']

    # subscription_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subscription_category = models.CharField(
        max_length=50, choices=[(c, c) for c in CATEGORY_CHOICES]
    )
    payment_status = models.CharField(
        max_length=20, choices=[(s, s) for s in PAYMENT_STATUS_CHOICES]
    )
    status = models.CharField(
        max_length=20, choices=[(s, s) for s in STATUS_CHOICES]
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='subscription_provider')
    
    subscription_key =models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    billing_cycle = models.CharField(
        max_length=20, 
        # choices=[
        #     ('monthly', 'Monthly'),
        #     ('quarterly', 'Quarterly'),
        #     ('yearly', 'Yearly'),
        #     ('one-time', 'One-Time')
        # ],
        default='monthly'
    )
    # renewal_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    # payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES)
    payment_method = models.CharField(
        max_length=50, 
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('paypal', 'PayPal'),
            ('bank_transfer', 'Bank Transfer'),
            ('other', 'Other')
        ]
    )
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    # status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    auto_renewal = models.BooleanField(default=False)  # Checkbox for auto-renewal
    discount_coupon = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subscriptions')
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_subscriptions')

    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time

    def soft_delete(self):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than the start date.")
      
    @property
    def renewal_date(self):
        if self.billing_cycle == 'monthly':
            return self.end_date + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.end_date + relativedelta(months=3)
        elif self.billing_cycle == 'yearly':
            return self.end_date + relativedelta(years=1)
        return None  # For one-time payments
    
    def __str__(self):
        return f" - {self.subscription_category}"
    
class SoftwareSubscriptions(models.Model):
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='software_detail', unique=True)
    software_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True, null=True)
    features = models.TextField(blank=True, null=True)
    license_type = models.CharField(max_length=255)
    no_of_users = models.PositiveIntegerField(default=1)  # Ensures no negative users

    def __str__(self):
        return f"Software Details for {self.subscription.id}"
    
# BILLING_TYPE_CHOICES = [
#     ('Prepaid', 'Prepaid'),
#     ('Postpaid', 'Postpaid'),
# ]

# UTILITY_TYPE_CHOICES = {
#     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
# }

# def get_utility_type_choices():
#         return Utilities.UTILITY_TYPE_CHOICES.get('Prepaid', []) + Utilities.UTILITY_TYPE_CHOICES.get('Postpaid', [])

# class Utilities(models.Model):
#     subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='billing', unique=True)

#     # BILLING_TYPE_CHOICES = [
#     #     ('Prepaid', 'Prepaid'),
#     #     ('Postpaid', 'Postpaid'),
#     # ]

#     # UTILITY_TYPE_CHOICES = {
#     #     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     #     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
#     # }

#     billing_type = models.CharField(max_length=50, choices=BILLING_TYPE_CHOICES)

#     utility_type = models.CharField(
#     max_length=50,
#     choices=get_utility_type_choices()  # Dynamically fetch choices
#     )

#     # utility_type = models.CharField(max_length=50)
#     location = models.CharField(max_length=50)
#     account_number = models.CharField(max_length=50, unique=True)  # Ensuring unique accounts

#     def clean(self):
#         """ Ensure subcategory matches the billing type. """
#         valid_choices = dict(self.UTILITY_TYPE_CHOICES).get(self.billing_type, [])
#         if self.utility_type not in [choice[0] for choice in valid_choices]:
#             raise ValidationError(f"Invalid utility type '{self.utility_type}' for billing type '{self.billing_type}'.")

#     def __str__(self):
#         return f"Billing for {self.subscription.subscription_category} - {self.billing_type} ({self.utility_type})"

from django.db import models
from django.core.exceptions import ValidationError

UTILITY_TYPE_CHOICES = [
    ('Prepaid', 'Prepaid'),
    ('Postpaid', 'Postpaid'),
]

# BILLING_TYPE_CHOICES= {
#     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
# }

# def get_utility_type_choices():
#     """Fetch choices dynamically from UTILITY_TYPE_CHOICES."""
#     return UTILITY_TYPE_CHOICES.get('Prepaid', []) + UTILITY_TYPE_CHOICES.get('Postpaid', [])

class Utilities(models.Model):
    subscription = models.OneToOneField('Subscription', on_delete=models.CASCADE, related_name='billing', unique=True)

    utility_name= models.CharField(max_length=255)
    utility_type = models.CharField(max_length=50, choices=UTILITY_TYPE_CHOICES)
    # billing_type = models.CharField(max_length=50, choices=get_utility_type_choices())  # Use function to set choices
    location = models.CharField(max_length=50)
    account_number = models.CharField(max_length=50, unique=True)

    # def clean(self):
    #     """ Ensure utility_type matches the selected billing_type. """
    #     valid_choices = UTILITY_TYPE_CHOICES.get(self.billing_type, [])
    #     if self.utility_type not in [choice[0] for choice in valid_choices]:
    #         raise ValidationError(f"Invalid utility type '{self.utility_type}' for billing type '{self.billing_type}'.")

    # def __str__(self):
    #     return f"Billing for {self.subscription.subscription_category} - {self.billing_type} ({self.utility_type})"

class Domain(models.Model):
    DOMAIN_TYPE_CHOICES = [
        ('.com', '.com'),
        ('.in', '.in'),
    ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="domain", unique=True)
    
    domain_name = models.CharField(max_length=255, unique=True, help_text="Fully Qualified Domain Name (FQDN)")
    domain_type = models.CharField(max_length=255, choices=DOMAIN_TYPE_CHOICES)
    
    ssl_certification = models.BooleanField(default=False, help_text="Indicates if SSL is enabled for the domain")
    ssl_expiry_date = models.DateField(blank=True, null=True, help_text="SSL certificate expiration date")
    
    whois_protection = models.BooleanField(default=False, help_text="WHOIS privacy protection enabled or not")
    
    domain_transfer_status = models.CharField(
        max_length=50,
        choices=[
            ('locked', 'Locked'),
            ('unlocked', 'Unlocked'),
            ('pending_transfer', 'Pending Transfer'),
        ],
        default='locked',
        help_text="Current status of domain transfer"
    )

    def __str__(self):
        return self.domain_name


class Servers(models.Model):
    SERVER_TYPE_CHOICES = [
        ('In-house', 'In-house'),
        ('External', 'External'),
    ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="server", unique=True)
    
    server_name = models.CharField(max_length=255)
    server_type = models.CharField(max_length=50, choices=SERVER_TYPE_CHOICES)
    server_capacity = models.PositiveIntegerField(default=0, help_text="Total resource capacity (e.g., CPU, RAM, storage).")

    def __str__(self):
        return self.server_name

class Hardware(models.Model):

    TYPE_CHOICES = [
        ('laptop', 'Laptop'),
        ('desktop', 'Desktop'),
        ('server', 'Server'),
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('modem', 'Modem'),
        ('firewall', 'Firewall'),
        ('printer', 'Printer'),
        ('scanner', 'Scanner'),
        ('ups', 'UPS'),
        ('cooling_unit', 'Cooling Unit'),
        ('iot_device', 'IoT Device'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance')
    ]

    hardware_name = models.CharField(max_length=100)
    hardware_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    manufacturer = models.CharField(max_length=255)
    model_number = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=100, unique=True)
    assigned_department = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    # purchase_date = models.DateField()
    # purchase_cost = models.DecimalField(max_digits=10, decimal_places=2)
    # supplier = models.CharField(max_length=255)
    # supplier_contact = models.CharField(max_length=20, blank=True, null=True)
    # purchase_type = models.CharField(max_length=100)
    # last_service_date = models.DateField(blank=True, null=True)
    # next_service_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hardware')

    def __str__(self):
        return f"{self.hardware_name} ({self.serial_number})"

    class Meta:
        db_table = 'hardware'

class Warranty(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name="warranty")
    warranty_provider = models.CharField(max_length=100)
    warranty_period = models.IntegerField(help_text="Warranty period in months")
    warranty_expiry_date = models.DateField()
    is_extended_warranty = models.BooleanField(default=False)
    extended_period = models.IntegerField(blank=True, null=True, help_text="Extended warranty period in months")

    def __str__(self):
        return f"{self.hardware.hardware_name} - Warranty Expires: {self.warranty_expiry_date}"

    class Meta:
        db_table = 'warranty'

class Purchase(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name="purchase")
    purchase_date = models.DateField()
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_type = models.CharField(max_length=50)
    supplier_name = models.CharField(max_length=255)
    supplier_contact = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.hardware.hardware_name} - {self.purchase_cost}"

    class Meta:
        db_table = 'purchase'

class HardwareService(models.Model):
    
    # STATUS_CHOICES = [
    #     ('active', 'Active'),
    #     ('completed', 'Completed'),
    #     ('pending', 'Pending'),
    #     ('cancelled', 'Cancelled')
    # ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name="service")
    service_provider = models.CharField(max_length=100)
    service_provider_contact = models.CharField(max_length=100)
    last_service_date = models.DateField(blank=True, null=True)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2)
    no_of_services_done = models.IntegerField(default=0)
    no_of_free_services = models.IntegerField(default=0)
    free_services_used = models.IntegerField(default=0)
    service_period = models.IntegerField(help_text="Service interval in days", default=180)

    @property
    def next_service_date(self):
        if self.last_service_date and self.service_period:
            return self.last_service_date + timedelta(days=self.service_period)
        return None  

    def is_free_service_exhausted(self):
        return self.free_services_used >= self.no_of_free_services

    def __str__(self):
        return f"Service for {self.hardware.hardware_name} - Next: {self.next_service_date}"
    
    def __str__(self):
        status = "Exhausted" if self.is_free_service_exhausted() else "Available"
        return f"Free Service for {self.hardware.hardware_name} ({status})"

    class Meta:
        db_table = 'hardware_service'

