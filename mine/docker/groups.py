#!/usr/bin/python
import json
import jenkins
import sys, os
import logging, time
import commands
import ansible_task

mes = 'will restart to load new config or use new docker images'
un = 'tenghui.li'
ut = '37153754ebeb1d9a301ec6576a3814b5'
url = 'http://172.26.35.81:8080/'
# '172.26.35.113_2','172.26.35.186_2', '172.26.35.245_2''172.26.35.123_2'
# nodes_name = ['172.26.35.30_2']
# nodes_name = ['172.26.35.242_2']
nodes_name = ['172.26.35.226_2']
# nodes_name = ['172.26.35.30_2', '172.26.35.216_2',  '172.26.35.218_2',
#               '172.26.35.224_2', '172.26.35.225_2', '172.26.35.226_2', '172.26.35.235_2', '172.26.35.242_2'
#     ]
# nodes_info = []
server = 0
log_dir = 'log'
wait_nodes_hosts_fn = 'wait_nodes_hosts'


# config logger to save install and run jenkins in docker log

def get_mylogger(name='groups', level='debug'):
    log = logging.getLogger(name)
    lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
    current_time = time.strftime('%Y-%m-%d', time.localtime())
    filename = current_time + name
    log.setLevel(lelel_dict[level])
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
        log1 = commands.getoutput('sudo mkdir %s' % log_dir)
        log.info(log1)
    # if os.path.exists('%s/%s.log' % (log_dir, filename)):
    #     os.system('mv %s/%s2.log ' % (log_dir, filename))
    fh = logging.FileHandler('%s/%s.log' % (log_dir, filename), 'w')
    fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
    fm.datefmt = '%d %H:%M:%S'
    fh.setFormatter(fm)
    log.addHandler(fh)
    log_wh = os.getcwd() + '/%s/%s.log' % (log_dir, filename)
    print('log_wh is:' + str(log_wh))
    return log


logger = get_mylogger()


def get_jenkins_nodes(nodes_name_=None):
    if nodes_name_ is None:
        nodes_name_ = nodes_name
    # return {'all': nodes_name_[:1], 'busy': nodes_name_[1:]}
    global server
    try:
        server = jenkins.Jenkins(url, un, ut)
    except Exception as e:
        logger.error('some thing is error:' + str(e))
        sys.exit(1)
    nodes_info = []
    nodes_idle = []
    nodes_busy = []
    nodes_offline = []
    nodes_none = []
    # global nodes_info

    for node in nodes_name_:
        try:
            n = server.get_node_info(node, depth=1)
            nodes_info.append(n)
        except jenkins.NotFoundException as e:
            logger.error('the node %s is not found:%s' % (node, str(e)))
            nodes_none.append(node)
        except Exception as e:
            logger.error('some thing is error:' + str(e))
            # sys.exit(1)
    for node in nodes_info:
        if node['offline'] is True:
            nodes_offline.append(node['displayName'])
        elif node['idle'] is True:
            nodes_idle.append(node['displayName'])
        else:
            nodes_busy.append(node['displayName'])
    test_node = []
    if len(nodes_idle) > 0:
        test_node.append(nodes_idle[0])
    dict_re = {'all': nodes_idle + nodes_offline, 'busy': nodes_busy,
               'idle': nodes_idle, 'offline': nodes_offline,
               'none': nodes_none, 'test': test_node}
    logger.info('get host states is %s' % str(dict_re))
    return dict_re


def disable_nodes(nodes, mes_=None, check=True):
    logger.info('at disable_node,mes is:' + str(mes))
    if mes_ is None:
        mes_ = mes
    # if check:
    #     for node in nodes:
    #         if not node.endswith('_2'):
    #             logger.error('this node %s is not docker host please '
    #                          'check your maintained host' % node)
    #             sys.exit(1)
    for node in nodes:
        try:
            if not node.endswith('_2'):
                node += '_2'
            server.disable_node(node, mes_)
            logger.info('disable_node node %s ok' % node)
        except Exception as e:
            logger.info('disable_node failed ! some thing is error:' + str(e))
            # sys.exit(1)


def enable_nodes(nodes):
    logger.info('at enable_node nodes are:' + str(nodes))
    global server
    try:
        server = jenkins.Jenkins(url, un, ut)
    except Exception as e:
        logger.error('some thing is error:' + str(e))
        sys.exit(1)
    for node in nodes:
        try:
            server.enable_node(node)
            logger.info('enable_node node %s ok' % node)
            # logger.info('at groups.py :enable_node node %s ok' % node)
        except Exception as e:
            logger.info('enable_node failed ! some thing is error:' + str(e))
            # sys.exit(1)


def get_host_name(nodes):
    nodes_copy = {}
    if isinstance(nodes, dict):
        for node_type in nodes.keys():
            nodes_copy[node_type] = []
            for node in nodes[node_type]:
                nodes_copy[node_type].append(node[:-2])
    elif isinstance(nodes, str):
        nodes_copy = nodes[:-2]
    elif isinstance(nodes, list):
        nodes_copy = [n[:-2] for n in nodes]
    logger.info('the %s parsed to are %s' % (str(nodes), str(nodes_copy)))
    return nodes_copy


def check_result(host, res):
    # logger.info('at check_result')
    # logger.info('get result from %s' % (str(host)))
    logger.info('get result from %s , res is %s' % (str(host), str(res)))
    res_ = res['stdout_lines']
    logger.info('res_ is' + str(res_))
    host_ = str(host) + '_2'
    if 'start jenkins container flag is:False' not in res_:
        logger.info('start jenkins container flag is:True')
        enable_nodes((host_,))
    else:
        logger.info('start jenkins container flag is:False')


def save_wait_nodes(nodes):
    if isinstance(nodes, str):
        nodes += '\n'
    else:
        nodes = [node + '\n' for node in nodes]
    print('saved nodes is:' + str(nodes))
    logger.info('saved nodes is:' + str(nodes))
    with open(wait_nodes_hosts_fn, 'a') as f:
        f.writelines(nodes)
    with open(wait_nodes_hosts_fn, 'r') as fn:
        nodes_get = fn.read()
    if 'master' not in nodes_get:
        print('master not in %s file' % wait_nodes_hosts_fn)
        logger.info('master not in %s file' % wait_nodes_hosts_fn)
        import threading
        t = threading.Thread(wait_busy())
        t.start()
        return 'save_and_process'
    else:
        print('master in %s file' % wait_nodes_hosts_fn)
        logger.info('master in %s file' % wait_nodes_hosts_fn)
    return 'save'


def wait_busy():
    print('in wait_busy-------------------')
    logger.info('in wait_busy-------------------')

    nodes_new = set()
    nodes_ok = set()
    counts = 0
    wait_time = 30
    expire_time = 100
    while True:
        counts += 1
        logger.info('this is the %d time' % counts)
        print('this is the %d time' % counts)
        with open(wait_nodes_hosts_fn, 'r') as fn:
            nodes_get = fn.read()
        with open(wait_nodes_hosts_fn, 'w') as fn:
            fn.write('master\n')
        nodes_get = nodes_get.split('\n')
        logger.info('nodes_get is:' + str(nodes_get))
        print('nodes_get is:' + str(nodes_get))
        nodes_get = set(nodes_get)
        nodes_get.discard('master')
        nodes_get.discard('')
        logger.debug('nodes_get2 is:' + str(nodes_get))
        nodes_ = nodes_get - nodes_ok
        logger.debug('nodes_ is:' + str(nodes_))
        nodes_new |= nodes_
        logger.debug('nodes_new is:' + str(nodes_new))
        if len(nodes_new) <= 0:
            logger.info('process waited nodes over!!\n')
            print('process waited nodes over!!\n')
            with open(wait_nodes_hosts_fn, 'w') as fn:
                fn.write('\n')
            return
        nodes_new_ = [node + '_2' for node in nodes_new if not node.endswith('_2')]
        nodes_p = set(get_jenkins_nodes(nodes_new_)['all'])
        nodes_p = set([node[:-2] for node in nodes_p if node.endswith('_2')])
        logger.info('nodes_processing is:' + str(nodes_p))
        print('nodes_processing is:' + str(nodes_p))
        if len(nodes_p) > 0:
            nodes_new -= nodes_p
            logger.info('nodes_waiting is:' + str(nodes_new))
            print('nodes_waiting is:' + str(nodes_new))
            disable_nodes(nodes_p)
            nodes_ok |= nodes_p
            logger.debug('nodes_ok is:' + str(nodes_ok))
            ansible_task.run_jenkins_slave(list(nodes_p))
            if counts * wait_time >= expire_time:
                nodes_ok.clear()
        else:
            print('waiting in sleeping')
            logger.info('waiting in sleeping')
            time.sleep(wait_time)


def parse_jdn2host(nodes):
    if isinstance(nodes, dict):
        nodes_ = {nodename: [node[:-2] for node in nodes[nodename]] for nodename in nodes.keys()}
    elif isinstance(nodes, list):
        nodes_ = [node[:-2] for node in nodes]
    return nodes_


if __name__ == '__main__':
    ns = get_jenkins_nodes()
    print(json.dumps(get_host_name(ns)))
    # ns = 'sdf'
    busy_nodes = parse_jdn2host(ns)['busy']
    if len(busy_nodes) > 0:
        save_wait_nodes(busy_nodes)
    # logger.info(get_wait_nodes())

    disable_nodes(ns['all'])
    ansible_task.run_jenkins_slave(get_host_name(ns['all']))

    # wait_busy()
    # logger.info(json.dumps(get_jenkins_nodes(['172.26.35.136', '172.26.35.137', '172.26.35.211', '172.26.35.144'])))
