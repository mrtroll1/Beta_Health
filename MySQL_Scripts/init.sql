DROP TABLE IF EXISTS user_cases;
DROP TABLE IF EXISTS user_doctors;
DROP TABLE IF EXISTS user_names;


CREATE TABLE user_names (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(50)
);

CREATE TABLE user_doctors (
    doctor_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    doctor_name VARCHAR(50)
);

CREATE TABLE user_cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    case_name TEXT,
    user_id BIGINT NOT NULL,
    doctor_id BIGINT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME DEFAULT NULL,
    case_status VARCHAR(20),
    case_data TEXT,
    FOREIGN KEY (user_id) REFERENCES user_names(user_id),
    FOREIGN KEY (doctor_id) REFERENCES user_doctors(doctor_id)
);

