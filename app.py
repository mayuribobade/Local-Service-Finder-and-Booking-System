import os
from functools import wraps
from datetime import date
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import create_tables, get_db_connection, seed_data

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.jinja_env.globals["today"] = date.today().isoformat()
create_tables()
seed_data()


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You are not authorized to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@app.context_processor
def inject_user():
    return {
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("name"),
            "role": session.get("role"),
        }
    }


@app.route("/")
def home():
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT * FROM categories WHERE active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("index.html", categories=categories)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email, password, role = (
            request.form["name"].strip(),
            request.form["email"].strip().lower(),
            request.form["password"],
            request.form["role"],
        )
        if role not in ("customer", "provider") or len(password) < 6:
            flash(
                "Choose a valid role and a password of at least 6 characters.", "danger"
            )
            return redirect(url_for("register"))
        conn = get_db_connection()
        try:
            user_id = conn.execute(
                "INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,?,?)",
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    request.form.get("phone", "").strip(),
                ),
            ).lastrowid
            conn.commit()
            session.update(user_id=user_id, name=name, role=role)
            flash("Your account has been created.", "success")
            return redirect(url_for("dashboard"))
        except Exception:
            flash("An account with that email already exists.", "danger")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form["email"].strip().lower(),),
        ).fetchone()
        conn.close()
        # The equality fallback keeps the original starter-project demo accounts usable;
        # all accounts created by this finished application use a Werkzeug password hash.
        stored = user["password"] if user else ""
        valid = user and (
            stored == request.form["password"]
            or (":" in stored and check_password_hash(stored, request.form["password"]))
        )
        if valid:
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required()
def dashboard():
    return redirect(
        url_for(
            {
                "customer": "customer_dashboard",
                "provider": "provider_dashboard",
                "admin": "admin_dashboard",
            }[session["role"]]
        )
    )


@app.route("/customer/dashboard")
@login_required("customer")
def customer_dashboard():
    conn = get_db_connection()
    counts = conn.execute(
        "SELECT status,COUNT(*) total FROM bookings WHERE customer_id=? GROUP BY status",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/dashboard.html", counts=counts)


@app.route("/services")
def services():
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT * FROM categories WHERE active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("customer/services.html", categories=categories)


@app.route("/providers")
def providers():
    category, location = (
        request.args.get("category", ""),
        request.args.get("location", "").strip(),
    )
    conn = get_db_connection()
    sql = "SELECT sp.*,u.name FROM service_providers sp JOIN users u ON u.id=sp.user_id WHERE 1=1"
    params = []
    if category:
        sql += " AND sp.service=?"
        params.append(category)
    if location:
        sql += " AND sp.location LIKE ?"
        params.append("%" + location + "%")
    records = conn.execute(sql + " ORDER BY sp.rating DESC,u.name", params).fetchall()
    categories = conn.execute(
        "SELECT * FROM categories WHERE active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template(
        "customer/providers.html",
        providers=records,
        categories=categories,
        selected_category=category,
        location=location,
    )


@app.route("/provider/<int:provider_id>")
def provider_details(provider_id):
    conn = get_db_connection()
    provider = conn.execute(
        "SELECT sp.*,u.name,u.phone,u.email FROM service_providers sp JOIN users u ON u.id=sp.user_id WHERE sp.id=?",
        (provider_id,),
    ).fetchone()
    reviews = conn.execute(
        "SELECT r.*,u.name FROM reviews r JOIN users u ON u.id=r.customer_id WHERE r.provider_id=? ORDER BY r.created_at DESC",
        (provider_id,),
    ).fetchall()
    conn.close()
    if not provider:
        flash("Provider not found.", "danger")
        return redirect(url_for("providers"))
    return render_template(
        "customer/provider_details.html", provider=provider, reviews=reviews
    )


@app.route("/book/<int:provider_id>", methods=["GET", "POST"])
@login_required("customer")
def book(provider_id):
    conn = get_db_connection()
    provider = conn.execute(
        "SELECT sp.*,u.name FROM service_providers sp JOIN users u ON u.id=sp.user_id WHERE sp.id=?",
        (provider_id,),
    ).fetchone()
    if not provider:
        conn.close()
        flash("Provider not found.", "danger")
        return redirect(url_for("providers"))
    if request.method == "POST":
        conn.execute(
            "INSERT INTO bookings (customer_id,provider_id,service_date,preferred_time,address,description) VALUES (?,?,?,?,?,?)",
            (
                session["user_id"],
                provider_id,
                request.form["service_date"],
                request.form["preferred_time"],
                request.form["address"].strip(),
                request.form["description"].strip(),
            ),
        )
        conn.commit()
        conn.close()
        flash("Booking request sent.", "success")
        return redirect(url_for("customer_bookings"))
    conn.close()
    return render_template("customer/book.html", provider=provider)


@app.route("/customer/bookings")
@login_required("customer")
def customer_bookings():
    conn = get_db_connection()
    bookings = conn.execute(
        "SELECT b.*,sp.service,u.name provider_name,r.id review_id FROM bookings b JOIN service_providers sp ON sp.id=b.provider_id JOIN users u ON u.id=sp.user_id LEFT JOIN reviews r ON r.booking_id=b.id WHERE b.customer_id=? ORDER BY b.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/bookings.html", bookings=bookings)


@app.route("/customer/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required("customer")
def cancel_booking(booking_id):
    """Customers may cancel an upcoming request before its scheduled date."""
    conn = get_db_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id=? AND customer_id=?",
        (booking_id, session["user_id"]),
    ).fetchone()
    if not booking:
        flash("Booking not found.", "danger")
    elif booking["status"] not in ("Pending", "Accepted"):
        flash("Only pending or accepted bookings can be cancelled.", "danger")
    else:
        try:
            service_day = date.fromisoformat(booking["service_date"])
            if service_day <= date.today():
                flash(
                    "Bookings can only be cancelled before the service date.", "danger"
                )
            else:
                conn.execute(
                    'UPDATE bookings SET status="Cancelled" WHERE id=?', (booking_id,)
                )
                conn.commit()
                flash("Your booking has been cancelled.", "success")
        except ValueError:
            flash(
                "This booking has an invalid service date and cannot be cancelled.",
                "danger",
            )
    conn.close()
    return redirect(url_for("customer_bookings"))


@app.route("/review/<int:booking_id>", methods=["GET", "POST"])
@login_required("customer")
def review(booking_id):
    conn = get_db_connection()
    booking = conn.execute(
        'SELECT * FROM bookings WHERE id=? AND customer_id=? AND status="Completed"',
        (booking_id, session["user_id"]),
    ).fetchone()
    if not booking:
        conn.close()
        flash("Only completed bookings can be reviewed.", "danger")
        return redirect(url_for("customer_bookings"))
    if request.method == "POST":
        try:
            conn.execute(
                "INSERT INTO reviews (booking_id,customer_id,provider_id,rating,comment) VALUES (?,?,?,?,?)",
                (
                    booking_id,
                    session["user_id"],
                    booking["provider_id"],
                    request.form["rating"],
                    request.form.get("comment", "").strip(),
                ),
            )
            conn.execute(
                "UPDATE service_providers SET rating=(SELECT ROUND(AVG(rating),1) FROM reviews WHERE provider_id=?) WHERE id=?",
                (booking["provider_id"], booking["provider_id"]),
            )
            conn.commit()
            flash("Thank you for your review!", "success")
        except Exception:
            flash("A review already exists for this booking.", "danger")
        conn.close()
        return redirect(url_for("customer_bookings"))
    conn.close()
    return render_template("customer/review.html", booking=booking)


@app.route("/provider/dashboard")
@login_required("provider")
def provider_dashboard():
    conn = get_db_connection()
    profiles = conn.execute(
        "SELECT * FROM service_providers WHERE user_id=?", (session["user_id"],)
    ).fetchall()
    pending = conn.execute(
        'SELECT COUNT(*) FROM bookings b JOIN service_providers sp ON sp.id=b.provider_id WHERE sp.user_id=? AND b.status="Pending"',
        (session["user_id"],),
    ).fetchone()[0]
    conn.close()
    return render_template(
        "provider/dashboard.html", profiles=profiles, pending=pending
    )


@app.route("/provider/services", methods=["GET", "POST"])
@login_required("provider")
def manage_services():
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT * FROM categories WHERE active=1 ORDER BY name"
    ).fetchall()
    if request.method == "POST":
        cat = conn.execute(
            "SELECT id FROM categories WHERE name=?", (request.form["service"],)
        ).fetchone()
        conn.execute(
            "INSERT INTO service_providers (user_id,category_id,service,experience,location,charges,description) VALUES (?,?,?,?,?,?,?)",
            (
                session["user_id"],
                cat["id"],
                request.form["service"],
                request.form["experience"],
                request.form["location"],
                request.form["charges"],
                request.form["description"],
            ),
        )
        conn.commit()
        flash("Service profile added.", "success")
    profiles = conn.execute(
        "SELECT * FROM service_providers WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template(
        "provider/services.html", services=profiles, categories=categories
    )


@app.route("/provider/services/<int:service_id>/delete", methods=["POST"])
@login_required("provider")
def delete_service(service_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM service_providers WHERE id=? AND user_id=?",
        (service_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Service profile removed.", "success")
    return redirect(url_for("manage_services"))


@app.route("/provider/bookings")
@login_required("provider")
def provider_bookings():
    conn = get_db_connection()
    bookings = conn.execute(
        "SELECT b.*,sp.service,u.name customer_name,u.phone customer_phone FROM bookings b JOIN service_providers sp ON sp.id=b.provider_id JOIN users u ON u.id=b.customer_id WHERE sp.user_id=? ORDER BY b.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("provider/bookings.html", bookings=bookings)


@app.route("/provider/booking/<int:booking_id>/status", methods=["POST"])
@login_required("provider")
def update_booking_status(booking_id):
    status = request.form["status"]
    if status in ("Accepted", "Rejected", "In Progress", "Completed"):
        conn = get_db_connection()
        conn.execute(
            "UPDATE bookings SET status=? WHERE id=? AND provider_id IN (SELECT id FROM service_providers WHERE user_id=?)",
            (status, booking_id, session["user_id"]),
        )
        conn.commit()
        conn.close()
        flash("Booking status updated.", "success")
    return redirect(url_for("provider_bookings"))


@app.route("/provider/reviews")
@login_required("provider")
def provider_reviews():
    conn = get_db_connection()
    reviews = conn.execute(
        "SELECT r.*,u.name customer_name,sp.service FROM reviews r JOIN users u ON u.id=r.customer_id JOIN service_providers sp ON sp.id=r.provider_id WHERE sp.user_id=? ORDER BY r.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("provider/reviews.html", reviews=reviews)


@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    conn = get_db_connection()
    stats = {
        "customers": conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='customer'"
        ).fetchone()[0],
        "providers": conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='provider'"
        ).fetchone()[0],
        "bookings": conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        "categories": conn.execute(
            "SELECT COUNT(*) FROM categories WHERE active=1"
        ).fetchone()[0],
    }
    recent = conn.execute(
        "SELECT b.*,c.name customer_name,p.name provider_name FROM bookings b JOIN users c ON c.id=b.customer_id JOIN service_providers sp ON sp.id=b.provider_id JOIN users p ON p.id=sp.user_id ORDER BY b.created_at DESC LIMIT 6"
    ).fetchall()
    conn.close()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@app.route("/admin/users")
@login_required("admin")
def admin_users():
    conn = get_db_connection()
    users = conn.execute(
        "SELECT * FROM users WHERE role!='admin' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)


@app.route("/admin/categories", methods=["GET", "POST"])
@login_required("admin")
def admin_categories():
    conn = get_db_connection()
    if request.method == "POST":
        try:
            conn.execute(
                "INSERT INTO categories (name,description) VALUES (?,?)",
                (
                    request.form["name"].strip(),
                    request.form.get("description", "").strip(),
                ),
            )
            conn.commit()
            flash("Category added.", "success")
        except Exception:
            flash("That category already exists.", "danger")
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/categories.html", categories=categories)


@app.route("/admin/category/<int:category_id>/toggle", methods=["POST"])
@login_required("admin")
def toggle_category(category_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE categories SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
        (category_id,),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_categories"))


@app.route("/admin/bookings")
@login_required("admin")
def admin_bookings():
    conn = get_db_connection()
    bookings = conn.execute(
        "SELECT b.*,c.name customer_name,p.name provider_name,sp.service FROM bookings b JOIN users c ON c.id=b.customer_id JOIN service_providers sp ON sp.id=b.provider_id JOIN users p ON p.id=sp.user_id ORDER BY b.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("admin/bookings.html", bookings=bookings)


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@login_required("admin")
def admin_delete_user(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=? AND role!='admin'", (user_id,))
    conn.commit()
    conn.close()
    flash("Record removed.", "success")
    return redirect(url_for("admin_users"))


if __name__ == "__main__":
    app.run(debug=True)
