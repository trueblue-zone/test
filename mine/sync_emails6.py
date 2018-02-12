#!/usr/bin/python
# -*- coding:utf8 -*-
import sqlite3
import json, re
import hashlib
from pymongo import MongoClient, collection, database, ReadPreference, ASCENDING
import pyhdfs
import os, Queue, threading, time, sys
import logging, socket, fcntl, struct
from os import path
import commands
import signal

file_queue = Queue.Queue(maxsize=100)
mes_queue = Queue.Queue(maxsize=200)

# file_size_limit = 63 * 1024 * 1024
file_size_limit = 2 * 1024 * 1024
mongodb_uri = 'mongodb://172.26.35.136:27041,172.26.35.154:27042,172.26.35.242:27043'
client = MongoClient(mongodb_uri)
dba = database.Database(client, 'admin')
dba.authenticate('test', 'test')
db = database.Database(client, 'static_web_test')
table = collection.Collection(db, 'emails', read_preference=ReadPreference.SECONDARY_PREFERRED)
# table_contacts = collection.Collection(db, 'emails_contacts', read_preference=ReadPreference.SECONDARY_PREFERRED)
# table_contacts.create_index([('name', ASCENDING)], unique=True)
# table_contacts 存放所有机器上pc上解析来的联系人别名，包括 Ac Bd ，Aaaa 等别名，作为三级缓存使用
to_contacts_reserved = dict()  # 存放本地联系人别名，是table_contacts的一部分，生命周期比它短，是这个脚本的生命长度，作为二级缓存

hdfs_client = pyhdfs.HdfsClient('172.26.35.242:50070')
sync_duration = 10
sync_times = 30

# work_dir = '/data/dock/docker_test/email'
work_dir = os.getcwd() + '/email'
logger = None


# Define signal handler function
# def myHandler(signum, frame):
#     print("Now, it's the time")
#     exit()
#
#
# signal.signal(signal.SIGTERM, myHandler)


def goto_workspace(wdir):
    username = 'dock'
    if not os.path.exists(wdir):
        log1 = commands.getoutput('sudo mkdir -p %s' % wdir)
        print(log1)
        log1 = commands.getoutput('sudo chown -R %s:%s %s' % (username, username, wdir))
        print(log1)
        log1 = commands.getoutput('sudo chmod -R a+r  %s' % wdir)
        print(log1)
    os.chdir(wdir)


def get_mylogger(name='emails', level='info'):
    log = logging.getLogger(name)
    lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
    current_time = time.strftime('%Y-%m-%d', time.localtime())
    filename = current_time + name
    log.setLevel(lelel_dict[level])
    log_dir = work_dir + '/logs/'
    if not os.path.exists(log_dir):
        log1 = commands.getoutput('sudo mkdir -p %s' % log_dir)
        log.info(log1)
        username = 'dock'
        log1 = commands.getoutput('sudo chown -R %s:%s %s' % (username, username, log_dir))
        print(log1)
        log1 = commands.getoutput('sudo chmod -R a+w  %s' % log_dir)
        print(log1)
    fh = logging.FileHandler('%s/%s.log' % (log_dir, filename), 'w')
    fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
    fm.datefmt = '%d %H:%M:%S'
    fh.setFormatter(fm)
    log.addHandler(fh)
    return log


def cp_myself(fn):
    fname = __file__
    logger.info('in cp_myself, this file name is:%s' % fname)
    if fname is not fn:
        log = commands.getoutput('cp %s %s' % (fname, fn))
        logger.info(log)


def get_ip_address():
    ifnames = ['eth0', ]
    for ifname in ifnames:
        logger.info("try to get %s's ip" % ifname)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])
            logger.info("get %s's ip is:" + str(ip))
            return ip
        except Exception as e:
            logger.warn('exception on:' + str(e.message))
    logger.error("try failed, no ip for interfaces:%s" % str(ifnames))
    sys.exit(1)


def get_email_path():
    logger.info('start get_userpath')
    s, user = commands.getstatusoutput('sudo ls /home/')
    logger.info('ls /home/ ,log is:' + user)
    user = user.split('\n')[0]
    logger.info('get user is:' + user)
    s, l = commands.getstatusoutput('sudo chmod a+xr /home/%s/' % user)
    logger.info('chmod ,log is:' + l)
    s, l = commands.getstatusoutput('sudo chmod a+xr /home/%s/.thunderbird/' % user)
    logger.info('chmod ,log is:' + l)
    s, ps = commands.getstatusoutput('sudo ls /home/%s/.thunderbird/' % user)
    logger.info('ls thunderbird ,log is:' + ps)
    ps = ps.split('\n')
    path_ = '/hhhhh**'
    for p in ps:
        if '.default' in p:
            path_ = '/home/%s/.thunderbird/%s/global-messages-db.sqlite' % (user, p)
            s, l = commands.getstatusoutput('sudo chmod a+xr /home/%s/.thunderbird/%s/' % (user, p))
            logger.info('chmod ,log is:' + l)
            s, l = commands.getstatusoutput(
                'sudo chmod a+xr /home/%s/.thunderbird/%s/global-messages-db.sqlite' % (user, p))
            logger.info('chmod ,log is:' + l)
            break
    logger.info('get email sqlite path:%s' % path_)
    if os.path.exists(path_):
        return path_
    else:
        logger.error('not exist path_')
        sys.exit(1)


def parse_file(contacts_fn):
    lines = open(contacts_fn, 'r').readlines()
    i = -1000
    global work_dir, temp_fn1, temp_fn2, temp_fn3, temp_fn4, temp_fn5, temp_fn6
    work_dir = work_dir + '/test/'
    if not os.path.exists(work_dir):
        log1 = commands.getoutput('mkdir -p %s' % work_dir)
        logger.info(log1)
    temp_fn1 = open(work_dir + '/contacts_results1', 'a')  # 存放最为靠谱的联系人解析结果，一般为<>里面解析出来的
    temp_fn2 = open(work_dir + '/contacts_results2', 'a')
    temp_fn3 = open(work_dir + '/contacts_parse', 'a')
    temp_fn4 = open(work_dir + '/tmp_not_exist', 'a')
    temp_fn5 = open(work_dir + '/tmp_not_equal', 'a')
    temp_fn6 = open(work_dir + '/result_recommend', 'a')
    for l in lines:
        i += 1
        # parse_contacts(l, i)


def get_news(conditions):
    logger.info('start get_news thread')
    email_path = get_email_path()
    # email_path = work_dir+'/global-messages-db.sqlite'
    conn = sqlite3.connect(email_path, check_same_thread=False)
    conn_ = sqlite3.connect(work_dir + '/mydb.sqlite', check_same_thread=False)
    cur = conn.cursor()
    cur_my = conn_.cursor()
    cur_my.execute('create table IF NOT EXISTS con_hash \
    ( conversationId int primary key not null, hashId char(50) not null, docid int not null)')
    conn_.commit()
    sync_count = 30
    id_record_len = 180
    reserved_ids_fn = open(work_dir + '/ids.log', 'a')

    def get_lastid(the_newest=False):
        if the_newest:
            ret = [f for f in cur.execute('select id from messages order by id desc limit 1')]
            return ret[0][0]
        with open(work_dir + '/ids.log', 'r') as reserved_ids_fn_:
            reserved_ids_fn_.seek(0, 2)
            len_ids = reserved_ids_fn_.tell()
            if len_ids > id_record_len:
                reserved_ids_fn_.seek(-id_record_len, 2)
            else:
                reserved_ids_fn_.seek(-len_ids, 2)
            lines = reserved_ids_fn_.readlines()
        if len(lines) > 0:
            return int(lines[-1].split(',')[2])
        else:
            return -1

    # reserved_ids = [get_lastid(False)]
    reserved_ids = [get_lastid(True)-10]
    # reserved_ids = [-1]
    j = 0  # 记录解析了多少个邮件的收件的地址
    contacts_arr = ['null']

    def get_contacts(id):
        cmd_sql = 'select contactID, value from identities ' \
                  'where contactID >= %d and kind="email" order by contactID asc' % id
        contacts = cur.execute(cmd_sql).fetchall()
        i = id
        for con in contacts:
            if con[0] == i:
                contacts_arr.append(con[1])
            else:
                contacts_arr.append("null")
            i += 1
        del contacts

    get_contacts(1)
    hash_re_ids = {}
    while True:
        last_id = reserved_ids[-1]
        logger.info('last saved id is:%d' % last_id)
        cmd_sql = 'select docid, conversationID, jsonAttributes, date, c0body, c1subject, c2attachmentNames ' \
                  'from messagesText_content , messages ' \
                  'where messagesText_content.docid=messages.id and messagesText_content.docid>%d ' \
                  'and messages.jsonAttributes is not null' % last_id
        if conditions:
            cmd_sql += ' and ' + conditions
            logger.info('with conditions sql cmd is:' + cmd_sql)
        contents = cur.execute(cmd_sql).fetchall()
        count = len(contents)
        i = 0
        logger.info('get some new emails,count:%d' % count)
        if count < 1:
            time.sleep(sync_duration)
            continue
        record_time = time.localtime()
        record_time_ = '%d-%d-%d,%d:%d:%d' % (record_time.tm_year, record_time.tm_mon, record_time.tm_mday,
                                              record_time.tm_hour, record_time.tm_min, record_time.tm_sec)
        for content in contents:
            i += 1
            j += 1
            try:
                attrs = json.loads(content[2])
            except Exception as e:
                logger.warn('try json load, occur errors, mes is:' + str(e.message))
                logger.info('content[2] is:' + content[2])
            try:
                author = contacts_arr[attrs['43']]
                to = []
                for c in attrs['44']:
                    to.append(contacts_arr[c])
            except Exception as e:
                logger.warn('maybe for contacts id, occur errors, mes is:' + str(e.message))
                get_contacts(len(contacts_arr))
                author = contacts_arr[attrs['43']]
                for c in attrs['44']:
                    to.append(contacts_arr[c])
            if len(to) > 0:
                to = ':'.join(set(to))
            else:
                logger.error('to contacts has nothing')
            mes = json.dumps(content[3:7] + (author, to))
            h = hashlib.md5(mes)
            hash_id = h.hexdigest()

            hash_re = hash_re_ids.get(content[1])
            if not hash_re:
                hash_re = cur_my.execute(
                    'select conversationId, hashId from con_hash where conversationId = %d' % content[1])
                hash_re = [f for f in hash_re]
                if len(hash_re) < 1:
                    re_mes = table.find_one({'_id': hash_id}, {'_id': 0, 'reply': 1})
                    if re_mes is not None:
                        hash_re = re_mes['reply']
                    else:
                        hash_re = hash_id
                    cur_my.execute('insert into con_hash (conversationId, hashId, docid) values(%d, "%s", %d)' % (
                        content[1], hash_re, content[0]))
                    conn_.commit()
                else:
                    hash_re = hash_re[0][1]
                hash_re_ids[content[1]] = hash_re

            re_mes = table.find_one({'_id': hash_id}, {'_id': 0, 'reply': 1})
            # if True:
            if re_mes is None:
                logger.info('insert_one ')
                table.insert_one({'_id': hash_id, 'date': content[3], 'from': author, 'to': to, 'reply': hash_re,
                                  'content': content[4], 'subject': content[5], 'attach': content[6]})
            else:
                if re_mes['reply'] != hash_re:
                    table.update_one({'_id': hash_id, 'reply': hash_re})
            reserved_ids_fn.write(
                'line:%d,saved id is,%d,and hash_id is,%s,at time,%s\n' % (j, content[0], hash_id, record_time_))
            # if i > 20:
            #     logger.info('mes_queue put start')
            #     break
        sync_count += 1
        if sync_count >= sync_times:
            sync_count = 0
            reserved_ids_fn.flush()
            logger.info('reserved_ids_fn flushed')
        reserved_ids.append(contents[-1][0])
        logger.info('sleep start')
        logger.info('appended last reserved_id is:%d' % contents[-1][0])
        reserved_ids_fn.flush()
        # break
        # time.sleep(sync_duration)


def append_to_file():
    logger.info('start append_to_file thread')
    local_ip = get_ip_address()
    file_name = local_ip + '_1'
    fn = open(path.join(work_dir, file_name), 'w+')
    flush_count = 0
    while True:
        mes = mes_queue.get()

        file_len = os.path.getsize(path.join(work_dir, file_name))
        lent = len(mes[0])
        if file_len + lent > file_size_limit or mes[0] == 'start':
            fn.close()
            file_queue.put(file_name)
            logger.info('put a file:%s to queue' % file_name)
            fsp = file_name.rsplit('_', 1)
            file_name = fsp[0] + '_' + str(int(fsp[1]) + 1)
            fn = open(file_name, 'w+')
            logger.info('open a new file:%s' % file_name)
        if len(mes) > 1:
            fn.write('--------------hash_id:%s----------\n' % mes[1])
            fn.write(mes[0])
            fn.write('\n')
        if flush_count > 10:
            flush_count = 0
            fn.flush()
        flush_count += 1


def push_to_hdfs():
    logger.info('start push_to_hdfs thread')
    while True:
        f = file_queue.get()
        logger.info('push file is:' + f)
        # hdfs_client.copy_from_local(path.join(work_dir, f), '/data/email_contents/%s' % f)


def main():
    goto_workspace(work_dir)
    global logger
    logger = get_mylogger()
    logger.info('the logger init ok, now init other thins')
    # cp_myself(work_dir + '/sync_emails.py')
    condition = None
    sys.argv.append('sirui.wang@tcl.com')
    # sys.argv.append('tenghui.li@tcl.com')
    if len(sys.argv) > 1:
        condition = '(c3author like "%{0}%" or c4recipients like "%{0}%")'.format(sys.argv[1])
    get_news(condition)


if __name__ == '__main__':
    main()


    # 解析邮件往返关系有个关键的 问题，数据库里以什么字段表示出邮件之间的关系？而靠读取内容或是主题来判断邮件的往返关系是不可靠的
    # 现在能想到的手段就是用数据库自己的表达来识别往返关系（即通过conversationid），
    # 而这些数据库是分离在各个机器上，并且数据是部分相同的（在hashid能正确计算的前提下）
    # 所以用以上方式的话，就会在获取和存储手段上出现问题：
    # 1 各个机器上读取数据的先后关系，导致往返关系可能需要更新
    # 2部分数据在一些机器上已经被删除，导致这部分邮件的往返关系不能完全解析，
    # 而其他机器又解析出是同一个往返关系长的一部分邮件
    # 3 是2的一种极端情况，这封邮件的回复历史在这个机器都被删除了，而其他机器只留下了这封邮件的回复历史，导致这封邮件的回复历史不可能被解析出来
