import os
import psycopg2
from psycopg2 import pool
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import streamlit as st
import gc

class DatabaseManager:
    _connection_pool = None
    _CHUNK_SIZE = 1000  # Process data in chunks of 1000 rows
    
    def __init__(self):
        self.conn_string = self._build_connection_string()
        self._init_pool()
        self._init_tables()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from secrets"""
        return f"host={st.secrets['POSTGRES_HOST']} " \
               f"port={st.secrets['POSTGRES_PORT']} " \
               f"dbname={st.secrets['POSTGRES_DATABASE']} " \
               f"user={st.secrets['POSTGRES_USER']} " \
               f"password={st.secrets['POSTGRES_PASSWORD']}"
    
    def _init_pool(self):
        """Initialize the connection pool if it doesn't exist"""
        if DatabaseManager._connection_pool is None:
            try:
                DatabaseManager._connection_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=5,  # Reduced max connections to save memory
                    dsn=self.conn_string
                )
                print("Database connection pool initialized")
            except Exception as e:
                print(f"Error initializing connection pool: {str(e)}")
    
    def _get_connection(self):
        """Get a connection from the pool"""
        if DatabaseManager._connection_pool:
            return DatabaseManager._connection_pool.getconn()
        return None
    
    def _return_connection(self, conn):
        """Return a connection to the pool"""
        if DatabaseManager._connection_pool and conn:
            DatabaseManager._connection_pool.putconn(conn)
    
    def _init_tables(self):
        """Initialize database tables if they don't exist"""
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                with conn.cursor() as cur:
                    # Check if tables exist first
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'exchange_balances'
                        );
                    """)
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        try:
                            # Add indexes for better query performance
                            cur.execute("""
                                CREATE TABLE IF NOT EXISTS exchange_balances (
                                    id SERIAL PRIMARY KEY,
                                    exchange VARCHAR(50) NOT NULL,
                                    usdt_balance DECIMAL NOT NULL,
                                    balance_change DECIMAL NOT NULL,
                                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                                
                                CREATE INDEX IF NOT EXISTS idx_exchange_balances_exchange 
                                ON exchange_balances(exchange);
                                
                                CREATE INDEX IF NOT EXISTS idx_exchange_balances_timestamp 
                                ON exchange_balances(timestamp);
                            """)
                            conn.commit()
                        except Exception as e:
                            if "must be owner of table" in str(e):
                                print("Warning: Database tables already exist but user lacks owner permissions")
                                print("The application will continue but some features may be limited")
                            else:
                                print(f"Error creating tables: {str(e)}")
                    else:
                        print("Database tables already exist")
        except Exception as e:
            print(f"Error checking database tables: {str(e)}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def record_balance(self, exchange: str, current_balance: float):
        """Record current USDT balance and calculate change"""
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                with conn.cursor() as cur:
                    # Get the last recorded balance for this exchange
                    cur.execute("""
                        SELECT usdt_balance 
                        FROM exchange_balances 
                        WHERE exchange = %s 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """, (exchange,))
                    
                    last_balance = cur.fetchone()
                    last_balance = float(last_balance[0]) if last_balance else 0
                    balance_change = current_balance - last_balance
                    
                    # Insert new balance record
                    cur.execute("""
                        INSERT INTO exchange_balances 
                        (exchange, usdt_balance, balance_change) 
                        VALUES (%s, %s, %s)
                    """, (exchange, current_balance, balance_change))
                    
                    conn.commit()
        except Exception as e:
            print(f"Error recording balance for {exchange}: {str(e)}")
        finally:
            if conn:
                self._return_connection(conn)
    
    @st.cache_data(ttl=300, max_entries=50)  # Cache for 5 minutes, limit entries
    def get_balance_history(self, exchange: str, days: int = 30) -> pd.DataFrame:
        """Get balance change history for an exchange"""
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                # Use server-side cursor for efficient memory usage
                with conn.cursor('balance_history_cursor') as cur:
                    cur.execute("""
                        SELECT 
                            DATE(timestamp) as date,
                            SUM(balance_change) as realized_pnl
                        FROM exchange_balances 
                        WHERE exchange = %s 
                        AND timestamp >= NOW() - INTERVAL '%s days'
                        GROUP BY DATE(timestamp)
                        ORDER BY date DESC
                    """, (exchange, str(days)))
                    
                    # Fetch data in chunks
                    data = []
                    while True:
                        chunk = cur.fetchmany(self._CHUNK_SIZE)
                        if not chunk:
                            break
                        data.extend(chunk)
                        
                    # Create DataFrame from accumulated data
                    df = pd.DataFrame(data, columns=['date', 'realized_pnl'])
                    return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Error getting balance history for {exchange}: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                self._return_connection(conn)
            gc.collect()  # Force garbage collection after large data processing
    
    @st.cache_data(ttl=60, max_entries=20)  # Cache for 1 minute, limit entries
    def get_latest_balances(self) -> Dict[str, float]:
        """Get latest balance for each exchange"""
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH latest_balance AS (
                            SELECT DISTINCT ON (exchange) 
                                exchange, 
                                usdt_balance,
                                timestamp
                            FROM exchange_balances
                            ORDER BY exchange, timestamp DESC
                        )
                        SELECT exchange, usdt_balance 
                        FROM latest_balance
                    """)
                    return {row[0]: row[1] for row in cur.fetchall()}
            return {}
        except Exception as e:
            print(f"Error getting latest balances: {str(e)}")
            return {}
        finally:
            if conn:
                self._return_connection(conn)
            gc.collect()
    
    def __del__(self):
        """Clean up the connection pool when the instance is destroyed"""
        if DatabaseManager._connection_pool:
            DatabaseManager._connection_pool.closeall()
            DatabaseManager._connection_pool = None
