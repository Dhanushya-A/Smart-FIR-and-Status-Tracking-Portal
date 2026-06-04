#  Smart FIR and Status Tracking Portal

A secure web-based FIR (First Information Report) Management System developed using Flask that enables complainants, police officers, and administrators to manage FIRs digitally. The system supports FIR submission, evidence management, status tracking, email notifications, SMS alerts, geolocation tracking, and role-based access control.

---

## 📌 Features

### 👤 User Management

* User Registration and Login
* Password Reset
* Role-Based Access Control

  * Complainant
  * Police Officer
  * Administrator
* Secure Password Hashing

### 📝 FIR Management

* Submit FIR Online
* Track FIR Status
* Assign FIRs to Police Officers
* Update FIR Investigation Status
* FIR History and Timeline

### 📂 Evidence Management

* Upload Multimedia Evidence

  * Images
  * Videos
  * Audio Files
  * PDF Documents
* Evidence Verification by Police
* Evidence Rejection with Remarks
* Evidence Audit Logs

### 📧 Email Notifications

* Registration Confirmation
* FIR Submission Confirmation
* FIR Status Updates
* Evidence Verification Notifications

### 📱 SMS Notifications

* FIR Status Alerts
* Evidence Verification Updates
* Twilio API Integration

### 📍 Geo-Location Tracking

* Store User Coordinates
* View User Locations
* Admin Location Monitoring Dashboard

### 🔐 Security Features

* Password Hashing
* Session Management
* Role-Based Authorization
* Secure File Upload Validation
* Device Locking Using IMEI

---

## 🛠️ Technologies Used

### Backend

* Python
* Flask
* Flask-SQLAlchemy
* Flask-Login
* Flask-Migrate

### Database

* SQLite

### Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

### APIs & Services

* Twilio SMS API
* Flask-Mail SMTP Service

### Utilities

* dotenv
* Werkzeug

---

## 📁 Project Structure

```text
E-Police-System/
│
├── static/
│   ├── uploads/
│   ├── css/
│   ├── js/
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── submit_fir.html
│   ├── complainant_dashboard.html
│   ├── police_dashboard.html
│   ├── admin_dashboard.html
│   └── view_fir.html
│
├── app.py
├── requirements.txt
├── .env
├── README.md
└── instance/
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/e-police-fir-system.git
cd e-police-fir-system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux/Mac

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your_secret_key

DATABASE_URL=sqlite:///epolice.db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password

TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=your_twilio_number

UPLOAD_FOLDER=static/uploads
```

### 6. Run Database

```bash
python app.py
```

### 7. Start Application

```bash
python app.py
```

Visit:

```text
http://127.0.0.1:5000
```

---

## 👥 User Roles

### Complainant

* Register/Login
* Submit FIR
* Upload Evidence
* Track FIR Status
* Receive Notifications

### Police Officer

* View Assigned FIRs
* Verify Evidence
* Reject Evidence
* Update FIR Status

### Administrator

* Manage Users
* Ban Users
* Assign Police Officers
* Monitor Locations
* View All FIRs
* Override Evidence Decisions

---

## 📊 Database Models

### User

Stores user information and authentication details.

### FIR

Stores FIR records and investigation details.

### Evidence

Stores uploaded files related to FIRs.

### FIRStatusUpdate

Stores FIR progress history.

### EvidenceLog

Stores evidence verification logs.

### UserLocation

Stores user GPS coordinates.

---

## 🔔 Notification System

### Email Notifications

* User Registration
* FIR Submission
* FIR Status Changes
* Evidence Verification

### SMS Notifications

* FIR Updates
* Evidence Approval/Rejection

Powered by Twilio API.

---

## 📍 Location Tracking

The system captures and stores user coordinates during FIR submission and location updates.

Admins can:

* View latest user locations
* Monitor complainant locations
* Track investigation-related positions

---

## 🔮 Future Enhancements

* AI-Based Crime Analysis
* Face Recognition Integration
* Aadhaar Verification
* Digital Signature Support
* Crime Hotspot Visualization
* Real-Time Police Tracking
* Mobile Application

---

## 📸 Screenshots

Add screenshots here:

* Login Page
  
  <img width="766" height="512" alt="Screenshot 2025-10-12 215100" src="https://github.com/user-attachments/assets/18f8c9aa-841b-4828-b6a1-3e2ff50bd8c3" />
* Registration Page
  
  <img width="769" height="511" alt="Screenshot 2025-10-12 215223" src="https://github.com/user-attachments/assets/114034b8-1d3f-4a95-98b4-16d2d7af0997" />
* FIR Submission Form
  
  <img width="750" height="511" alt="Screenshot 2025-10-12 220242" src="https://github.com/user-attachments/assets/bea763d9-cbeb-442b-b483-a8a9e75fadc1" />
* Police Dashboard
  
  <img width="1788" height="709" alt="Screenshot 2025-10-12 160011" src="https://github.com/user-attachments/assets/8793a60a-b882-4365-b47d-a6fc8d1d9d9a" />

* Admin Dashboard
* Complainant Dashboard

---

## 👨‍💻 Developer

Developed by **Dhanushya**
Department of Information Technology
PKN Arts ans Science College

---

## 📄 License

This project is developed for educational and academic purposes.
