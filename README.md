# Personal Service Management System

A Flask-based application for managing personalized services, including user and provider dashboards, booking management, and automated notifications.

## 🚀 Features
- **User Dashboard**: Browse and book services.
- **Provider Dashboard**: Manage services and view bookings.
- **Admin Dashboard**: Oversee system activities and verify providers.
- **Automated Tasks**: Reminders and auto-completion of past bookings.

## 🛠️ Prerequisites
- Python 3.x
- MySQL Database

## ⚙️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repository-url>
   cd <repository-folder>
   ```

2. **Set up a virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Update your `.env` file with your MySQL credentials and a strong `SECRET_KEY`.

5. **Set up the Database**:
   - Create a database named `personal_service` in MySQL.
   - Run the initial schema setup (if a script is provided) or import `schema.sql`.

## 🏃 Running the Application
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`.

## 🗃️ Database Schema
The core tables include:
- `users`: Stores user and provider information.
- `services`: Services offered by providers.
- `bookings`: Appointment and booking details.
- `notifications`: Alerts for providers and users.
