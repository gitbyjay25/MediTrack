
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS medicines;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_medicines;
DROP TABLE IF EXISTS medicine_recommendations;
DROP TABLE IF EXISTS dosage_optimization;

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    date_of_birth DATE,
    phone VARCHAR(20),
    emergency_contact VARCHAR(100),
    emergency_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Gamification columns
    streak_days INT DEFAULT 0,
    total_points INT DEFAULT 0,
    level INT DEFAULT 1,
    badges TEXT,
    last_streak_date DATE,
    longest_streak INT DEFAULT 0,
    -- Analytics columns
    total_medicines_taken INT DEFAULT 0,
    total_doses_missed INT DEFAULT 0,
    avg_adherence_rate DECIMAL(5,2) DEFAULT 0.00,
    last_analytics_update DATETIME,
    INDEX idx_username (username),
    INDEX idx_email (email)
);

-- Create medicines table (updated for WHO data)
CREATE TABLE medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    list_type ENUM('Core', 'Complementary') DEFAULT 'Core',
    main_category VARCHAR(100),
    sub_category_1 VARCHAR(100),
    sub_category_2 VARCHAR(100),
    form VARCHAR(100),
    dosage_concentration VARCHAR(200),
    salt_form VARCHAR(100),
    container_type VARCHAR(100),
    container_volume VARCHAR(100),
    specific_indication TEXT,
    preparation_instruction TEXT,
    additional_notes TEXT,
    first_choice_indications TEXT,
    second_choice_indications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_medicine_name (medicine_name),
    INDEX idx_main_category (main_category),
    INDEX idx_list_type (list_type)
);

-- Create interactions table (updated for comprehensive data)
CREATE TABLE interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drug1 VARCHAR(200) NOT NULL,
    drug2 VARCHAR(200) NOT NULL,
    drug3 VARCHAR(200),
    severity_level ENUM('High', 'Medium', 'Low') NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    clinical_significance TEXT,
    mechanism TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_drug1 (drug1),
    INDEX idx_drug2 (drug2),
    INDEX idx_severity (severity_level)
);

-- Create user_medicines table (main user medicine tracking)
CREATE TABLE user_medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    medicine_name VARCHAR(200) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    age_group VARCHAR(50),
    weight DECIMAL(5,2),
    height DECIMAL(5,2),
    gender VARCHAR(20),
    purpose TEXT,
    medical_conditions TEXT,
    allergies TEXT,
    adherence_score INT DEFAULT 100,
    reminder_times TEXT,
    reminder_enabled BOOLEAN DEFAULT TRUE,
    status ENUM('active', '0') DEFAULT 'active',
    daily_doses_taken INT DEFAULT 0,
    total_doses_required INT DEFAULT 1,
    last_taken_date DATE,
    last_taken TIMESTAMP,
    taken_count INT DEFAULT 0,
    missed_count INT DEFAULT 0,
    last_week_adherence DECIMAL(5,2) DEFAULT 0.00,
    last_month_adherence DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_medicine_name (medicine_name),
    INDEX idx_status (status)
);

-- Create medicine_recommendations table 
CREATE TABLE medicine_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(200) NOT NULL,
    primary_conditions TEXT,
    secondary_conditions TEXT,
    age_group_recommendations TEXT,
    contraindications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_medicine_name (medicine_name)
);

-- Create dosage_optimization table 
CREATE TABLE dosage_optimization (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(200) NOT NULL,
    adult_dosage VARCHAR(200),
    pediatric_dosage TEXT,
    elderly_dosage TEXT,
    weight_based_adjustments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_medicine_name (medicine_name)
);
