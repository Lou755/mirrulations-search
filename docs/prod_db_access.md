
## Create an EC2 instance

When you create an EC2 instance, you need to put it in the same security group
as the databases:

* Under "Network Settings" click "Edit"
* Change the "VPC" to "mirrulationsdb" (the name is after the VPC id)
* Configure the "Firewall (security groups)" to allow access to the DBs (TBD How to achieve this)


