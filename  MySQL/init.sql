DROP TABLE IF EXISTS user_cases;
DROP TABLE IF EXISTS user_names;

CREATE TABLE user_cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME DEFAULT NULL,
    status VARCHAR(50),
    case_data TEXT
);

CREATE TABLE user_names (
	user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(50)
);

INSERT INTO user_cases (user_id, status, case_data) VALUES (0, 'active', 'Pilot case data.');
INSERT INTO user_names (user_id, user_name) VALUES (0, 'Luka'); 

