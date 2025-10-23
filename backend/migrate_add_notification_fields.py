"""
Migration script to add notification tracking fields to sites table.

This script adds the last_notified_at and last_notified_status fields
to track when we last sent notifications to prevent spam.
Run this once after updating the models to add the new columns.
"""
import sqlite3
import os

def migrate():
    # Get database path
    db_path = os.environ.get("DATABASE_URL", "sqlite:///./status_dashboard.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")

    # Check if running in Docker
    if os.path.exists("/data/status_dashboard.db"):
        db_path = "/data/status_dashboard.db"

    print(f"Migrating database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(sites)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'last_notified_at' in columns:
            print("✓ Column 'last_notified_at' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE sites
                ADD COLUMN last_notified_at TIMESTAMP
            """)
            conn.commit()
            print("✓ Added column 'last_notified_at' to sites table")

        if 'last_notified_status' in columns:
            print("✓ Column 'last_notified_status' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE sites
                ADD COLUMN last_notified_status TEXT
            """)
            conn.commit()
            print("✓ Added column 'last_notified_status' to sites table")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
