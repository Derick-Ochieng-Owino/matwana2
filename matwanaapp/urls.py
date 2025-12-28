from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),


    # Dashboard routes
    path('dashboard/', views.dashboard, name='dashboard'),
    # path('auth-dashboard/', views.auth_passenger_dashboard, name='auth_dashboard'),


# Route pages
    path('routes_list/', views.routes_list, name='routes_list'),
    path('quick-book/', views.quick_book, name='quick_book'),
    path('my-trips/', views.my_trips, name='my_trips'),
    path('top-up/', views.top_up_wallet, name='top_up_wallet'),
    path('process-payment/', views.process_payment, name='process_payment'),

    # Other dashboards
    path('sacco/', views.sacco_dashboard, name='sacco_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    path('conductor/', views.conductor_dashboard, name='conductor_dashboard'),

    # API endpoints
    path('api/dashboard-data/', views.dashboard_data_api, name='dashboard_data_api'),
    path('api/routes/search/', views.search_routes_api, name='search_routes_api'),
    path('api/routes/<int:route_id>/details/', views.route_details_api, name='route_details_api'),
    path('api/book-trip/', views.book_trip_api, name='book_trip_api'),
    path('api/active-bookings/', views.active_bookings_api, name='active_bookings_api'),

# Admin Dashboard
    path('superadmin/', views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
    path('superadmin/users/', views.admin_manage_users, name='admin_manage_users'),
    path('superadmin/users/add/', views.admin_add_user, name='admin_add_user'),
    path('superadmin/users/edit/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),
    path('superadmin/users/delete/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    
    # Sacco Management
    path('superadmin/saccos/', views.admin_manage_saccos, name='admin_manage_saccos'),
    path('superadmin/saccos/add/', views.admin_add_sacco, name='admin_add_sacco'),
    path('superadmin/saccos/edit/<int:sacco_id>/', views.admin_edit_sacco, name='admin_edit_sacco'),
    path('superadmin/saccos/delete/<int:sacco_id>/', views.admin_delete_sacco, name='admin_delete_sacco'),
    
    # Matatu Management
    path('superadmin/matatus/', views.admin_manage_matatus, name='admin_manage_matatus'),
    path('superadmin/matatus/add/', views.admin_add_matatu, name='admin_add_matatu'),
    path('superadmin/matatus/edit/<int:matatu_id>/', views.admin_edit_matatu, name='admin_edit_matatu'),
    path('superadmin/matatus/delete/<int:matatu_id>/', views.admin_delete_matatu, name='admin_delete_matatu'),
    
    # Route Management
    path('superadmin/routes/', views.admin_manage_routes, name='admin_manage_routes'),
    path('superadmin/routes/add/', views.admin_add_route, name='admin_add_route'),
    path('superadmin/routes/edit/<int:route_id>/', views.admin_edit_route, name='admin_edit_route'),
    path('superadmin/routes/delete/<int:route_id>/', views.admin_delete_route, name='admin_delete_route'),
    
    # Notification Management
    path('superadmin/notifications/', views.admin_manage_notifications, name='admin_manage_notifications'),
    path('superadmin/notifications/add/', views.admin_add_notification, name='admin_add_notification'),
    path('superadmin/notifications/edit/<int:notification_id>/', views.admin_edit_notification, name='admin_edit_notification'),
    path('superadmin/notifications/delete/<int:notification_id>/', views.admin_delete_notification, name='admin_delete_notification'),
    
    # Trip Management
    path('superadmin/trips/', views.admin_manage_trips, name='admin_manage_trips'),
    
    # Payment Management
    path('superadmin/payments/', views.admin_manage_payments, name='admin_manage_payments'),
    
    # API Endpoints
    path('superadmin/api/dashboard-stats/', views.admin_dashboard_stats, name='admin_dashboard_stats'),
]