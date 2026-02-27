-- Mirrulations Search Schema
-- Postgres Schema for Flask application

-- =========================================
-- DOCKETS TABLE
-- =========================================
-- Stores docket metadata

CREATE TABLE IF NOT EXISTS dockets (
    docket_id VARCHAR(50) NOT NULL PRIMARY KEY,
    docket_api_link VARCHAR(2000) NOT NULL UNIQUE,
    agency_id VARCHAR(20) NOT NULL,
    docket_category VARCHAR(100),
    docket_type VARCHAR(50) NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE,
    flex_field1 TEXT,
    flex_field2 TEXT,
    modify_date TIMESTAMP WITH TIME ZONE NOT NULL,
    organization VARCHAR,
    petition_nbr VARCHAR,
    program VARCHAR,
    rin VARCHAR(20),
    short_title VARCHAR,
    flex_subtype1 TEXT,
    flex_subtype2 TEXT,
    docket_title VARCHAR(500),
    docket_abstract TEXT
);

-- =========================================
-- DOCUMENTS TABLE
-- =========================================
-- Stores document metadata; references dockets
-- When a new document is added then a column in the CFR part table should be added

CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(50) NOT NULL PRIMARY KEY,
    docket_id VARCHAR(50) NOT NULL,
    document_api_link VARCHAR(2000) NOT NULL UNIQUE,
    address1 VARCHAR(200),
    address2 VARCHAR(200),
    agency_id VARCHAR(20) NOT NULL,
    is_late_comment BOOLEAN,
    author_date TIMESTAMP WITH TIME ZONE,
    comment_category VARCHAR(200),
    city VARCHAR(100),
    comment TEXT,
    comment_end_date TIMESTAMP WITH TIME ZONE,
    comment_start_date TIMESTAMP WITH TIME ZONE,
    country VARCHAR(100),
    document_type CHAR(30) NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE,
    email VARCHAR(320),
    fax VARCHAR(20),
    flex_field1 TEXT,
    flex_field2 TEXT,
    first_name VARCHAR(100),
    submitter_gov_agency VARCHAR(300),
    submitter_gov_agency_type VARCHAR(50),
    implementation_date TIMESTAMP WITH TIME ZONE,
    last_name VARCHAR(100),
    modify_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_open_for_comment BOOLEAN DEFAULT FALSE,
    submitter_org VARCHAR(200),
    phone VARCHAR(40),
    posted_date TIMESTAMP WITH TIME ZONE NOT NULL,
    postmark_date TIMESTAMP WITH TIME ZONE,
    reason_withdrawn VARCHAR(1000),
    receive_date TIMESTAMP WITH TIME ZONE,
    reg_writer_instruction TEXT,
    restriction_reason VARCHAR(1000),
    restriction_reason_type VARCHAR(20),
    state_province_region VARCHAR(100),
    subtype VARCHAR(100),
    document_title VARCHAR(500),
    topics VARCHAR(250)[],
    is_withdrawn BOOLEAN DEFAULT FALSE,
    postal_code VARCHAR(10)
);

-- =========================================
-- CFR PARTS TABLE
-- =========================================
-- Stores cfr part numbers for corresponding documents; references documents
-- cfrPart and frDocNum will be null at table creation & are retrieved from federal reserve & inserted into the table at the first query

CREATE TABLE IF NOT EXISTS cfrparts (
    document_id VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES documents(document_id),
    frDocNum VARCHAR(50),
    cfrPart VARCHAR(50)
);

-- =========================================
-- LINKS TABLE
-- =========================================
-- Stores links for corresponding cfr parts; references cfr parts

CREATE TABLE IF NOT EXISTS links (
    document_id VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES cfrparts(document_id),
    link VARCHAR(2000)
);