# /usr/bin/python2.7
import commands, sys, os
import argparse, logging, time
import socket
import fcntl
import struct

config_ip = '172.26.35.211'
work_dir = '/data/dock/docker_test/service/mongo'
mongo_conf_dir = work_dir + "/etc_mongo"
log_dir = 'log'
config_runed_file = 'shared_replica.log'

# cmd_mcfv = "docker %s run -it -p %s:27017 --name %s " \
#            "-v %s:/data/db -v %s:/data/mongo/ " \
#            "172.26.35.81:4000/busybox ls /"
#
# cmd_mros = "docker %s run -it -p %s:27017 --name %s " \
#            "-v %s:/data/db -v %s:/data/mongos/ " \
#            "172.26.35.81:4000/busybox ls " \
#            " %s "
#
# cmd_mshd = "docker %s run -it -p %s:27017 --name %s " \
#            "-v %s:/data/db -v %s:/data/mongoshd/ " \
#            "172.26.35.81:4000/busybox ls  " \
#            "%s "

cmd_mcfv = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongo/ " \
           "172.26.35.81:4000/mongo " \
           "--configsvr --replSet cs " \
           "--port 27017 --logpath /data/mongo/log.log"

cmd_mros = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongos/ " \
           "172.26.35.81:4000/mongo mongos " \
           "--configdb %s " \
           "--port 27017 --logpath /data/mongos/log.log"

cmd_mshd = "docker %s run -d -p %s:27017 --name %s " \
           "-v %s:/data/db -v %s:/data/mongoshd/ " \
           "172.26.35.81:4000/mongo " \
           "--shardsvr --replSet %s " \
           "--port 27017 --logpath /data/mongoshd/log.log"

objects = {'mongo_cfs': cmd_mcfv, 'mongo_os': cmd_mros, 'mongo_shd': cmd_mshd}
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
    # if os.path.exists("%s/%s.log" % (log_dir, filename)):
    #     os.system("mv %s/%s2.log " % (log_dir, filename))
    fh = logging.FileHandler("%s/%s.log" % (log_dir, filename), "w")
    fm = logging.Formatter("[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s")
    fm.datefmt = "%d %H:%M:%S"
    fh.setFormatter(fm)
    log.addHandler(fh)
    return log


def argv_parse(opt_argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="this opts is used to deploy docker")
    parser.add_argument('object', help='deploy all, ceph and mongo:%s' % str(objects.keys()))
    # parser.add_argument('-check', action='store_true', default=False, help='check container status')
    # parser.add_argument("-dm", action="store_true", default=False, dest="mon",
    #                     help="run mon node or not")
    # parser.add_argument("-imp", dest="mon_ip", help="init mon node ip")
    # parser.add_argument("-imn", dest="mon_name", help="init mon node name")
    #
    # parser.add_argument("-do", action="store_true", default=False, dest="osd",
    #                     help="run osd node or not")
    # parser.add_argument("-on", dest="osd_name", help="osd name")
    #
    # parser.add_argument("-dmds", action="store_true", default=False, dest="mds",
    #                     help="run mds node or not")
    # parser.add_argument("-mds_name", dest="mds_name", help="osd name")
    parser.add_argument("-ip", dest="ip", help="node ip")
    parser.add_argument("-port", dest="port", help="node port")
    parser.add_argument("-name", dest="name", help="node name")
    parser.add_argument("-dvol", dest="data_volume", help="volume to mount")
    parser.add_argument("-lvol", dest="log_volume", help="volume to mount")
    parser.add_argument("-cn", dest="cluster_name", help="cluster_name")
    parser.add_argument("-cfd", dest="configdb", help="configdb")

    parser.add_argument("-v", action="version", version="%(prog)s 1.0")
    # parser.add_argument_group()
    # results = parser.parse_args("-a dk -a di -f -B -A".split())
    results = parser.parse_args(opt_argv)
    return results


# def check_conf(opts):
#     logger.info('will check')
#     if not os.path.exists(work_dir):
#         logger.info('workdir is now exist!,will create')
#         log = commands.getoutput('mkdir -p %s' % work_dir)
#         logger.info(log)
#     os.chdir(work_dir)
#     if not os.path.exists(mongo_conf_dir):
#         logger.info('mongo_conf_dir is now exist!,will create')
#         log = commands.getoutput('mkdir -p %s' % mongo_conf_dir)
#         logger.info(log)
#         logger.info('workdir is now exist!,will create')
#         log = commands.getoutput("scp -r jenkins@%s:%s/* %s" % (config_ip, mongo_conf_dir, mongo_conf_dir))
#         logger.info(log)


def run_(opts):
    fn = open(config_runed_file, 'a')

    # host_port = '-H 172.26.35.133:4243'
    host_port = '-H %s:4243' % opts.ip
    obj = opts.object
    print(obj)
    if obj not in objects.keys():
        raise AttributeError('the name should be in %s' % str(objects.keys()))
        # if not os.path.exists(opts.data_volume):
        #     os.mkdir(opts.data_volume)
        # if not os.path.exists(opts.log_volume):
        #     os.mkdir(opts.log_volume)
    cmd = ''
    if obj == 'mongo_cfs':
        cmd = cmd_mcfv % (host_port, opts.port, opts.name, opts.data_volume, opts.log_volume)
        fn.write('%s:%s\n' % (obj, cmd))
        fn.write('mongo_config server ip_port ---cs---%s:%s\n' % (opts.ip, opts.port))
    elif obj == 'mongo_os':
        configdbs = parse_config('config')
        if len(configdbs) < 2:
            raise Exception('there are not enough configdb!')
        dbs = ''
        for db in configdbs.keys():
            dbs += ',' + db
        dbs = configdbs.values()[0] + '/' + dbs[1:]
        cmd = cmd_mros % (host_port, opts.port, opts.name, opts.data_volume, opts.log_volume, dbs)
        fn.write('%s:%s\n' % (obj, cmd))
        fn.write('mongo_router server ip_port ---none---%s:%s\n' % (opts.ip, opts.port))
    elif obj == 'mongo_shd':
        cmd = cmd_mshd % (host_port, opts.port, opts.name, opts.data_volume, opts.log_volume, opts.cluster_name)
        fn.write('%s:%s\n' % (obj, cmd))
        fn.write('mongo_shared server ip_port ---%s---%s:%s\n' % (opts.ip, opts.cluster_name, opts.port))
    logger.info("cmd is:" + cmd)
    print(cmd)
    status, log = commands.getstatusoutput(cmd)
    logger.info("status is" + str(status))
    logger.info("log is" + str(log))
    print('log is:' + log)
    fn.close()


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
            # members[m[2]] = (m[1])
    # if len(members) <= 2:
    #     return []
    # else:
    #     return members
    return members


def init_cluster(obj, cluster_name=None):
    print('obj is:' + obj)
    # return
    members = parse_config(obj)

    cluster_name = members.keys()[0]
    ip_port = members[cluster_name][0]
    cmd = 'mongo  %s/admin --eval "rs.status();"' % ip_port
    status, log = commands.getstatusoutput(cmd)
    print(status)
    print(log)
    rsconf = {
        '_id': cluster_name, 'members': [{'_id': 0, 'host': ip_port}]}
    cmd_ = 'rs.initiate(%s)' % str(rsconf)
    cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
    print('final cmd is:' + cmd)
    # status, log = commands.getstatusoutput(cmd)
    # print(status)
    # print(log)

    members[cluster_name].pop(0)
    i = 0
    for m in members[cluster_name]:
        i += 1
        doc = {'_id': i, 'host': m}
        if i > 1:
            cmd_ = 'rs.addArb(%s)' % str(doc)
        else:
            cmd_ = 'rs.add(%s)' % str(doc)
        cmd = 'mongo  %s/admin --eval "%s"' % (ip_port, cmd_)
        print('final cmd is:' + cmd)
        # status, log = commands.getstatusoutput(cmd)
        # print(status)
        # print(log)


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


logger = get_mylogger("mongo", "info")


def main():
    # opts = argv_parse(['init_cluster_config'])
    # cmd_string = 'mongo_os -name cfdb1 -dvol /data/dock/docker_test/mongodb/test/osdata1 -lvol /data/dock/docker_test/mongodb/test/oslog1 -port 27041 -ip 172.26.35.133'
    # opts = argv_parse(cmd_string.split(' '))
    opts = argv_parse()
    print("opts is" + str(opts))
    if 'init_cluster' in opts.object:
        init_cluster(opts.object[13:])
    else:
        run_(opts)


if __name__ == "__main__":
    main()

    # sudo python run-mongo.py -imp 172.26.35.217 -imn mon1 -dm
    # sudo python run-mongo.py -imp 172.26.35.217 -imn mon -on 0 -do
    # python deploy_cluster.py
    # mongo_cfs -name cfdb3 -dvol /data/dock/docker_test/mongodb/test/cfdata3
    # -lvol /data/dock/docker_test/mongodb/test/log3 -port 27033 -ip 172.26.35.133

    # python deploy_cluster.py mongo_os -name os1 -dvol /data/dock/docker_test/mongodb/test/osdata1 -lvol /data/dock/docker_test/mongodb/test/oslog1 -port 27041 -ip 172.26.35.133
