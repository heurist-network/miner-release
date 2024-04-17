import logging

def configure_logging(config, miner_id=None):
    """
    Configures the logging settings for the miner process.

    This function sets up the logging configuration based on the provided config object
    and the miner ID. It constructs the log filename using the base log filename from
    the config and appends the miner ID if provided. The log file is opened in append
    mode, and the log messages are formatted with timestamp, name, level, and message.
    The log level is set to INFO.

    Parameters:
        config (BaseConfig): The configuration object containing the base log filename.
        miner_id (str, optional): The ID of the miner process. If provided, it will be
            appended to the log filename. Defaults to None.

    Returns:
        None
    """
    # Construct the log filename using both cuda_device_id and miner_id
    base_log_filename = config.log_filename.split('.')[0]
    if miner_id is not None:
        process_log_filename = f"{base_log_filename}_{miner_id}.log"
    else:
        process_log_filename = f"{base_log_filename}.log"

    print(f"Configuring log level to: {logging.getLevelName(logging.INFO)}. Log file name: {process_log_filename}")
    # Verifying log level

    # Setup logging with the configured filename and log level
    logging.basicConfig(
        filename=process_log_filename,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )