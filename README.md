# mirrulations-search

## CI/CD Configuration

- Personal Access token must allow for github workflows for CI/CD to work

## Dev Setup

* Create a virtual environment

  ```
  python3 -m venv .venv
  source .venv/bin/activate
  ```

* Install Dependencies

  ```
  pip install -r requirements.txt
  ```

* Install source as a package named `mirrsearch`

  ```
  pip install -e .
  ```

  NOTE: `-e` means the package is editable



## Run the Flask Server

Because the code is in a module, you can run it with the `-m` switch:

```
python -m mirrsearch.app
```

If you are in `src/mirrsearch`, you can run `app.py` directly:

```
python app.py
```

## Run with Gunicorn using the Postgres database
You must run ./db/setup_postgres.sh before to have created the actual database.
This also requires python-dotenv to be intalled which is now added in the requirements.txt file.
Or run pip install python-dotenv in your .venv.

Create a `.env` file in the root directory with the following variables:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mirrulations
DB_USER=your_macOS_username (You can find this by doing `whoami` in your terminal)
DB_PASSWORD=
USE_POSTGRES=true
```
Then run:
```bash
./dev_up.sh
```

## Database Testing Guide

## Overview
This folder contains tests for the Mirrulations database layer:

- `test_db.py` - Unit tests for the DBLayer mock (no database required)

## Setup for Integration Tests

### 1. Install MySQL
```bash
# macOS
brew install mysql
brew services start mysql

### 2. Install Python dependencies
```bash
pip install mysql-connector-python pytest
```

### 3. Set up the database
```bash
# Login to MySQL
mysql -u root -p

# Run the create.sql script
mysql -u root -p < create.sql
```

## Running the Tests

### Run all database tests:
```bash
pytest test_db.py -v
```