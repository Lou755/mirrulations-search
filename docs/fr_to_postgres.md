# fr_to_postgres.py

Fetches CFR references (title/part) from the Federal Register API for given FR doc numbers and docket IDs, and inserts them into PostgreSQL (`frtocfr`, table `cfr_references`). Creates the database and table if missing. Input: manual entry, text file, or JSON (regulations.gov).

---

## Setup (first time)

1. **Install dependencies**

   ```bash
   pip install requests psycopg2-binary python-dotenv
   ```

   Or: `pip install -r requirements.txt` then `pip install requests` if needed.  
   Missing deps → script prints the `pip install` command and exits.

2. **Configure PostgreSQL**  
   Create **`db/cfr_and_fr/.env`** and paste the following (replace placeholders with your values):

   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```
   For no password (common locally), use `DB_PASSWORD=` and leave the rest after the `=` empty.

   **Where do these come from?**  
   They are your **local PostgreSQL** credentials. If you installed Postgres with Homebrew (e.g. for this project), the username is usually your **macOS username** (run `whoami` in a terminal). The password is often **empty** for local connections, or whatever you set when you first set up Postgres.

   Script loads `.env` from that directory (run from project root or `db/cfr_and_fr`).

3. **PostgreSQL** must be running.

   **How to get Postgres running (macOS with Homebrew):**
   - Install (if needed): `brew install postgresql@15` (or `brew install postgresql` for latest).
   - Start the service: `brew services start postgresql@15` (use your version number if different).
   - Check it's up: `pg_isready -h localhost` or `psql -h localhost -U $(whoami) -d postgres -c 'select 1'`.
     - **"accepting connections"**: Success! Postgres is up and running.
     - **"no response"**: The service hasn't fully started yet. Give it 5 seconds.
     - **"command not found"**: The PATH command in Step 1 didn't stick—let me know if this happens!
   - Optional: from the project root, `./db/setup_postgres.sh` will start Postgres (if installed via Homebrew) and set up the main app DB; the script in this doc uses a separate DB `frtocfr`.

---

## Run

**Interactive:**

```bash
cd db/cfr_and_fr
python3 fr_to_postgres.py
```

From project root: `python3 db/cfr_and_fr/fr_to_postgres.py`

**Single entry:** both flags required; otherwise the menu runs.

```bash
python3 fr_to_postgres.py --fr-doc 2025-13271 --docket-id FDA-2027-0001
```

---

## Menu options

| Option | Description |
|--------|-------------|
| **1) Manual** | Prompts for count, then each FR doc number and docket ID. Blank → skip. |
| **2) Text file** | Path to text file. Lines with path + `frDocNum=...`; docket ID = 3rd path segment. See [Text file format](#text-file-format). |
| **3) JSON file** | Path to JSON array. Needs `document.attributes.docketId` and `frDocNum`. Skips missing/invalid or numeric-only `frDocNum`. See [JSON file format](#json-file-format). |
| **4) View database** | Prints rows in `cfr_references`, then back to menu. Message if DB/table missing. |
| **0) Exit** | Quit. |

---

## Input file formats

### Text file format

Parse lines containing `frDocNum=`. Path (before `|`) split on `/` → docket ID = segment at index 2. FR doc number = value after `frDocNum=`. Duplicate pairs added once.

Example:

```
data/AMS/AMS-2005-0001/text-.../documents/....json | frDocNum=05-17055
```

→ docket `AMS-2005-0001`, FR doc `05-17055`.

### JSON file format

Top level = JSON array. Each element: `document.attributes.docketId`, `document.attributes.frDocNum`. Skips missing/invalid or 1–3 digit `frDocNum` (volume number). Duplicate pairs added once.

```json
{ "document": { "attributes": { "docketId": "FDA-2027-0001", "frDocNum": "2025-13271" } } }
```

---

## Quick reference

- **DB:** `frtocfr` (auto-created). **Table:** `cfr_references` (`id`, `docket_id`, `cfr_title`, `cfr_section`); API `title`/`part` → `cfr_title`/`cfr_section`.
- **No dedup:** Same (FR doc, docket) can be run again → more rows.
- **API:** [Federal Register API](https://www.federalregister.gov/developers/documentation/api/v1); no key.
- **Paths:** Script `db/cfr_and_fr/fr_to_postgres.py`; `.env` `db/cfr_and_fr/.env`.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| No .env / Missing from .env | Create `db/cfr_and_fr/.env` and paste the four variables from [Setup](#setup-first-time) (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD). |
| Could not connect to PostgreSQL | Postgres running? Check host/port/user/password in `.env`. |
| FR doc not found | API 404; check doc number. |
| Could not reach Federal Register API | Network issue; retry. |
| pip install message on exit | Run the printed `pip install` command. |

Run output: DB check/create, connect, "Fetching CFR references…", "Inserted N row(s)…", "Done. N total row(s)…".
