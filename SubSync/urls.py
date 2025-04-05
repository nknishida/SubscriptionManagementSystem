from django.urls import path
from .views import ActiveSubscriptionsView, AddHardwareAPIView, CustomTokenRefreshView, CustomerAPIView, CustomerDetailView, CustomerListView, CustomerTypePercentageAPIView, DashboardOverview, DashboardOverviewAll, ExpiredSubscriptionsView, HardwareSummaryView, IsSuperUserCheckAPIView, ListHardwareView, LoginAPIView, ForgotPasswordAPIView, LogoutView, MarkNotificationAsReadView, NotificationListView, ProviderListView, RecycleBinView, ReminderAPIView, ResetPasswordAPIView, CreateUserAPIView, ResourceCreateView, ResourceDetailUpdateView, ResourceListCreateView, ResourceNameListView, RetrieveUpdateDestroyHardwareView, ServerListByHostingTypeAPIView, ServerReportAPIView, ServerUsageView, SubscriptionCategoryDistributionView, SubscriptionChoicesView, SubscriptionCountView, SubscriptionCreateView, ProviderCreateView,ChangePasswordView, SubscriptionListView, SubscriptionDetailView, SubscriptionMonthlyAnalysisView, SubscriptionReportView, SubscriptionSoftDeleteAPIView, UpcomingHardwareAPIView, UserListView, UserProfileView, UserStatusUpdateView, WarningSubscriptionsView, YearlyHardwareCostBreakdownAPIView, hardware_report, spending_report
from .views import SubscriptionDetailUpdateView, ExpenditureAnalysisView
from rest_framework_simplejwt import views as jwt_views

urlpatterns = [

    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path('create-user/', CreateUserAPIView.as_view(), name='create-user'),
    path('check-superuser/', IsSuperUserCheckAPIView.as_view(), name='check-superuser'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/status/', UserStatusUpdateView.as_view(), name='user-status-update'),

    path('recycle-bin/', RecycleBinView.as_view(), name='recycle-bin'),
    
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    # path('token/', jwt_views.TokenObtainPairView.as_view(), name = 'token'),
    # path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),


    path('dashboard_overview/', DashboardOverview.as_view(), name='dashboard_overview'),
    path('dashboard/', DashboardOverviewAll.as_view(), name='all'),
    path('expenditure-analysis/', ExpenditureAnalysisView.as_view(), name='total-expenditure-analysis'),


    path('add-subscription/', SubscriptionCreateView.as_view(), name='add-subscription'),
    path('subscriptions/', SubscriptionListView.as_view(), name='subscriptions-list'),  # GET for listing & filtering
    # path('subscriptions/<int:id>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path("subscriptions/<int:pk>/", SubscriptionDetailUpdateView.as_view(), name="subscription-detail-update"),
    path('subscriptions_warnings/', WarningSubscriptionsView.as_view(), name='warning-subscriptions'),
     path('subscriptions/delete/<int:subscription_id>/', SubscriptionSoftDeleteAPIView.as_view(), name='subscription-soft-delete'),


    path('subscriptions_active/', ActiveSubscriptionsView.as_view(), name='active-subscriptions'),
    path('subscriptions_expired/', ExpiredSubscriptionsView.as_view(), name='expired-subscriptions'),
    path('subscription_count/', SubscriptionCountView.as_view(), name='subscription-count'),
    path('subscriptions_category_distribution/', SubscriptionCategoryDistributionView.as_view(), name='category-distribution'),
    path('subscriptions_monthly-analysis/', SubscriptionMonthlyAnalysisView.as_view(), name='monthly-analysis'),
    # path("subscriptions/expenditure/", ExpenditureAnalysisView.as_view(), name="expenditure-analysis"),
    path("subscription_choices/", SubscriptionChoicesView.as_view(), name="subscription-choices"),
    path('subscription-report/', SubscriptionReportView.as_view(), name='subscription-report'),
   
   
    path('providers/', ProviderCreateView.as_view(), name='provider-create'),
    path('view_providers/', ProviderListView.as_view(), name='provider-list'),


    path('hardware/add/', AddHardwareAPIView.as_view(), name='add-hardware'),
    path('hardware/', ListHardwareView.as_view(), name='list-hardware'),
    path('hardware/<int:pk>/', RetrieveUpdateDestroyHardwareView.as_view(), name='retrieve-update-hardware'),

    path('hardware_summary/', HardwareSummaryView.as_view(), name='hardware-summary'),
    path("upcoming_hardware/", UpcomingHardwareAPIView.as_view(), name="upcoming-hardware"),
    path('hardware-report/', hardware_report, name='hardware-report'),
    path('spending-reports/', spending_report, name='spending-reports'),
    path("yearly-hardware-cost/", YearlyHardwareCostBreakdownAPIView.as_view(), name="yearly-hardware-cost"),


    path('reminders/', ReminderAPIView.as_view(), name='reminder-list'),
    path('reminders/<int:pk>/', ReminderAPIView.as_view(), name='reminder-detail'),

    path('resources/names/', ResourceNameListView.as_view(), name='resource-names'),
    path('resources/add/', ResourceCreateView.as_view(), name='resource-add'),
    path('resources/', ResourceListCreateView.as_view(), name='resource-list-create'),
    path('resources/<int:pk>/', ResourceDetailUpdateView.as_view(), name='resource-detail'),
    path('servers-by-hosting-type/', ServerListByHostingTypeAPIView.as_view(), name='get_servers_by_hosting_type'),

    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/", MarkNotificationAsReadView.as_view(), name="mark-notification-read"),



    path("server-usage/", ServerUsageView.as_view(), name="server-usage"),
    path('server-report/', ServerReportAPIView.as_view(), name='server-report'),


    path('add-customer/', CustomerAPIView.as_view(), name='add-customer'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customer-type-percentage/', CustomerTypePercentageAPIView.as_view(), name='customer-type-percentage'),
    

]
