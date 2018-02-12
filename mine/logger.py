# coding=utf-8
import logging, os
from logging.handlers import TimedRotatingFileHandler

from settings import conf
log_dir = conf.work_dir+'/log'


class Logger(object):
    _instances = dict()

    @classmethod
    def getMyLogger(cls, name, level='info'):  # name should be : front back task
        if name in cls._instances.keys():
            return cls._instances[name]
        logger = logging.getLogger(name)
        lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
        filename = log_dir + '/flask/' + name
        logger.setLevel(lelel_dict[level])
        if not os.path.exists('%s/flask/' % log_dir):
            os.mkdir('%s/flask/' % log_dir)
        fh = TimedRotatingFileHandler(filename=filename, when="midnight", interval=1)  # , backupCount=2
        fh.suffix = "%Y-%m-%d.log"
        fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
        fm.datefmt = '%d %H:%M:%S'
        fh.setFormatter(fm)
        logger.addHandler(fh)
        cls._instances[name] = logger
        return logger
