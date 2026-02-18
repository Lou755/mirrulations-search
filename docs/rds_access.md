# Accessing the Aurora RDS Database from EC2

## Prerequisites

- You are connected to the EC2 instance via the [EC2 Instance Connect web interface](./ec2-setup.md)
- You have access to AWS Secrets Manager
- `psql` is installed on the EC2 instance

## Steps

### 1. Navigate to the Project Directory

```bash
cd mirrulations-search
```

### 2. Retrieve the Database Password

Go to **AWS Console → Secrets Manager**, find the secret named:

```
mirrulationsdb/postgres/master
```

Click **"Retrieve secret value"** and copy the password.

### 3. Download the SSL Certificate

Aurora RDS requires an SSL connection. Download the global certificate bundle:

```bash
sudo mkdir -p /certs
sudo curl -o /certs/global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

### 4. Set the RDS Endpoint as an Environment Variable

The RDS endpoint can be found in **AWS Console → RDS → Databases → mirrulationsdb → Connectivity & Security**.

```bash
export RDSHOST="your-cluster-endpoint-here"
```

### 5. Connect to the Database

```bash
psql "host=$RDSHOST port=5432 dbname=postgres user=postgres sslmode=verify-full sslrootcert=/certs/global-bundle.pem password=yourpasswordhere"
```

Replace `yourpasswordhere` with the password retrieved in Step 2.

### 6. Confirm You Are Connected

You should now see the Postgres prompt:

```
postgres=#
```

## Verifying the Database Contents

Use the following commands to confirm the data looks correct:

```sql
\l                          -- list all databases
\c dbname                   -- switch to a specific database
\dt                         -- list tables in the current database
SELECT COUNT(*) FROM tablename;  -- spot check row counts
```

Replace `dbname` and `tablename` with the actual names for your database and tables.

### Exit the Database

```sql
\q
```

