CREATE TABLE user (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    active BOOLEAN
);

CREATE TABLE website (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    domain VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE website_pages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    url VARCHAR(255) NOT NULL,
    canonical_url VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    keywords TEXT,
    language_code VARCHAR(10) NOT NULL,
    text TEXT NOT NULL,
    markdown TEXT NOT NULL,
    website_id INT NOT NULL,
    FOREIGN KEY (website_id) REFERENCES Website(id)
);

CREATE TABLE user_website (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    website_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User(id),
    FOREIGN KEY (website_id) REFERENCES Website(id)
);