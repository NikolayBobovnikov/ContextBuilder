import os
import logging

def setup_logging():
    logs_dir = os.path.join(".", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(os.path.join(logs_dir, "app.log"), mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh) 