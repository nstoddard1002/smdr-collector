##Basic Call Accounting Software

This python script simply collects SMDR records, sent in CSV format over the network from a PBX. This script is designed to collect data from IP Office 500 V2 Control Units, manufactured by Avaya. 

#Features Include:

- Saves call records into a CSV format file in "/opt/smdr/call_logs/"
- Rolls over log on customizable time interval (default is 1 hour)
- Rolls over log if customizable size threshold is reached (default is 100 MBs)
- Locks files to prevent accidental file corruption from multiple writes
- Closes files properly when shutdown signal is received
- Installation script sets up the file directories and scripts and permissions
- Installation script also creates an SMDR user and a systemd service


#Features to be added:

- concurrency for supporting multiple PBXs
- support for different model PBXs
- automatic email of CSV records
- database for querying and reports

#Feedback

-Questions, comments, and other feedback: email nstoddard@proton.me
