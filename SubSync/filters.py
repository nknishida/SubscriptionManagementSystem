import django_filters
from .models import Subscription
from django.db import models
from django.db.models import Q

class SubscriptionFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_by_related_names")

    class Meta:
        model = Subscription
        fields = ['status', 'provider', 'subscription_category']

    def filter_by_related_names(self, queryset, name, value):
        return queryset.filter(
            models.Q(software_detail__software_name__icontains=value) |
            models.Q(server__server_name__icontains=value) |
            models.Q(domain__domain_name__icontains=value) |
            models.Q(billing__utility_type__icontains=value)
        )

