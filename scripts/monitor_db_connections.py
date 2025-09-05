#!/usr/bin/env python
"""
Database Connection Pool Monitoring Script
Monitors active connections, locks, and replication lag for operational excellence
"""

import os
import sys
import django
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')
django.setup()

from django.db import connections, connection
from django.conf import settings
from django.core.mail import mail_admins


class DatabaseMonitor:
    def __init__(self):
        self.db_alias = 'default'
        self.connection = connections[self.db_alias]
        self.thresholds = {
            'max_connections_percent': 80,  # Alert if >80% of max connections used
            'long_running_query_seconds': 300,  # 5 minutes
            'replication_lag_seconds': 60,  # 1 minute
            'lock_wait_seconds': 30,
        }
        
    def get_database_type(self):
        """Determine database type"""
        engine = self.connection.settings_dict['ENGINE']
        if 'postgresql' in engine:
            return 'postgresql'
        elif 'mysql' in engine:
            return 'mysql'
        elif 'sqlite' in engine:
            return 'sqlite'
        else:
            return 'unknown'
    
    def monitor_postgresql(self):
        """Monitor PostgreSQL specific metrics"""
        metrics = {}
        
        with self.connection.cursor() as cursor:
            # Connection metrics
            cursor.execute("""
                SELECT 
                    count(*) as total_connections,
                    count(CASE WHEN state = 'active' THEN 1 END) as active_connections,
                    count(CASE WHEN state = 'idle' THEN 1 END) as idle_connections,
                    count(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction
                FROM pg_stat_activity
                WHERE pid != pg_backend_pid();
            """)
            conn_stats = cursor.fetchone()
            metrics['connections'] = {
                'total': conn_stats[0],
                'active': conn_stats[1], 
                'idle': conn_stats[2],
                'idle_in_transaction': conn_stats[3]
            }
            
            # Long running queries
            cursor.execute("""
                SELECT 
                    pid,
                    user,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    NOW() - query_start as duration,
                    LEFT(query, 100) as query_snippet
                FROM pg_stat_activity 
                WHERE state = 'active' 
                    AND query_start < NOW() - INTERVAL '%s seconds'
                    AND pid != pg_backend_pid()
                ORDER BY query_start;
            """, [self.thresholds['long_running_query_seconds']])
            
            long_queries = []
            for row in cursor.fetchall():
                long_queries.append({
                    'pid': row[0],
                    'user': row[1],
                    'application': row[2],
                    'client_addr': row[3],
                    'state': row[4],
                    'query_start': row[5],
                    'duration': str(row[6]),
                    'query_snippet': row[7]
                })
            metrics['long_running_queries'] = long_queries
            
            # Lock information
            cursor.execute("""
                SELECT 
                    blocked_locks.pid AS blocked_pid,
                    blocked_activity.usename AS blocked_user,
                    blocking_locks.pid AS blocking_pid,
                    blocking_activity.usename AS blocking_user,
                    blocked_activity.query AS blocked_statement,
                    blocking_activity.query AS blocking_statement
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks 
                    ON blocking_locks.locktype = blocked_locks.locktype
                    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
                    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
                    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
                    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
                    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
                    AND blocking_locks.pid != blocked_locks.pid
                JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted;
            """)
            
            locks = []
            for row in cursor.fetchall():
                locks.append({
                    'blocked_pid': row[0],
                    'blocked_user': row[1],
                    'blocking_pid': row[2],
                    'blocking_user': row[3],
                    'blocked_query': row[4][:100],
                    'blocking_query': row[5][:100]
                })
            metrics['blocked_queries'] = locks
            
            # Database size
            cursor.execute("""
                SELECT 
                    pg_database.datname,
                    pg_size_pretty(pg_database_size(pg_database.datname)) as size
                FROM pg_database
                WHERE datname = current_database();
            """)
            db_size = cursor.fetchone()
            metrics['database_size'] = {
                'name': db_size[0],
                'size': db_size[1]
            }
            
        return metrics
    
    def monitor_sqlite(self):
        """Monitor SQLite metrics (limited)"""
        metrics = {}
        
        with self.connection.cursor() as cursor:
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
            size_bytes = cursor.fetchone()[0]
            metrics['database_size'] = {
                'size_bytes': size_bytes,
                'size_mb': round(size_bytes / (1024 * 1024), 2)
            }
            
            # Basic table info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            metrics['tables'] = len(tables)
            
            # SQLite doesn't have connection pooling or replication
            metrics['connections'] = {'note': 'SQLite uses file-based connections'}
            
        return metrics
    
    def check_replication_status(self):
        """Check replication lag (PostgreSQL only)"""
        if self.get_database_type() != 'postgresql':
            return {'status': 'not_applicable', 'reason': 'Not PostgreSQL'}
        
        try:
            with self.connection.cursor() as cursor:
                # Check if this is a primary or standby server
                cursor.execute("SELECT pg_is_in_recovery();")
                is_standby = cursor.fetchone()[0]
                
                if is_standby:
                    # On standby server, check lag
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() 
                                THEN 0
                                ELSE EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())
                            END AS lag_seconds;
                    """)
                    lag_result = cursor.fetchone()
                    lag_seconds = lag_result[0] if lag_result[0] else 0
                    
                    return {
                        'status': 'standby',
                        'lag_seconds': lag_seconds,
                        'lag_ok': lag_seconds <= self.thresholds['replication_lag_seconds']
                    }
                else:
                    # On primary server, check connected standbys
                    cursor.execute("""
                        SELECT 
                            client_addr,
                            state,
                            sent_lsn,
                            write_lsn,
                            flush_lsn,
                            replay_lsn,
                            write_lag,
                            flush_lag,
                            replay_lag
                        FROM pg_stat_replication;
                    """)
                    
                    replicas = []
                    for row in cursor.fetchall():
                        replicas.append({
                            'client_addr': row[0],
                            'state': row[1],
                            'sent_lsn': row[2],
                            'write_lsn': row[3],
                            'flush_lsn': row[4],
                            'replay_lsn': row[5],
                            'write_lag': str(row[6]) if row[6] else None,
                            'flush_lag': str(row[7]) if row[7] else None,
                            'replay_lag': str(row[8]) if row[8] else None,
                        })
                    
                    return {
                        'status': 'primary',
                        'connected_replicas': len(replicas),
                        'replicas': replicas
                    }
                    
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def generate_alerts(self, metrics):
        """Generate alerts based on thresholds"""
        alerts = []
        
        if 'connections' in metrics and isinstance(metrics['connections'], dict):
            total_conn = metrics['connections'].get('total', 0)
            active_conn = metrics['connections'].get('active', 0)
            
            # Check connection usage (assuming max_connections of 100 for example)
            max_connections = 100  # This should be read from DB config
            if total_conn > (max_connections * self.thresholds['max_connections_percent'] / 100):
                alerts.append({
                    'severity': 'HIGH',
                    'type': 'connection_limit',
                    'message': f'High connection usage: {total_conn}/{max_connections} ({total_conn/max_connections*100:.1f}%)'
                })
        
        # Check long running queries
        if metrics.get('long_running_queries'):
            for query in metrics['long_running_queries']:
                alerts.append({
                    'severity': 'MEDIUM',
                    'type': 'long_running_query',
                    'message': f'Long running query: PID {query["pid"]}, Duration: {query["duration"]}'
                })
        
        # Check blocked queries
        if metrics.get('blocked_queries'):
            for lock in metrics['blocked_queries']:
                alerts.append({
                    'severity': 'HIGH',
                    'type': 'blocked_query',
                    'message': f'Blocked query: PID {lock["blocked_pid"]} blocked by PID {lock["blocking_pid"]}'
                })
        
        return alerts
    
    def run_monitoring(self):
        """Main monitoring function"""
        print(f"=== Database Monitoring Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        
        db_type = self.get_database_type()
        print(f"Database Type: {db_type.upper()}")
        
        # Get metrics based on database type
        if db_type == 'postgresql':
            metrics = self.monitor_postgresql()
        elif db_type == 'sqlite':
            metrics = self.monitor_sqlite()
        else:
            print(f"Monitoring not implemented for {db_type}")
            return
        
        # Print connection metrics
        if 'connections' in metrics:
            print("\n📊 Connection Status:")
            if isinstance(metrics['connections'], dict) and 'total' in metrics['connections']:
                conn = metrics['connections']
                print(f"   Total: {conn['total']}")
                print(f"   Active: {conn['active']}")
                print(f"   Idle: {conn['idle']}")
                print(f"   Idle in Transaction: {conn['idle_in_transaction']}")
            else:
                print(f"   {metrics['connections']}")
        
        # Print database size
        if 'database_size' in metrics:
            print(f"\n💾 Database Size:")
            if 'size' in metrics['database_size']:
                print(f"   {metrics['database_size']['name']}: {metrics['database_size']['size']}")
            elif 'size_mb' in metrics['database_size']:
                print(f"   Size: {metrics['database_size']['size_mb']} MB")
        
        # Check replication status
        replication = self.check_replication_status()
        print(f"\n🔄 Replication Status: {replication['status'].upper()}")
        if replication['status'] == 'standby':
            print(f"   Lag: {replication.get('lag_seconds', 0)} seconds")
        elif replication['status'] == 'primary':
            print(f"   Connected Replicas: {replication.get('connected_replicas', 0)}")
        
        # Generate and display alerts
        alerts = self.generate_alerts(metrics)
        if alerts:
            print(f"\n🚨 Alerts ({len(alerts)}):")
            for alert in alerts:
                print(f"   {alert['severity']}: {alert['message']}")
        else:
            print(f"\n✅ No alerts - system healthy")
        
        # Save metrics to file for monitoring systems
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metrics_file = f"db_metrics_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'database_type': db_type,
            'metrics': metrics,
            'replication': replication,
            'alerts': alerts
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Metrics saved to: {metrics_file}")
        
        return report_data


def main():
    monitor = DatabaseMonitor()
    return monitor.run_monitoring()


if __name__ == '__main__':
    main()