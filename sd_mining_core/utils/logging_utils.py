import logging
import warnings

def setup_warning_logging():
    """
    Configure Python warnings to be captured by the logging system.
    """
    logging.captureWarnings(True)
    for category in [DeprecationWarning, FutureWarning]:
        warnings.filterwarnings('default', category=category)
    # Configure the warnings logger
    logger = logging.getLogger('py.warnings')
    logger.setLevel(logging.WARNING)  # Adjust the level as needed

def configure_logging(cuda_device_id, config, miner_id=None):
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Construct the log filename using both cuda_device_id and miner_id
    base_log_filename = config.log_filename.split('.')[0]
    if miner_id is not None:
        process_log_filename = f"{base_log_filename}_{cuda_device_id}_{miner_id}.log"
    else:
        process_log_filename = f"{base_log_filename}_{cuda_device_id}.log"
    print(f"Configuring log level to: {logging.getLevelName(log_level)}. Log file name: {process_log_filename}")  # Verifying log level
    
    # Setup logging with the configured filename and log level
    logging.basicConfig(
        filename=process_log_filename,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=log_level
    )

    setup_warning_logging()

    # Optionally, set higher log levels for external libraries to reduce noise
    for ext_logger in ['urllib3', 'botocore']:
        logging.getLogger(ext_logger).setLevel(logging.CRITICAL)
        
def initialize_logging_and_args(config, cuda_device_id=None, miner_id=None):
    try:
        # Retrieve parsed argument values from the config object
        log_level = config.log_level
        auto_confirm = config.auto_confirm
        exclude_sdxl = config.exclude_sdxl
        skip_signature = config.skip_signature
        skip_checksum = config.skip_checksum

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            logging.error(f"Invalid log level: {log_level}. Must be one of {valid_log_levels}.")

        # Update config with parsed arguments
        config.log_level = log_level if log_level else "INFO"
        config.auto_confirm = auto_confirm
        config.exclude_sdxl = exclude_sdxl
        config.skip_signature = skip_signature
        config.skip_checksum = skip_checksum

        # Validate cuda_device_id
        if cuda_device_id is not None:
            try:
                cuda_device_id = int(cuda_device_id)
            except ValueError:
                logging.error(f"Invalid cuda_device_id: {cuda_device_id}. Must be an integer.")
            if cuda_device_id < 0:
                logging.error("cuda_device_id cannot be negative.")
        else:
            cuda_device_id = 0  # Default value if not provided

        # Configure logging with the potentially updated config
        configure_logging(cuda_device_id, config, miner_id)

    except Exception as e:
        # Here, you can decide how you want to handle the exception.
        # For example, log an error message and exit, or raise the exception further after logging.
        logging.error(f"Failed to initialize logging and arguments: {e}")

    return config

