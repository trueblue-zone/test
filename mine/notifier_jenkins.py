# coding=utf-8
from os import path
import os, time
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_CLOSE_WRITE
import logging
from pymongo import MongoClient, collection, database, ReadPreference, ASCENDING
from zabbix_static import get_history

data_path = '/data/jenkins/jobs/'
# data_path = './jenkins/'
# data_bak = '/home/thli/workspace/Documents/docker_test/nextcloud/data_bak'
clock_time = 4
log_dir = os.getcwd() + '/log/'

client = MongoClient('mongodb://172.26.35.242:27061')
mongo_db = database.Database(client, 'jenkins')
table_builds = collection.Collection(mongo_db, 'builds', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_builds.create_index([('project', ASCENDING)])
table_builds.create_index([('builtOn', ASCENDING)])
# 存放项目构建历史结果，来自builds.xml文件，project,number,builton,result,starttime,duration
table_pro = collection.Collection(mongo_db, 'projects', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_pro.create_index([('project', ASCENDING)], unique=True)
# 存放table_builds的在pro上的粗略统计结果
table_pc = collection.Collection(mongo_db, 'computers', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_pc.create_index([('pc', ASCENDING)], unique=True)
# 存放table_builds的在host上的粗略统计结果

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


def insert_one(record):
    table_builds.insert_one(record)


def full_scan_sync(dir_):  # 寻找所有目录下的builds.xml文件
    logger.info('another_call, dir_ is:' + dir_)
    pros_d = os.listdir(dir_)
    i = 0
    for pros_ in pros_d:
        i += 1
        if i > 20:
            break
        p_ = os.path.join(dir_, pros_, 'builds')
        logger.info('parsing dir is:' + p_)
        if not os.path.exists(p_):
            continue
        if not os.path.isdir(p_):
            continue
        builds = os.listdir(p_)
        j = 0
        b_bak = 0
        for b in builds:
            try:
                b = int(b)
                b_bak = b
            except Exception:
                continue
            j += 1
            if j > 20:
                break
            re_ = table_builds.find_one({'project': pros_, 'number': b})
            if re_:  # mongodb里面没有存储致辞编译结果才去解析builds.xml文件
                logger.info('re_ is:' + str(re_))
                continue
            f = os.path.join(dir_, pros_, 'builds', str(b), 'build.xml')
            logger.info('parsing file is:' + f)
            re_build = parse_jenkins_fn(f)
            if re_build:
                table_builds.insert_one(re_build)
                _id = table_pro.find_one({'project': pros_}, {'_id': 1})
                logger.info('pro:%s, _id is:%s' % (pros_, str(_id)))
                if not _id:
                    table_pro.insert_one({'project': pros_, 'pcs': '*' * 100,
                                          'start_num': re_build['number'],
                                          'end_num': re_build['number']})
                    table_pro.update_one({'project': pros_}, {'$set': {'pcs': []}})
                table_pro.update_one({'project': pros_}, {'$addToSet': {'pcs': re_build['builtOn']}})
                _id = table_pc.find_one({'pc': re_build['builtOn']}, {'_id': 1})
                logger.info('pc:%s, _id is:%s' % (re_build['builtOn'], str(_id)))
                if not _id:
                    table_pc.insert_one({'pc': re_build['builtOn'], 'projects': '*' * 100})
                    table_pc.update_one({'pc': re_build['builtOn']}, {'$set': {'projects': []}})
                table_pc.update_one({'pc': re_build['builtOn']}, {'$addToSet': {'projects': pros_}})
        table_pro.update_one({'project': pros_}, {'$set': {'end_num': b_bak}})


class EventHandler(ProcessEvent):
    def process_IN_CREATE(self, event):
        print("Create file:%s." % path.join(event.path, event.name))
        logger.info("Create file:%s." % path.join(event.path, event.name))

    def process_IN_CLOSE_WRITE(self, event):
        if event.name != 'build.xml':
            return
        try:
            int(event.path.rsplit('/', 1)[-1])
        except Exception as e:
            logger.warn('not detected dir is:' + event.path)
            return
        print("IN_CLOSE_WRITE file:%s." % path.join(event.path, event.name))
        logger.info("IN_CLOSE_WRITE file:%s." % path.join(event.path, event.name))
        re_build = parse_jenkins_fn(path.join(event.path, event.name))
        if re_build:
            table_builds.insert_one(re_build)


def FsMonitor(path_='./'):
    mask = IN_CLOSE_WRITE
    logger.info("now starting monitor %s." % path)
    wm = WatchManager()
    wm.add_watch(path_, mask, auto_add=True, rec=True)
    # wm.add_watch(path_bak, mask, auto_add=True, rec=True)
    notifier = Notifier(wm, EventHandler())
    notifier.coalesce_events()
    while True:
        try:
            if notifier.check_events():
                print "check event true."
                notifier.read_events()
                notifier.process_events()
                print "process_events."
            else:
                print "check event false."
            print "sleeping."
            time.sleep(1)
        except KeyboardInterrupt:
            print "keyboard Interrupt."
            notifier.stop()
            break


def parse_jenkins_fn(lines_f):  # 解析结果xlm文件，返回一次编译结果的dict类型
    if not os.path.exists(lines_f):
        logger.warn('not exist file:' + lines_f)
        return False
    pro = lines_f.rsplit('/', 4)
    results = {'project': pro[-4], 'number': int(pro[-2]), 'startTime': 0, 'duration': 0, 'builtOn': 0, 'result': 0}
    num_type = ('number', 'startTime', 'duration')
    with open(lines_f, 'r') as lines_fn:
        lines = lines_fn.readlines()[-20:]
    flag = 0
    len_ = len(results) - 2  # 记录解析文件需要解析出多少条记录
    for l in lines:
        if flag >= len_:
            break
        l_ = l.replace('<', '>').split('>')
        if len(l_) < 5:
            continue
        if l_[1] in results.keys():
            if l_[1] in num_type:
                results[l_[1]] = int(l_[2][:-3])
            else:
                results[l_[1]] = l_[2]
            flag += 1
    if flag < 1:
        return False
    return results


def save_zabbix_data(host, start_time, duration):
    ret = get_history(host, start_time, duration)
    for r in ret:
        pass


def tidy_multy():
    all = table_builds.find({})
    base = set()
    i = 0
    for obj in all:
        key = obj['project'] + '-' + obj['number']
        if key in base:
            i += 1
            table_builds.delete_one({'_id': obj['_id']})
        else:
            base.add(key)
    logger.info('remove covered count is:' + str(i))
    logger.info('have all count as:' + str(len(base)))


def get_jenkins_pc(pc, start_time, duration):
    ret = []
    pass


def test():
    builds = [f for f in table_builds.find({})]
    ret = []
    for b in builds:
        if not b['builtOn'].startswith('172.26.35'):
            continue
        if b['builtOn'].endswith('_2') or b['builtOn'].endswith('_3'):
            b['builtOn'] = b['builtOn'].splite('_')[0]
        ret.append(get_history(b['builtOn'], b['startTime'], b['duration']))
    return ret

if __name__ == "__main__":
    pass
    # FsMonitor(data_path)
    # full_scan_sync(data_path)
    # tidy_multy()
    test()
    # #apt-get install davfs2
    # sudo mount -t davfs http://172.26.35.47:8087/remote.php/webdav/ /home/thli/workspace/Documents/docker_test/nextcloud/nextcloud_data
