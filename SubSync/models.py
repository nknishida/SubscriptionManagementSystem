from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta  # For date calculations
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from calendar import monthrange
from datetime import timedelta, date
import logging
logger = logging.getLogger(__name__)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    # profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    phone_numbers = models.TextField(blank=True, help_text="Comma-separated list of phone numbers for SMS")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Provider(models.Model):
    # CATEGORY_CHOICES = ['Software', 'Billing', 'Server', 'Domain']
    provider_name = models.CharField(max_length=255, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    website = models.URLField()
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time
    deleted_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_provider')
    # category = models.CharField(
    #     max_length=50, choices=[(c, c) for c in CATEGORY_CHOICES]
    # )
    def soft_delete(self,deleted_by=None):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.deleted_by=deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by=None
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])
    
    def __str__(self):
        return self.provider_name

class Subscription(models.Model):
    CATEGORY_CHOICES = ['Software', 'Billing', 'Server', 'Domain']
    PAYMENT_STATUS_CHOICES = ['Paid', 'pending']
    STATUS_CHOICES = ['Active', 'Expired', 'Canceled']
    subscription_category = models.CharField(max_length=50, choices=[(c, c) for c in CATEGORY_CHOICES])
    payment_status = models.CharField(max_length=20, choices=[(s, s) for s in PAYMENT_STATUS_CHOICES])
    status = models.CharField(max_length=20, choices=[(s, s) for s in STATUS_CHOICES])
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='subscription_provider')
    start_date = models.DateField()
    # end_date = models.DateField(null=True, blank=True)
    billing_cycle = models.CharField(max_length=20)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    auto_renewal = models.BooleanField(default=False)  # Checkbox for auto-renewal

    created_at = models.DateTimeField(auto_now_add=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subscriptions')
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_subscriptions')

    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time
    deleted_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_subscriptions')

    history = HistoricalRecords()
    # history = HistoricalRecords(
    # cascade_delete_history=True,  # Delete history when model is deleted
    # excluded_fields=['updated_at'],  # Exclude auto-updated fields
    # history_change_reason_field=models.TextField(null=True),
    # inherit=True  # For model inheritance
    # )

    def soft_delete(self,deleted_by=None):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.deleted_by=deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by=None
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def calculate_next_payment_date(self):
        """Calculate the next payment date based on !start_date //last_payment_date and billing_cycle."""
        if not self.start_date:
            print("Start date not set")
            return None

        cycle_mapping = {
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi-annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
            'biennial': relativedelta(years=2),
            'triennial': relativedelta(years=3),
        }

        base_date = self.last_payment_date if self.last_payment_date else self.start_date
        cycle_delta = cycle_mapping.get(self.billing_cycle.lower(), relativedelta())

        # If next_payment_date is not set, calculate it from !start_date//last_payment_date
        if not self.next_payment_date or self.next_payment_date < timezone.now().date():
            self.next_payment_date = base_date + cycle_delta
        else:
            # If next_payment_date exists, calculate from that
            self.next_payment_date = self.next_payment_date + cycle_delta
        
        # if self.end_date and self.next_payment_date > self.end_date:
        #     self.next_payment_date = self.end_date

        print(f"Next Payment Date: {self.next_payment_date}")
        return self.next_payment_date
    
    def update_status_and_reminders(self):
        """Update status, payment status, and manage reminders."""
        today = timezone.now().date()

        if self.is_deleted:
            self.status = "Canceled"
            self.payment_status = "Unpaid"
            return
        
        # Update payment status
        if self.next_payment_date:
            if today > self.next_payment_date:
                if self.auto_renewal and self.payment_status == "Paid":
                    # Auto-renewal case
                    self.last_payment_date = self.next_payment_date
                    self.calculate_next_payment_date()
                    self.payment_status = "Paid"
                else:
                    # Overdue case
                    self.payment_status = "Pending"
                    if not self.auto_renewal:
                        self.status = "Expired"
            elif (self.next_payment_date - today).days <= 10:
                # Upcoming payment case
                if self.payment_status == "Paid":
                    self.payment_status = "Pending"
            else:
                # Active and paid case
                self.payment_status = "Paid"
                self.status = "Active"
        
        # Update all related reminders
        self.update_reminders()
        
    def update_reminders(self):
        """Update all reminders associated with this subscription."""
        for reminder_sub in self.reminder_subscriptions.all():
            reminder = reminder_sub.reminder
            new_dates = reminder.calculate_all_reminder_dates(self)
            
            if new_dates:
                next_reminder_date = min(d for d in new_dates if d >= timezone.now().date())
                reminder.reminder_date = next_reminder_date
                reminder.reminder_status = "pending"
                reminder.save()
            else:
                reminder.reminder_status = "cancelled"
                reminder.save()

    def save(self, *args, **kwargs):
        """Override save method to update status , payment status,and next payment date before saving."""
        if not self.last_payment_date:
            self.last_payment_date = self.start_date
        
        if self.pk:  # Only for existing instances
            original = Subscription.objects.get(pk=self.pk)
            if original.billing_cycle != self.billing_cycle:
                self.next_payment_date = self.calculate_next_payment_date()
            # If last_payment_date changed, recalculate next_payment_date
            elif original.last_payment_date != self.last_payment_date:
                self.next_payment_date = self.calculate_next_payment_date()
        else:
            # New object: first-time calculation
            self.next_payment_date = self.calculate_next_payment_date()

        self.update_status_and_reminders()
        # if not self.next_payment_date:
        #     self.next_payment_date = self.calculate_next_payment_date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subscription_category} - {self.billing_cycle}"

class SoftwareSubscriptions(models.Model):
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='software_detail', unique=True)

    software_id =models.CharField(unique=True,max_length=200)
    software_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True, null=True)
    # features = models.TextField(blank=True, null=True)
    no_of_users = models.PositiveIntegerField(default=1)  # Ensures no negative users

    history = HistoricalRecords()

    def clean(self):
        """ Custom validation to prevent duplicate software_id """
        if SoftwareSubscriptions.objects.filter(software_id=self.software_id).exclude(id=self.id).exists():
            raise ValidationError(f"A software subscription with ID '{self.software_id}' already exists.")
        
    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Software Details for {self.subscription.id}"

class Utilities(models.Model):
    subscription = models.OneToOneField('Subscription', on_delete=models.CASCADE, related_name='billing', unique=True)

    UTILITY_TYPE_CHOICES = [
    ('Prepaid', 'Prepaid'),
    ('Postpaid', 'Postpaid'),
    ]
    consumer_no =models.IntegerField(unique=True)
    utility_name= models.CharField(max_length=255)
    utility_type = models.CharField(max_length=50, choices=UTILITY_TYPE_CHOICES)

    history = HistoricalRecords()

    def clean(self):
        """ Custom validation to prevent duplicate consumer_no """
        if Utilities.objects.filter(consumer_no=self.consumer_no).exclude(id=self.id).exists():
            raise ValidationError(f"A utility with consumer number '{self.consumer_no}' already exists.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
class Domain(models.Model):
    DOMAIN_TYPE_CHOICES = [
        ('.com', '.com'),
        ('.in', '.in'),
    ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="domain", unique=True)

    domain_id =models.IntegerField(unique=True)
    domain_name = models.CharField(max_length=255, unique=True, help_text="Fully Qualified Domain Name (FQDN)")
    domain_type = models.CharField(max_length=255)
    
    ssl_certification = models.BooleanField(default=False, help_text="Indicates if SSL is enabled for the domain")
    ssl_expiry_date = models.DateField(blank=True, null=True, help_text="SSL certificate expiration date")
    whois_protection = models.BooleanField(default=False, help_text="WHOIS privacy protection enabled or not")
    name_servers = models.CharField(max_length=255)
    hosting_provider = models.CharField(max_length=255)

    history = HistoricalRecords()
    
    def clean(self):
        """ Custom validation to prevent duplicate domain_name """
        if Domain.objects.filter(domain_name=self.domain_name).exclude(id=self.id).exists():
            raise ValidationError(f"The domain '{self.domain_name}' is already registered.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.domain_name

class Servers(models.Model):
    # SERVER_TYPE_CHOICES = [
    #     ('In-house', 'In-house'),
    #     ('External', 'External'),
    # ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="server", unique=True)
    
    server_name = models.CharField(max_length=255,unique=True)
    server_type = models.CharField(max_length=50)
    server_capacity= models.CharField(max_length=255)

    history = HistoricalRecords()

    def clean(self):
        """ Custom validation to prevent duplicate server_name """
        if Servers.objects.filter(server_name=self.server_name).exclude(id=self.id).exists():
            raise ValidationError(f"The server '{self.server_name}' already exists.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.server_name

class Hardware(models.Model):

    # TYPE_CHOICES = [
    #     ('Laptop', 'Laptop'),
    #     ('Desktop', 'Desktop'),
    #     ('Mobile Phone', 'Mobile Phone'),
    #     ('Tablet', 'Tablet'),
    #     ('Network Device', 'Network Device'),
    #     ('Air Conditioner', 'Air Conditioner'),
    #     ('on-premise server', 'on-premise server'),
    #     ('Printer', 'Printer'),
    #     ('Scanner', 'Scanner'),
    #     ('Other', 'Other'),
    # ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        # ('Maintenance', 'Maintenance')
        ('retired', 'Retired'),
    ]

    # hardware_name = models.CharField(max_length=100)
    hardware_type = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=255)
    model_number = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=100, unique=True)
    assigned_department = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    
    vendor_name=models.CharField(max_length=250)
    vendor_contact=models.CharField(max_length=15)
    vendor_email=models.EmailField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_hardware')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hardware')

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.hardware_type} ({self.serial_number})"
    
    def soft_delete(self,deleted_by=None):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.deleted_by=deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by=None
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    class Meta:
        db_table = 'hardware'

class Warranty(models.Model):
    EXTENDED_WARRANTY_PERIODS = [
        (1, '1 Year'),
        (2, '2 Years'),
        (3, '3 Years'),
        (5, '5 Years'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Expiring Soon', 'Expiring Soon'),
        ('Expired', 'Expired'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='warranty')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    warranty_expiry_date = models.DateField()
    is_extended_warranty = models.BooleanField(default=False)
    extended_warranty_period = models.IntegerField(choices=EXTENDED_WARRANTY_PERIODS, null=True, blank=True)

    history = HistoricalRecords()

    EXPIRY_THRESHOLD = 7

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.is_extended_warranty and self.extended_warranty_period:
                # Extend the warranty expiry date
                self.warranty_expiry_date += timedelta(days=365 * self.extended_warranty_period)

        today = date.today()
        days_remaining = (self.warranty_expiry_date - today).days

        # Automatically update the status based on expiry date
        if self.warranty_expiry_date < date.today():
            self.status = 'Expired'
            logger.info(f"Warranty expired for {self.hardware}")
        elif days_remaining <= self.EXPIRY_THRESHOLD:
            self.status = 'Expiring Soon'
            logger.info(f"Warranty expiring soon for {self.hardware}: {days_remaining} days remaining")
        else:
            self.status = 'Active'
            logger.info(f"Warranty is active for {self.hardware}: {days_remaining} days remaining")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Warranty for {self.hardware} expires on {self.warranty_expiry_date}"

class Purchase(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='purchase')
    purchase_date = models.DateField()
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Purchase for {self.hardware} on {self.purchase_date}"

class HardwareService(models.Model):
    SERVICE_STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Maintenance Soon', 'Maintenance Soon'),
        ('Maintenance Due', 'Maintenance Due'),
        # ('Expired', 'Expired'),
    ]
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='services')
    last_service_date = models.DateField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    free_service_until = models.DateField(null=True, blank=True)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_provider = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=SERVICE_STATUS_CHOICES, 
        default='Active',
        help_text="Status of the service contract"
    )

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        
        # Update status based on dates
        if self.next_service_date:
            if self.next_service_date <= today:
                self.status = 'Maintenance Due'
            elif self.next_service_date <= today + timedelta(days=7):
                self.status = 'Maintenance Soon'
            else:
                self.status = 'Active'
        
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Service for {self.hardware} on {self.last_service_date}"

class Computer(models.Model):
    COMPUTER_TYPES = [
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
         ('Server', 'Server'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='computer')

    computer_type = models.CharField(max_length=50, choices=COMPUTER_TYPES)
    cpu = models.CharField(max_length=100)
    ram = models.CharField(max_length=100)
    storage = models.CharField(max_length=100)

    hardware_server_name = models.CharField(max_length=100,blank=True, null=True)
    operating_system = models.CharField(max_length=100,blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.computer_type}: {self.hardware}"
    
class PortableDevice(models.Model):
    PORTABLE_DEVICE_TYPES = [
        ('Mobile Phone', 'Mobile Phone'),
        ('Tablet', 'Tablet'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='portable_device')
    device_type = models.CharField(max_length=50, choices=PORTABLE_DEVICE_TYPES)
    os_version = models.CharField(max_length=100)
    storage = models.CharField(max_length=100)
    imei_number = models.CharField(max_length=100, null=True, blank=True)  # Only for Mobile Phone

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.device_type}: {self.hardware}"

class NetworkDevice(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='network_device')
    throughput = models.CharField(max_length=100)
    ip_address = models.CharField(max_length=100)
    name_specification=models.CharField(max_length=100)

    history = HistoricalRecords()

    def __str__(self):
        return f"Network Device: {self.hardware}"
    
class AirConditioner(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='air_conditioner')
    btu_rating = models.CharField(max_length=100)
    energy_rating = models.CharField(max_length=100)

    history = HistoricalRecords()

    def __str__(self):
        return f"Air Conditioner: {self.hardware}"
    
class Printer(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='printer')
    print_technology = models.CharField(max_length=100)
    print_speed = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=100)

    history = HistoricalRecords()

    def __str__(self):
        return f"Printer: {self.hardware}"
    
class Scanner(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='scanner')
    scan_resolution = models.CharField(max_length=100)
    scan_type = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=100)

    history = HistoricalRecords()

    def __str__(self):
        return f"Scanner: {self.hardware}"

class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('renewal', 'Renewal'),

        ('maintenance', 'Maintenance'),
        ('warranty', 'warranty'),

        ('over due', 'Over Due'),

        ('server break down', 'Server Break Down'),
        ('server_expiry', 'Server Expiry'),
        ('customer_expiry', 'Customer Expiry'),
    ]
    REMINDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    NOTIFICATION_METHOD_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        # ('in-app', 'In-App'),
        ('both', 'Both'),
    ]
    
    reminder_days_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="For weekly/monthly cycles: How many days before to receive a reminder?"
    )
    reminder_months_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="For long-term cycles: How many months before to receive a reminder?"
    )
    reminder_day_of_month = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="For long-term cycles: Specific day of the month for reminder."
    )
    optional_days_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="Optional: Extra days before the reminder."
    )
    reminder_status = models.CharField(
        max_length=20, choices=REMINDER_STATUS_CHOICES, default='pending'
    )
    notification_method = models.CharField(
        max_length=20, choices=NOTIFICATION_METHOD_CHOICES, default='email',
        help_text="Method of notification (email, SMS, etc.)"
    )
    recipients = models.TextField(
        blank=True, null=True, help_text="Comma-separated email addresses."
    )
    # phone_numbers = models.TextField(blank=True, help_text="Comma-separated list of phone numbers for SMS")
    custom_message = models.TextField(
        blank=True, null=True, help_text="Custom message for the reminder."
    )
    reminder_date = models.DateField(blank=True, null=True, help_text="Next reminder date.")
    created_at = models.DateTimeField(auto_now_add=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    reminder_type = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES, default='renewal')
    scheduled_task_id = models.CharField(max_length=255, blank=True, null=True)
    # reminder_time = models.TimeField(default="09:00:00"default="15:15:00",help_text="Time to send the reminder.")

    def get_valid_day(self, year, month, day):
        """Helper method to get a valid day of the month."""
        _, last_day = monthrange(year, month)
        return min(day, last_day)

    def calculate_all_reminder_dates(self, subscription):
        """Calculate all reminder dates for a subscription."""
        print("\n**********************************************models.py***************************************************************************************")

        if not hasattr(subscription, "next_payment_date") or not subscription.next_payment_date:
            logger.error(f"Subscription {subscription.id if hasattr(subscription, 'id') else 'Unknown'} has no next_payment_date.")
            return []

        today = timezone.now().date()
        reminder_dates = []

        # Stop reminders if the subscription is paid
        if hasattr(subscription, "payment_status") and subscription.payment_status == "Paid":
            logger.info(f"Subscription ID {subscription.id} is paid. No reminders needed.")
            return reminder_dates

        # For weekly/monthly cycles
        if hasattr(subscription, "billing_cycle") and subscription.billing_cycle in ['weekly', 'monthly']:
            if self.reminder_days_before:
                start_date = subscription.next_payment_date - timedelta(days=int(self.reminder_days_before))
                current_date = start_date
                while current_date < subscription.next_payment_date:
                    if current_date >= today:
                        reminder_dates.append(current_date)
                    current_date += timedelta(days=1)

        # For long-term cycles
        elif hasattr(subscription, "billing_cycle") and subscription.billing_cycle in ['quarterly', 'semi-annual', 'annual', 'biennial', 'triennial']:
            if self.reminder_months_before and self.reminder_day_of_month:
                start_date = max(
                    subscription.next_payment_date - relativedelta(months=self.reminder_months_before),
                    today
                )
                start_date = start_date.replace(
                    day=self.get_valid_day(start_date.year, start_date.month, self.reminder_day_of_month)
                )
                current_date = start_date
                while current_date < subscription.next_payment_date:
                    if current_date >= today:
                        reminder_dates.append(current_date)
                    current_date += relativedelta(months=1)

        # Add optional_days_before reminder if present
        if self.optional_days_before:
            optional_reminder_date = subscription.next_payment_date - timedelta(days=self.optional_days_before)
            current_date = optional_reminder_date
            while current_date < subscription.next_payment_date:
                    if optional_reminder_date >= today:
                        reminder_dates.append(optional_reminder_date)
                    current_date += timedelta(days=1)

        # Overdue reminder logic (continue reminders if unpaid/expired)
        if hasattr(subscription, "status") and hasattr(subscription, "payment_status"):
            if subscription.status == "Expired" or subscription.payment_status == "Unpaid":
                overdue_reminder_date = subscription.next_payment_date + timedelta(days=1)
                while overdue_reminder_date <= today:  # Keep generating overdue reminders
                    reminder_dates.append(overdue_reminder_date)
                    overdue_reminder_date += timedelta(days=3)  # Overdue reminders every 3 days

        logger.info(f"Generated Reminder Dates(in models.py): {reminder_dates}")
        return reminder_dates
    
    def should_send_reminder(self, subscription):
        """
        Determine if a reminder should be sent based on subscription status
        """
        if (subscription.payment_status == "Paid" and subscription.next_payment_date and
        (subscription.next_payment_date - timezone.now().date()).days <= 7):
            subscription.payment_status = "Pending"
            subscription.save()
            return True

        if subscription.is_deleted:
            return False
        
        # if self.reminder_status == "pending" and not Reminder.objects.filter(
        #     subscription_reminder__subscription=subscription, 
        #     reminder_status="sent"
        # ).exists():
        #     return True
            
        # Always send overdue reminders if payment is pending
        if subscription.payment_status == "Pending":
            return True
        
        if subscription.payment_status == "Paid":
            return False
            
        # Don't send renewal reminders for expired/canceled subscriptions
        if subscription.status in [ "Canceled"] and self.reminder_type == "renewal":
            return False
            
        return True

    def __str__(self):
        return f"Reminder of type {self.reminder_type} - {self.reminder_status}"
    
# Separate Linking Tables
class ReminderSubscription(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='subscription_reminder')
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE ,related_name='reminder_subscriptions')

class ReminderHardware(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='hardware_reminder')
    hardware = models.ForeignKey('Hardware', on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=50, choices=[
        ('warranty', 'Warranty Expiry'),
        ('service', 'Service Due'),
        ('maintenance', 'Maintenance')
    ])
    
    class Meta:
        unique_together = ('reminder', 'hardware', 'reminder_type')

class Customer(models.Model):
    # STATUS_CHOICES = [
    #     ('active', 'Active'),
    #     ('inactive', 'Inactive'),
    #     # ('pending', 'Pending')
    # ]
    STATUS_CHOICES = ['Active', 'Inactive']

    # CUSTOMER_TYPE_CHOICES = [
    #     ('Inhouse', 'Inhouse'),
    #     ('External', 'External'),
    # ]
    
    customer_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=[(s, s) for s in STATUS_CHOICES])
    # customer_type = models.CharField(max_length=50)
    payment_method= models.CharField(max_length=20)
    last_payment_date = models.DateField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    billing_cycle = models.CharField(max_length=20)
    cost= models.DecimalField(max_digits=10, decimal_places=2)
    next_payment_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time
    deleted_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_customer')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    # resource = models.OneToOneField(Resource, on_delete=models.SET_NULL, related_name='customer_resources', null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.customer_name
    
    def soft_delete(self,deleted_by=None):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.deleted_by=deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by=None
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def calculate_next_payment_date(self,force_update=False):
        """Calculate the next payment date based on !provisioned_date //last_payment_date and billing_cycle."""
        if not self.start_date:
            print("start date not set")
            return None

        cycle_mapping = {
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi-annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
            'biennial': relativedelta(years=2),
            'triennial': relativedelta(years=3),
        }

        cycle_delta = cycle_mapping.get(self.billing_cycle, relativedelta())

        # If next_payment_date is not set, calculate it from !start_date//last_payment_date
        if force_update or not self.next_payment_date:
            base_date = self.last_payment_date or self.start_date
            self.next_payment_date = base_date + cycle_delta
            print(f"1 Next Payment Date: {self.next_payment_date}")
        else:
            # If next_payment_date is set, calculate the next payment date based on the billing cycle
            self.next_payment_date = self.next_payment_date + cycle_delta
            print(f"2 Next Payment Date: {self.next_payment_date}")

        print(f"3 Next Payment Date: {self.next_payment_date}")
        return self.next_payment_date
    
    def save(self, *args, **kwargs):
        now = timezone.now().date()
        """Override save method to update status , payment status,and next payment date before saving."""
        
        if not self.next_payment_date or self.next_payment_date < now:
            self.next_payment_date = self.calculate_next_payment_date(force_update=True)

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'customer'
        ordering = ['-created_at']

class ReminderCustomer(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='customer_reminder')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

class Resource(models.Model):
    STATUS_CHOICES = [
        # ('available', 'Available'),
        # ('in_use', 'In Use'),
        # ('maintenance', 'Maintenance'),
        ('Active', 'Active'),  # Added based on frontend data
        ('Inactive', 'Inactive'),
        # ('pending', 'Pending'),
    ]

    resource_name = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default='Active')
    billing_cycle = models.CharField(max_length=20, 
                                    #  choices=BILLING_CYCLE_CHOICES
                                    default="monthly")
    resource_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    storage_capacity = models.CharField(max_length=100, blank=True, null=True)
    provisioned_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50)

    hosting_type = models.CharField(max_length=100, blank=True, null=True)
    # hosting_location_name= models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time
    deleted_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_resources')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_resources')
    server = models.ForeignKey(Servers, on_delete=models.CASCADE, related_name='server_resources')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='resources')

    history = HistoricalRecords()

    def soft_delete(self,deleted_by=None):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.deleted_by=deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by=None
        self.save(update_fields=['is_deleted', 'deleted_at','deleted_by'])

    def calculate_next_payment_date(self,force_update=False):
        """Calculate the next payment date based on !provisioned_date //last_payment_date and billing_cycle."""
        if not self.provisioned_date:
            print("provisioned date not set")
            return None

        cycle_mapping = {
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi-annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
            'biennial': relativedelta(years=2),
            'triennial': relativedelta(years=3),
        }

        cycle_delta = cycle_mapping.get(self.billing_cycle, relativedelta())

        # If next_payment_date is not set, calculate it from !start_date//last_payment_date
        if force_update or not self.next_payment_date:
            base_date = self.last_payment_date or self.provisioned_date
            self.next_payment_date = base_date + cycle_delta
            print(f"1 Next Payment Date: {self.next_payment_date}")
        else:
            # If next_payment_date is set, calculate the next payment date based on the billing cycle
            self.next_payment_date = self.next_payment_date + cycle_delta
            print(f"2 Next Payment Date: {self.next_payment_date}")

        print(f"3 Next Payment Date: {self.next_payment_date}")
        return self.next_payment_date
    
    def save(self, *args, **kwargs):
        now = timezone.now().date()
        """Override save method to update status , payment status,and next payment date before saving."""

        if not self.last_payment_date and self.provisioned_date:
            self.last_payment_date = self.provisioned_date

        
        # if not self.next_payment_date or self.next_payment_date < now:
        #     self.next_payment_date = self.calculate_next_payment_date(force_update=True)
        if not self.next_payment_date or (self.last_payment_date and 
                                     (not self.next_payment_date or 
                                      self.next_payment_date <= timezone.now().date())):
            self.calculate_next_payment_date(force_update=True)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.resource_name
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True, blank=True)
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50, choices=[
        ('reminder', 'Reminder'),
        ('payment', 'Payment'),
        ('system', 'System')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']