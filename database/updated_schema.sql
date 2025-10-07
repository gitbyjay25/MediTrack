
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS medicines;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS dose_logs;
DROP TABLE IF EXISTS user_medicine_history;
DROP TABLE IF EXISTS schedules;
DROP TABLE IF EXISTS users;
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

-- Create dose_logs table
CREATE TABLE dose_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    medicine_id INT NOT NULL,
    dose_taken DECIMAL(10,2),
    dose_unit VARCHAR(20),
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_medicine_id (medicine_id),
    INDEX idx_taken_at (taken_at)
);

-- Create recommendations table
CREATE TABLE recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(200) NOT NULL,
    medical_condition VARCHAR(200),
    recommendation_text TEXT NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 0.80,
    source VARCHAR(100) DEFAULT 'WHO Essential Medicines List',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_medicine_name (medicine_name),
    INDEX idx_medical_condition (medical_condition)
);
-- Create user_medicine_history table
CREATE TABLE user_medicine_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    medicine_id INT NOT NULL,
    start_date DATE,
    end_date DATE,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    prescribed_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_medicine_id (medicine_id)
);

-- Create schedules table
CREATE TABLE schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    medicine_id INT NOT NULL,
    dose_amount DECIMAL(10,2),
    dose_unit VARCHAR(20),
    frequency VARCHAR(50),
    time_of_day TIME,
    days_of_week VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_medicine_id (medicine_id),
    INDEX idx_is_active (is_active)
);

-- Create medicine_recommendations table (from Gemini data)
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

-- Create dosage_optimization table (from Gemini data)
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
