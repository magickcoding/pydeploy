# encoding=utf-8

import os
import os.path
import logging
import logging.handlers
def init_logger(log_conf_items):
    """ 初始化logger.

    Args:
      log_conf_items: 配置项list.
    """
    LOGGER_LEVEL = {
            'DEBUG': logging.DEBUG,
            'INFO' : logging.INFO,
            'WARNING' : logging.WARNING,
            'ERROR' : logging.ERROR,
            'CRITICAL':logging.CRITICAL
            }
    for log_item in log_conf_items:
        logger = logging.getLogger(log_item['name'])
        path = log_item['file']
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        handler = logging.handlers.TimedRotatingFileHandler( log_item['file'], 'H', 1, 0 )
        handler.suffix='%Y%m%d%H'
        formatter = logging.Formatter(log_item['format'])
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(LOGGER_LEVEL[log_item['level']])

if __name__ == '__main__':
    log_items = [
            { 'name':'indexer', 'file':'a.log', 'level':'DEBUG', 'format':'%(asctime)s %(levelname)s %(message)s' },
            { 'name':'goods_id_dist', 'file':'b.log', 'level':'DEBUG', 'format':'%(asctime)s %(levelname)s %(message)s'},
            ]
    init_logger(log_items)
    logger = logging.getLogger('indexer')
    logger.info('haha')
