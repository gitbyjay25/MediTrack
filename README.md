# MediTrek - Intelligent Medicine Management System

A comprehensive medicine tracking system combining DBMS, Machine Learning, and Operating System concepts with real WHO Essential Medicines data.

## Project Structure

```
TrackMedi/
├── database/
│   ├── updated_schema.sql     # MySQL schema for WHO data
│   └── db_config.py          # Database connection
├── backend/
│   ├── main.py               # Flask application
│   └── ml/
│       ├── drug_interactions.py  # Drug interaction checking
│       └── scheduler.py          # Reminder scheduling
├── templates/                # HTML templates
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── Data_Cleaning_Only.md     # Colab data cleaning
├── Colab_Notebook_Instructions.md  # ML training
└── README.md
```

## Key Features

- **Real WHO Data**: 500+ Essential Medicines from WHO database
- **Drug Interactions**: 380+ real drug interactions with severity levels
- **ML-Powered**: Machine learning models for interaction prediction
- **Database-Driven**: MySQL with proper normalization and indexing
- **Smart Reminders**: Operating system-based scheduling
- **Clean Architecture**: Simple, maintainable codebase
- **Professional UI**: Bootstrap-based responsive interface

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Data Processing (Google Colab)**:
   - Run `Data_Cleaning_Only.md` in Colab for data cleaning
   - Run `Colab_Notebook_Instructions.md` for ML model training
   - Download cleaned data and trained model

3. **Database Setup**:
   ```bash
   # Create MySQL database
   mysql -u root -p < database/updated_schema.sql
   
   # Import cleaned data
   mysql -u root -p meditrek < medicine_clean.csv
   mysql -u root -p meditrek < interaction_clean.csv
   ```

4. **Configure Database**:
   - Update `config.py` with your MySQL credentials

5. **Run Application**:
   ```bash
   python backend/main.py
   ```

6. **Access Application**:
   - Open browser: http://localhost:5000
   - Register new account

## Database Schema

- **users**: User authentication and profiles
- **medicines**: WHO Essential Medicines (500+ medicines)
- **interactions**: Drug interactions (380+ interactions)
- **dose_logs**: Medication tracking
- **recommendations**: Medicine recommendations
- **schedules**: Reminder scheduling

## Technical Stack

- **Database**: MySQL with WHO Essential Medicines data
- **Backend**: Flask with clean architecture
- **Frontend**: Bootstrap 5 responsive interface
- **ML**: Scikit-learn models for interaction prediction
- **Security**: bcrypt password hashing, session management
- **Data**: Real WHO Essential Medicines List (2023)

## API Endpoints

### **Authentication**
- `POST /login` - User login
- `POST /register` - User registration
- `GET /logout` - User logout

### **Medicine Management**
- `GET /dashboard` - Main dashboard
- `GET /add_medicine` - Add medicine form
- `POST /add_medicine` - Create new medicine with interaction checking
- `POST /take_dose/<med_id>` - Log taken dose
- `POST /miss_dose/<med_id>` - Log missed dose

### **Recommendations**
- `GET /recommendations` - Medicine recommendations

## Data Sources

- **WHO Essential Medicines List (2023)**: 500+ essential medicines
- **Drug Interactions Database**: 380+ real drug interactions
- **Machine Learning Models**: Trained on real medical data

## Repository Description

**Intelligent Medicine Management System combining DBMS, ML, and OS concepts with real WHO Essential Medicines data. Features drug interaction prediction, smart reminders, and comprehensive medicine tracking.**

Built with real medical data for professional healthcare applications.
