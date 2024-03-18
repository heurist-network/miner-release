import logging

def configure_logging(config, miner_id=None):
    # Construct the log filename using both cuda_device_id and miner_id
    base_log_filename = config.log_filename.split('.')[0]
    if miner_id is not None:
        process_log_filename = f"{base_log_filename}_{miner_id}.log"
    else:
        process_log_filename = f"{base_log_filename}.log"
    print(f"Configuring log level to: {logging.getLevelName(logging.INFO)}. Log file name: {process_log_filename}")  # Verifying log level
    
    # Setup logging with the configured filename and log level
    logging.basicConfig(
        filename=process_log_filename,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )