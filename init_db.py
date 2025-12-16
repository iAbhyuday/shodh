from src.db.sql_db import init_db

if __name__ == "__main__":
    print("Initializing database with new schema...")
    init_db()
    print("Database initialized successfully!")
