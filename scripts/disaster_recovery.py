#!/usr/bin/env python
"""
Disaster Recovery Automation Script
Provides RTO/RPO compliance and automated recovery procedures
"""

import os
import sys
import django
import json
import subprocess
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')
django.setup()

from django.core.management import call_command
from django.db import connection, connections
from django.conf import settings
from django.utils import timezone


class DisasterRecovery:
    def __init__(self):
        self.backup_dir = Path('./backups')
        self.recovery_log = []
        self.rto_target = 30  # Recovery Time Objective: 30 minutes
        self.rpo_target = 15  # Recovery Point Objective: 15 minutes
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
        
    def log_action(self, action, status='SUCCESS', details=''):
        """Log recovery actions with timestamp"""
        timestamp = datetime.now()
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'action': action,
            'status': status,
            'details': details
        }
        self.recovery_log.append(log_entry)
        print(f"[{timestamp.strftime('%H:%M:%S')}] {status}: {action}")
        if details:
            print(f"    Details: {details}")
    
    def check_system_health(self):
        """Comprehensive system health check"""
        print("=== System Health Check ===")
        health_status = {
            'database': False,
            'redis': False,
            'storage': False,
            'external_apis': False
        }
        
        # Database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['database'] = True
                self.log_action("Database connection test", "SUCCESS")
        except Exception as e:
            self.log_action("Database connection test", "FAILED", str(e))
        
        # Redis connectivity (if configured)
        try:
            if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
                import redis
                r = redis.from_url(settings.REDIS_URL)
                r.ping()
                health_status['redis'] = True
                self.log_action("Redis connection test", "SUCCESS")
        except Exception as e:
            self.log_action("Redis connection test", "FAILED", str(e))
        
        # Storage accessibility
        try:
            test_file = self.backup_dir / 'health_check.tmp'
            test_file.write_text('test')
            test_file.unlink()
            health_status['storage'] = True
            self.log_action("Storage access test", "SUCCESS")
        except Exception as e:
            self.log_action("Storage access test", "FAILED", str(e))
        
        return health_status
    
    def create_emergency_backup(self):
        """Create emergency backup before recovery"""
        print("\n=== Creating Emergency Backup ===")
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"emergency_backup_{timestamp}"
            
            # Use Django management command for backup
            call_command('backup_database', 
                        f'--backup-dir={self.backup_dir}',
                        '--compress')
            
            self.log_action("Emergency backup created", "SUCCESS", backup_name)
            return True
            
        except Exception as e:
            self.log_action("Emergency backup creation", "FAILED", str(e))
            return False
    
    def find_latest_backup(self):
        """Find the latest valid backup"""
        print("\n=== Locating Latest Backup ===")
        
        backup_files = list(self.backup_dir.glob("fyxerai_backup_*"))
        if not backup_files:
            self.log_action("Backup search", "FAILED", "No backups found")
            return None
        
        # Sort by modification time, newest first
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        latest_backup = backup_files[0]
        backup_age = datetime.now() - datetime.fromtimestamp(latest_backup.stat().st_mtime)
        
        self.log_action("Latest backup found", "SUCCESS", 
                       f"{latest_backup.name}, Age: {backup_age}")
        
        # Check if backup meets RPO requirement
        if backup_age > timedelta(minutes=self.rpo_target):
            self.log_action("RPO Compliance Check", "WARNING", 
                           f"Backup is {backup_age} old, exceeds RPO of {self.rpo_target} minutes")
        
        return latest_backup
    
    def restore_database(self, backup_file):
        """Restore database from backup"""
        print(f"\n=== Restoring Database from {backup_file.name} ===")
        
        try:
            db_config = settings.DATABASES['default']
            db_engine = db_config['ENGINE']
            
            if 'sqlite' in db_engine:
                return self._restore_sqlite(backup_file, db_config)
            elif 'postgresql' in db_engine:
                return self._restore_postgresql(backup_file, db_config)
            else:
                self.log_action("Database restore", "FAILED", f"Unsupported engine: {db_engine}")
                return False
                
        except Exception as e:
            self.log_action("Database restore", "FAILED", str(e))
            return False
    
    def _restore_sqlite(self, backup_file, db_config):
        """Restore SQLite database"""
        db_path = Path(db_config['NAME'])
        
        # Backup current database
        if db_path.exists():
            backup_current = db_path.with_suffix('.sqlite3.backup')
            shutil.copy2(db_path, backup_current)
            self.log_action("Current database backed up", "SUCCESS", str(backup_current))
        
        # Restore from backup
        if backup_file.suffix == '.gz':
            # Decompress first
            import gzip
            with gzip.open(backup_file, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_file, db_path)
        
        self.log_action("SQLite database restored", "SUCCESS")
        return True
    
    def _restore_postgresql(self, backup_file, db_config):
        """Restore PostgreSQL database"""
        # Build pg_restore command
        cmd = [
            'pg_restore',
            '--host', db_config.get('HOST', 'localhost'),
            '--port', str(db_config.get('PORT', 5432)),
            '--username', db_config.get('USER', ''),
            '--dbname', db_config.get('NAME', ''),
            '--verbose',
            '--clean',
            '--if-exists',
            str(backup_file)
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log_action("PostgreSQL database restored", "SUCCESS")
            return True
        else:
            self.log_action("PostgreSQL restore", "FAILED", result.stderr)
            return False
    
    def verify_data_integrity(self):
        """Verify restored data integrity"""
        print("\n=== Verifying Data Integrity ===")
        
        try:
            from core.models import User, EmailAccount, EmailMessage
            
            # Basic count checks
            user_count = User.objects.count()
            account_count = EmailAccount.objects.count()
            message_count = EmailMessage.objects.count()
            
            self.log_action("Data integrity check", "SUCCESS", 
                           f"Users: {user_count}, Accounts: {account_count}, Messages: {message_count}")
            
            # Check for orphaned records
            orphaned_messages = EmailMessage.objects.filter(account__isnull=True).count()
            if orphaned_messages > 0:
                self.log_action("Orphaned messages found", "WARNING", f"{orphaned_messages} orphaned messages")
            
            # Test basic queries
            latest_user = User.objects.first()
            if latest_user:
                self.log_action("Query test", "SUCCESS", f"Latest user: {latest_user.username}")
            
            return True
            
        except Exception as e:
            self.log_action("Data integrity check", "FAILED", str(e))
            return False
    
    def restart_services(self):
        """Restart application services"""
        print("\n=== Restarting Services ===")
        
        services_restarted = []
        
        # Clear Django cache
        try:
            from django.core.cache import cache
            cache.clear()
            self.log_action("Cache cleared", "SUCCESS")
            services_restarted.append("cache")
        except Exception as e:
            self.log_action("Cache clear", "FAILED", str(e))
        
        # Restart Celery workers (if running)
        try:
            # This would need to be customized based on deployment
            # subprocess.run(['supervisorctl', 'restart', 'celery'], check=True)
            self.log_action("Celery restart", "SKIPPED", "Manual restart required")
        except Exception as e:
            self.log_action("Celery restart", "FAILED", str(e))
        
        return services_restarted
    
    def run_full_recovery(self):
        """Execute complete disaster recovery procedure"""
        recovery_start = datetime.now()
        print(f"=== DISASTER RECOVERY STARTED at {recovery_start.strftime('%Y-%m-%d %H:%M:%S')} ===")
        print(f"RTO Target: {self.rto_target} minutes")
        print(f"RPO Target: {self.rpo_target} minutes")
        
        # Step 1: Health check
        health = self.check_system_health()
        
        # Step 2: Emergency backup
        if not self.create_emergency_backup():
            print("WARNING: Emergency backup failed, proceeding anyway...")
        
        # Step 3: Find latest backup
        backup_file = self.find_latest_backup()
        if not backup_file:
            self.log_action("Recovery", "FAILED", "No backup file available")
            return False
        
        # Step 4: Restore database
        if not self.restore_database(backup_file):
            self.log_action("Recovery", "FAILED", "Database restoration failed")
            return False
        
        # Step 5: Verify data integrity
        if not self.verify_data_integrity():
            self.log_action("Recovery", "FAILED", "Data integrity check failed")
            return False
        
        # Step 6: Restart services
        self.restart_services()
        
        # Step 7: Final health check
        final_health = self.check_system_health()
        
        recovery_end = datetime.now()
        recovery_time = recovery_end - recovery_start
        
        # Generate recovery report
        self.generate_recovery_report(recovery_start, recovery_end, recovery_time, final_health)
        
        # Check RTO compliance
        if recovery_time > timedelta(minutes=self.rto_target):
            self.log_action("RTO Compliance", "FAILED", 
                           f"Recovery took {recovery_time}, exceeds RTO of {self.rto_target} minutes")
        else:
            self.log_action("RTO Compliance", "SUCCESS", 
                           f"Recovery completed in {recovery_time}")
        
        print(f"\n=== DISASTER RECOVERY COMPLETED in {recovery_time} ===")
        return True
    
    def generate_recovery_report(self, start_time, end_time, duration, health_status):
        """Generate detailed recovery report"""
        report = {
            'recovery_start': start_time.isoformat(),
            'recovery_end': end_time.isoformat(),
            'recovery_duration': str(duration),
            'rto_target_minutes': self.rto_target,
            'rpo_target_minutes': self.rpo_target,
            'rto_compliance': duration <= timedelta(minutes=self.rto_target),
            'final_health_status': health_status,
            'recovery_log': self.recovery_log,
            'recommendations': self._generate_recommendations(duration, health_status)
        }
        
        # Save report
        report_file = f"recovery_report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Recovery report saved: {report_file}")
        
        # Print summary
        print("\n📊 Recovery Summary:")
        print(f"   Duration: {duration}")
        print(f"   RTO Compliance: {'✅ PASS' if report['rto_compliance'] else '❌ FAIL'}")
        print(f"   Final Health: {sum(health_status.values())}/{len(health_status)} systems healthy")
    
    def _generate_recommendations(self, duration, health_status):
        """Generate recommendations for improving recovery"""
        recommendations = []
        
        if duration > timedelta(minutes=self.rto_target):
            recommendations.append("Consider implementing hot standby for faster recovery")
            recommendations.append("Optimize backup/restore procedures")
        
        if not health_status.get('redis', True):
            recommendations.append("Set up Redis clustering for high availability")
        
        if not health_status.get('database', False):
            recommendations.append("CRITICAL: Database connectivity issues require immediate attention")
        
        recommendations.append("Test disaster recovery procedures regularly")
        recommendations.append("Consider implementing automated failover")
        
        return recommendations
    
    def test_recovery_procedures(self):
        """Test recovery procedures without actual restoration"""
        print("=== DISASTER RECOVERY TEST MODE ===")
        
        # Simulate recovery steps
        health = self.check_system_health()
        backup_file = self.find_latest_backup()
        
        print(f"\n✅ Recovery test completed")
        print(f"   Latest backup: {backup_file.name if backup_file else 'None found'}")
        print(f"   System health: {sum(health.values())}/{len(health)} systems healthy")
        
        return backup_file is not None and all(health.values())


def main():
    dr = DisasterRecovery()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return dr.test_recovery_procedures()
    elif len(sys.argv) > 1 and sys.argv[1] == 'health':
        return dr.check_system_health()
    else:
        return dr.run_full_recovery()


if __name__ == '__main__':
    main()