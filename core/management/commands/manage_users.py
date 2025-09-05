from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from core.models import EmailAccount, UserPreference
from tabulate import tabulate
import secrets
import string

User = get_user_model()


class Command(BaseCommand):
    help = 'User management and access control with least privilege principle'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'create', 'deactivate', 'reset-password', 'permissions', 'audit'],
            help='Action to perform'
        )
        parser.add_argument(
            '--username',
            help='Username for user operations'
        )
        parser.add_argument(
            '--email',
            help='Email for user creation'
        )
        parser.add_argument(
            '--role',
            choices=['admin', 'user', 'readonly'],
            help='User role (admin, user, readonly)'
        )
        parser.add_argument(
            '--group',
            help='Group name for permission operations'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export user data to CSV'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(
            self.style.SUCCESS('=== User Management System ===\n')
        )

        if action == 'list':
            self._list_users(options)
        elif action == 'create':
            self._create_user(options)
        elif action == 'deactivate':
            self._deactivate_user(options)
        elif action == 'reset-password':
            self._reset_password(options)
        elif action == 'permissions':
            self._manage_permissions(options)
        elif action == 'audit':
            self._audit_users(options)

    def _list_users(self, options):
        """List all users with their details"""
        users = User.objects.all().order_by('date_joined')
        
        if not users.exists():
            self.stdout.write("No users found.")
            return

        # Prepare table data
        table_data = []
        for user in users:
            email_accounts = EmailAccount.objects.filter(user=user).count()
            last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
            
            # Get user groups
            groups = ', '.join([g.name for g in user.groups.all()]) or 'None'
            
            # Check if user is premium
            premium_status = "✓" if getattr(user, 'is_premium', False) else "✗"
            
            table_data.append([
                user.id,
                user.username,
                user.email,
                "✓" if user.is_active else "✗",
                "✓" if user.is_staff else "✗",
                "✓" if user.is_superuser else "✗",
                premium_status,
                email_accounts,
                last_login,
                user.date_joined.strftime('%Y-%m-%d'),
                groups
            ])

        headers = [
            "ID", "Username", "Email", "Active", "Staff", "Super", 
            "Premium", "Accounts", "Last Login", "Created", "Groups"
        ]

        self.stdout.write(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Summary
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        staff_users = users.filter(is_staff=True).count()
        superusers = users.filter(is_superuser=True).count()
        
        self.stdout.write(f"\n📊 Summary: {total_users} total, {active_users} active, {staff_users} staff, {superusers} superuser")

        if options.get('export'):
            self._export_users_csv(users)

    def _create_user(self, options):
        """Create a new user with specified role"""
        username = options.get('username')
        email = options.get('email')
        role = options.get('role', 'user')
        
        if not username or not email:
            raise CommandError("Both --username and --email are required for user creation")

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists")
        
        if User.objects.filter(email=email).exists():
            raise CommandError(f"Email '{email}' already exists")

        # Generate secure temporary password
        password = self._generate_password()
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Set role-based permissions
                self._assign_role(user, role)
                
                # Create user preferences
                UserPreference.objects.create(
                    user=user,
                    default_tone='professional',
                    auto_categorize=True,
                    auto_generate_drafts=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ User '{username}' created successfully")
                )
                self.stdout.write(f"   Email: {email}")
                self.stdout.write(f"   Role: {role}")
                self.stdout.write(f"   Temporary Password: {password}")
                self.stdout.write("   ⚠️  User should change password on first login")
                
        except Exception as e:
            raise CommandError(f"Failed to create user: {str(e)}")

    def _deactivate_user(self, options):
        """Deactivate a user account"""
        username = options.get('username')
        
        if not username:
            raise CommandError("--username is required for deactivation")

        try:
            user = User.objects.get(username=username)
            
            if not user.is_active:
                self.stdout.write(f"User '{username}' is already inactive")
                return
            
            # Deactivate user
            user.is_active = False
            user.save()
            
            # Deactivate associated email accounts
            email_accounts = EmailAccount.objects.filter(user=user)
            deactivated_accounts = email_accounts.update(is_active=False, sync_enabled=False)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ User '{username}' deactivated")
            )
            self.stdout.write(f"   Deactivated {deactivated_accounts} email accounts")
            
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

    def _reset_password(self, options):
        """Reset user password"""
        username = options.get('username')
        
        if not username:
            raise CommandError("--username is required for password reset")

        try:
            user = User.objects.get(username=username)
            
            new_password = self._generate_password()
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Password reset for '{username}'")
            )
            self.stdout.write(f"   New Password: {new_password}")
            self.stdout.write("   ⚠️  User should change password on next login")
            
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

    def _manage_permissions(self, options):
        """Manage user groups and permissions"""
        self._ensure_groups_exist()
        
        # List all groups and their permissions
        self.stdout.write("🔐 User Groups and Permissions:\n")
        
        groups = Group.objects.all().prefetch_related('permissions')
        for group in groups:
            permissions = list(group.permissions.values_list('name', flat=True))
            self.stdout.write(f"Group: {group.name}")
            self.stdout.write(f"  Permissions: {len(permissions)}")
            for perm in permissions[:5]:  # Show first 5 permissions
                self.stdout.write(f"    - {perm}")
            if len(permissions) > 5:
                self.stdout.write(f"    ... and {len(permissions) - 5} more")
            self.stdout.write("")

    def _audit_users(self, options):
        """Audit user access and security"""
        self.stdout.write("🔍 User Security Audit:\n")
        
        # Users without recent login
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        inactive_users = User.objects.filter(
            is_active=True,
            last_login__lt=thirty_days_ago
        ).exclude(last_login__isnull=True)
        
        if inactive_users.exists():
            self.stdout.write("⚠️  Users inactive for 30+ days:")
            for user in inactive_users:
                days_inactive = (timezone.now() - user.last_login).days
                self.stdout.write(f"   - {user.username}: {days_inactive} days")
        else:
            self.stdout.write("✅ No users inactive for 30+ days")
        
        # Users with no email accounts
        users_no_accounts = User.objects.filter(email_accounts__isnull=True)
        if users_no_accounts.exists():
            self.stdout.write("\n⚠️  Users with no email accounts:")
            for user in users_no_accounts:
                self.stdout.write(f"   - {user.username}")
        
        # Superusers audit
        superusers = User.objects.filter(is_superuser=True)
        self.stdout.write(f"\n🔑 Superusers ({superusers.count()}):")
        for user in superusers:
            last_login = user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never'
            self.stdout.write(f"   - {user.username} (Last login: {last_login})")
        
        # Permission analysis
        self._audit_permissions()

    def _audit_permissions(self):
        """Audit user permissions for least privilege"""
        self.stdout.write("\n🔐 Permission Analysis:")
        
        # Users with potentially excessive permissions
        staff_users = User.objects.filter(is_staff=True, is_superuser=False)
        self.stdout.write(f"   Staff users (non-superuser): {staff_users.count()}")
        
        # Group membership analysis
        groups = Group.objects.all()
        self.stdout.write(f"   Total groups: {groups.count()}")
        
        for group in groups:
            user_count = group.user_set.count()
            perm_count = group.permissions.count()
            self.stdout.write(f"   - {group.name}: {user_count} users, {perm_count} permissions")

    def _assign_role(self, user, role):
        """Assign role-based permissions following least privilege"""
        self._ensure_groups_exist()
        
        # Clear existing groups
        user.groups.clear()
        
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
            admin_group = Group.objects.get(name='Administrators')
            user.groups.add(admin_group)
        elif role == 'user':
            user.is_staff = False
            user.is_superuser = False
            user_group = Group.objects.get(name='Standard Users')
            user.groups.add(user_group)
        elif role == 'readonly':
            user.is_staff = False
            user.is_superuser = False
            readonly_group = Group.objects.get(name='Read Only Users')
            user.groups.add(readonly_group)
        
        user.save()

    def _ensure_groups_exist(self):
        """Ensure required groups exist with appropriate permissions"""
        from django.contrib.contenttypes.models import ContentType
        
        # Define groups and their permissions
        group_permissions = {
            'Administrators': [
                'add_user', 'change_user', 'delete_user', 'view_user',
                'add_emailaccount', 'change_emailaccount', 'delete_emailaccount', 'view_emailaccount',
                'add_emailmessage', 'change_emailmessage', 'delete_emailmessage', 'view_emailmessage',
                'add_userpreference', 'change_userpreference', 'delete_userpreference', 'view_userpreference',
                'add_meeting', 'change_meeting', 'delete_meeting', 'view_meeting'
            ],
            'Standard Users': [
                'view_emailaccount', 'change_emailaccount',
                'add_emailmessage', 'change_emailmessage', 'view_emailmessage',
                'change_userpreference', 'view_userpreference',
                'add_meeting', 'change_meeting', 'view_meeting'
            ],
            'Read Only Users': [
                'view_emailaccount',
                'view_emailmessage',
                'view_userpreference',
                'view_meeting'
            ]
        }
        
        for group_name, perm_codes in group_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                self.stdout.write(f"Created group: {group_name}")
            
            # Add permissions to group
            for perm_code in perm_codes:
                try:
                    permission = Permission.objects.get(codename=perm_code)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Permission '{perm_code}' not found")
                    )

    def _generate_password(self, length=12):
        """Generate a secure temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def _export_users_csv(self, users):
        """Export users to CSV file"""
        import csv
        from django.utils import timezone
        
        filename = f"users_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'ID', 'Username', 'Email', 'First Name', 'Last Name',
                'Is Active', 'Is Staff', 'Is Superuser', 'Date Joined',
                'Last Login', 'Email Accounts', 'Groups'
            ])
            
            # Write user data
            for user in users:
                email_accounts = EmailAccount.objects.filter(user=user).count()
                groups = ', '.join([g.name for g in user.groups.all()])
                
                writer.writerow([
                    user.id,
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.is_active,
                    user.is_staff,
                    user.is_superuser,
                    user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                    email_accounts,
                    groups
                ])
        
        self.stdout.write(f"✅ Users exported to: {filename}")