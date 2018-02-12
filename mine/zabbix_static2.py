import pymysql, sqlite3
import time

# db = pymysql.connect("172.26.35.211", "root", "root", "zabbix")
db = pymysql.connect("172.26.35.123", "zabbix", "zabbix", "zabbix")
cursor = db.cursor()
hosts_jenkins = ['10', '113', '113_2', '123', '123_2', '133', '134', '136', '137', '140', '143', '149', '151',
                 '151_2', '167', '175', '178', '184', '186_2', '198', '203', '204', '208', '210', '212', '216',
                 '216_2', '218', '218_2', '224', '224_2', '225', '225_2', '226_2', '230', '235_2', '242_2',
                 '245', '245_2', '249_2', '30_2', '40', '47', '61', '63', '66', '69', '70', '82', '85'
                 ]
# sql = "SELECT * FROM users"
# sql1 = "SELECT host, hostid  FROM hosts where hostid in (select hostid, itemid from items where key_='system.cpu.load[percpu,avg15]')"

conn = sqlite3.connect('./mydb.sqlite', check_same_thread=False)
cur = conn.cursor()
item_keys_ = ('system.cpu.load[percpu,avg15]', 'vm.memory.size[available]')
# item_keys_ = ('system.cpu.load[percpu,avg15]', 'vm.memory.size[available]',
#               'vfs.fs.size[{#FSNAME},free]', 'net.if.in[{#IFNAME}]')


# sql = "SELECT itemid, value  FROM history limit 10 "
# sql = "SELECT itemid, value  FROM history where itemid = 25065 "
# sql = "SELECT itemid, value  FROM history where itemid in (25065,25066,25067)"
# sql = "SELECT itemid, value  FROM history where itemid in (25065,25066,25067) and clock > %d order by clock desc"
# sql = "SELECT itemid, value  FROM history where itemid in %s order by clock desc limit %d"
# sql_ = sql % (str(a), len(a))

def save_dicts(hosts=None):
    cur.execute("create table IF NOT EXISTS host_item "
                "( host char(50) not null, hostid int not null, "
                "key_ char(50) not null, itemid int primary key not null)")
    sql_insert = "insert into host_item (host, hostid, key_, itemid) values %s"
    sql_item = "select hosts.host, hosts.hostid, items.key_, items.itemid " \
               "from items,hosts where hosts.hostid=items.hostid " \
               "and items.key_ in %s and hosts.status =0 and hosts.available!=0" % str(item_keys_)
    if hosts:
        sql_item += " and hosts.host in %s" % str(hosts)

    cursor.execute(sql_item)
    results = cursor.fetchall()
    for row in results:
        cur.execute(sql_insert % str(tuple(row)))
    conn.commit()
    if hosts:
        return {f[-1]: f[:-1] for f in results}


def get_dicts(host):
    sql_item = "select * from host_item where host='%s'" % host
    cur.execute(sql_item)
    results = cur.fetchall()
    ret = {}
    for row in results:
        ret[row[-1]] = row[:-1]
    if len(ret) == 0:
        return save_dicts(host)
    return ret


def get_history(host, start_time, duration):
    item_host_dict = get_dicts(host)
    host_history = {f: [] for f in item_keys_}
    limit_len = 10000
    wh = 0
    dur_ = 2 * 15 * 60
    start_time_ = start_time - dur_
    end_time_ = start_time + duration + dur_
    time_sql_start = time.time()
    for t in ('history', 'history_uint'):
        sql = "SELECT itemid, value,clock  FROM " + t \
              + " where itemid in %s and clock > %d and clock < %d limit %d,%d"
        if duration:
            sql += " and clock < %d"
            sql_ = sql % (str(tuple(item_host_dict.keys())), start_time_, end_time_,limit_len, wh, limit_len)
        else:
            sql_ = sql % (str(tuple(item_host_dict.keys())), start_time_)
        cursor.execute(sql_)
    results = cursor.fetchall()
    results = [f for f in results]
    results.sort(key=lambda x: x[2])
    for row in results:
        # host_history[item_host_dict[row[0]][2]].append(row[1])
        host_history.append({'pc':[item_host_dict[row[0]][2]],item_keys_[0]:[],item_keys_[1]:[]})
    time_sql_end = time.time()
    print('used time is:%d' % (time_sql_end - time_sql_start))

    return host_history


def get_():
    ret = []
    hosts_jenkins_ = ['172.26.35.' + f for f in hosts_jenkins]
    hosts_jenkins_ = hosts_jenkins_[:2]
    hosts_jenkins_ = tuple(hosts_jenkins_)
    # save_dicts(hosts_jenkins_)
    for host in hosts_jenkins_:
        ret.append(get_history(host, 0))


get_()
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
