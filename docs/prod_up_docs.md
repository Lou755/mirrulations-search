# How to Set up Production Environment
Authors: Jeffery Eisenhardt, Cole Aydelotte, Collin Cabral-Castro.

# What this script does

prod_up.sh is a production deployment bootstrap script that sets up (or reuses) the project environment, provisions TLS certificates, installs the systemd service, and restarts the running backend.

When executed, the script will:

- Enforce safe bash execution (set -euo pipefail) so failures stop the deploy
- Sets up the project root dynamically and runs from that directory
- Installs the project and dependencies inside .venv
- Ensures certbot is available at /use/bin/certbot via symlink
- Stops the currently running mirrsearch service (if it exists)
- Users Certbot's standalone mode to request/renew a certificate for the configured domain
- Copies the mirrsearch.service file into /etc/systemd/system/, reloads systemd, enable the service, and restarts it
- Displays the service status at the end so you can confirm it's running

# Why we need this

Production deploys have more moving parts than local dev: service management, repeatable startup, and TLS certificate provisioning. Doing those steps manually increases the chance of downtime and misconfiguration.

This script exists to:

- Make production setup and redeploys repeatable and predictable
- Ensure the systemd service definition is installed and enabled correctly
- Automate TLS certificate provisioning/renewal for the target domain
- Reduce human error during deployment (wrong directory, missed restart, stale service file, etc.)
- Provide a single command that gets the server back into a known-good running state

# Run the script
```bash
./prod_up.sh
```