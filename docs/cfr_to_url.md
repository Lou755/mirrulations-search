# cfr_to_url.py

Terminal program that fetches eCFR corrections from the API, stores them in PostgreSQL (database `cfrurl`, table `regulations`), and lets you look up CFR entries by name or list all rows with their URLs.

---

## Setup (first time)

1. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure PostgreSQL**  
   Create a `.env` file in the project root with `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD`.

---

## Run

```bash
source .venv/bin/activate   # if not already active
python cfr_to_url.py
```

At the prompt, enter one of the commands below.

---

## Commands

| Command | Description |
|--------|-------------|
| **create** | Fetch corrections from the eCFR API and populate the `regulations` table. |
| **erase** | Drop and recreate the `regulations` table (asks for confirmation). |
| **view** | List all rows (id, name, URL). |
| **view** \<name\> | Search rows by name (case-insensitive partial match). Example: `view Title-42` |
| **view id** \<number\> | Show full details for one row by ID. Example: `view id 42` |
| **exit** | Quit the program. |

---

## Quick reference

- **Database:** `cfrurl` (created automatically if missing).
- **Table:** `regulations` (columns: `id`, `name`, `url`).
