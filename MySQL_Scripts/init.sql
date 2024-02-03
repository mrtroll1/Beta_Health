DROP TABLE IF EXISTS user_cases;
DROP TABLE IF EXISTS user_plans;
DROP TABLE IF EXISTS user_doctors;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(50),
    num_cases INT DEFAULT 0,
    medical_bio TEXT DEFAULT NULL
);

CREATE TABLE user_doctors (
    doctor_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    doctor_name VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(user_id) 
);

CREATE TABLE user_plans (
    plan_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    plan_data TEXT,
    plan_reminder_ids TEXT DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE user_cases (
    case_id VARCHAR(64) PRIMARY KEY,
    case_name VARCHAR(64) DEFAULT 'Без названия',
    user_id BIGINT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME DEFAULT NULL,
    case_status VARCHAR(20),
    case_data TEXT DEFAULT NULL,
    case_media_path VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);


