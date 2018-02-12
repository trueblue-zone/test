#!/usr/bin/python2.7
# -*- coding:utf8 -*-
import commands, sys, os
import logging, time

config_ip = '172.26.35.211'
work_dir = '/data/dock/docker_test/service/mongo'
mongo_conf_dir = work_dir + "/etc_mongo"
log_dir = 'log'
config_runed_file = 'shared_replica.log'

host1 = '172.26.35.136'
host2 = '172.26.35.154'
host3 = '172.26.35.242'
# host指定的是容器服务将部署在哪些节点，如果有多个节点的host使用还需要分化，都会有多个
# 同一个机器用的端口必须不同，不同机器用的可以相同

configdb_name = 'mongo_cfg%d'
configdb_vol = '/data/dock/docker_test/mongodb/test/cfdata%d'
configdb_vol_log = '/data/dock/docker_test/mongodb/test/cflog%d'
config_cn = 'cs'
cmd_mcfv = "docker -H %s:4243 run -d -p %s:27017 --name %s --restart=always " \
           "-v %s:/data/db -v %s:/data/mongo/ " \
           "172.26.35.81:4000/mongo " \
           "--configsvr --replSet %s " \
           "--port 27017 --dbpath /data/db --logpath /data/mongo/log.log"

router_name = 'mongo_os%d'
router_vol = '/data/dock/docker_test/mongodb/test/osdata%d'
router_vol_log = '/data/dock/docker_test/mongodb/test/oslog%d'
cmd_mros = "docker -H %s:4243 run -d -p %s:27017 --name %s --restart=always " \
           "-v %s:/data/db -v %s:/data/mongos/ " \
           "172.26.35.81:4000/mongo mongos " \
           "--configdb %s --maxConns 200 " \
           "--port 27017 --logpath /data/mongos/log.log"

shared_name = 'mongo_shd%d'
shared_vol = '/data/dock/docker_test/mongodb/test/shddata%d'
shared_vol_log = '/data/dock/docker_test/mongodb/test/shdlog%d'
cmd_mshd = "docker -H %s:4243 run -d -p %s:27017 --name %s --restart=always " \
           "-v %s:/data/db -v %s:/data/mongoshd/ " \
           "172.26.35.81:4000/mongo " \
           "--shardsvr --replSet %s " \
           "--port 27017 --logpath /data/mongoshd/log.log"
shd_name = 'shd%d'
init_node_config = None
config_ips = '%s/%s:27031,%s:27032,%s:27033' % (config_cn, host1, host2, host3)
clusters_config = {
    'config': {config_cn: (
        {'host': host1, 'port': '27031', 'container_name': configdb_name % 1, 'data_volume': configdb_vol % 1,
         'log_volume': configdb_vol_log % 1, 'cluster_name': config_cn, 'cmd': cmd_mcfv},
        {'host': host2, 'port': '27032', 'container_name': configdb_name % 2, 'data_volume': configdb_vol % 2,
         'log_volume': configdb_vol_log % 2, 'cluster_name': config_cn, 'cmd': cmd_mcfv},
        {'host': host3, 'port': '27033', 'container_name': configdb_name % 3, 'data_volume': configdb_vol % 3,
         'log_volume': configdb_vol_log % 3, 'cluster_name': config_cn, 'cmd': cmd_mcfv})},
    'router': {'none': (
        {'host': host1, 'port': '27041', 'container_name': router_name % 1, 'data_volume': router_vol % 1,
         'log_volume': router_vol_log % 1, 'cluster_name': config_ips, 'cmd': cmd_mros},
        {'host': host2, 'port': '27042', 'container_name': router_name % 2, 'data_volume': router_vol % 2,
         'log_volume': router_vol_log % 2, 'cluster_name': config_ips, 'cmd': cmd_mros},
        {'host': host3, 'port': '27043', 'container_name': router_name % 3, 'data_volume': router_vol % 3,
         'log_volume': router_vol_log % 3, 'cluster_name': config_ips, 'cmd': cmd_mros})},
    'shared': {
        shd_name % 1: ({'host': host1, 'port': '27051', 'container_name': shared_name % 1,
                        'data_volume': shared_vol % 1, 'log_volume': shared_vol_log % 1,
                        'cluster_name': shd_name % 1, 'cmd': cmd_mshd},
                       {'host': host3, 'port': '27052', 'container_name': shared_name % 2,
                        'data_volume': shared_vol % 2, 'log_volume': shared_vol_log % 2,
                        'cluster_name': shd_name % 1, 'cmd': cmd_mshd},
                       {'host': host2, 'port': '27053', 'container_name': shared_name % 3,
                        'data_volume': shared_vol % 3, 'log_volume': shared_vol_log % 3,
                        'cluster_name': shd_name % 1, 'cmd': cmd_mshd}),
        shd_name % 2: ({'host': host2, 'port': '27054', 'container_name': shared_name % 4,
                        'data_volume': shared_vol % 4, 'log_volume': shared_vol_log % 4,
                        'cluster_name': shd_name % 2, 'cmd': cmd_mshd},
                       {'host': host1, 'port': '27055', 'container_name': shared_name % 5,
                        'data_volume': shared_vol % 5, 'log_volume': shared_vol_log % 5,
                        'cluster_name': shd_name % 2, 'cmd': cmd_mshd},
                       {'host': host3, 'port': '27056', 'container_name': shared_name % 6,
                        'data_volume': shared_vol % 6, 'log_volume': shared_vol_log % 6,
                        'cluster_name': shd_name % 2, 'cmd': cmd_mshd}),
        shd_name % 3: (
            {'host': host3, 'port': '27057', 'container_name': shared_name % 7, 'data_volume': shared_vol % 7,
             'log_volume': shared_vol_log % 7, 'cluster_name': shd_name % 3, 'cmd': cmd_mshd},
            {'host': host2, 'port': '27058', 'container_name': shared_name % 8, 'data_volume': shared_vol % 8,
             'log_volume': shared_vol_log % 8, 'cluster_name': shd_name % 3, 'cmd': cmd_mshd},
            {'host': host1, 'port': '27059', 'container_name': shared_name % 9, 'data_volume': shared_vol % 9,
             'log_volume': shared_vol_log % 9, 'cluster_name': shd_name % 3, 'cmd': cmd_mshd})
    }
}
cmd_attr_sort = ('host', 'port', 'container_name', 'data_volume', 'log_volume', 'cluster_name')
user_configs = {'common': [{'name': 'test', 'pwd': 'test', 'database': 'static_web_test', 'role': 'dbOwner'},
                           {'name': 'read', 'pwd': 'read', 'database': 'static_web_test', 'role': 'read'}],
                'root': {'name': 'root', 'pwd': 'root'}}

mongo_express_cmd = 'docker -H %s:4243 run -d -p %s:8081 --name mongo-express%s  --restart=always ' \
                    '-e ME_CONFIG_BASICAUTH_USERNAME="%s" ' \
                    '-e ME_CONFIG_BASICAUTH_PASSWORD="%s" ' \
                    '-e ME_CONFIG_MONGODB_ADMINUSERNAME="%s" ' \
                    '-e ME_CONFIG_MONGODB_ADMINPASSWORD="%s" ' \
                    '-e ME_CONFIG_MONGODB_SERVER="%s" ' \
                    '-e ME_CONFIG_MONGODB_PORT="%s" ' \
                    '172.26.35.81:4000/mongo-express'


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
    fh = logging.FileHandler("%s/%s.log" % (log_dir, filename), "a")
    fm = logging.Formatter("[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s")
    fm.datefmt = "%d %H:%M:%S"
    fh.setFormatter(fm)
    log.addHandler(fh)
    return log


logger = get_mylogger("mongo", "info")


def init_cluster(members, add_arbiter=True):
    cluster_name = members[0]['cluster_name']
    print('init_cluster members is:' + str(members))
    logger.info('init_cluster members is:' + str(members))
    ip_port = members[0]['host'] + ':' + members[0]['port']
    rsconf = {'_id': cluster_name, 'members': [{'_id': 0, 'host': ip_port, 'priority': 2}]}
    cmd_ = 'rs.initiate(%s)' % str(rsconf)
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
    print('rs.initiate cmd is:' + cmd)
    logger.info('rs.initiate cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    print(status)
    print(log)
    logger.info(status)
    logger.info(log)
    time.sleep(4)
    cmd = 'mongo  %s/admin --eval "rs.status();"' % ip_port
    print('rs.status cmd is:' + cmd)
    logger.info('rs.status cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info(status)
    logger.info(log)
    print(status)
    print(log)

    i = 0
    for m in members[1:]:
        i += 1
        ip_p = m['host'] + ':' + m['port']
        doc = {'_id': i, 'host': ip_p}
        if add_arbiter and i > 1:
            cmd_ = "rs.add('%s', true)" % ip_p
        else:
            cmd_ = 'rs.add(%s)' % str(doc)
        cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
        print('rs.add cmd is:' + cmd)
        logger.info('rs.add cmd is:' + cmd)
        status, log = commands.getstatusoutput(cmd)
        logger.info(status)
        logger.info(log)
        print(status)
        print(log)
        time.sleep(4)


def add_shared(ip_port_router, ip_port_shareds, shared_set_name):
    # 将ip_port_shared指定的
    shds = '%s/%s' % (shared_set_name, ip_port_shareds)
    cmd_ = "sh.addShard('%s')" % shds
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port_router, cmd_)
    print('add_shared cmd is:' + cmd)
    logger.info('add_shared cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info(status)
    logger.info(log)
    print(status)
    print(log)


def shutdown_server(ip_port):
    # 将ip_port_shared指定的
    cmd = 'mongo  %s:%s@%s/admin --eval "db.shutdownServer()"' % (
        user_configs['root']['name'], user_configs['root']['pwd'], ip_port)
    print('shutdownServer cmd is:' + cmd)
    logger.info('add_shared cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info(status)
    logger.info(log)
    print(status)
    print(log)
    time.sleep(2)


def add_account(ip_port_router, users_configs):
    users_config = users_configs['common']
    dbs = []
    for user in users_config:
        dbs.append({'role': 'dbOwner', 'db': user['database']})
        user_cmd = "db.createUser({'user':'%s','pwd':'%s','roles':[{'role':'%s','db':'%s'}]})" % (
            user['name'], user['pwd'], user['role'], user['database'])
        cmd = 'mongo  %s/admin --eval "%s"' % (ip_port_router, user_cmd)
        print('createUser cmd is:' + cmd)
        logger.info('createUser cmd is:' + cmd)
        status, log = commands.getstatusoutput(cmd)
        logger.info(status)
        logger.info(log)
        print(status)
        print(log)

    dbs.append({'role': 'root', 'db': 'admin'})
    dbs.append({'role': 'dbOwner', 'db': 'admin'})
    dbs.append({'role': 'clusterAdmin', 'db': 'admin'})
    user_cmd = "db.createUser({'user':'%s','pwd':'%s','roles':%s})" % (
        users_configs['root']['name'], users_configs['root']['pwd'], str(dbs))
    # user_cmd = "db.createUser({'user':'root','pwd':'root'," \
    #            "'roles':[{'role':'dbOwner','db':[]},{'role':'clusterAdmin','db':'admin'}]})"
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port_router, user_cmd)
    print('create_root user cmd is:' + cmd)
    logger.info('create_root user cmd is:' + cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info(status)
    logger.info(log)
    print(status)
    print(log)


def start_services(clusters, add_to_config=False, add_arbiter=True):
    # 启动服务器容器
    for cluster in clusters.keys():
        members = clusters[cluster]
        print('init_cluster members is:' + str(members))
        for m in members:
            cmd_attr = []
            for attr in cmd_attr_sort:
                cmd_attr.append(m[attr])
            cmd = m['cmd'] % tuple(cmd_attr)
            print('cmd_of %s is:%s' % (cluster, cmd))
            logger.info('cmd_of %s is:%s' % (cluster, cmd))
            status, log = commands.getstatusoutput(cmd)
            logger.info("status is" + str(status))
            logger.info("log is" + str(log))
            print('log is:' + log)
        time.sleep(4)
        if cluster != 'none':
            init_cluster(members, add_arbiter)
        if add_to_config:
            ip_port_router = clusters_config['router']['none'][0]['host'] + ':' + clusters_config['router']['none'][0][
                'port']
            ip_port_shareds = ''
            for m in members:
                ip_port_shareds += m['host'] + ':' + m['port'] + ','
            shared_set_name = members[0]['cluster_name']
            add_shared(ip_port_router, ip_port_shareds[:-1], shared_set_name)


def restart_services_auth(clusters_configs):
    # 启动服务器容器
    time.sleep(10)
    for services_name in clusters_configs.keys():
        if services_name == 'router':
            cmd_add = ' --keyFile /data/db/keyfile.txt'
        else:
            cmd_add = ' --auth --keyFile /data/db/keyfile.txt'
        for clusters_name in clusters_configs[services_name]:
            members = clusters_configs[services_name][clusters_name]
            print('init_cluster members is:' + str(members))
            for m in members:
                # 想关掉服务，这样安全些，就像些文件的flush函数，防止有数据没写回数据库就被强制关闭了
                # shutdown_server(m['host'] + ':' + m['port']) #不起作用，因为shutdownserver必须在本地执行
                # 开始杀掉对应服务的容器
                rm_cmd = 'docker -H %s:4243 rm -f %s' % (m['host'], m['container_name'])
                print('rm_cmd %s/%s is:%s' % (services_name, clusters_name, rm_cmd))
                logger.info('cmd_of %s/%s is:%s' % (services_name, clusters_name, rm_cmd))
                status, log = commands.getstatusoutput(rm_cmd)
                logger.info("status is" + str(status))
                logger.info("log is" + str(log))
                print('log is:' + log)
                time.sleep(1)
                # 用权限参数(加keyfile和auth的)启动对应服务的容器
                cmd_attr = []
                for attr in cmd_attr_sort:
                    cmd_attr.append(m[attr])
                cmd = m['cmd'] % tuple(cmd_attr) + cmd_add
                print('cmd_of %s/%s is:%s' % (services_name, clusters_name, cmd))
                logger.info('cmd_of %s/%s is:%s' % (services_name, clusters_name, cmd))
                status, log = commands.getstatusoutput(cmd)
                logger.info("status is" + str(status))
                logger.info("log is" + str(log))
                print('log is:' + log)


# def cp_myself(fn):
#         fname = __file__
#         logger.info('in cp_myself, this file name is:%s' % fname)
#         if fname is not fn:
#             log = commands.getoutput('cp %s %s' % (fname, fn))
#             logger.info(log)
#
#
# def remote_init(configs):
#     cmd = 'ansible -i host '

def run_express(ip, port, container_name, l_name, l_pwd, s_name, s_pwd, s_host, s_port):
    cmd = mongo_express_cmd % (ip, port, container_name, l_name, l_pwd, s_name, s_pwd, s_host, s_port)
    print('mongo_express_cmd %s' % cmd)
    logger.info('mongo_express_cmd %s' % cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info("status is" + str(status))
    logger.info("log is" + str(log))
    print('log is:' + log)


def main():
    # opts = argv_parse()
    # print("opts is" + str(opts))
    # if 'init_cluster' in opts.object:
    #     init_cluster(opts.object[13:])
    # else: pass
    logger.info('===================start deploy cluster for mongo================')
    logger.info('----------------------start_services config--------------')
    start_services(clusters_config['config'], add_arbiter=False)
    logger.info('----------------------start_services router--------------')
    start_services(clusters_config['router'])
    logger.info('----------------------start_services shared--------------')
    start_services(clusters_config['shared'], add_to_config=True)
    logger.info('----------------------add_account test--------------')
    ip_port_router = clusters_config['router']['none'][0]['host'] + ':' + clusters_config['router']['none'][0]['port']
    add_account(ip_port_router, user_configs)
    logger.info('===================end deploy cluster for mongo first, restarting==================')
    restart_services_auth(clusters_config)
    logger.info('===================starting mongo-express on 172.26.35.242:8093 ==================')
    run_express('172.26.35.242', '8093', 'root', 'root', 'root',
                user_configs['root']['name'], user_configs['root']['pwd'],
                clusters_config['router']['none'][0]['host'], clusters_config['router']['none'][0]['port'])
    logger.info('===================end deploy cluster for mongo final==================')


if __name__ == "__main__":
    main()
    pass

# openssl rand -base64 64 > keyfile.dat
# --keyFile / data / db / keyfile.txt
# db.createUser({user:'root',pwd:'root',roles:[{ role :"dbOwner", db : "test"},{ role : "clusterAdmin", db : "admin" }]} )
# db.createUser({user:'test',pwd:'test',roles:[{role :"dbOwner",db :"test"}, {role:"clusterAdmin",db:"admin" }]})
# db.createUser({user:'read',pwd:'read',roles:[{role :"read",db :"test" }]})
# mongo  %s/admin --eval "sh.status()"

# 远端host要做的操作： 0 每个远端要有mongo镜像 ， 1 创建对应服务容器要挂载的目录（数据目录和日志目录）， 2 每个数据里面里面都要有个600权限的keyfile
# { "_id" : "admin.read", "user" : "read", "db" : "admin", "credentials" : { "SCRAM-SHA-1" : { "iterationCount" : 10000, "salt" : "LS5EB750ypzRpbm6c3gCtQ==", "storedKey" : "yT6QT4iNqaMM7HFHt9blmGAWWVk=", "serverKey" : "T30dznipt5KH/lr1ssUwo2uUBT0=" } }, "roles" : [ { "role" : "read", "db" : "static_web_test" } ] }
# { "_id" : "admin.test", "user" : "test", "db" : "admin", "credentials" : { "SCRAM-SHA-1" : { "iterationCount" : 10000, "salt" : "LKEe8A+kQqma2yKH6vdoWQ==", "storedKey" : "FYwnF6rU3zHM0Jgrbu4BCfJs580=", "serverKey" : "+y2hlaT2+9OlEi1tAbOXTfcaZJQ=" } }, "roles" : [ { "role" : "dbOwner", "db" : "static_web_test" } ] }
# { "_id" : "admin.root", "user" : "root", "db" : "admin", "credentials" : { "SCRAM-SHA-1" : { "iterationCount" : 10000, "salt" : "wbpcFZfGEMDz6F8rhpv7PQ==", "storedKey" : "rtqUoOles7JLxRS2TEdXnJmltrU=", "serverKey" : "0wVx8eItHzdVhuB7xfRyKWvJ5FM=" } }, "roles" : [ { "role" : "dbOwner", "db" : "admin" }, { "role" : "clusterAdmin", "db" : "admin" } ] }

import commands


# kf = 'keyfile.txt'
# dirs = ['cfdata1', 'cfdata2' ,'cfdata3', 'cflog1' ,'cflog2', 'cflog3', 'osdata1', 'osdata2', 'osdata3', 'oslog1', 'oslog2' ,'oslog3' ,'shddata1' ,'shddata2','shddata3','shddata4','shddata5','shddata6','shddata7','shddata8','shddata9','shdlog1','shdlog2','shdlog3','shdlog4','shdlog5','shdlog6','shdlog7','shdlog8','shdlog9']
# status = []
# logs = []
# for d in dirs:
#     s ,l = commands.getstatusoutput('cp %s %s'%(kf, d))
#     logs.append(l)
#     status.append(s)
# s ,l = commands.getstatusoutput('chmod 600 */%s'%kf)
# logs.append(l)
# status.append(s)
# s ,l = commands.getstatusoutput('sudo chown 999:999 */%s'%kf)
# logs.append(l)
# status.append(s)
# for l in logs:
#     print('l is:'+str(l))
# for s in status:
#     print('s is:'+str(s))


# openssl rand -base64 64 > keyfile.dat

# docker -H 172.26.35.133:4243 run -d -p 27031:27017 --name mongo_cfg1 -v /data/dock/docker_test/mongodb/test/cfdata1:/data/db -v /data/dock/docker_test/mongodb/test/cflog1:/data/mongo/ 172.26.35.81:4000/mongo --configsvr --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log

# replica
# docker run -d -p 27031:27017 --name mongo_cfg1 -v /data/dock/docker_test/mongodb/test/cfdata1:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog1:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log
# docker run -d -p 27032:27017 --name mongo_cfg2 -v /data/dock/docker_test/mongodb/test/cfdata2:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog2:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log
# docker run -d -p 27033:27017 --name mongo_cfg3 -v /data/dock/docker_test/mongodb/test/cfdata3:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog3:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log

# keyfile replica
# docker run -d -p 27031:27017 --name mongo_cfg1 -v /data/dock/docker_test/mongodb/test/cfdata1:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog1:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log --auth --keyFile /data/configdb/keyfile.txt
# docker run -d -p 27032:27017 --name mongo_cfg2 -v /data/dock/docker_test/mongodb/test/cfdata2:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog2:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log --auth --keyFile /data/configdb/keyfile.txt
# docker run -d -p 27033:27017 --name mongo_cfg3 -v /data/dock/docker_test/mongodb/test/cfdata3:/data/configdb -v /data/dock/docker_test/mongodb/test/cflog3:/data/mongo/ 172.26.35.81:4000/mongo  --replSet cs --port 27017 --dbpath /data/configdb --logpath /data/mongo/log.log --auth --keyFile /data/configdb/keyfile.txt

# mongo cmd shd
# mongo  172.26.35.133:27051/admin --eval "rs.initiate({'_id': 'shd1', 'members': [{'priority': 2, 'host': '172.26.35.133:27051', '_id': 0}]})
# mongo  172.26.35.133:27051/admin --eval "rs.add({'host': '172.26.35.133:27052', '_id': 1})"
# mongo  172.26.35.133:27051/admin --eval "rs.add('172.26.35.133:27053', true)"

# mongo cmd cfg
# mongo  172.26.35.133:27031/admin --eval "rs.initiate({'_id': 'cs', 'members': [{'priority': 2, 'host': '172.26.35.133:27031', '_id': 0}]})"
# mongo  172.26.35.133:27031/admin --eval "rs.add({'host': '172.26.35.133:27032', '_id': 1})"
# mongo  172.26.35.133:27031/admin --eval "rs.add({'host': '172.26.35.133:27033', '_id': 2})"


# docker -H 172.26.35.133:4243 run -d -p 27054:27017 --name mongo_shd4 -v /data/dock/docker_test/mongodb/test/shddata4:/data/db -v /data/dock/docker_test/mongodb/test/shdlog4:/data/mongoshd/ 172.26.35.81:4000/mongo --shardsvr --replSet shd2 --port 27017 --logpath /data/mongoshd/log.log --auth --keyFile /data/db/keyfile.txt
# docker run -d -p 27054:27017 --name mongo_shd10 -v /data/dock/docker_test/mongodb/shddata10:/data/db -v /data/dock/docker_test/mongodb/shdlog10:/data/mongoshd/ 172.26.35.81:4000/mongo --shardsvr --port 27017 --logpath /data/mongoshd/log.log --auth --keyFile /data/db/keyfile.txt

# 291和Tiger_K2_3G-black/110很奇怪是217_2出现问题 ，其他都是217或是216_2出问题
