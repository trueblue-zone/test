from os import path
import os, time
import logging
from pymongo import MongoClient, collection, database, ReadPreference, ASCENDING

clock_time = 4
log_dir = os.getcwd() + '/log/'

client = MongoClient('mongodb://172.26.35.242:27061')
mongo_db = database.Database(client, 'jenkins')
table = collection.Collection(mongo_db, 'builds', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_pro = collection.Collection(mongo_db, 'projects', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_pc = collection.Collection(mongo_db, 'computers', read_preference=ReadPreference.SECONDARY_PREFERRED)

def getMyLogger(name, level='info'):
    logger = logging.getLogger(name)
    filename = name
    lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
    logger.setLevel(lelel_dict[level])
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    fh = logging.FileHandler(filename=filename)  # , backupCount=2
    fh.suffix = "%Y-%m-%d.log"
    fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
    fm.datefmt = '%d %H:%M:%S'
    fh.setFormatter(fm)
    logger.addHandler(fh)
    return logger


logger = getMyLogger('parse')


def parse_data():
    pass


# results = {'project': pro[-4], 'number': pro[-2], 'startTime': 0, 'duration': 0, 'builtOn': 0, 'result': 0}
def parse_test(project_name=None):
    if project_name:
        pass
        result = table.find({'project': project_name})
    else:
        result = table_pro.find({}).limit(1)[0]
        result = table.find({'project':result['project']})
    v1 = {}
    v2 = {}
    result = [f for f in result]
    for r in result:
        # ips.append(r['builtOn'])
        # if v2.get(r['builtOn'], -1) == -1:
        #     v2[r['builtOn']] = 0
        #     v1[r['builtOn']] = 0
        # if r['result'] == 'FAILURE':
        # else:
        #     v1[r['builtOn']] += 1
            v2[r['builtOn']] = v2.get(r['builtOn'], 0) + 1
            v1[r['builtOn']] = v1.get(r['builtOn'], 0) + 1
    ips = v2.keys()
    v1 = v1.values()
    v2 = v2.values()
    return (ips, v1, v2)
