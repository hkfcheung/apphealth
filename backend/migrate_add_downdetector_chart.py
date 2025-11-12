"""
Migration script to add downdetector_chart column to readings table.

This script adds the downdetector_chart field to existing Reading records.
Run this once after updating the models to add the new column.
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
        # Check if column already exists
        cursor.execute("PRAGMA table_info(readings)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'downdetector_chart' in columns:
            print("✓ Column 'downdetector_chart' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE readings
                ADD COLUMN downdetector_chart TEXT
            """)
            conn.commit()
            print("✓ Added column 'downdetector_chart' to readings table")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
