"""
Migration script to add downdetector screenshot fields to sites table.

This script adds the latest_downdetector_screenshot and downdetector_screenshot_uploaded_at
fields to existing Site records.
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

        if 'latest_downdetector_screenshot' in columns:
            print("✓ Column 'latest_downdetector_screenshot' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE sites
                ADD COLUMN latest_downdetector_screenshot TEXT
            """)
            conn.commit()
            print("✓ Added column 'latest_downdetector_screenshot' to sites table")

        if 'downdetector_screenshot_uploaded_at' in columns:
            print("✓ Column 'downdetector_screenshot_uploaded_at' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE sites
                ADD COLUMN downdetector_screenshot_uploaded_at TIMESTAMP
            """)
            conn.commit()
            print("✓ Added column 'downdetector_screenshot_uploaded_at' to sites table")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
