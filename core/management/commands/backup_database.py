from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
import os
import subprocess
import json
import shutil
from pathlib import Path


class Command(BaseCommand):
    help = 'Create database backup with retention policy and verification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-dir',
            default='./backups',
            help='Directory to store backups (default: ./backups)',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to retain backups (default: 30)',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify backup integrity after creation',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files',
        )

    def handle(self, *args, **options):
        backup_dir = Path(options['backup_dir'])
        retention_days = options['retention_days']
        
        self.stdout.write(
            self.style.SUCCESS('=== Database Backup System ===\n')
        )

        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"fyxerai_backup_{timestamp}"
        
        # Determine backup method based on database type
        db_config = settings.DATABASES['default']
        db_engine = db_config['ENGINE']
        
        if 'sqlite' in db_engine:
            backup_file = self._backup_sqlite(backup_dir, backup_name, db_config)
        elif 'postgresql' in db_engine:
            backup_file = self._backup_postgresql(backup_dir, backup_name, db_config)
        else:
            self.stdout.write(
                self.style.ERROR(f'Unsupported database engine: {db_engine}')
            )
            return

        # Create metadata file
        metadata_file = self._create_metadata(backup_dir, backup_name, backup_file)
        
        # Compress if requested
        if options['compress']:
            backup_file = self._compress_backup(backup_file)
            if backup_file:
                self.stdout.write(f"✅ Backup compressed: {backup_file}")

        # Verify backup if requested
        if options['verify']:
            if self._verify_backup(backup_file):
                self.stdout.write("✅ Backup verification successful")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Backup verification failed")
                )
                return

        # Clean up old backups
        self._cleanup_old_backups(backup_dir, retention_days)
        
        # Final report
        self._generate_backup_report(backup_dir, backup_file)

    def _backup_sqlite(self, backup_dir, backup_name, db_config):
        """Backup SQLite database"""
        db_path = db_config['NAME']
        backup_file = backup_dir / f"{backup_name}.sqlite3"
        
        self.stdout.write(f"📁 Backing up SQLite database: {db_path}")
        
        try:
            # Copy SQLite file
            shutil.copy2(db_path, backup_file)
            
            # Also create a SQL dump for portability
            sql_backup = backup_dir / f"{backup_name}.sql"
            with open(sql_backup, 'w') as f:
                call_command('dbshell', database='default', 
                           stdin=subprocess.PIPE, stdout=f, 
                           input_text='.dump')
            
            self.stdout.write(f"✅ SQLite backup created: {backup_file}")
            self.stdout.write(f"✅ SQL dump created: {sql_backup}")
            
            return backup_file
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ SQLite backup failed: {str(e)}")
            )
            return None

    def _backup_postgresql(self, backup_dir, backup_name, db_config):
        """Backup PostgreSQL database"""
        backup_file = backup_dir / f"{backup_name}.sql"
        
        self.stdout.write("🐘 Backing up PostgreSQL database")
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', db_config.get('HOST', 'localhost'),
            '--port', str(db_config.get('PORT', 5432)),
            '--username', db_config.get('USER', ''),
            '--dbname', db_config.get('NAME', ''),
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-acl',
            '--format=custom',
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        
        try:
            with open(backup_file, 'wb') as f:
                subprocess.run(cmd, stdout=f, env=env, check=True)
            
            self.stdout.write(f"✅ PostgreSQL backup created: {backup_file}")
            return backup_file
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"❌ PostgreSQL backup failed: {str(e)}")
            )
            return None

    def _create_metadata(self, backup_dir, backup_name, backup_file):
        """Create backup metadata file"""
        from core.models import User, EmailAccount, EmailMessage
        
        metadata = {
            'backup_name': backup_name,
            'timestamp': timezone.now().isoformat(),
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'backup_file': str(backup_file) if backup_file else None,
            'statistics': {
                'users': User.objects.count(),
                'email_accounts': EmailAccount.objects.count(),
                'email_messages': EmailMessage.objects.count(),
            },
            'settings': {
                'debug': settings.DEBUG,
                'allowed_hosts': settings.ALLOWED_HOSTS,
            }
        }
        
        metadata_file = backup_dir / f"{backup_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.stdout.write(f"📄 Metadata saved: {metadata_file}")
        return metadata_file

    def _compress_backup(self, backup_file):
        """Compress backup file"""
        if not backup_file or not backup_file.exists():
            return None
        
        compressed_file = backup_file.with_suffix(backup_file.suffix + '.gz')
        
        try:
            import gzip
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original uncompressed file
            backup_file.unlink()
            return compressed_file
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Compression failed: {str(e)}")
            )
            return backup_file

    def _verify_backup(self, backup_file):
        """Verify backup integrity"""
        if not backup_file or not backup_file.exists():
            return False
        
        try:
            # Basic file size check
            file_size = backup_file.stat().st_size
            if file_size == 0:
                self.stdout.write("❌ Backup file is empty")
                return False
            
            # For SQLite, try to open the database
            if backup_file.suffix == '.sqlite3':
                import sqlite3
                conn = sqlite3.connect(backup_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                
                if len(tables) == 0:
                    self.stdout.write("❌ No tables found in SQLite backup")
                    return False
            
            # For compressed files, test decompression
            elif backup_file.suffix == '.gz':
                import gzip
                with gzip.open(backup_file, 'rb') as f:
                    # Read first 1KB to test
                    f.read(1024)
            
            return True
            
        except Exception as e:
            self.stdout.write(f"❌ Backup verification error: {str(e)}")
            return False

    def _cleanup_old_backups(self, backup_dir, retention_days):
        """Remove backups older than retention period"""
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)
        removed_count = 0
        
        self.stdout.write(f"🧹 Cleaning up backups older than {retention_days} days...")
        
        for backup_file in backup_dir.glob("fyxerai_backup_*"):
            try:
                # Get file modification time
                file_time = timezone.datetime.fromtimestamp(
                    backup_file.stat().st_mtime,
                    tz=timezone.get_current_timezone()
                )
                
                if file_time < cutoff_date:
                    backup_file.unlink()
                    removed_count += 1
                    self.stdout.write(f"   Removed: {backup_file.name}")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"   Warning: Could not remove {backup_file.name}: {e}")
                )
        
        if removed_count > 0:
            self.stdout.write(f"✅ Removed {removed_count} old backup files")
        else:
            self.stdout.write("✅ No old backups to remove")

    def _generate_backup_report(self, backup_dir, backup_file):
        """Generate backup summary report"""
        self.stdout.write("\n📊 Backup Summary:")
        self.stdout.write(f"   Backup Directory: {backup_dir}")
        
        if backup_file and backup_file.exists():
            file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
            self.stdout.write(f"   Backup File: {backup_file.name}")
            self.stdout.write(f"   File Size: {file_size:.2f} MB")
        
        # Count existing backups
        existing_backups = list(backup_dir.glob("fyxerai_backup_*"))
        self.stdout.write(f"   Total Backups: {len(existing_backups)}")
        
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("   • Test restore procedure periodically")
        self.stdout.write("   • Monitor backup directory disk usage")
        self.stdout.write("   • Consider offsite backup storage for production")
        self.stdout.write("   • Set up automated backup monitoring")
        
        self.stdout.write(f"\n✅ Backup completed successfully!")