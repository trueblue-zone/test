#!/usr/bin/python2.7
# -*- coding:utf8 -*-
import commands, sys, os
import argparse, logging, time

config_ip = '172.26.35.211'
work_dir = '/data/dock/docker_test/service/mongo'
mongo_conf_dir = work_dir + "/etc_mongo"
log_dir = 'log'
config_runed_file = 'shared_replica.log'

host = '172.26.35.133'
# host指定的是容器服务将部署在哪些节点，如果有多个节点的host使用还需要分化，都会有多个
# 同一个机器用的端口必须不同，不同机器用的可以相同
host_port = '-H %s:4243' % host

configdb_name = 'mongo_cfg%d'
configdb_vol = '/data/dock/docker_test/mongodb/test/cfdata%d'
configdb_vol_log = '/data/dock/docker_test/mongodb/test/cflog%d'
config_cn = 'cs'
cmd_mcfv = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongo/ " \
           "172.26.35.81:4000/mongo " \
           "--configsvr --replSet %s " \
           "--port 27017 --logpath /data/mongo/log.log"
cmd_mcfvs = [cmd_mcfv % (host_port, '27031', configdb_name % 1, configdb_vol % 1, configdb_vol_log % 1, config_cn),
             cmd_mcfv % (host_port, '27032', configdb_name % 2, configdb_vol % 2, configdb_vol_log % 2, config_cn),
             cmd_mcfv % (host_port, '27033', configdb_name % 3, configdb_vol % 3, configdb_vol_log % 3, config_cn),
             ]

router_name = 'mongo_os%d'
router_vol = '/data/dock/docker_test/mongodb/test/osdata%d'
router_vol_log = '/data/dock/docker_test/mongodb/test/oslog%d'
config_ips = '%s/%s:27031,%s:27032,%s:27033' % (config_cn, host, host, host)
cmd_mros = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongos/ " \
           "172.26.35.81:4000/mongo mongos " \
           "--configdb %s " \
           "--port 27017 --logpath /data/mongos/log.log"
cmd_mross = [cmd_mros % (host_port, '27041', router_name % 1, router_vol % 1, router_vol_log % 1, config_ips),
             cmd_mros % (host_port, '27042', router_name % 2, router_vol % 2, router_vol_log % 2, config_ips),
             cmd_mros % (host_port, '27043', router_name % 3, router_vol % 3, router_vol_log % 3, config_ips),
             ]

shared_name = 'mongo_shd%d'
shared_vol = '/data/dock/docker_test/mongodb/test/shddata%d'
shared_vol_log = '/data/dock/docker_test/mongodb/test/shdlog%d'
cmd_mshd = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongoshd/ " \
           "172.26.35.81:4000/mongo " \
           "--shardsvr --replSet %s " \
           "--port 27017 --logpath /data/mongoshd/log.log"
shd_name = 'shd%d'
cmd_mshds = [
    cmd_mshd % (host_port, '27051', shared_name % 1, shared_vol % 1, shared_vol_log % 1, shd_name % 1),
    cmd_mshd % (host_port, '27052', shared_name % 2, shared_vol % 2, shared_vol_log % 2, shd_name % 1),
    cmd_mshd % (host_port, '27053', shared_name % 3, shared_vol % 3, shared_vol_log % 3, shd_name % 1),
    cmd_mshd % (host_port, '27054', shared_name % 4, shared_vol % 4, shared_vol_log % 4, shd_name % 2),
    cmd_mshd % (host_port, '27055', shared_name % 5, shared_vol % 5, shared_vol_log % 5, shd_name % 2),
    cmd_mshd % (host_port, '27056', shared_name % 6, shared_vol % 6, shared_vol_log % 6, shd_name % 2),
    cmd_mshd % (host_port, '27057', shared_name % 7, shared_vol % 7, shared_vol_log % 7, shd_name % 3),
    cmd_mshd % (host_port, '27058', shared_name % 8, shared_vol % 8, shared_vol_log % 8, shd_name % 3),
    cmd_mshd % (host_port, '27059', shared_name % 9, shared_vol % 9, shared_vol_log % 9, shd_name % 3),
]

objects = {'mongo_cfs': cmd_mcfvs, 'mongo_os': cmd_mross, 'mongo_shd': cmd_mshds}
init_node_config = None


def get_mylogger(name="jenkins", level="info"):
    log = logging.getLogger(name)
    lelel_dict = {"info": logging.INFO, "debug": logging.DEBUG, "error": logging.ERROR}
    current_time = time.strftime("%Y-%m-%d", time.localtime())
    filename = current_time + name
    log.setLevel(lelel_dict[level])
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
        log1 = commands.getoutput("sudo mkdir %s" % log_dir)
        log.info(log1)
    fh = logging.FileHandler("%s/%s.log" % (log_dir, filename), "w")
    fm = logging.Formatter("[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s")
    fm.datefmt = "%d %H:%M:%S"
    fh.setFormatter(fm)
    log.addHandler(fh)
    return log


def argv_parse(opt_argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="this opts is used to deploy docker")
    parser.add_argument('object', help='deploy all, ceph and mongo:%s' % str(objects.keys()))
    parser.add_argument("-ip", dest="ip", help="node ip")
    parser.add_argument("-port", dest="port", help="node port")
    parser.add_argument("-name", dest="name", help="node name")
    parser.add_argument("-dvol", dest="data_volume", help="volume to mount")
    parser.add_argument("-lvol", dest="log_volume", help="volume to mount")
    parser.add_argument("-cn", dest="cluster_name", help="cluster_name")
    parser.add_argument("-cfd", dest="configdb", help="configdb")

    parser.add_argument("-v", action="version", version="%(prog)s 1.0")
    results = parser.parse_args(opt_argv)
    return results


def parse_config(obj=''):
    members = {}
    with open(config_runed_file, 'r') as fn:
        logs = fn.readlines()
        print(logs)
    for log in logs:
        print('the log is:' + log)
        if 'mongo_%s server ip_port' % obj in log:
            m = log.strip().split('---')
            print(str(m))
            if m[1] != 'none':
                if m[1] not in members.keys():
                    members[m[1]] = []
                members[m[1]].append(m[2])
    # if len(members) <= 2:
    #     return []
    # else:
    #     return members
    return members


def init_cluster(members, cluster_name=None):
    print('init_cluster members is:' + str(members))
    ip_port = members[0]

    rsconf = {
        '_id': cluster_name, 'members': [{'_id': 0, 'host': ip_port, 'priority': 2}]}
    cmd_ = 'rs.initiate(%s)' % str(rsconf)
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
    print('rs.initiate cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    print(status)
    print(log)
    time.sleep(4)
    cmd = 'mongo  %s/admin --eval "rs.status();"' % ip_port
    print('rs.status cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    print(status)
    print(log)

    members.pop(0)
    i = 0
    for m in members:
        i += 1
        doc = {'_id': i, 'host': m}
        if i > 1:
            cmd_ = "rs.add('%s', true)" % m
        else:
            cmd_ = 'rs.add(%s)' % str(doc)
        cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
        print('rs.add cmd is:' + cmd)
        status, log = commands.getstatusoutput(cmd)
        print(status)
        print(log)
        time.sleep(4)


logger = get_mylogger("mongo", "info")


def start_configs():
    # 启动3个配置服务器容器
    for cmd in cmd_mcfvs:
        print('cmd_mcfvs is:' + cmd)
        # continue
        status, log = commands.getstatusoutput(cmd)
        logger.info("status is" + str(status))
        logger.info("log is" + str(log))
        print('log is:' + log)
    time.sleep(4)
    # 连接配置服务器做集群初始化配置，加节点
    init_cluster(['%s:27031' % host, '%s:27032' % host, '%s:27033' % host], config_cn)


def start_routers():
    # 启动3个路由服务容器
    for cmd in cmd_mross:
        print('cmd_mross is:' + cmd)
        # continue
        status, log = commands.getstatusoutput(cmd)
        logger.info("status is" + str(status))
        logger.info("log is" + str(log))
        print('log is:' + log)


def add_shared(ip_port_router, ip_port_shared, shared_set_name):
    shds = '%s/%s' % (shared_set_name, ip_port_shared)
    cmd_ = "sh.addShard('%s')" % shds
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port_router, cmd_)
    print('final cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    print(status)
    print(log)


def start_shareds():
    i = 0
    # 启动9个分片服务容器
    for cmd in cmd_mshds:
        i += 1
        if i < 4:
            continue
        print('cmd_mshds is:' + cmd)
        # continue
        status, log = commands.getstatusoutput(cmd)
        logger.info("status is" + str(status))
        logger.info("log is" + str(log))
        print('log is:' + log)

    time.sleep(8)
    # 将9个分片服务分成三组，每组都是一个复制集群（primary+second+atrd）,配置三个复制集群
    init_cluster(['%s:27051' % host, '%s:27052' % host, '%s:27053' % host], shd_name % 1)
    # 将其一个复制集群加入分片集群作为一个分片,用的router随便哪个节点都可以
    add_shared(host + ':27041', host + ':27051', shd_name % 1)

    init_cluster(['%s:27054' % host, '%s:27055' % host, '%s:27056' % host], shd_name % 2)
    # 将其一个复制集群加入分片集群作为一个分片
    add_shared(host + ':27041', host + ':27054', shd_name % 2)

    init_cluster(['%s:27057' % host, '%s:27058' % host, '%s:27059' % host], shd_name % 3)
    # 将其一个复制集群加入分片集群作为一个分片
    add_shared(host + ':27041', host + ':27056', shd_name % 3)


def main():
    # opts = argv_parse()
    # print("opts is" + str(opts))
    # if 'init_cluster' in opts.object:
    #     init_cluster(opts.object[13:])
    # else: pass
    start_configs()
    start_routers()
    start_shareds()


if __name__ == "__main__":
    pass
    # main()
