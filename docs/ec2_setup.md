# Creating an EC2 Instance to Access Mirrulations Data

## Steps

### 1. Navigate to EC2

Go to **AWS Console → EC2 → Instances → Launch Instances**.

### 2. Name Your Instance

Give your instance a descriptive name.

### 3. Select an AMI and Instance Type

Choose the appropriate AMI (e.g., Amazon Linux 2 or Ubuntu) and instance type for your workload.

### 4. Set Up a Key Pair

Select the existing key pair named **`mirrulations`**.

### 5. Configure Network Settings

Under **Network Settings**, select the existing VPC named **`mirrulations db`**.

Once the VPC is selected, click **"Select existing security group"** and choose **`mirrulations-search-security-group`**.

### 6. Launch the Instance

Review your settings and click **Launch Instance**.

### 7. Connect to the Instance

1. Go to **AWS Console → EC2 → Instances** and select your running instance.
2. Click the **Connect** button at the top.
3. Select the **EC2 Instance Connect** tab.
4. Click **Connect** — this will open a terminal in your browser.

