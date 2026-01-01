from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template import loader
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import User, PassengerTrip, Route, Trip, Notification, Payment, Sacco, Matatu
from .forms import LoginForm, SignupForm, ForgotPasswordForm

def home(request):
    template = loader.get_template('home.html')
    return HttpResponse(template.render())

def login(request):
    # If user is already logged in via session, redirect to dashboard
    if 'user_id' in request.session:
        user_type = request.session.get('user_type', 'passenger')
        if user_type == 'passenger':
            return redirect('dashboard')
        elif user_type == 'sacco_admin':
            return redirect('sacco_dashboard')
        elif user_type == 'driver':
            return redirect('driver_dashboard')
        elif user_type == 'conductor':
            return redirect('conductor_dashboard')
        elif user_type == 'super_admin':
            return redirect('admin_dashboard')
    
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login_input = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        try:
            # Search for user matching the input
            user = User.objects.get(
                Q(id_number=login_input) | 
                Q(email=login_input) | 
                Q(phone_number=login_input)
            )
            
            # Check the hashed password
            if check_password(password, user.password):
                # Set session variables
                request.session['user_id'] = user.id
                request.session['user_type'] = user.user_type
                request.session['user_name'] = f"{user.first_name} {user.last_name}"
                
                # Update last login
                user.last_login = timezone.now()
                user.save()
                
                # Redirect based on user type
                if user.user_type == 'passenger':
                    return redirect('dashboard')
                elif user.user_type == 'sacco_admin':
                    return redirect('sacco_dashboard')
                elif user.user_type == 'driver':
                    return redirect('driver_dashboard')
                elif user.user_type == 'conductor':
                    return redirect('conductor_dashboard')
                elif user.user_type == 'super_admin':
                    return redirect('admin_dashboard')
                else:
                    return redirect('dashboard')
            else:
                form.add_error('password', 'Incorrect password')
                
        except User.DoesNotExist:
            form.add_error('username', 'Account not found with that Email, ID or Phone')

    return render(request, 'auth/login.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'passenger'  # Default to passenger
            user.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = SignupForm()
    
    return render(request, 'auth/signup.html', {'form': form})

# Add these imports at the top
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import random
import string

# Super Admin Dashboard View
def admin_dashboard(request):
    """Super Admin Dashboard"""
    # Check if user is logged in and is a super admin
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied. Super admin only.')
        return redirect('login')
    
    # Statistics
    total_saccos = Sacco.objects.count()
    total_passengers = User.objects.filter(user_type='passenger').count()
    total_drivers = User.objects.filter(user_type='driver').count()
    total_conductors = User.objects.filter(user_type='conductor').count()
    total_sacco_admins = User.objects.filter(user_type='sacco_admin').count()
    total_matatus = Matatu.objects.count()
    total_routes = Route.objects.count()
    total_trips = Trip.objects.count()
    total_payments = Payment.objects.count()
    
    # Recent activity
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    recent_saccos = Sacco.objects.all().order_by('-date_registered')[:5]
    recent_matatus = Matatu.objects.all().order_by('-registration_date')[:5]
    recent_routes = Route.objects.all().order_by('-id')[:5]
    recent_trips = Trip.objects.all().order_by('-created_at')[:5]
    recent_payments = Payment.objects.all().order_by('-created_at')[:5]
    
    # Monthly stats for charts
    import datetime
    from django.db.models.functions import TruncMonth
    
    # User registrations by month
    users_by_month = User.objects.annotate(
        month=TruncMonth('date_joined')
    ).values('month').annotate(
        count=models.Count('id')
    ).order_by('month')[:6]
    
    # Payment statistics
    payment_stats = {
        'total_amount': Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_transactions': Payment.objects.filter(status='completed').count(),
        'pending_payments': Payment.objects.filter(status='pending').count(),
    }
    
    context = {
        'admin': user,
        'total_saccos': total_saccos,
        'total_passengers': total_passengers,
        'total_drivers': total_drivers,
        'total_conductors': total_conductors,
        'total_sacco_admins': total_sacco_admins,
        'total_matatus': total_matatus,
        'total_routes': total_routes,
        'total_trips': total_trips,
        'total_payments': total_payments,
        'recent_users': recent_users,
        'recent_saccos': recent_saccos,
        'recent_matatus': recent_matatus,
        'recent_routes': recent_routes,
        'recent_trips': recent_trips,
        'recent_payments': recent_payments,
        'users_by_month': list(users_by_month),
        'payment_stats': payment_stats,
        'saccos': Sacco.objects.all(),
    }
    
    return render(request, 'admin/dashboard.html', context)

# User Management Views
def admin_manage_users(request):
    """Manage all users"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    user_type = request.GET.get('user_type', '')
    search = request.GET.get('search', '')
    
    # Filter users
    users = User.objects.all()
    
    if user_type:
        users = users.filter(user_type=user_type)
    
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(id_number__icontains=search)
        )
    
    # Order by date joined
    users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'user_types': User.USER_TYPES,
        'selected_type': user_type,
        'search_query': search,
    }
    
    return render(request, 'admin/manage_users.html', context)

def admin_add_user(request):
    """Add new user (any type)"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Get form data
            user_type = request.POST.get('user_type')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            id_number = request.POST.get('id_number')
            password = request.POST.get('password')
            sacco_id = request.POST.get('sacco')
            
            # Validate required fields
            if not all([user_type, first_name, last_name, email, phone_number, id_number, password]):
                raise ValidationError('All fields are required')
            
            # Validate email
            validate_email(email)
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise ValidationError('Email already registered')
            
            # Check if phone already exists
            if User.objects.filter(phone_number=phone_number).exists():
                raise ValidationError('Phone number already registered')
            
            # Check if ID number already exists
            if User.objects.filter(id_number=id_number).exists():
                raise ValidationError('ID number already registered')
            
            # For sacco_admin, check if sacco is provided
            if user_type == 'sacco_admin' and not sacco_id:
                raise ValidationError('SACCO is required for SACCO Admin')
            
            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                user_type=user_type,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                id_number=id_number,
                is_verified=True  # Super admin adds verified users
            )
            
            # If user is sacco_admin, assign to sacco
            if user_type == 'sacco_admin' and sacco_id:
                try:
                    sacco = Sacco.objects.get(id=sacco_id)
                    sacco.admin = user
                    sacco.save()
                except Sacco.DoesNotExist:
                    pass
            
            messages.success(request, f'User {first_name} {last_name} added successfully')
            return redirect('admin_manage_users')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error adding user: {str(e)}')
    
    context = {
        'user_types': User.USER_TYPES,
        'saccos': Sacco.objects.all(),
    }
    
    return render(request, 'admin/add_user.html', context)

def admin_edit_user(request, user_id):
    """Edit user"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        user = get_object_or_404(User, id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            user_type = request.POST.get('user_type')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            is_active = request.POST.get('is_active') == 'on'
            sacco_id = request.POST.get('sacco')
            
            # Validate required fields
            if not all([user_type, first_name, last_name, email, phone_number]):
                raise ValidationError('All fields are required')
            
            # Check if email already exists (excluding current user)
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                raise ValidationError('Email already registered')
            
            # Check if phone already exists (excluding current user)
            if User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                raise ValidationError('Phone number already registered')
            
            # Update user
            user.user_type = user_type
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number
            user.is_active = is_active
            
            # Update password if provided
            password = request.POST.get('password')
            if password:
                user.set_password(password)
            
            user.save()
            
            # Update sacco admin if applicable
            if user_type == 'sacco_admin':
                if sacco_id:
                    try:
                        sacco = Sacco.objects.get(id=sacco_id)
                        # Remove from old sacco
                        Sacco.objects.filter(admin=user).update(admin=None)
                        # Assign to new sacco
                        sacco.admin = user
                        sacco.save()
                    except Sacco.DoesNotExist:
                        pass
                else:
                    # Remove from any sacco
                    Sacco.objects.filter(admin=user).update(admin=None)
            else:
                # Remove from any sacco if not sacco_admin
                Sacco.objects.filter(admin=user).update(admin=None)
            
            messages.success(request, 'User updated successfully')
            return redirect('admin_manage_users')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    # Get current sacco if user is sacco_admin
    current_sacco = None
    if user.user_type == 'sacco_admin':
        current_sacco = Sacco.objects.filter(admin=user).first()
    
    context = {
        'user': user,
        'user_types': User.USER_TYPES,
        'saccos': Sacco.objects.all(),
        'current_sacco': current_sacco,
    }
    
    return render(request, 'admin/edit_user.html', context)

def admin_delete_user(request, user_id):
    """Delete user"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        user = get_object_or_404(User, id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            user_name = f"{user.first_name} {user.last_name}"
            user.delete()
            messages.success(request, f'User {user_name} deleted successfully')
            return redirect('admin_manage_users')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    
    return render(request, 'admin/delete_user.html', {'user': user})

# Sacco Management Views
def admin_manage_saccos(request):
    """Manage all saccos"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    search = request.GET.get('search', '')
    
    # Filter saccos
    saccos = Sacco.objects.all()
    
    if search:
        saccos = saccos.filter(
            Q(name__icontains=search) |
            Q(registration_number__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(contact_email__icontains=search)
        )
    
    # Order by date registered
    saccos = saccos.order_by('-date_registered')
    
    # Get stats for each sacco
    for sacco in saccos:
        sacco.matatu_count = Matatu.objects.filter(sacco=sacco).count()
        sacco.route_count = Route.objects.filter(sacco=sacco).count()
        sacco.driver_count = User.objects.filter(
            user_type='driver',
            assigned_matatu_as_driver__sacco=sacco
        ).distinct().count()
    
    context = {
        'saccos': saccos,
        'search_query': search,
    }
    
    return render(request, 'admin/manage_saccos.html', context)

def admin_add_sacco(request):
    """Add new sacco"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            registration_number = request.POST.get('registration_number')
            contact_person = request.POST.get('contact_person')
            contact_phone = request.POST.get('contact_phone')
            contact_email = request.POST.get('contact_email')
            address = request.POST.get('address')
            admin_id = request.POST.get('admin')
            
            # Validate required fields
            if not all([name, registration_number, contact_person, contact_phone, contact_email]):
                raise ValidationError('All required fields must be filled')
            
            # Validate email
            validate_email(contact_email)
            
            # Check if name already exists
            if Sacco.objects.filter(name=name).exists():
                raise ValidationError('SACCO name already exists')
            
            # Check if registration number already exists
            if Sacco.objects.filter(registration_number=registration_number).exists():
                raise ValidationError('Registration number already exists')
            
            # Get admin user if provided
            admin_user = None
            if admin_id:
                try:
                    admin_user = User.objects.get(id=admin_id, user_type='sacco_admin')
                except User.DoesNotExist:
                    raise ValidationError('Selected admin user not found or not a SACCO admin')
            
            # Create sacco
            sacco = Sacco.objects.create(
                name=name,
                registration_number=registration_number,
                contact_person=contact_person,
                contact_phone=contact_phone,
                contact_email=contact_email,
                address=address,
                admin=admin_user
            )
            
            messages.success(request, f'SACCO {name} added successfully')
            return redirect('admin_manage_saccos')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error adding SACCO: {str(e)}')
    
    # Get available sacco admins (users with no sacco assigned)
    available_admins = User.objects.filter(
        user_type='sacco_admin',
        sacco__isnull=True  # This assumes you have a related_name in Sacco model
    )
    
    context = {
        'available_admins': available_admins,
    }
    
    return render(request, 'admin/add_sacco.html', context)

def admin_edit_sacco(request, sacco_id):
    """Edit sacco"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        sacco = get_object_or_404(Sacco, id=sacco_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            registration_number = request.POST.get('registration_number')
            contact_person = request.POST.get('contact_person')
            contact_phone = request.POST.get('contact_phone')
            contact_email = request.POST.get('contact_email')
            address = request.POST.get('address')
            admin_id = request.POST.get('admin')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate required fields
            if not all([name, registration_number, contact_person, contact_phone, contact_email]):
                raise ValidationError('All required fields must be filled')
            
            # Validate email
            validate_email(contact_email)
            
            # Check if name already exists (excluding current)
            if Sacco.objects.filter(name=name).exclude(id=sacco.id).exists():
                raise ValidationError('SACCO name already exists')
            
            # Check if registration number already exists (excluding current)
            if Sacco.objects.filter(registration_number=registration_number).exclude(id=sacco.id).exists():
                raise ValidationError('Registration number already exists')
            
            # Get admin user if provided
            admin_user = None
            if admin_id:
                try:
                    admin_user = User.objects.get(id=admin_id, user_type='sacco_admin')
                except User.DoesNotExist:
                    raise ValidationError('Selected admin user not found or not a SACCO admin')
            
            # Update sacco
            sacco.name = name
            sacco.registration_number = registration_number
            sacco.contact_person = contact_person
            sacco.contact_phone = contact_phone
            sacco.contact_email = contact_email
            sacco.address = address
            sacco.admin = admin_user
            sacco.is_active = is_active
            sacco.save()
            
            messages.success(request, f'SACCO {name} updated successfully')
            return redirect('admin_manage_saccos')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error updating SACCO: {str(e)}')
    
    # Get available sacco admins
    available_admins = User.objects.filter(user_type='sacco_admin')
    
    context = {
        'sacco': sacco,
        'available_admins': available_admins,
    }
    
    return render(request, 'admin/edit_sacco.html', context)

def admin_delete_sacco(request, sacco_id):
    """Delete sacco"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        sacco = get_object_or_404(Sacco, id=sacco_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Check if sacco has matatus
            if Matatu.objects.filter(sacco=sacco).exists():
                messages.error(request, 'Cannot delete SACCO with registered matatus')
                return redirect('admin_manage_saccos')
            
            sacco_name = sacco.name
            sacco.delete()
            messages.success(request, f'SACCO {sacco_name} deleted successfully')
            return redirect('admin_manage_saccos')
        except Exception as e:
            messages.error(request, f'Error deleting SACCO: {str(e)}')
    
    return render(request, 'admin/delete_sacco.html', {'sacco': sacco})

# Matatu Management Views
def admin_manage_matatus(request):
    """Manage all matatus"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    sacco_id = request.GET.get('sacco', '')
    search = request.GET.get('search', '')
    
    # Filter matatus
    matatus = Matatu.objects.select_related('sacco', 'current_driver', 'current_conductor')
    
    if sacco_id:
        matatus = matatus.filter(sacco_id=sacco_id)
    
    if search:
        matatus = matatus.filter(
            Q(plate_number__icontains=search) |
            Q(fleet_number__icontains=search) |
            Q(sacco__name__icontains=search)
        )
    
    # Order by registration date
    matatus = matatus.order_by('-registration_date')
    
    context = {
        'matatus': matatus,
        'saccos': Sacco.objects.all(),
        'selected_sacco': sacco_id,
        'search_query': search,
    }
    
    return render(request, 'admin/manage_matatus.html', context)

def admin_add_matatu(request):
    """Add new matatu"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            plate_number = request.POST.get('plate_number')
            fleet_number = request.POST.get('fleet_number')
            sacco_id = request.POST.get('sacco')
            vehicle_type = request.POST.get('vehicle_type')
            capacity = request.POST.get('capacity')
            driver_id = request.POST.get('driver')
            conductor_id = request.POST.get('conductor')
            
            # Validate required fields
            if not all([plate_number, fleet_number, sacco_id, vehicle_type, capacity]):
                raise ValidationError('All required fields must be filled')
            
            # Check if plate number already exists
            if Matatu.objects.filter(plate_number=plate_number).exists():
                raise ValidationError('Plate number already registered')
            
            # Check if fleet number already exists
            if Matatu.objects.filter(fleet_number=fleet_number).exists():
                raise ValidationError('Fleet number already exists')
            
            # Get sacco
            try:
                sacco = Sacco.objects.get(id=sacco_id)
            except Sacco.DoesNotExist:
                raise ValidationError('SACCO not found')
            
            # Get driver if provided
            driver = None
            if driver_id:
                try:
                    driver = User.objects.get(id=driver_id, user_type='driver')
                except User.DoesNotExist:
                    raise ValidationError('Selected driver not found or not a driver')
            
            # Get conductor if provided
            conductor = None
            if conductor_id:
                try:
                    conductor = User.objects.get(id=conductor_id, user_type='conductor')
                except User.DoesNotExist:
                    raise ValidationError('Selected conductor not found or not a conductor')
            
            # Generate QR code data
            qr_data = f"MATATU:{plate_number}:{fleet_number}:{int(timezone.now().timestamp())}"
            
            # Create matatu
            matatu = Matatu.objects.create(
                plate_number=plate_number,
                fleet_number=fleet_number,
                sacco=sacco,
                vehicle_type=vehicle_type,
                capacity=int(capacity),
                current_driver=driver,
                current_conductor=conductor,
                qr_code_data=qr_data
            )
            
            messages.success(request, f'Matatu {plate_number} added successfully')
            return redirect('admin_manage_matatus')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error adding matatu: {str(e)}')
    
    # Get available drivers and conductors
    available_drivers = User.objects.filter(user_type='driver')
    available_conductors = User.objects.filter(user_type='conductor')
    
    context = {
        'saccos': Sacco.objects.all(),
        'vehicle_types': Matatu.VEHICLE_TYPES,
        'available_drivers': available_drivers,
        'available_conductors': available_conductors,
    }
    
    return render(request, 'admin/add_matatu.html', context)

def admin_edit_matatu(request, matatu_id):
    """Edit matatu"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        matatu = get_object_or_404(Matatu, id=matatu_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            plate_number = request.POST.get('plate_number')
            fleet_number = request.POST.get('fleet_number')
            sacco_id = request.POST.get('sacco')
            vehicle_type = request.POST.get('vehicle_type')
            capacity = request.POST.get('capacity')
            driver_id = request.POST.get('driver')
            conductor_id = request.POST.get('conductor')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate required fields
            if not all([plate_number, fleet_number, sacco_id, vehicle_type, capacity]):
                raise ValidationError('All required fields must be filled')
            
            # Check if plate number already exists (excluding current)
            if Matatu.objects.filter(plate_number=plate_number).exclude(id=matatu.id).exists():
                raise ValidationError('Plate number already registered')
            
            # Check if fleet number already exists (excluding current)
            if Matatu.objects.filter(fleet_number=fleet_number).exclude(id=matatu.id).exists():
                raise ValidationError('Fleet number already exists')
            
            # Get sacco
            try:
                sacco = Sacco.objects.get(id=sacco_id)
            except Sacco.DoesNotExist:
                raise ValidationError('SACCO not found')
            
            # Get driver if provided
            driver = None
            if driver_id:
                try:
                    driver = User.objects.get(id=driver_id, user_type='driver')
                except User.DoesNotExist:
                    raise ValidationError('Selected driver not found or not a driver')
            
            # Get conductor if provided
            conductor = None
            if conductor_id:
                try:
                    conductor = User.objects.get(id=conductor_id, user_type='conductor')
                except User.DoesNotExist:
                    raise ValidationError('Selected conductor not found or not a conductor')
            
            # Update matatu
            matatu.plate_number = plate_number
            matatu.fleet_number = fleet_number
            matatu.sacco = sacco
            matatu.vehicle_type = vehicle_type
            matatu.capacity = int(capacity)
            matatu.current_driver = driver
            matatu.current_conductor = conductor
            matatu.is_active = is_active
            matatu.save()
            
            messages.success(request, f'Matatu {plate_number} updated successfully')
            return redirect('admin_manage_matatus')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error updating matatu: {str(e)}')
    
    # Get available drivers and conductors
    available_drivers = User.objects.filter(user_type='driver')
    available_conductors = User.objects.filter(user_type='conductor')
    
    context = {
        'matatu': matatu,
        'saccos': Sacco.objects.all(),
        'vehicle_types': Matatu.VEHICLE_TYPES,
        'available_drivers': available_drivers,
        'available_conductors': available_conductors,
    }
    
    return render(request, 'admin/edit_matatu.html', context)

def admin_delete_matatu(request, matatu_id):
    """Delete matatu"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        matatu = get_object_or_404(Matatu, id=matatu_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            plate_number = matatu.plate_number
            matatu.delete()
            messages.success(request, f'Matatu {plate_number} deleted successfully')
            return redirect('admin_manage_matatus')
        except Exception as e:
            messages.error(request, f'Error deleting matatu: {str(e)}')
    
    return render(request, 'admin/delete_matatu.html', {'matatu': matatu})

# Route Management Views
def admin_manage_routes(request):
    """Manage all routes"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    sacco_id = request.GET.get('sacco', '')
    search = request.GET.get('search', '')
    
    # Filter routes
    routes = Route.objects.select_related('sacco')
    
    if sacco_id:
        routes = routes.filter(sacco_id=sacco_id)
    
    if search:
        routes = routes.filter(
            Q(name__icontains=search) |
            Q(start_point__icontains=search) |
            Q(end_point__icontains=search)
        )
    
    # Order by name
    routes = routes.order_by('name')
    
    # Get trip counts for each route
    for route in routes:
        route.trip_count = Trip.objects.filter(route=route).count()
        route.active_trips = Trip.objects.filter(route=route, status='active').count()
    
    context = {
        'routes': routes,
        'saccos': Sacco.objects.all(),
        'selected_sacco': sacco_id,
        'search_query': search,
    }
    
    return render(request, 'admin/manage_routes.html', context)

def admin_add_route(request):
    """Add new route"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            start_point = request.POST.get('start_point')
            end_point = request.POST.get('end_point')
            distance_km = request.POST.get('distance_km')
            estimated_duration = request.POST.get('estimated_duration_minutes')
            standard_fare = request.POST.get('standard_fare')
            sacco_id = request.POST.get('sacco')
            
            # Validate required fields
            if not all([name, start_point, end_point, distance_km, estimated_duration, standard_fare, sacco_id]):
                raise ValidationError('All fields are required')
            
            # Get sacco
            try:
                sacco = Sacco.objects.get(id=sacco_id)
            except Sacco.DoesNotExist:
                raise ValidationError('SACCO not found')
            
            # Check if route name already exists for this sacco
            if Route.objects.filter(sacco=sacco, name=name).exists():
                raise ValidationError(f'Route "{name}" already exists for {sacco.name}')
            
            # Create route
            route = Route.objects.create(
                name=name,
                start_point=start_point,
                end_point=end_point,
                distance_km=float(distance_km),
                estimated_duration_minutes=int(estimated_duration),
                standard_fare=float(standard_fare),
                sacco=sacco
            )
            
            messages.success(request, f'Route {name} added successfully')
            return redirect('admin_manage_routes')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error adding route: {str(e)}')
    
    context = {
        'saccos': Sacco.objects.all(),
    }
    
    return render(request, 'admin/add_route.html', context)

def admin_edit_route(request, route_id):
    """Edit route"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        route = get_object_or_404(Route, id=route_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            start_point = request.POST.get('start_point')
            end_point = request.POST.get('end_point')
            distance_km = request.POST.get('distance_km')
            estimated_duration = request.POST.get('estimated_duration_minutes')
            standard_fare = request.POST.get('standard_fare')
            sacco_id = request.POST.get('sacco')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate required fields
            if not all([name, start_point, end_point, distance_km, estimated_duration, standard_fare, sacco_id]):
                raise ValidationError('All fields are required')
            
            # Get sacco
            try:
                sacco = Sacco.objects.get(id=sacco_id)
            except Sacco.DoesNotExist:
                raise ValidationError('SACCO not found')
            
            # Check if route name already exists for this sacco (excluding current)
            if Route.objects.filter(sacco=sacco, name=name).exclude(id=route.id).exists():
                raise ValidationError(f'Route "{name}" already exists for {sacco.name}')
            
            # Update route
            route.name = name
            route.start_point = start_point
            route.end_point = end_point
            route.distance_km = float(distance_km)
            route.estimated_duration_minutes = int(estimated_duration)
            route.standard_fare = float(standard_fare)
            route.sacco = sacco
            route.is_active = is_active
            route.save()
            
            messages.success(request, f'Route {name} updated successfully')
            return redirect('admin_manage_routes')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error updating route: {str(e)}')
    
    context = {
        'route': route,
        'saccos': Sacco.objects.all(),
    }
    
    return render(request, 'admin/edit_route.html', context)

def admin_delete_route(request, route_id):
    """Delete route"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        route = get_object_or_404(Route, id=route_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Check if route has trips
            if Trip.objects.filter(route=route).exists():
                messages.error(request, 'Cannot delete route with scheduled trips')
                return redirect('admin_manage_routes')
            
            route_name = route.name
            route.delete()
            messages.success(request, f'Route {route_name} deleted successfully')
            return redirect('admin_manage_routes')
        except Exception as e:
            messages.error(request, f'Error deleting route: {str(e)}')
    
    return render(request, 'admin/delete_route.html', {'route': route})

# Notification Management Views
def admin_manage_notifications(request):
    """Manage all notifications"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get notifications
    notifications = Notification.objects.select_related('created_by').order_by('-created_at')
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'admin/manage_notifications.html', context)

def admin_add_notification(request):
    """Add new notification"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            message = request.POST.get('message')
            notification_type = request.POST.get('notification_type')
            recipient_type = request.POST.get('recipient_type')
            recipient_ids = request.POST.getlist('recipients')
            sacco_ids = request.POST.getlist('saccos')
            
            # Validate required fields
            if not all([title, message, notification_type, recipient_type]):
                raise ValidationError('All required fields must be filled')
            
            # Create notification
            notification = Notification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                created_by=admin
            )
            
            # Add recipients based on type
            if recipient_type == 'all':
                # Send to all users
                all_users = User.objects.filter(is_active=True)
                notification.recipients.set(all_users)
            elif recipient_type == 'specific':
                # Send to specific users
                if recipient_ids:
                    recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
                    notification.recipients.set(recipients)
            
            # Add saccos if specified
            if sacco_ids:
                saccos = Sacco.objects.filter(id__in=sacco_ids)
                notification.saccos.set(saccos)
            
            messages.success(request, 'Notification created and sent successfully')
            return redirect('admin_manage_notifications')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error creating notification: {str(e)}')
    
    # Get all users for recipient selection
    all_users = User.objects.filter(is_active=True)
    
    context = {
        'notification_types': Notification.NOTIFICATION_TYPES,
        'all_users': all_users,
        'saccos': Sacco.objects.all(),
    }
    
    return render(request, 'admin/add_notification.html', context)

def admin_edit_notification(request, notification_id):
    """Edit notification"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')  
        
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        notification = get_object_or_404(Notification, id=notification_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            message = request.POST.get('message')
            notification_type = request.POST.get('notification_type')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate required fields
            if not all([title, message, notification_type]):
                raise ValidationError('All required fields must be filled')
            
            # Update notification
            notification.title = title
            notification.message = message
            notification.notification_type = notification_type
            notification.is_active = is_active
            notification.save()
            
            messages.success(request, 'Notification updated successfully')
            return redirect('admin_manage_notifications')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error updating notification: {str(e)}')
    
    context = {
        'notification': notification,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'admin/edit_notification.html', context)

def admin_delete_notification(request, notification_id):
    """Delete notification"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
        notification = get_object_or_404(Notification, id=notification_id)
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            notification.delete()
            messages.success(request, 'Notification deleted successfully')
            return redirect('admin_manage_notifications')
        except Exception as e:
            messages.error(request, f'Error deleting notification: {str(e)}')
    
    return render(request, 'admin/delete_notification.html', {'notification': notification})

# Trip Management Views
def admin_manage_trips(request):
    """Manage all trips"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    sacco_id = request.GET.get('sacco', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Filter trips
    trips = Trip.objects.select_related(
        'matatu', 'matatu__sacco', 'route', 'driver', 'conductor'
    ).order_by('-scheduled_departure')
    
    if status:
        trips = trips.filter(status=status)
    
    if sacco_id:
        trips = trips.filter(matatu__sacco_id=sacco_id)
    
    if date_from:
        trips = trips.filter(scheduled_departure__date__gte=date_from)
    
    if date_to:
        trips = trips.filter(scheduled_departure__date__lte=date_to)
    
    # Get passenger counts for each trip
    for trip in trips:
        trip.passenger_count = PassengerTrip.objects.filter(trip=trip).count()
    
    context = {
        'trips': trips,
        'status_choices': Trip.TRIP_STATUS,
        'saccos': Sacco.objects.all(),
        'selected_status': status,
        'selected_sacco': sacco_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin/manage_trips.html', context)

# Payment Management Views
def admin_manage_payments(request):
    """Manage all payments"""
    if 'user_id' not in request.session:
        messages.error(request, 'Please login')
        return redirect('login')
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied')
        return redirect('login')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    payment_type = request.GET.get('payment_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Filter payments
    payments = Payment.objects.select_related('passenger').order_by('-created_at')
    
    if status:
        payments = payments.filter(status=status)
    
    if payment_type:
        payments = payments.filter(payment_type=payment_type)
    
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
    
    # Calculate totals
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    completed_amount = payments.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'payments': payments,
        'status_choices': Payment.STATUS_CHOICES,
        'payment_types': Payment.PAYMENT_TYPES,
        'selected_status': status,
        'selected_type': payment_type,
        'date_from': date_from,
        'date_to': date_to,
        'total_amount': total_amount,
        'completed_amount': completed_amount,
    }
    
    return render(request, 'admin/manage_payments.html', context)

# Dashboard Statistics API
def admin_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
    
    try:
        admin = User.objects.get(id=request.session['user_id'], user_type='super_admin')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    # Get stats for the last 7 days
    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    
    # User registrations by day
    user_registrations = []
    for i in range(7):
        date = last_week + timedelta(days=i)
        count = User.objects.filter(date_joined__date=date).count()
        user_registrations.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Payment statistics by day
    payment_stats = []
    for i in range(7):
        date = last_week + timedelta(days=i)
        daily_payments = Payment.objects.filter(created_at__date=date, status='completed')
        total = daily_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        count = daily_payments.count()
        payment_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': float(total),
            'count': count
        })
    
    # Active trips by status
    active_trips = Trip.objects.filter(status='active').count()
    scheduled_trips = Trip.objects.filter(status='scheduled').count()
    completed_trips = Trip.objects.filter(status='completed').count()
    
    # Recent activities
    recent_activities = []
    
    # Add user registrations
    new_users = User.objects.filter(date_joined__date=today)[:5]
    for user in new_users:
        recent_activities.append({
            'type': 'user_registration',
            'title': f'New {user.get_user_type_display()} Registered',
            'description': f'{user.first_name} {user.last_name}',
            'time': user.date_joined,
            'icon': 'fas fa-user-plus'
        })
    
    # Add new payments
    new_payments = Payment.objects.filter(created_at__date=today, status='completed')[:5]
    for payment in new_payments:
        recent_activities.append({
            'type': 'payment',
            'title': 'Payment Received',
            'description': f'KES {payment.amount} from {payment.passenger.first_name}',
            'time': payment.created_at,
            'icon': 'fas fa-credit-card'
        })
    
    # Add new trips
    new_trips = Trip.objects.filter(created_at__date=today)[:5]
    for trip in new_trips:
        recent_activities.append({
            'type': 'trip',
            'title': 'New Trip Scheduled',
            'description': f'{trip.route.name} - {trip.matatu.plate_number}',
            'time': trip.created_at,
            'icon': 'fas fa-bus'
        })
    
    # Sort by time
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    
    return JsonResponse({
        'success': True,
        'user_registrations': user_registrations,
        'payment_stats': payment_stats,
        'trip_stats': {
            'active': active_trips,
            'scheduled': scheduled_trips,
            'completed': completed_trips
        },
        'recent_activities': recent_activities[:10]
    })

def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # Password reset logic would go here
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('login')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'auth/forgot_password.html', {'form': form})

def logout(request):
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# Dashboard view
def dashboard(request):
    # Check if user is logged in via session
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='passenger')
    except User.DoesNotExist:
        messages.error(request, 'Passenger not found')
        return redirect('login')
    
    # Calculate greeting based on time
    current_hour = timezone.now().hour
    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    
    # Get passenger statistics
    total_trips = PassengerTrip.objects.filter(passenger=user).count()
    
    # Get active bookings (trips in next 24 hours)
    next_24_hours = timezone.now() + timedelta(hours=24)
    active_bookings = PassengerTrip.objects.filter(
        passenger=user,
        trip__scheduled_departure__gte=timezone.now(),
        trip__scheduled_departure__lte=next_24_hours,
        trip__status__in=['scheduled', 'active']
    ).select_related('trip', 'trip__route', 'trip__matatu', 'trip__driver')
    
    # Calculate total spent
    total_spent_result = PassengerTrip.objects.filter(
        passenger=user,
        is_paid=True
    ).aggregate(total=Sum('fare_paid'))
    total_spent = total_spent_result['total'] or 0
    
    # Get popular routes (based on frequency)
    popular_routes = Route.objects.filter(
        is_active=True
    ).annotate(
        trip_count=Count('trips')
    ).order_by('-trip_count')[:6]
    
    # Get recent trips (last 10)
    recent_trips = PassengerTrip.objects.filter(
        passenger=user
    ).select_related('trip', 'trip__route').order_by('-alighted_at')[:10]
    
    # Get notifications
    unread_notifications = []
    recent_notifications = []
    
    try:
        # Get unread notifications
        unread_notifications = Notification.objects.filter(
            recipients=user,
            created_at__gte=user.last_login or timezone.now() - timedelta(days=7)
        ).exclude(
            id__in=request.session.get('read_notifications', [])
        )
        
        # Get recent notifications for dropdown
        recent_notifications = Notification.objects.filter(
            Q(recipients=user) | Q(recipients__isnull=True)
        ).order_by('-created_at')[:10]
    except:
        pass  # If notifications model doesn't exist yet
    
    context = {
        'passenger': user,
        'greeting': greeting,
        'current_time': timezone.now(),
        'total_trips': total_trips,
        'active_bookings': active_bookings,
        'total_spent': total_spent,
        'popular_routes': popular_routes,
        'recent_trips': recent_trips,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'average_rating': 4.8,  # Default value
    }
    
    return render(request, 'passenger/dashboard.html', context)

# Other dashboard views
def sacco_dashboard(request):
    """Sacco Admin Dashboard"""
    # Check if user is logged in and is a sacco admin
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='sacco_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied. Sacco admin only.')
        return redirect('login')
    
    # Get sacco associated with this admin
    try:
        sacco = Sacco.objects.get(admin=user)
    except Sacco.DoesNotExist:
        messages.error(request, 'No Sacco assigned to your account')
        return render(request, 'sacco/dashboard.html', {'sacco': None})
    
    # Get sacco statistics
    total_matatus = Matatu.objects.filter(sacco=sacco).count()
    total_routes = Route.objects.filter(sacco=sacco).count()
    total_drivers = User.objects.filter(user_type='driver', assigned_matatu_as_driver__sacco=sacco).distinct().count()
    total_conductors = User.objects.filter(user_type='conductor', assigned_matatu_as_conductor__sacco=sacco).distinct().count()
    
    # Get recent trips
    recent_trips = Trip.objects.filter(
        matatu__sacco=sacco
    ).select_related('matatu', 'route', 'driver').order_by('-scheduled_departure')[:10]
    
    context = {
        'sacco': sacco,
        'total_matatus': total_matatus,
        'total_routes': total_routes,
        'total_drivers': total_drivers,
        'total_conductors': total_conductors,
        'recent_trips': recent_trips,
    }
    
    return render(request, 'sacco/dashboard.html', context)

def admin_dashboard(request):
    """Super Admin Dashboard"""
    # Check if user is logged in and is a super admin
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='super_admin')
    except User.DoesNotExist:
        messages.error(request, 'Access denied. Super admin only.')
        return redirect('login')
    
    # Admin statistics
    total_saccos = Sacco.objects.count()
    total_passengers = User.objects.filter(user_type='passenger').count()
    total_drivers = User.objects.filter(user_type='driver').count()
    total_conductors = User.objects.filter(user_type='conductor').count()
    
    # Recent registrations
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    
    context = {
        'total_saccos': total_saccos,
        'total_passengers': total_passengers,
        'total_drivers': total_drivers,
        'total_conductors': total_conductors,
        'recent_users': recent_users,
    }
    
    return render(request, 'admin/dashboard.html', context)

def driver_dashboard(request):
    """Driver Dashboard"""
    # Check if user is logged in and is a driver
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='driver')
    except User.DoesNotExist:
        messages.error(request, 'Access denied. Driver only.')
        return redirect('login')
    
    # Get assigned matatu
    try:
        matatu = Matatu.objects.filter(current_driver=user).first()
        current_trip = Trip.objects.filter(
            driver=user,
            status__in=['active', 'scheduled']
        ).order_by('-scheduled_departure').first()
    except:
        matatu = None
        current_trip = None
    
    # Driver statistics
    total_trips_driven = Trip.objects.filter(driver=user).count()
    completed_trips = Trip.objects.filter(driver=user, status='completed').count()
    
    context = {
        'driver': user,
        'matatu': matatu,
        'current_trip': current_trip,
        'total_trips_driven': total_trips_driven,
        'completed_trips': completed_trips,
    }
    
    return render(request, 'driver/dashboard.html', context)

def conductor_dashboard(request):
    """Conductor Dashboard"""
    # Check if user is logged in and is a conductor
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access dashboard')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = User.objects.get(id=user_id, user_type='conductor')
    except User.DoesNotExist:
        messages.error(request, 'Access denied. Conductor only.')
        return redirect('login')
    
    # Get assigned matatu
    try:
        matatu = Matatu.objects.filter(current_conductor=user).first()
        current_trip = Trip.objects.filter(
            conductor=user,
            status__in=['active', 'scheduled']
        ).order_by('-scheduled_departure').first()
    except:
        matatu = None
        current_trip = None
    
    # Conductor statistics
    total_trips_conducted = Trip.objects.filter(conductor=user).count()
    
    # Today's passengers
    today = timezone.now().date()
    todays_passengers = PassengerTrip.objects.filter(
        trip__conductor=user,
        trip__scheduled_departure__date=today
    ).select_related('passenger').count()
    
    context = {
        'conductor': user,
        'matatu': matatu,
        'current_trip': current_trip,
        'total_trips_conducted': total_trips_conducted,
        'todays_passengers': todays_passengers,
    }
    
    return render(request, 'conductor/dashboard.html', context)

# API Views
def dashboard_data_api(request):
    """API endpoint for dashboard data updates"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
    
    user_id = request.session['user_id']
    try:
        passenger = User.objects.get(id=user_id, user_type='passenger')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
    
    # Get updated stats
    stats = {
        'total_trips': PassengerTrip.objects.filter(passenger=passenger).count(),
        'wallet_balance': float(passenger.credits),
        'active_bookings': PassengerTrip.objects.filter(
            passenger=passenger,
            trip__status__in=['scheduled', 'active'],
            trip__scheduled_departure__gte=timezone.now()
        ).count(),
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })

def search_routes_api(request):
    """API endpoint for route search"""
    query = request.GET.get('q', '')
    
    routes = Route.objects.filter(
        Q(name__icontains=query) |
        Q(start_point__icontains=query) |
        Q(end_point__icontains=query) |
        Q(sacco__name__icontains=query),
        is_active=True
    ).select_related('sacco')[:10]
    
    route_list = []
    for route in routes:
        route_list.append({
            'id': route.id,
            'name': route.name,
            'sacco_name': route.sacco.name,
            'fare': float(route.standard_fare),
            'start_point': route.start_point,
            'end_point': route.end_point,
            'duration': route.estimated_duration_minutes
        })
    
    return JsonResponse({
        'success': True,
        'routes': route_list
    })

def route_details_api(request, route_id):
    """API endpoint for route details"""
    route = get_object_or_404(Route, id=route_id)
    
    # Get upcoming trips for this route
    upcoming_trips = Trip.objects.filter(
        route=route,
        scheduled_departure__gte=timezone.now(),
        status='scheduled'
    ).select_related('matatu')[:5]
    
    trips_list = []
    for trip in upcoming_trips:
        trips_list.append({
            'id': trip.id,
            'time': trip.scheduled_departure.strftime('%I:%M %p'),
            'matatu': trip.matatu.plate_number if trip.matatu else 'Not assigned',
            'driver': trip.driver.get_full_name() if trip.driver else 'Not assigned'
        })
    
    return JsonResponse({
        'success': True,
        'route': {
            'id': route.id,
            'name': route.name,
            'sacco': route.sacco.name if route.sacco else 'No Sacco',
            'fare': float(route.standard_fare),
            'distance': float(route.distance_km) if route.distance_km else 0,
            'duration': route.estimated_duration_minutes,
            'description': f"{route.start_point} to {route.end_point}"
        },
        'upcoming_trips': trips_list
    })

def book_trip_api(request):
    """API endpoint to book a trip"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            route_id = data.get('route_id')
            trip_id = data.get('trip_id')
            
            # Get user from session
            if 'user_id' not in request.session:
                return JsonResponse({
                    'success': False,
                    'message': 'Not authenticated'
                })
            
            user_id = request.session['user_id']
            passenger = get_object_or_404(User, id=user_id, user_type='passenger')
            
            # Get trip
            trip = get_object_or_404(Trip, id=trip_id, route_id=route_id)
            
            # Check if already booked
            existing_booking = PassengerTrip.objects.filter(
                passenger=passenger,
                trip=trip
            ).exists()
            
            if existing_booking:
                return JsonResponse({
                    'success': False,
                    'message': 'You have already booked this trip'
                })
            
            # Check wallet balance
            if passenger.credits < trip.route.standard_fare:
                return JsonResponse({
                    'success': False,
                    'message': 'Insufficient wallet balance'
                })
            
            # Create booking
            booking = PassengerTrip.objects.create(
                passenger=passenger,
                trip=trip,
                boarding_stop=trip.route.start_point,
                alighting_stop=trip.route.end_point,
                fare_paid=trip.route.standard_fare,
                payment_method='credits',
                is_paid=True
            )
            
            # Deduct from wallet
            passenger.credits -= booking.fare_paid
            passenger.save()
            
            # Create payment record
            try:
                payment = Payment.objects.create(
                    passenger=passenger,
                    payment_type='trip',
                    amount=booking.fare_paid,
                    transaction_id=f"TRIP{booking.id:06d}",
                    payment_method='credits',
                    status='completed',
                    description=f'Trip booking for {trip.route.name}',
                    completed_at=timezone.now()
                )
            except:
                pass  # If Payment model doesn't exist yet
            
            return JsonResponse({
                'success': True,
                'booking_id': booking.id,
                'message': 'Booking successful'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def active_bookings_api(request):
    """API endpoint for active bookings"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
    
    user_id = request.session['user_id']
    try:
        passenger = User.objects.get(id=user_id, user_type='passenger')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
    
    active_bookings = PassengerTrip.objects.filter(
        passenger=passenger,
        trip__scheduled_departure__gte=timezone.now() - timedelta(hours=1),
        trip__status__in=['scheduled', 'active']
    ).select_related('trip', 'trip__route', 'trip__matatu', 'trip__driver')
    
    bookings_list = []
    for booking in active_bookings:
        bookings_list.append({
            'trip_id': booking.trip.id,
            'route_name': booking.trip.route.name,
            'matatu': booking.trip.matatu.plate_number if booking.trip.matatu else 'Not assigned',
            'driver': booking.trip.driver.get_full_name() if booking.trip.driver else 'Unknown',
            'status': booking.trip.status,
            'time': booking.trip.scheduled_departure.strftime('%I:%M %p'),
            'seats_available': booking.trip.matatu.capacity - booking.trip.passengers.count() if booking.trip.matatu else 0
        })
    
    return JsonResponse({
        'success': True,
        'bookings': bookings_list
    })

# Route pages - SINGLE OPTIMIZED VIEW
def routes_list(request):
    """Display all available routes with filtering and pagination"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.info(request, 'Please login to view all routes')
        return redirect('login')
    
    # Get all active routes
    routes = Route.objects.filter(is_active=True).select_related('sacco').order_by('name')
    
    # Get filter parameters
    start_point = request.GET.get('start_point', '')
    end_point = request.GET.get('end_point', '')
    sacco_id = request.GET.get('sacco', '')
    min_fare = request.GET.get('min_fare', '')
    max_fare = request.GET.get('max_fare', '')
    
    # Apply filters
    if start_point:
        routes = routes.filter(start_point__icontains=start_point)
    if end_point:
        routes = routes.filter(end_point__icontains=end_point)
    if sacco_id:
        routes = routes.filter(sacco_id=sacco_id)
    if min_fare:
        try:
            routes = routes.filter(standard_fare__gte=float(min_fare))
        except ValueError:
            pass
    if max_fare:
        try:
            routes = routes.filter(standard_fare__lte=float(max_fare))
        except ValueError:
            pass
    
    # Get passenger info for booking
    passenger = None
    if 'user_id' in request.session:
        try:
            passenger = User.objects.get(id=request.session['user_id'], user_type='passenger')
        except User.DoesNotExist:
            pass
    
    # Get all saccos for filter dropdown
    saccos = Sacco.objects.filter(is_active=True).order_by('name')
    
    # Get unique start and end points for filter suggestions
    start_points = Route.objects.filter(is_active=True).values_list('start_point', flat=True).distinct().order_by('start_point')[:20]
    end_points = Route.objects.filter(is_active=True).values_list('end_point', flat=True).distinct().order_by('end_point')[:20]
    
    # Get upcoming trips count for each route
    for route in routes:
        route.upcoming_trips_count = Trip.objects.filter(
            route=route,
            scheduled_departure__gte=timezone.now(),
            status='scheduled'
        ).count()
    
    context = {
        'routes': routes,
        'saccos': saccos,
        'start_points': start_points,
        'end_points': end_points,
        'start_point': start_point,
        'end_point': end_point,
        'sacco_id': sacco_id,
        'min_fare': min_fare,
        'max_fare': max_fare,
        'passenger': passenger,
        'total_routes': routes.count(),
    }
    
    return render(request, 'passenger/routes_list.html', context)

def my_trips(request):
    """Display passenger's trip history"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access this page')
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        passenger = User.objects.get(id=user_id, user_type='passenger')
    except User.DoesNotExist:
        messages.error(request, 'Passenger not found')
        return redirect('login')
    
    trips = PassengerTrip.objects.filter(
        passenger=passenger
    ).select_related('trip', 'trip__route', 'trip__matatu').order_by('-transaction_time')
    
    # Filter by date if provided
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            trips = trips.filter(trip__scheduled_departure__date=filter_date)
        except ValueError:
            pass
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        trips = trips.filter(trip__status=status_filter)
    
    context = {
        'trips': trips,
        'date_filter': date_filter or '',
        'status_filter': status_filter or '',
    }
    return render(request, 'trips/my_trips.html', context)

def top_up_wallet(request):
    """Display wallet top-up page"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access this page')
        return redirect('login')
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        
        # Validate amount
        try:
            amount = float(amount)
            if amount < 100:
                messages.error(request, 'Minimum top-up amount is KES 100')
                return redirect('top_up_wallet')
        except ValueError:
            messages.error(request, 'Invalid amount')
            return redirect('top_up_wallet')
        
        user_id = request.session['user_id']
        try:
            passenger = User.objects.get(id=user_id, user_type='passenger')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('login')
        
        # Update wallet balance
        passenger.credits += amount
        passenger.save()
        
        # Create payment record
        try:
            payment = Payment.objects.create(
                passenger=passenger,
                payment_type='credit_topup',
                amount=amount,
                transaction_id=f"TOPUP{int(timezone.now().timestamp())}",
                payment_method=payment_method,
                status='completed',
                description=f'Wallet top-up of KES {amount}',
                completed_at=timezone.now()
            )
        except:
            pass  # If Payment model doesn't exist yet
        
        messages.success(request, f'Successfully topped up KES {amount}')
        return redirect('dashboard')
    
    return render(request, 'payments/top_up.html')

# Quick action view
def quick_book(request):
    """Handle quick booking requests"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to access this page')
        return redirect('login')
    
    if request.method == 'POST':
        start_point = request.POST.get('start_point')
        end_point = request.POST.get('end_point')
        travel_date = request.POST.get('travel_date')
        
        # Find matching routes
        routes = Route.objects.filter(
            start_point__icontains=start_point,
            end_point__icontains=end_point,
            is_active=True
        ).select_related('sacco')
        
        # Find trips for the selected date
        trips = Trip.objects.filter(
            route__in=routes,
            scheduled_departure__date=travel_date,
            status='scheduled'
        ).select_related('route', 'matatu', 'driver')
        
        context = {
            'routes': routes,
            'trips': trips,
            'start_point': start_point,
            'end_point': end_point,
            'travel_date': travel_date,
        }
        return render(request, 'bookings/quick_book_results.html', context)
    
    return render(request, 'bookings/quick_book.html')



def process_payment(request):
    """Process payment for wallet top-up"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            payment_method = data.get('payment_method')
            
            # Validate amount
            if not amount or float(amount) < 100:
                return JsonResponse({
                    'success': False, 
                    'message': 'Minimum top-up amount is KES 100'
                })
            
            user_id = request.session['user_id']
            try:
                passenger = User.objects.get(id=user_id, user_type='passenger')
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'User not found'})
            
            # Simulate payment processing
            # In a real app, you would integrate with M-Pesa, Stripe, etc.
            amount_float = float(amount)
            
            # Update wallet balance
            passenger.credits += amount_float
            passenger.save()
            
            # Create payment record
            try:
                payment = Payment.objects.create(
                    passenger=passenger,
                    payment_type='credit_topup',
                    amount=amount_float,
                    transaction_id=f"PAY{int(timezone.now().timestamp())}",
                    payment_method=payment_method,
                    status='completed',
                    description=f'Wallet top-up of KES {amount_float}',
                    completed_at=timezone.now()
                )
            except:
                pass  # If Payment model doesn't exist yet
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully topped up KES {amount_float}',
                'new_balance': float(passenger.credits)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Payment failed: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})