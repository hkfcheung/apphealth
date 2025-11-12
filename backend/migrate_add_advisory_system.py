"""
Migration script to add advisory analysis and LLM system tables.

This creates:
- site_modules: Track which modules/packages user cares about per site
- advisories: Store and analyze service advisories
- chat_messages: Admin chat history for querying data
- Updates app_settings with LLM configuration fields
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

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create site_modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id TEXT NOT NULL,
                module_name TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_site_modules_site_id ON site_modules(site_id)")
        print("✓ Created site_modules table")

        # Create advisories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advisories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT,
                criticality TEXT DEFAULT 'unknown',
                affects_us BOOLEAN DEFAULT 0,
                affected_modules TEXT DEFAULT '[]',
                relevance_reason TEXT,
                is_informational BOOLEAN DEFAULT 0,
                source_url TEXT,
                published_at TIMESTAMP,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_advisories_site_id ON advisories(site_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_advisories_created_at ON advisories(created_at)")
        print("✓ Created advisories table")

        # Create chat_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)")
        print("✓ Created chat_messages table")

        # Update app_settings with LLM fields
        cursor.execute("PRAGMA table_info(app_settings)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'llm_provider' not in columns:
            cursor.execute("ALTER TABLE app_settings ADD COLUMN llm_provider TEXT")
            print("✓ Added llm_provider to app_settings")

        if 'llm_api_key' not in columns:
            cursor.execute("ALTER TABLE app_settings ADD COLUMN llm_api_key TEXT")
            print("✓ Added llm_api_key to app_settings")

        if 'llm_model' not in columns:
            cursor.execute("ALTER TABLE app_settings ADD COLUMN llm_model TEXT")
            print("✓ Added llm_model to app_settings")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
