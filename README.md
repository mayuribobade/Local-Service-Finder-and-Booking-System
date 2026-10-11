# Local Service Finder and Booking System

A web-based Local Service Finder and Booking System developed using Python, Flask, HTML, CSS, and SQLite. It helps customers find local service providers, explore available services, and book services through a simple and user-friendly platform.

## Features

- **Customer Module:** Search for service providers, view provider details, book services, track bookings, and submit reviews.
- **Provider Module:** Manage service profiles, view booking requests, update booking status, and view customer reviews.
- **Admin Module:** Manage users, service categories, bookings, and dashboard activity.
- **Database:** SQLite database for storing application data.

## Technologies Used

- Python
- Flask
- HTML
- CSS
- SQLite

## How to Run Locally

1. Install Python on your system.
2. Install the required dependencies:

   `pip install -r requirements.txt`

3. Run the application:

   `python app.py`

4. Open the following URL in your browser:

   `http://127.0.0.1:5000`

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Administrator | admin@localfinder.com | admin123 |
| Demo Provider | rahul.demo@example.com | demo123 |

Customers and providers can also register through the application.

## Project Structure

- `app.py` — Main Flask application
- `database/` — Database-related code
- `static/` — CSS and static files
- `templates/` — HTML templates for customers, providers, and administrators
- `requirements.txt` — Required Python packages
- `.gitignore` — Files excluded from Git tracking

## Future Enhancements

- Online payment integration
- Email and SMS notifications
- Advanced search and filtering
- Improved booking and provider management

