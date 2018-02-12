#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib3, urllib, time
import json
import eventlet
import os, commands
import socket, fcntl, struct

fname = 'static1.txt'
talbe_id = '2jxg956nsdf12'
urls = ['http://172.26.35.211:8055/table/cd_swd2/Simba6_cricket',
        'http://172.26.35.211:8055/table/cd_swd2/Mickey6_tf_umts_5046g',
        'http://172.26.35.211:8055/table/cd_swd1/Gandalf']


def get_page_static(url, result_fn):
    start_time = time.time()
    page = urllib.urlopen(url)
    if page.getcode() != 200:
        return 'error'
    page_content = page.read()
    content_len = len(page_content)
    wh1 = page_content.index(talbe_id)
    wh2 = page_content.index('<div>', wh1)
    wh3 = page_content.index('</div>', wh1)
    static_content = page_content[wh2:wh3].split('\n')
    # ip_wh = static_content.index('<tr>')
    # ip_content = static_content[ip_wh+1:ip_wh+3].split('\n')
    # static_wh = static_content.index('<table>')
    # time_content = static_content[static_wh+1:-2].split('\n')
    time_static = []
    wh_ = -1
    for item in static_content:
        if '<tr' in item:
            time_static.append([])
            wh_ += 1
        elif '<th>' in item:
            wh = item.index('<th>')
            time_static[wh_].append(item[wh + 4:-5])
    for i in range(len(time_static)):
        time_static[i] = str(time_static[i])
    end_time = time.time()
    end_time_ = int(end_time % 3600)
    end_time_ = str(end_time_ / 60) + ':' + str(end_time_ % 60)
    start_time_ = int(start_time % 3600)
    start_time_ = str(start_time_ / 60) + ':' + str(start_time_ % 60)
    obj = {
        'content_info': {'url': url, 'content_len': content_len},
        'backend_time': time_static,
        'curl_time': str((start_time_, end_time_, '%.3f' % (end_time - start_time)))
    }
    # print(obj)
    with open(result_fn, 'a') as fn:
        fn.write(json.dumps(obj, indent=4))
        fn.write('\n------------------------------\n')
    del page_content, static_content, time_static
    return 'OK'


def dispatch(handle, times, *args):
    print 'dispatch handle(%s)...' % handle
    pile = eventlet.GreenPile()
    for i in range(times):
        pile.spawn(handle, *args)

    for ret in pile:
        if ret != 'OK':
            print ret
            # sys.exit(1)


def reset_filename():
    global fname
    ifac = ['eth0','eth1','enp1s0']
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for ifac_ in ifac:
        try:
            localip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifac_[:15])
            )[20:24])
            break
        except IOError:
            localip = '111.111.111.111'
    localip_ = localip.split('.')
    start_time = time.time()
    start_time = int(start_time % 3600)
    start_time_ = str(start_time / 60) + '-' + str(start_time % 60)
    fname = localip_[-1]+'-'+start_time_+'-'+fname


def scp_config_files(files):
    username = 'dock'
    remote_host_ip = '172.26.35.211'
    source_path = './'
    remote_path = '/data/dock/docker_test/time_static_log'
    for f in files:
        status,log = commands.getstatusoutput('scp  %s/%s %s@%s:%s'
                        % (source_path, f, username, remote_host_ip, remote_path))



def main():
    reset_filename()
    os.chdir('/data/dock/docker_test')
    if not os.path.exists('./swarm'):
        os.mkdir('./swarm')
    os.chdir('/data/dock/docker_test/swarm')

    with open(fname, 'w') as fn:
        fn.write('====---------start---------====\n')
    # url = 'http://172.26.35.211:8055/cd_swd1/'
    start_time = time.time()

    # url = 'http://172.26.35.211:8052/cd_swd1/'
    url = 'http://172.26.35.211:8051/cd_swd1/'
    dispatch(get_page_static, 10, url, fname)

    end_time = time.time()
    end_time_ = int(end_time % 3600)
    end_time_ = str(end_time_ / 60) + ':' + str(end_time_ % 60)
    start_time_ = int(start_time % 3600)
    start_time_ = str(start_time_ / 60) + ':' + str(start_time_ % 60)
    statics = {'all_time': str((start_time_, end_time_, '%.3f' % (end_time - start_time)))}
    with open(fname, 'a') as fn:
        fn.write('=======================\n')
        fn.write(str(statics) + '\n')
        fn.write('=====-----------end--------========\n')
    # get_page_static('http://172.26.35.211:8055/cd_swd1/', 'static1.txt')
    scp_config_files((fname,))


if __name__ == "__main__":
    main()