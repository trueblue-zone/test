#/usr/bin/python2.7
import commands,sys,os
import argparse, logging, time
import socket
import fcntl
import struct

config_ip = '172.26.35.211'
work_dir = '/data/jenkins/docker_test/service/ceph'
ceph_conf_dir = work_dir+"/etc-ceph"
log_dir = 'log'
cmd_osd = "docker run -itd --name=%s --net=host\
  -e CLUSTER=ceph -e WEIGHT=1.0 -e MON_NAME=%s\
  -e MON_IP=%s -v %s:/etc/ceph\
  -v %s:%s\
  --restart always\
  172.26.35.81:4000/ceph/osd:hammer"

cmd_mds = "docker run -itd --name=%s --net=host\
  -e MDS_NAME=%s -v %s:/etc/ceph\
  -v %s:%s\
  --restart always\
  172.26.35.81:4000/ceph/mds:hammer"

cmd_mon = "docker run -itd --name=%s --net=host\
  -e CLUSTER=ceph -e MON_NAME=%s\
  -e MON_IP=%s -v %s:/etc/ceph\
  -v %s:%s\
  -v /etc/localtime:/etc/localtime\
  --restart always\
  172.26.35.81:4000/ceph/mon:hammer"

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
    parser.add_argument("-dm", action="store_true", default=False, dest="mon",
                        help="run mon node or not")
    parser.add_argument("-imp", dest="mon_ip", help="init mon node ip")
    parser.add_argument("-imn", dest="mon_name", help="init mon node name")

    parser.add_argument("-do", action="store_true", default=False, dest="osd",
                        help="run osd node or not")
    parser.add_argument("-on", dest="osd_name", help="osd name")

    parser.add_argument("-dmds", action="store_true", default=False, dest="mds",
                        help="run mds node or not")
    parser.add_argument("-mds_name", dest="mds_name", help="osd name")


    parser.add_argument("-v", action="version", version="%(prog)s 1.0")
    # parser.add_argument_group()
    # results = parser.parse_args("-a dk -a di -f -B -A".split())
    results = parser.parse_args(opt_argv)
    return results

def check_conf(opts):
    logger.info('will check')
    if not os.path.exists(work_dir):
        logger.info('workdir is now exist!,will create')
        log = commands.getoutput('mkdir -p %s'%work_dir)
        logger.info(log)
    os.chdir(work_dir)
    if not os.path.exists(ceph_conf_dir):
        logger.info('ceph_conf_dir is now exist!,will create')
        log = commands.getoutput('mkdir -p %s'%ceph_conf_dir)
        logger.info(log)
        logger.info('workdir is now exist!,will create')
        log = commands.getoutput("scp -r jenkins@%s:%s/* %s" % (config_ip, ceph_conf_dir, ceph_conf_dir))
        logger.info(log)

def run_osd(opts):
    name = opts.osd_name
    name_ = "osd"+name
    osd_data = "/data/ceph-osd%s"%name
    osd_data_ = "/var/lib/ceph/osd/ceph-%s"%name
    mon_name = opts.mon_name
    mon_ip = opts.mon_ip
    if not os.path.exists(osd_data):
        os.mkdir(osd_data)
    cmd = cmd_osd%(name_, mon_name, mon_ip, ceph_conf_dir, osd_data, osd_data_)
    logger.info("cmd is:"+cmd)

    log, status = commands.getstatusoutput(cmd)
    logger.info("status is"+str(status))
    logger.info("log is"+str(log))

def run_mds(opts):
    name = opts.mds_name
    mds_data = "/data/ceph-mds%s"%name
    mds_data_ = "/var/lib/ceph/mds/ceph-%s"%name
    if not os.path.exists(mds_data):
        os.mkdir(mds_data)
    cmd = cmd_mds%(name, name,  ceph_conf_dir, mds_data, mds_data_)
    logger.info("cmd is:"+cmd)
    log, status = commands.getstatusoutput(cmd)
    logger.info("status is"+str(status))
    logger.info("log is"+str(log))

def run_mon(opts):
    mon_name = opts.mon_name
    mon_data = "/data/ceph-mon%s"%mon_name
    mon_data_ = "/var/lib/ceph/mon/ceph-%s"%mon_name
    cmd = cmd_mon%(mon_name, mon_name, opts.localip, ceph_conf_dir, mon_data, mon_data_)
    logger.info("cmd is:"+cmd)

    log, status = commands.getstatusoutput(cmd)
    logger.info("status is"+str(status))
    logger.info("log is"+str(log))

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


logger = get_mylogger("ceph","info")
def main():
    opts = argv_parse()
    localip = get_ip_address('eth0')
    opts.localip = localip
    if opts.localip != opts.mon_ip:
        logger.info('localip != opts.mon_ip')
        check_conf(opts)
    else:
        logger.info('localip == opts.mon_ip')

    print("opts is"+str(opts))
    if opts.osd:
        run_osd(opts)
    if opts.mon:
        run_mon(opts)
    if opts.mds:
        run_mds(opts)

if __name__ == "__main__":
    main()

# sudo python run-ceph.py -imp 172.26.35.217 -imn mon1 -dm
# sudo python run-ceph.py -imp 172.26.35.217 -imn mon -on 0 -do
