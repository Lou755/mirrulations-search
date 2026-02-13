# PostgreSQL Installation and Launch Guide (macOS with Homebrew)

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