# -*- coding:utf-8 -*-
# !/usr/bin/python
#
import json
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from collections import namedtuple
import groups

logger = groups.get_mylogger('ansible1')

loader = DataLoader()  # 用来加载解析yaml文件或JSON内容,并且支持vault的解密
variable_manager = VariableManager()  # 管理变量的类,包括主机,组,扩展等变量,之前版本是在 inventory 中的
inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list='./hosts')
# inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=['172.26.35.226'])
variable_manager.set_inventory(inventory)  # 根据 inventory 加载对应变量

Options = namedtuple(
    'Options', [
        'listtags', 'listtasks', 'listhosts', 'syntax', 'connection', 'module_path',
        'forks', 'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args',
        'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user',
        'verbosity', 'check'
    ]
)

options = Options(
    listtags=False, listtasks=True, listhosts=True, syntax=False, connection='smart',
    module_path='/usr/lib/python2.7/site-packages/ansible/modules', forks=100,
    remote_user='dock', private_key_file=None, ssh_common_args=None, ssh_extra_args=None,
    sftp_extra_args=None, scp_extra_args=None, become=False, become_method=None, become_user='dock',
    verbosity=None, check=False
)


def run_jenkins_slave(hosts):
    print('run_jenkins_slave ---------on:' + str(hosts))
    # return
    logger.info('run_jenkins_slave ---------on:' + str(hosts))
    variable_manager.extra_vars = {"ansible_ssh_user": "dock", "ansible_ssh_pass": "docker"}  # 增加外部变量
    play_source = {"name": "Ansible Ad-Hoc", "hosts": hosts, "gather_facts": "no",
                   "tasks": [
                       # {"action":
                       #  # {"module": "script", "args": "./deploy.py -gnd -cp"}
                       #      {"module": "command",
                       #       "args": "echo `uptime` >> /data/jenkins/docker_test/ansible.log"}
                       #  },
                       {"action":
                        #     {"module": "command", "args": "uptime"}
                        # {"module": "script", "args": "./deploy.py -gnd -cp"},
                            {"module": "script", "args": "./deploy.py jenkins -update -run -check"},
                        }
                   ]}
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=dict(vault_pass='docker'),
            stdout_callback='default',
            run_tree=False,
        )
        result = tqm.run(play)
        # tqm._stdout_callback = ResultsCollector()
        logger.info("the tqm.run(play) result is:" + str(result))
    finally:
        if tqm is not None:
            tqm.cleanup()


if __name__ == '__main__':
    nodes = groups.get_jenkins_nodes()
    logger.info('get_jenkins_nodes is:' + str(nodes))
    print('get_jenkins_nodes is:' + str(nodes))

    nodes = groups.parse_jdn2host(nodes)
    logger.info('ansible parsed nodes is:' + str(nodes))

    # groups.disable_nodes(nodes['all'], 'to maintain docker container')
    #
    # import threading
    # t = threading.Thread(target=run_jenkins_slave,  kwargs={'hosts':nodes['all']})
    # t.start()

    if len(nodes['busy']) > 0:
        rc = groups.save_wait_nodes(nodes['busy'])
        logger.info('return rc is:' + rc)
        print('return rc is:' + rc)
        print('return rc is:' + rc)
