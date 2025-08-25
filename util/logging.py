import logging
import os

class SingleLineFormatter(logging.Formatter):
    def format(self, record):
        # 先用父类格式化
        formatted = super().format(record)
        # 将换行符替换为 \n，制表符替换为 \t
        return formatted.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""

    formatter = SingleLineFormatter('[%(asctime)s] [%(levelname)s] [%(filename)s] [%(funcName)s] [%(lineno)d] - %(message)s')
    
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

if not os.path.exists('logs'):
    os.makedirs('logs')

default_logger = setup_logger('default', 'logs/default.log', level=logging.DEBUG)


