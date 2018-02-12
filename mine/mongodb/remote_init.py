#!/usr/bin/python2.7
# -*- coding:utf8 -*-
import commands, os, sys
import argparse

kf = 'keyfile.txt'
dirs = ['cfdata1', 'cfdata2', 'cfdata3', 'cflog1', 'cflog2', 'cflog3', 'osdata1', 'osdata2', 'osdata3', 'oslog1',
        'oslog2', 'oslog3', 'shddata1', 'shddata2', 'shddata3', 'shddata4', 'shddata5', 'shddata6', 'shddata7',
        'shddata8', 'shddata9', 'shdlog1', 'shdlog2', 'shdlog3', 'shdlog4', 'shdlog5', 'shdlog6', 'shdlog7', 'shdlog8',
        'shdlog9']


def init(work_dir=None, host=None):
    status = []
    logs = []
    if work_dir is None:
        work_dir = "/data/dock/docker_test/mongodb/test/"
    if not os.path.exists(work_dir):
        # os.mkdir(work_dir)
        s, l = commands.getstatusoutput('sudo mkdir -p %s;sudo chown dock:dock %s' % (work_dir, work_dir))
        logs.append(l)
        status.append(s)
    os.chdir(work_dir)
    if host is not None:
        s, l = commands.getstatusoutput('sudo scp dock@%s:%s/%s .' % (host, work_dir, kf))
        logs.append(l)
        status.append(s)

    for d in dirs:
        s, l = commands.getstatusoutput('mkdir %s;chmod a+wr %s' % (d, d))
        logs.append(l)
        status.append(s)
        s, l = commands.getstatusoutput('sudo cp %s %s' % (kf, d))
        logs.append(l)
        status.append(s)
    s, l = commands.getstatusoutput('sudo chmod 600 */%s; sudo chown 999:999 */%s' % (kf, kf))
    logs.append(l)
    status.append(s)
    s, l = commands.getstatusoutput('sudo chown 999:999 */%s' % kf)
    logs.append(l)
    status.append(s)
    for l in logs:
        print('l is:' + str(l))
    for s in status:
        print('s is:' + str(s))


def argv_parse(opt_argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='this opts is used to deploy docker')
    parser.add_argument('-w',  default=None, dest='work_dir', help='check container status')
    parser.add_argument('-keyh',  default=None, dest='host', help='check container status')
    parser.add_argument('-v', action='version', version='%(prog)s 1.0')
    results = parser.parse_args(opt_argv)
    return results


if __name__ == '__main__':
    # opt = argv_parse('-keyh 172.26.35.133 -w /data/dock/docker_test/mongodb/test/'.split())
    opt = argv_parse()
    print(opt)
    init(work_dir=opt.work_dir, host=opt.host)

