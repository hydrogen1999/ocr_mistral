from loguru import logger
import os
import datetime
import sys

# Configure logger to create a log file for each date
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

today = datetime.datetime.now().strftime("%Y-%m-%d")
log_file = os.path.join(log_dir, f"{today}.log")

# Remove default logger and add file and console logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(log_file, rotation="12:00", level="INFO")