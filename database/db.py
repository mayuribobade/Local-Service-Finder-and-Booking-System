import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DATABASE = Path(__file__).resolve().parent.parent / "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('customer','provider','admin')), phone TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, description TEXT, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS service_providers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, category_id INTEGER, service TEXT NOT NULL, experience TEXT, location TEXT, charges TEXT, rating REAL DEFAULT 0, description TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, provider_id INTEGER NOT NULL, service_date TEXT NOT NULL, preferred_time TEXT NOT NULL, address TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Accepted','Rejected','In Progress','Completed','Cancelled')), created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(provider_id) REFERENCES service_providers(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER UNIQUE NOT NULL, customer_id INTEGER NOT NULL, provider_id INTEGER NOT NULL, rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), comment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE, FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(provider_id) REFERENCES service_providers(id) ON DELETE CASCADE);
    """)
    # Lightweight migration for the original starter database.
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "phone" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "created_at" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
    provider_columns = {
        r["name"]
        for r in conn.execute("PRAGMA table_info(service_providers)").fetchall()
    }
    if "category_id" not in provider_columns:
        conn.execute("ALTER TABLE service_providers ADD COLUMN category_id INTEGER")
    conn.commit()
    conn.close()


def seed_data():
    conn = get_db_connection()
    categories = [
        ("Electrician", "Electrical repairs, installation and maintenance"),
        ("Plumber", "Plumbing repairs, fittings and maintenance"),
        ("Home Cleaning", "Cleaning for homes and apartments"),
        ("AC Repair", "AC servicing, maintenance and repair"),
        ("Carpenter", "Furniture repairs and carpentry work"),
    ]
    for name, description in categories:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
            (name, description),
        )
    if not conn.execute(
        "SELECT id FROM users WHERE email=?", ("admin@localfinder.com",)
    ).fetchone():
        conn.execute(
            "INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,?,?)",
            (
                "System Administrator",
                "admin@localfinder.com",
                generate_password_hash("admin123"),
                "admin",
                "",
            ),
        )
    providers = [
        (
            "Rahul Electricals",
            "rahul.demo@example.com",
            "Electrician",
            "5 Years",
            "Andheri",
            "₹300 onwards",
            4.5,
            "Electrical repair and installation services.",
        ),
        (
            "Ajay Electrical Works",
            "ajay.demo@example.com",
            "Electrician",
            "3 Years",
            "Vikhroli",
            "₹250 onwards",
            4.2,
            "Home electrical repair and maintenance services.",
        ),
        (
            "Rohit Plumbing Services",
            "rohit.demo@example.com",
            "Plumber",
            "4 Years",
            "Powai",
            "₹300 onwards",
            4.4,
            "Plumbing repair and installation services.",
        ),
        (
            "Sneha Home Cleaning",
            "sneha.demo@example.com",
            "Home Cleaning",
            "3 Years",
            "Khar",
            "₹500 onwards",
            4.6,
            "Professional home cleaning services.",
        ),
        (
            "Rohan AC Care",
            "rohan.demo@example.com",
            "AC Repair",
            "6 Years",
            "Bandra",
            "₹400 onwards",
            4.7,
            "AC servicing and repair services.",
        ),
        (
            "Amit Carpenter Services",
            "amit.demo@example.com",
            "Carpenter",
            "5 Years",
            "Ghatkopar",
            "₹350 onwards",
            4.3,
            "Furniture repair and carpentry services.",
        ),
    ]
    for (
        name,
        email,
        service,
        experience,
        location,
        charges,
        rating,
        description,
    ) in providers:
        user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            user_id = conn.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash("demo123"), "provider"),
            ).lastrowid
        else:
            user_id = user["id"]
        category = conn.execute(
            "SELECT id FROM categories WHERE name=?", (service,)
        ).fetchone()
        if not conn.execute(
            "SELECT id FROM service_providers WHERE user_id=? AND service=?",
            (user_id, service),
        ).fetchone():
            conn.execute(
                "INSERT INTO service_providers (user_id,category_id,service,experience,location,charges,rating,description) VALUES (?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    category["id"],
                    service,
                    experience,
                    location,
                    charges,
                    rating,
                    description,
                ),
            )
    conn.commit()
    conn.close()
