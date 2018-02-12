# coding=utf-8
import pymysql
import time
from pymongo import MongoClient, collection, database, ReadPreference, ASCENDING

# db = pymysql.connect("172.26.35.211", "root", "root", "zabbix")
db = pymysql.connect("172.26.35.123", "zabbix", "zabbix", "zabbix")
cursor = db.cursor()
hosts_jenkins = ['10', '113', '113_2', '123', '123_2', '133', '134', '136', '137', '140', '143', '149', '151',
                 '151_2', '167', '175', '178', '184', '186_2', '198', '203', '204', '208', '210', '212', '216',
                 '216_2', '218', '218_2', '224', '224_2', '225', '225_2', '226_2', '230', '235_2', '242_2',
                 '245', '245_2', '249_2', '30_2', '40', '47', '61', '63', '66', '69', '70', '82', '85'
                 ]
client = MongoClient('mongodb://172.26.35.242:27061')
mongo_db = database.Database(client, 'jenkins')
table_item = collection.Collection(mongo_db, 'items', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_item.create_index([('item_id', ASCENDING)])
# table_item存放监控item和host的对应关系，itemid，itemkey，hostid，host
table_history = collection.Collection(mongo_db, 'historys', read_preference=ReadPreference.SECONDARY_PREFERRED)
table_history.create_index([('hosts', ASCENDING)])
item_keys_ = {'system.cpu.load[percpu,avg15]': 'history', 'vm.memory.size[available]': 'history_uint'}
# table_history存放一个个host的资源占用情况的历史记录，host，starttime，duration，key1:[],key2[]

# item_keys_ = ('system.cpu.load[percpu,avg15]', 'vm.memory.size[available]',
#               'vfs.fs.size[{#FSNAME},free]', 'net.if.in[{#IFNAME}]')

def get_item(item_attrs, update=False):
    if not update or not item_attrs.get('itemid'):
        items = table_item.find(item_attrs)
        items = {f['itemid']: f for f in items}
        if len(items) > 0:
            return items
    host = item_attrs['host']
    if not update and not host:
        items = table_item.find({})
        items = {f['itemid']: f for f in items}
        if len(items) > 0:
            return items
    sql_item = "select hosts.host, hosts.hostid, items.key_, items.itemid " \
               "from items,hosts where hosts.hostid=items.hostid " \
               "and items.key_ in %s and hosts.status =0 and hosts.available!=0" % str(tuple(item_keys_.keys()))
    if host:
        sql_item += " and hosts.host = '%s'" % str(host)
    else:
        hosts_jenkins_ = tuple(['172.26.35.' + f for f in hosts_jenkins if not f.endswith('_2')])
        sql_item += " and hosts.host in %s" % str(hosts_jenkins_)
    items = dict()
    cursor.execute(sql_item)
    results = cursor.fetchall()
    for row in results:
        # cur.execute(sql_insert % str(tuple(row)))
        record = {'host': row[0], 'host_id': row[1], 'key': row[2], 'itemid': row[3]}
        items[row[3]] = record
        table_item.insert_one(record)
    return items


# def get_dicts(host):
#     sql_item = "select * from host_item where host='%s'" % host
#     cur.execute(sql_item)
#     results = cur.fetchall()
#     ret = {}
#     for row in results:
#         ret[row[-1]] = row[:-1]
#     if len(ret) == 0:
#         return get_item(host)
#     return ret


def get_history(host, start_time, duration):
    # 只支持一个host的历史获取
    if type(start_time) is not int:
        if len(start_time) > 10:
            start_time = start_time[:10]
        start_time = int(start_time)
    if type(duration) is not int:
        duration = int(duration[:-3])
    ret = {'pc': host, 'start_time': start_time, 'duration': duration}
    ret_ = table_history.find_one(ret)
    if ret_:
        return ret_
    item_host_dict = get_item({'host': host})
    host_history = {f: [] for f in item_keys_}  # 放的是itemkey:[]
    dur_ = 1 * 15 * 60
    start_time_ = start_time - dur_
    end_time_ = start_time + duration + dur_
    time_sql_start = time.time()
    item_keys = {f: item_keys_[item_host_dict[f]['key']] for f in item_host_dict}
    # item_keys放的是itemid:table键值对
    for t in item_keys:
        sql = "SELECT value,clock  FROM " + item_keys[t] \
              + " where itemid = %s and clock > %d and clock < %d"
        sql_ = sql % (t, start_time_, end_time_)
        cursor.execute(sql_)
        results = cursor.fetchall()
        results = [f for f in results]
        results.sort(key=lambda x: x[1])
        for row in results:
            host_history[item_host_dict[t]['key']].append(row[0])
            # host_history.append({'pc':host,item_keys_[0]:[],item_keys_[1]:[]})
    time_sql_end = time.time()
    print('used time is:%d' % (time_sql_end - time_sql_start))
    ret = dict(ret.items() + host_history.items())
    table_history.insert_one(ret)
    return ret


def get_():
    ret = []
    hosts_jenkins_ = ['172.26.35.' + f for f in hosts_jenkins]
    hosts_jenkins_ = hosts_jenkins_[:2]
    hosts_jenkins_ = tuple(hosts_jenkins_)
    # get_item(hosts_jenkins_)
    for host in hosts_jenkins_:
        ret.append(get_history(host, 0))


# get_()
# get_history(host, start_time, duration=None)
# MariaDB [zabbix]> select key_,hostid from items where hostid=10001;
# +-------------------------------+--------+
# | key_                          | hostid |
# +-------------------------------+--------+
# | agent.hostname                |  10001 |
# | agent.ping                    |  10001 |
# | agent.version                 |  10001 |
# | kernel.maxfiles               |  10001 |
# | kernel.maxproc                |  10001 |
# | net.if.discovery              |  10001 |
# | net.if.in[{#IFNAME}]          |  10001 |
# | net.if.out[{#IFNAME}]         |  10001 |
# | proc.num[,,run]               |  10001 |
# | proc.num[]                    |  10001 |
# | system.boottime               |  10001 |
# | system.cpu.intr               |  10001 |
# | system.cpu.load[percpu,avg15] |  10001 |
# | system.cpu.load[percpu,avg1]  |  10001 |
# | system.cpu.load[percpu,avg5]  |  10001 |
# | system.cpu.switches           |  10001 |
# | system.cpu.util[,idle]        |  10001 |
# | system.cpu.util[,interrupt]   |  10001 |
# | system.cpu.util[,iowait]      |  10001 |
# | system.cpu.util[,nice]        |  10001 |
# | system.cpu.util[,softirq]     |  10001 |
# | system.cpu.util[,steal]       |  10001 |
# | system.cpu.util[,system]      |  10001 |
# | system.cpu.util[,user]        |  10001 |
# | system.hostname               |  10001 |
# | system.localtime              |  10001 |
# | system.swap.size[,free]       |  10001 |
# | system.swap.size[,pfree]      |  10001 |
# | system.swap.size[,total]      |  10001 |
# | vfs.file.cksum[/etc/passwd]   |  10001 |
# | vfs.fs.discovery              |  10001 |
# | vfs.fs.inode[{#FSNAME},pfree] |  10001 |
# | vfs.fs.size[{#FSNAME},free]   |  10001 |
# | vfs.fs.size[{#FSNAME},pfree]  |  10001 |
# | vfs.fs.size[{#FSNAME},total]  |  10001 |
# | vfs.fs.size[{#FSNAME},used]   |  10001 |
# | vm.memory.size[available]     |  10001 |
# | vm.memory.size[total]         |  10001 |
