#!/bin/bash

#Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' #No Color

#Color Print Functions

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#check if run as root
check_root(){
    if [ "$EUID" -ne 0]; then
        print_error "Please run this as root or with sudo"
        exit 1
    fi
}

#Check that Python3 is installed, and install it if not
setup_python() {
    print_message "Checking Python 3 installation..."
    if ! command -v python3 &> /dev/null; then
        print_message "Python 3 not found. Installing..."
        apt-get update
        apt-get install -y python3 python3-pip
    else
        print_message "Python 3 has been previously installed."
    fi
}

#Function that creates a service user 
create_service_user() {
    print_message "Creating service user..."
    if id "smdr" &>/dev/null; then
        print_warning "User 'smdr' already exists"
    else
        useradd -r -s /bin/false smdr
        print_message "Created service user 'smdr'"
    fi
}

#Create the directories
create_directories() {
    local base_dir="/opt/smdr"
    local dirs=("$base_dir" "$base_dir/call_logs" "$base_dir/log_files")

    print_message "Creating directory structure..."
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        print_message "Created directory: $dir"
    done
}

#Setup main script and make it executable
setup_main_script() {
    local script_path="/opt/smdr"

    cp main.py "$script_path/main.py"
    cp config.py "$script_path/config.py"
    cp config.json "$script_path/config.json"


    chmod +x "$script_path/main.py"
    print_message "Main script and config files have been installed and made executable"
}

#Make system service
create_systemd_service() {
    print_message "Creating systemd service..."
    cat > /etc/systemd/system/smdr-collector.service << EOF
[Unit]
Description=SMDR Collector Service
After=network.target

[Service]
Type=simple
User=smdr
Group=smdr
ExecStart=/usr/bin/python3 /opt/smdr/main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    print_message "Systemd service created"
}

#Set permissions
set_permissions() {
    print_message "Setting permissions..."
    chown -R smdr:smdr /opt/smdr
    chmod -R 750 /opt/smdr
    chmod 770 /opt/smdr/call_logs
    chmod 770 /opt/smdr/log_files
    chmod 640 /opt/smdr/config.json
    print_message "Permissions set"
}

#installation procedure
main() {
    print_message "Installing SMDR Collector Service"

    #check if running as root
    check_root

    #Make sure pythong is installed
    setup_python

    #Create service user
    create_service_user

    #create directories
    create_directories

    #copy files and make main script executable
    setup_main_script

    #Create systemd service
    create_systemd_service

    #Set permissions
    set_permissions

    print_message "Installation complete!"
    print_message "You can start the service with: systemctl start smdr-collector"
    print_message "Enable it to start on boot with: systemctl smdr-collector"
}

#Run installation
main