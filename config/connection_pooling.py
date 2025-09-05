"""
Database Connection Pooling Configuration
Optimized settings for production PostgreSQL and development SQLite
"""

import os
from django.conf import settings


def get_connection_pool_settings():
    """
    Get database connection pool settings based on environment
    """
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'postgresql' in db_engine:
        return get_postgresql_pool_config()
    elif 'mysql' in db_engine:
        return get_mysql_pool_config()
    else:
        return get_default_pool_config()


def get_postgresql_pool_config():
    """
    PostgreSQL connection pooling configuration
    Optimized for production workloads with proper resource management
    """
    return {
        # Connection pool settings
        'CONN_MAX_AGE': 300,  # 5 minutes - keep connections alive
        'CONN_HEALTH_CHECKS': True,  # Enable connection health checks
        
        # Connection limits per process
        'OPTIONS': {
            'MAX_CONNS': int(os.environ.get('DB_MAX_CONNS', '20')),  # Max connections per worker
            'MIN_CONNS': int(os.environ.get('DB_MIN_CONNS', '5')),   # Min connections to maintain
            
            # Connection pool timeouts
            'connect_timeout': 30,  # Connection timeout
            'read_timeout': 60,     # Query timeout
            'write_timeout': 60,    # Write timeout
            
            # Connection pool behavior
            'pool_reset_session_on_return': True,
            'pool_recycle': 3600,   # Recycle connections every hour
            'pool_pre_ping': True,  # Test connections before use
        },
        
        # Production monitoring
        'monitoring': {
            'log_slow_queries': True,
            'slow_query_threshold': 1.0,  # Log queries > 1 second
            'log_connections': bool(os.environ.get('LOG_DB_CONNECTIONS', 'False')),
        }
    }


def get_mysql_pool_config():
    """
    MySQL connection pooling configuration
    """
    return {
        'CONN_MAX_AGE': 300,
        'CONN_HEALTH_CHECKS': True,
        
        'OPTIONS': {
            'MAX_CONNS': int(os.environ.get('DB_MAX_CONNS', '15')),
            'MIN_CONNS': int(os.environ.get('DB_MIN_CONNS', '3')),
            
            # MySQL specific
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES',
            'isolation_level': 'read committed',
            
            # Connection timeouts
            'connect_timeout': 30,
            'read_timeout': 60,
            'write_timeout': 60,
        }
    }


def get_default_pool_config():
    """
    Default configuration for SQLite and other databases
    """
    return {
        'CONN_MAX_AGE': 60,  # Shorter for SQLite
        'CONN_HEALTH_CHECKS': False,  # Not needed for SQLite
        
        'OPTIONS': {
            'timeout': 30,  # SQLite lock timeout
            'check_same_thread': False,  # Allow multi-threading
        }
    }


def apply_connection_pooling(databases_config):
    """
    Apply connection pooling settings to Django DATABASES configuration
    
    Usage in settings.py:
        from config.connection_pooling import apply_connection_pooling
        DATABASES = apply_connection_pooling(DATABASES)
    """
    if not databases_config:
        return databases_config
    
    pool_config = get_connection_pool_settings()
    
    for db_name, db_config in databases_config.items():
        # Apply connection pooling settings
        db_config.update({
            'CONN_MAX_AGE': pool_config.get('CONN_MAX_AGE', 60),
            'CONN_HEALTH_CHECKS': pool_config.get('CONN_HEALTH_CHECKS', False),
        })
        
        # Merge OPTIONS
        if 'OPTIONS' not in db_config:
            db_config['OPTIONS'] = {}
        
        db_config['OPTIONS'].update(pool_config.get('OPTIONS', {}))
    
    return databases_config


# Connection Pool Monitoring Queries
MONITORING_QUERIES = {
    'postgresql': {
        'active_connections': """
            SELECT count(*) as active_connections
            FROM pg_stat_activity 
            WHERE state = 'active' AND pid != pg_backend_pid();
        """,
        
        'connection_states': """
            SELECT state, count(*) as count
            FROM pg_stat_activity 
            WHERE pid != pg_backend_pid()
            GROUP BY state
            ORDER BY count DESC;
        """,
        
        'long_running_queries': """
            SELECT 
                pid,
                user,
                client_addr,
                application_name,
                state,
                NOW() - query_start as duration,
                LEFT(query, 100) as query_snippet
            FROM pg_stat_activity 
            WHERE state = 'active' 
                AND query_start < NOW() - INTERVAL '5 minutes'
                AND pid != pg_backend_pid()
            ORDER BY query_start;
        """,
        
        'blocking_queries': """
            SELECT 
                blocked_activity.pid AS blocked_pid,
                blocked_activity.usename AS blocked_user,
                blocking_activity.pid AS blocking_pid,
                blocking_activity.usename AS blocking_user,
                blocked_activity.query AS blocked_statement,
                blocking_activity.query AS blocking_statement,
                NOW() - blocked_activity.query_start AS blocked_duration
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
        """,
        
        'database_stats': """
            SELECT 
                datname as database_name,
                numbackends as connections,
                xact_commit as commits,
                xact_rollback as rollbacks,
                blks_read as disk_reads,
                blks_hit as buffer_hits,
                temp_files as temp_files,
                temp_bytes as temp_bytes,
                deadlocks,
                stats_reset as stats_reset_time
            FROM pg_stat_database 
            WHERE datname = current_database();
        """
    },
    
    'mysql': {
        'active_connections': "SELECT count(*) as active_connections FROM information_schema.processlist WHERE command != 'Sleep';",
        
        'connection_states': """
            SELECT command as state, count(*) as count
            FROM information_schema.processlist 
            GROUP BY command
            ORDER BY count DESC;
        """,
        
        'long_running_queries': """
            SELECT 
                id as pid,
                user,
                host as client_addr,
                db as database_name,
                command as state,
                time as duration_seconds,
                LEFT(info, 100) as query_snippet
            FROM information_schema.processlist 
            WHERE command != 'Sleep' 
                AND time > 300
            ORDER BY time DESC;
        """
    }
}


def get_monitoring_query(query_name, db_type='postgresql'):
    """
    Get monitoring query for specific database type
    """
    return MONITORING_QUERIES.get(db_type, {}).get(query_name, None)


# Alerting thresholds
ALERT_THRESHOLDS = {
    'max_connections_percent': 80,  # Alert when > 80% of max connections used
    'long_running_query_minutes': 5,  # Alert for queries running > 5 minutes
    'blocked_query_minutes': 2,  # Alert for queries blocked > 2 minutes
    'high_temp_files_mb': 100,  # Alert when temp files > 100MB
    'high_rollback_ratio': 0.1,  # Alert when rollback ratio > 10%
}


def check_connection_health(db_alias='default'):
    """
    Check connection pool health and return status
    
    Returns:
        dict: Health status with metrics and alerts
    """
    from django.db import connections
    
    connection = connections[db_alias]
    db_engine = connection.settings_dict['ENGINE']
    
    health_status = {
        'healthy': True,
        'alerts': [],
        'metrics': {},
        'recommendations': []
    }
    
    try:
        with connection.cursor() as cursor:
            if 'postgresql' in db_engine:
                # Check active connections
                cursor.execute(get_monitoring_query('active_connections', 'postgresql'))
                active_conns = cursor.fetchone()[0]
                health_status['metrics']['active_connections'] = active_conns
                
                # Check for long running queries
                cursor.execute(get_monitoring_query('long_running_queries', 'postgresql'))
                long_queries = cursor.fetchall()
                
                if long_queries:
                    health_status['alerts'].append({
                        'type': 'long_running_queries',
                        'severity': 'WARNING',
                        'count': len(long_queries),
                        'message': f'{len(long_queries)} queries running longer than 5 minutes'
                    })
                
                # Check for blocking queries
                cursor.execute(get_monitoring_query('blocking_queries', 'postgresql'))
                blocked_queries = cursor.fetchall()
                
                if blocked_queries:
                    health_status['healthy'] = False
                    health_status['alerts'].append({
                        'type': 'blocked_queries',
                        'severity': 'CRITICAL',
                        'count': len(blocked_queries),
                        'message': f'{len(blocked_queries)} queries are blocked'
                    })
            
            elif 'sqlite' in db_engine:
                # SQLite specific health checks
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                if result[0] != 'ok':
                    health_status['healthy'] = False
                    health_status['alerts'].append({
                        'type': 'integrity_check',
                        'severity': 'CRITICAL',
                        'message': f'SQLite integrity check failed: {result[0]}'
                    })
    
    except Exception as e:
        health_status['healthy'] = False
        health_status['alerts'].append({
            'type': 'connection_error',
            'severity': 'CRITICAL',
            'message': f'Database connection failed: {str(e)}'
        })
    
    # Generate recommendations
    if not health_status['alerts']:
        health_status['recommendations'].append('Connection pool is healthy')
    else:
        health_status['recommendations'].extend([
            'Monitor connection pool metrics regularly',
            'Consider implementing connection pooling middleware',
            'Set up automated alerting for database issues'
        ])
    
    return health_status