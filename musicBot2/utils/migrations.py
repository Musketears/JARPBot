"""
Database migrations system for musicBot2.

This module provides a simple migration system to manage database schema changes.
Migrations are stored as numbered SQL files in the migrations/ directory.
"""

import os
import sqlite3
import logging
from typing import List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_path: str = "bot_data.db", migrations_dir: str = "migrations"):
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self._ensure_migrations_table()
        self._ensure_migrations_dir()
    
    def _ensure_migrations_dir(self):
        """Ensure the migrations directory exists"""
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            logger.info(f"Created migrations directory: {self.migrations_dir}")
    
    def _ensure_migrations_table(self):
        """Ensure the schema_version table exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def get_current_version(self) -> int:
        """Get the current schema version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
    
    def get_applied_migrations(self) -> List[Tuple[int, str, str]]:
        """Get list of applied migrations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT version, name, applied_at FROM schema_version ORDER BY version"
            )
            return cursor.fetchall()
    
    def get_pending_migrations(self) -> List[Tuple[int, str, str]]:
        """Get list of pending migrations"""
        current_version = self.get_current_version()
        pending = []
        
        # Get all migration files
        if not os.path.exists(self.migrations_dir):
            return pending
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.sql'):
                # Parse version number from filename (e.g., "001_initial_schema.sql")
                try:
                    version = int(filename.split('_')[0])
                    if version > current_version:
                        filepath = os.path.join(self.migrations_dir, filename)
                        pending.append((version, filename, filepath))
                except (ValueError, IndexError):
                    logger.warning(f"Skipping invalid migration filename: {filename}")
        
        return pending
    
    def apply_migration(self, version: int, name: str, filepath: str) -> bool:
        """Apply a single migration"""
        try:
            # Read the migration SQL
            with open(filepath, 'r') as f:
                sql = f.read()
            
            # Apply the migration within a transaction
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    # Execute the migration SQL
                    conn.executescript(sql)
                    
                    # Record the migration
                    conn.execute(
                        "INSERT INTO schema_version (version, name) VALUES (?, ?)",
                        (version, name)
                    )
                    
                    conn.commit()
                    logger.info(f"Applied migration {version}: {name}")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to apply migration {version}: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error reading migration file {filepath}: {e}")
            return False
    
    def run_pending_migrations(self) -> Tuple[int, int]:
        """
        Run all pending migrations.
        Returns tuple of (applied_count, failed_count)
        """
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations to apply")
            return 0, 0
        
        logger.info(f"Found {len(pending)} pending migrations")
        
        applied = 0
        failed = 0
        
        for version, name, filepath in pending:
            try:
                if self.apply_migration(version, name, filepath):
                    applied += 1
                else:
                    failed += 1
                    break  # Stop on first failure
            except Exception as e:
                logger.error(f"Migration {version} failed: {e}")
                failed += 1
                break  # Stop on first failure
        
        return applied, failed
    
    def create_migration(self, name: str, sql: str = "") -> str:
        """
        Create a new migration file.
        Returns the path to the created file.
        """
        # Get next version number
        current = self.get_current_version()
        pending = self.get_pending_migrations()
        
        if pending:
            next_version = max(m[0] for m in pending) + 1
        else:
            next_version = current + 1
        
        # Create filename
        safe_name = name.lower().replace(' ', '_').replace('-', '_')
        filename = f"{next_version:03d}_{safe_name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)
        
        # Create the file
        with open(filepath, 'w') as f:
            f.write(f"-- Migration {next_version}: {name}\n")
            f.write(f"-- Created at: {datetime.now().isoformat()}\n\n")
            if sql:
                f.write(sql)
            else:
                f.write("-- Add your SQL statements here\n")
        
        logger.info(f"Created migration file: {filepath}")
        return filepath


# Global migration manager instance
migration_manager = MigrationManager()


def run_migrations():
    """Convenience function to run pending migrations"""
    applied, failed = migration_manager.run_pending_migrations()
    return applied, failed
