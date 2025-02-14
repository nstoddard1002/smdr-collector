import socket
import os
import datetime
import csv
import signal
import sys 
import fcntl
from config import load_config

#config loader with error handling
try:
    #try 
    config = load_config()

    #Network configuration
    SYS_IP_ADDRESS = config['network']['SYS_IP_ADDRESS']
    PBX_IP_ADDRESS = config['network']['PBX_IP_ADDRESS']
    PORT_NUM = config['network']['PORT_NUM']
    PBX_MODEL = config['network']['PBX_MODEL']

    #SMDR Record File Configuration
    OUTPUT_FILE_TITLE = config['output_file']['OUTPUT_FILE_TITLE']
    OUTPUT_FILE_EXT = config['output_file']['OUTPUT_FILE_EXT']
    OUTPUT_FILE_DIR = config['output_file']['OUTPUT_FILE_DIR']

    #Log File Configuration
    LOG_FILE_TITLE = config['log_file']['LOG_FILE_TITLE']
    LOG_FILE_EXT = config['log_file']['LOG_FILE_EXT']
    LOG_FILE_DIR = config['log_file']['LOG_FILE_DIR']

    #SMDR Configuration
    SMDR_LOG_ROLLOVER = config['smdr']['SMDR_LOG_ROLLOVER']
    SMDR_MAX_SIZE_MBS = config['smdr']['SMDR_MAX_SIZE_MBS']

except Exception as e:
    print(f"Error loading configuration: {str(e)}")
    sys.exit(1)


#Global variables for cleanup
SERVER_SOCKET = None
CURRENT_CLIENT = None
LOG_FILE = None
SHUTDOWN_REQ = False

def signal_handler(signum, frame):
    #Handle SIGTERM signal
    global SHUTDOWN_REQ
    global LOG_FILE

    #check if LOG_FILE exists
    if not LOG_FILE:
        LOG_FILE = get_log_file_name()

    #write shutdown message to log
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
    shutdown_msg = f"{timestamp}: Received shutdown signal. Cleaning up and shutting down...\n"
    print(shutdown_msg)
    write_log_message(shutdown_msg, LOG_FILE)

    #set global SHUTDOWN_REQ
    SHUTDOWN_REQ = True

    #close active client with error handling
    if CURRENT_CLIENT:
        try:
            CURRENT_CLIENT.close()
        except Exception as e:
            close_client_err_msg = f"{timestamp}: Error closing active client: {str(e)}\n"
            print(close_client_err_msg)
            write_log_message(close_client_err_msg, LOG_FILE)
    
    #close active server socket with error handling
    if SERVER_SOCKET:
        try:
            SERVER_SOCKET.close()
        except Exception as e:
            close_socket_err_msg = f"{timestamp}: Error closing server socket: {str(e)}\n"
            print(close_socket_err_msg)
            write_log_message(close_client_err_msg, LOG_FILE)

def get_smdr_file_name():
    #get current time
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm')
    
    #make time stamped files for output
    output_file_name = OUTPUT_FILE_DIR + OUTPUT_FILE_TITLE + "-" + timestamp + "." + OUTPUT_FILE_EXT

    return output_file_name

def get_log_file_name():
    #Get Global Log File Variable
    global LOG_FILE
    #get current time
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm')
    
    #make time stamped files for output
    LOG_FILE = LOG_FILE_DIR + LOG_FILE_TITLE + "-" + timestamp + "." + LOG_FILE_EXT

    return LOG_FILE

def write_smdr_entry(data_list, file_path, log_file_path):
    #error handling for writing smdr entries
    try:
        #open file in append mode
        with open(file_path, mode='a', newline='') as file:
            #lock file
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            
            #try to write to the file, or write the error to the log
            try:
                writer = csv.writer(file)
                writer.writerow(data_list)
                return True
            except Exception as e:
                current_time = datetime.datetime.now()
                timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')

                smdr_write_error_message = f"{timestamp}: Error opening records file: {str(e)}\n"
                print(smdr_write_error_message)
                write_log_message(smdr_write_error_message, log_file_path)
            
            #unlock the file
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


        return True
    except Exception as e:
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')

        smdr_file_open_error = f"{timestamp}: Error opening records file: {str(e)}\n"
        print(smdr_file_open_error)
        write_log_message(smdr_file_open_error, log_file_path)
        return False

def write_log_message(data, file_path):
    #open log file (or create if it doesn't exist)
    with open(file_path, mode='a', newline='') as file:
        file.write(data)
    

def verify_smdr_data(data):
    #verify that the data received from the ip office has all the smdr fields
    split_data = data.split(',')
    if len(split_data) == 38:
        return True, split_data
    else:
        return False, None

def check_rollover_time(file_path, log_file_path):
    #error handling for time check
    try:
        #check the current time
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm')

        #get the time of the file's creation
        remove_l = OUTPUT_FILE_TITLE + "-"
        remove_r = "." + OUTPUT_FILE_EXT
        file_name = os.path.basename(file_path)
        if file_name.startswith(remove_l) and file_name.endswith(remove_r):
            file_timestamp = file_name[len(remove_l):-len(remove_r)]
        else:
            file_error_message = f"{timestamp}: Could not extract timestamp from file name: {file_name}\n"
            print(file_error_message)
            write_log_message(file_error_message, log_file_path)
            return file_path
        
        file_time = datetime.datetime.strptime(file_timestamp, '%Y-%m-%d-%Hh%Mm')

        #check if rollover time has elapsed, return the appropriate file path
        time_difference = current_time - file_time
        if time_difference >= datetime.timedelta(hours=SMDR_LOG_ROLLOVER):
            smdr_file_path = get_smdr_file_name()
            #log rollover event
            rollover_log_msg = f"{timestamp}: The SMDR log has been rolled over. The new file is: {smdr_file_path} \n"
            print(rollover_log_msg)
            write_log_message(rollover_log_msg, log_file_path)
            #return new file path
            return smdr_file_path
        else:
            #return current file path
            return file_path
    except Exception as e:
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')

        time_error_message = f"{timestamp}: Error checking rollover time: {str(e)}\n"
        print(time_error_message)
        write_log_message(time_error_message, log_file_path)
        return file_path

def check_rollover_size(file_path, log_file_path, max_size=SMDR_MAX_SIZE_MBS):
    #error handling for size check
    try:
        #check if file exists
        if os.path.exists(file_path):
            #calculate its size in MB
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            too_big = size_mb >= max_size
            if too_big:
                new_smdr_file_path = get_smdr_file_name()
                current_time = datetime.datetime.now()
                timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')  
                size_rollover_msg = f"{timestamp}: SMDR records file was rolled over as it exceed the maximum size of {max_size} Mbs"
                print(size_rollover_msg)
                write_log_message(size_rollover_msg, log_file_path)
                #return true if it's greater than or equal to the maximum size, or false otherwise
                return new_smdr_file_path
            else:
                return file_path 
        else:
            #return false if it doesn't exist
            return file_path
    
    except Exception as e:
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
        error_message = f"{timestamp}: Error checking file size: {str(e)}\n"
        print(error_message)
        write_log_message(error_message, log_file_path)
        return file_path

def collect_smdr_data():
    #get global variables
    global SERVER_SOCKET, CURRENT_CLIENT, LOG_FILE, SHUTDOWN_REQ

    #setup signal handler
    signal.signal(signal.SIGTERM, signal_handler)

    #get time stamped file names
    smdr_log_file = get_smdr_file_name()
    LOG_FILE = get_log_file_name()
    
    #opening server socket and setting up port with error handling
    try:
        #create SERVER_SOCKET
        SERVER_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #socket option should allow port reuse
        SERVER_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #set SERVER_SOCKET IP address and Port number
        SERVER_SOCKET.bind((SYS_IP_ADDRESS, PORT_NUM))
        #listen for connections
        SERVER_SOCKET.listen(5)

        #get current time
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss') 

        #write log entry
        listen_msg = f"{timestamp}: Listening for SMDR data on {SYS_IP_ADDRESS}:{PORT_NUM}...\n"
        print(listen_msg)
        write_log_message(listen_msg, LOG_FILE)

        while not SHUTDOWN_REQ:
            #socket error detection
            try:
                #timeout checks periodically if SHUTDOWN_REQ has been set
                SERVER_SOCKET.settimeout(1.0)
                try:
                    CURRENT_CLIENT, client_address = SERVER_SOCKET.accept()
                except socket.timeout:
                    continue

                connect_time = datetime.datetime.now()
                connect_accept_timestamp = connect_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
                client_accepted_msg = f"{connect_accept_timestamp}: Connection established with {client_address}\n"
                print(client_accepted_msg)
                write_log_message(client_accepted_msg, LOG_FILE)

                with CURRENT_CLIENT:
                    while not SHUTDOWN_REQ:
                        #socket client error detection
                        try:
                            #sets a timeout on receive to check SHUTDOWN_REQ
                            CURRENT_CLIENT.settimeout(1.0)
                            try:
                                raw_data = CURRENT_CLIENT.recv(1024)
                                if not raw_data:
                                    break
                            except socket.timeout:
                                continue
                            
                            #get timestamp of data for log
                            received_data_time = datetime.datetime.now()
                            raw_data_timestamp = received_data_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')

                            #unicode decode error detection
                            try:
                                #decode data
                                decoded_data = raw_data.decode('utf-8')
                                #verify data, get list of contents of CSV fields for writing to CSV file
                                is_valid, smdr_data = verify_smdr_data(decoded_data)

                                #save data to smdr csv file or write error to log file
                                if is_valid:
                                    smdr_log_file = check_rollover_time(smdr_log_file, LOG_FILE)
                                    smdr_log_file = check_rollover_size(smdr_log_file, LOG_FILE)
                                    write_successful = write_smdr_entry(smdr_data, smdr_log_file, LOG_FILE)
                                    if not write_successful:
                                        write_unsuccessful_msg = f"{raw_data_timestamp}: Did not successfully write data to SMDR records: {smdr_data}\n"
                                        print(write_unsuccessful_msg)
                                        write_log_message(write_unsuccessful_msg, LOG_FILE)
                                else: 
                                    data_error_msg = f"{raw_data_timestamp}: Erroneous data received: \n{decoded_data}\n"
                                    print(data_error_msg)
                                    write_log_message(data_error_msg, LOG_FILE)
                            except UnicodeDecodeError:
                                decode_error_msg = f"{raw_data_timestamp}: Failed to decode received data\n"
                                print(decode_error_msg)
                                write_log_message(decode_error_msg, LOG_FILE)
                        except socket.error as e:
                            if not SHUTDOWN_REQ:
                                client_error_time = datetime.datetime.now()
                                client_error_timestamp = client_error_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
                                client_error_msg = f"{client_error_timestamp}: Socket error while receiving data: {str(e)}\n"
                                print(client_error_msg)
                                write_log_message(client_error_msg, LOG_FILE)
            except socket.error as e:
                if not SHUTDOWN_REQ:
                    socket_error_time = datetime.datetime.now()
                    socket_error_timestamp = socket_error_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
                    socket_error_msg = f"{socket_error_timestamp}: Error accepting connections: {str(e)}\n"
                    print(socket_error_msg)
                    write_log_message(socket_error_msg, LOG_FILE)
    finally:
        #resource clean up
        if CURRENT_CLIENT:
            CURRENT_CLIENT.close()
        if SERVER_SOCKET:
            SERVER_SOCKET.close()
        
        if LOG_FILE:
            current_time = datetime.datetime.now()
            timestamp = current_time.strftime('%Y-%m-%d-%Hh%Mm%Ss')
            shutdown_complete_msg = f"{timestamp}: SMDR collector shutdown completed\n"
            print(shutdown_complete_msg)
            write_log_message(shutdown_complete_msg, LOG_FILE)
if __name__ == '__main__':
    collect_smdr_data()