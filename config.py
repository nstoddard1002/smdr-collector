import os
import json

def load_config(config_file_path='config.json'):
    #Load configuration file 
    #This function returns a dictionary of all the configuration paramters

    #open config file with error handling
    try:
        with open(config_file_path, 'r') as file:
            config = json.load(file)
        
        #required fields, used for validation
        required_fields = {
            'network': ['SYS_IP_ADDRESS', 'PBX_IP_ADDRESS', 'PORT_NUM', 'PBX_MODEL'],
            'output_file': ['OUTPUT_FILE_TITLE', 'OUTPUT_FILE_EXT', 'OUTPUT_FILE_DIR'],
            'log_file': ['LOG_FILE_TITLE', 'LOG_FILE_EXT', 'LOG_FILE_DIR'],
            'smdr': ['SMDR_LOG_ROLLOVER', 'SMDR_MAX_SIZE_MBS']
        }

        for section, fields in required_fields.items():
            if section not in config:
                raise KeyError(f"Missing section '{section}' in config file")
            for field in fields:
                if field not in config[section]:
                    raise KeyError(f"Missing field '{field}' in section '{section}'")
        
        #create directories if they don't exist
        os.makedirs(config['output_file']['OUTPUT_FILE_DIR'], exist_ok=True)
        os.makedirs(config['log_file']['LOG_FILE_DIR'], exist_ok=True)

        #return validated dictionary of values
        return config
    
    #error handling
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading configuration: {str(e)}")
