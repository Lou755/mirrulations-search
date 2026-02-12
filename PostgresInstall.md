# PostgreSQL Installation and Launch Guide (macOS with Homebrew)

## Create Virtual Environment

Before setting up PostgreSQL, create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

## Installation

Install PostgreSQL using Homebrew:

```bash
brew install postgresql
```

Or for a specific version:

```bash
brew install postgresql@15
```

## Launching PostgreSQL

### Start PostgreSQL

```bash
brew services start postgresql
```

### Stop PostgreSQL

```bash
brew services stop postgresql
```

### Restart PostgreSQL

```bash
brew services restart postgresql
```

## Verify Installation

Check PostgreSQL version:

```bash
psql --version
```

Check if PostgreSQL is running:

```bash
brew services list
```