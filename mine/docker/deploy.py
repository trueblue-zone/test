#!/usr/bin/python
# -*- coding:utf8 -*-
import os, sys, time
import commands, logging
import argparse

user_dir = '/data/dock/'
work_dir = user_dir + 'docker_test/'

# source_path_registry = work_dir + '/registry/'
source_host_ip = '172.26.35.211'
source_path = work_dir
username = 'dock'
docker_tar = 'docker_binerys.tar'
docker_tzg = 'docker_binerys.tar.zg'
log_dir = 'log'
logger = 0
myname = 'deploy.py'
option_groups = set({'test', 'deploy_all', 'restart_all'})

docker_settings = {'config_dir': 'etcdocker',
                   'config_files':
                       {'docker': '/etc/default/', 'daemon.json': '/etc/docker',
                        'docker.service': '/lib/systemd/system/',
                        'docker.socket': '/lib/systemd/system/'
                        }}

jenkins_settings = {'dir': 'jenkins', 'container_name': 'jenkins',
                    'image_name': '172.26.35.81:5000/jenkins:v7_5',
                    'container_config_dir': work_dir + 'jenkins/', 'compose-file': 'compose_jenkins.yml',
                    'config_files': ['compose_jenkins.yml', 'entry_jenkins.sh', 'entry2.sh', 'save_config.py',
                                     'load_config.py']}  # , '__init__.py'

zabbix_settings = {'dir': 'zabbix', 'container_name': 'zabbix-agent',
                   'image_name': '172.26.35.81:4000/million12/zabbix-agent',
                   'container_config_dir': work_dir + 'zabbix/', 'compose-file': 'zabbix_agentd.yml',
                   'config_files': ['zabbix_agentd.conf', 'zabbix_agentd.yml']}

hadoop_settings = {'dir': 'hadoop', 'container_name': 'hadoop_node',
                   'image_name': '172.26.35.211:4000/hadoop:2.7_v1',
                   'container_config_dir': work_dir + 'hadoop/', 'compose-file': 'compose_hadoop.yml',
                   'config_files': ['compose_hadoop.yml','etc_hadoop','conf_spark','entry_master.sh','entry_node.sh']}

registry_settings = {'dir': 'registry', 'container_name': 'registry',
                     'image_name': '172.26.35.81:4000/registry',
                     'container_config_dir': work_dir + 'registry/', 'compose-file': 'compose_registry.yml',
                     'config_files': ['compose_registry.yml']}


# ==================初始化，配置相关==================================
def argv_parse(opt_argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='this opts is used to deploy docker')
    # parser.add_argument('newdir', action='store_true', default=True, help='make the work dir and use it')
    # parser.add_argument('cp', action='store_true', default=True, help='copy the run file')
    parser.add_argument('object', help='deploy slave,one of docker,zabbix,jenkins,hadoop')
    parser.add_argument('-check', action='store_true', default=False, help='check container status')
    parser.add_argument('-update', action='store_true', default=False, help='pull config files')
    parser.add_argument('-run', action='store_true', default=False, help='run slave in docker')
    parser.add_argument('-rerun', action='store_true', default=False, help='run slave in docker')

    parser.add_argument('-install', action='store_true', default=False, help='install docker-engine')
    # parser.add_argument('init_jenkins', action='store_true', default=False, dest='init_jenkins',
    #                     help='init jenkins config at host')
    # parser.add_argument('-force', action='store_true', default=False, dest='force_clean',
    #                     help='force clean jenkins container even to restart docker')
    parser.add_argument('-v', action='version', version='%(prog)s 1.0')
    results = parser.parse_args(opt_argv)
    return results


# config logger to save install and run jenkins in docker log
def get_mylogger(name='ansible', level='info'):
    log = logging.getLogger(name)
    lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
    current_time = time.strftime('%Y-%m-%d', time.localtime())
    filename = current_time + name
    log.setLevel(lelel_dict[level])
    if not os.path.exists(log_dir):
        log1 = commands.getoutput('sudo mkdir -p %s' % log_dir)
        log.info(log1)
        username = 'dock'
        log1 = commands.getoutput('sudo chown -R %s:%s %s' % (username, username, log_dir))
        print(log1)
        log1 = commands.getoutput('sudo chmod -R a+w  %s' % log_dir)
        print(log1)
        # log1 = commands.getoutput('sudo makedirs %s' % log_dir)
        # log.info(log1)
    # if os.path.exists('%s/%s.log' % (log_dir, filename)):
    #     os.system('mv %s/%s2.log ' % (log_dir, filename))
    fh = logging.FileHandler('%s/%s.log' % (log_dir, filename), 'w')
    fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
    fm.datefmt = '%d %H:%M:%S'
    fh.setFormatter(fm)
    log.addHandler(fh)
    return log


class InitTool():
    @staticmethod
    def init():
        InitTool.goto_workspace(work_dir)
        global logger
        logger = get_mylogger()
        logger.info('the logger init ok, now init other thins')
        InitTool.check_all()
        InitTool.cp_myself(myname)

    @staticmethod
    def auto_init():
        # status, log = commands.getstatusoutput('su dock')
        # logger.info(log)
        InitTool.goto_workspace(work_dir)
        global logger
        logger = get_mylogger()
        logger.info('change to user dock')
        log = commands.getoutput('scp -r dock@172.26.35.211:~/.ssh ~/')
        logger.info(log)
        install_docker = ['docker', '-install', '-update', '-run', '-check']
        install_zabbix = ['zabbix', '-update', '-run', '-check']
        parse2slave(install_docker)
        parse2slave(install_zabbix)

    @staticmethod
    def init_user_config():
        InitTool.goto_workspace(work_dir)
        global logger
        logger = get_mylogger()
        username = 'dock'
        logger.info('at init_user_config')
        if not os.path.exists(user_dir):
            log1 = commands.getoutput('mkdir %s' % user_dir)
            logger.info(log1)
            log = commands.getoutput('scp -r %s@%s:%s/.ssh %s' %
                                     (username, source_host_ip, user_dir, user_dir))
            logger.info(log)

            # 这几行实际上执行不了，因为未受信赖的user不能在代码里写scp，这样会卡死吧
        log = commands.getoutput('addgroup docker')
        logger.info(log)
        log = commands.getoutput('id %s' % username)
        logger.info(log)
        if 'uid' not in log:
            logger.info('command id %s error, so there is no %s user, and will be added' % (username, username))
            passwd_en = 'aaOLN9pfuDGV.'
            log1 = commands.getoutput('useradd %s -p %s -d %s -s /bin/bash' % (username, passwd_en, user_dir))
            logger.info(log1)  # 这几句还是在宿主机上手动的执行好些
        if 'docker' not in log:
            log1 = commands.getoutput('gpasswd -a %s docker' % username)
            logger.info(log1)
        log1 = commands.getoutput('chown -R %s:%s %s' % (username, username, user_dir))
        logger.info(log1)
        log = commands.getoutput('echo "dock ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers')
        logger.info(log)
        log = commands.getoutput('cp /root/deploy.py /data/dock/docker_test')
        logger.info(log)
        log = commands.getoutput('chown dock:dock /data/dock/docker_test/deploy.py')
        logger.info(log)
        log = commands.getoutput('chmod a+x /data/dock/docker_test/deploy.py')
        logger.info(log)

    @staticmethod
    def goto_workspace(wdir):
        username = 'dock'
        if not os.path.exists(wdir):
            log1 = commands.getoutput('sudo mkdir -p %s' % wdir)
            print(log1)
            log1 = commands.getoutput('sudo chown -R %s:%s %s' % (username, username, wdir))
            print(log1)
            log1 = commands.getoutput('sudo chmod -R a+r  %s' % wdir)
            print(log1)
        os.chdir(wdir)

    @staticmethod
    def cp_myself(fn):
        fname = __file__
        logger.info('in cp_myself, this file name is:%s' % fname)
        if fname is not fn:
            log = commands.getoutput('cp %s %s' % (fname, fn))
            logger.info(log)

    @staticmethod
    def restart_all():
        status, log = commands.getstatusoutput('sudo restart docker')
        logger.info(log)
        if status > 0:
            sys.exit(1)

    @staticmethod
    def check_all():
        # 检查dock账户是否存在
        # 检查docker是否已经安装，是否正在运行，是否可以拖取指定镜像
        log = commands.getoutput('id dock')
        logger.info(log)
        if 'uid' not in log:
            logger.error('command id dock error, so there is no dock user')
            # InitTool.init_user_config()
        log = commands.getoutput('sudo docker version')
        logger.info(log)
        log_ = log.split('\n')
        if log.find('Version') >= 0:
            logger.info('docker is installed')
        else:
            logger.error('docker not installed')
            print('docker not installed')
            sys.exit(1)
        if log.find('Server') >= 0:
            logger.info('docker deamon is started backgroud')
        else:
            logger.error('docker deamon not started')
            print('docker deamon not started')
            sys.exit(1)
        test_cmd = "sudo docker pull %s:4000/busybox" % source_host_ip
        status, log = commands.getstatusoutput(test_cmd)
        if status >= 0:
            logger.info('docker can pull images for %s:4000' % source_host_ip)
        else:
            logger.error('docker can not pull images for %s:4000' % source_host_ip)
            print('docker can not pull images for %s:4000' % source_host_ip)
            sys.exit(1)


class DockerNode():
    # ==================docker相关==================================

    def __init__(self, settings=docker_settings):
        self.functions_dict = {
            'install': self.install_docker,
            'update': self.update_config,
            'run': self.run_docker,
            'rerun': self.rerun_docker,
            'check': self.check_depends}
        self.functions = ['install', 'update', 'run', 'check', 'rerun']
        InitTool.goto_workspace(work_dir)
        self.logger = get_mylogger('docker')
        self.logger.info('now init a docker node')
        self.setting = settings
        self.files = self.setting['config_files']
        log = commands.getoutput('sudo gpasswd -a dock docker')
        self.logger.info(log)

    def scp_config_files(self):
        InitTool.goto_workspace(work_dir)
        self.logger.info('at scp_config and files are:%s/%s'
                         % (self.setting['config_dir'], str(self.setting['config_files'])))
        cmd_scp = 'scp -r %s@%s:%s/%s .' % (username, source_host_ip, source_path, self.setting['config_dir'])
        self.logger.info(" cmd_scp is :%s" % cmd_scp)
        status, log = commands.getstatusoutput(cmd_scp)
        self.logger.info(log)
        if status > 0:
            sys.exit(1)
        for f in self.setting['config_files'].keys():
            cmd_cp = 'sudo cp %s/%s %s' % (self.setting['config_dir'], f, self.setting['config_files'][f])
            self.logger.info(" cmd_cp is :%s" % cmd_cp)
            status, log = commands.getstatusoutput(cmd_cp)
            self.logger.info(log)
            if status > 0:
                sys.exit(1)

    def update_config(self):
        self.logger.info('at update_docker_config_files')
        self.scp_config_files()
        status, log = commands.getstatusoutput('sudo systemctl daemon-reload')
        self.logger.info(log)
        # if status > 0:
        #     sys.exit(1)

    # check some depends for docker
    def check_depends(self):
        packages = ['iptables']
        self.logger.info('at check_depends and packages are:' + str(packages))
        log = commands.getoutput('uname -r')
        # log = commands.getoutput('lsb_release -a')
        self.logger.info(log)
        wh = log[:6].rfind('.')
        kernel_version = float(log[:wh])
        kernel_min_version = 1.13
        if kernel_version < kernel_min_version:
            self.logger.error('the linux kernel required 1.13 and above ')
            print('the linux kernel required 1.13 and above ')
            sys.exit(1)
        for p in packages:
            status, log = commands.getstatusoutput('%s --version' % p)
            self.logger.info(log)
            if status > 0:
                status, log = commands.getstatusoutput('sudo apt-get install %s' % p)
                self.logger.info(log)
                if status > 0:
                    sys.exit(1)

    # install docker with binnary files, and run docker service
    def install_docker(self):
        self.logger.info('at install_docker')
        self.logger.info('start install the docker relied on packages')
        self.check_depends()
        self.logger.info('start install_docker')
        log = commands.getoutput('sudo docker --version')
        self.logger.info(log)
        if log.find('1.12') >= 0:
            self.logger.info('docker version is already 1.12 up')
            return
        cmds = ['scp %s:%s .' % (source_host_ip, source_path + docker_tzg,),
                'sudo tar -zxvf %s' % docker_tzg,
                'sudo tar -xvf %s -C /' % docker_tar]
        for cmd in cmds:
            self.logger.info('cmd is:' + cmd)
            status, log = commands.getstatusoutput(cmd)
            self.logger.info(log)
            if status > 0:
                sys.exit(1)
        self.logger.info('end install_docker')

    def run_docker(self):
        self.logger.info('now start docker daemon')
        status, log = commands.getstatusoutput('sudo start docker')
        self.logger.info(log)
        if status > 0:
            self.logger.info('can not use upstart to start docker')
            status, log = commands.getstatusoutput('sudo systemctl daemon-reload')
            self.logger.info(log)
            status, log = commands.getstatusoutput('sudo systemctl enable docker')
            self.logger.info(log)
            status, log = commands.getstatusoutput('sudo systemctl start docker')
            self.logger.info(log)
            if status > 0:
                self.logger.error('can not use systemctl to start docker')
                print('error:can not use systemctl to start docker')
                sys.exit(1)
            else:
                self.logger.info('use systemctl to start docker ok')
        else:
            self.logger.info('use upstart to start docker ok')

    def rerun_docker(self):
        self.logger.info('now restart docker daemon')
        status, log = commands.getstatusoutput('sudo restart docker')
        self.logger.info(log)
        if status > 0:
            self.logger.info('can not use upstart to restart docker')
            status, log = commands.getstatusoutput('sudo systemctl daemon-reload')
            self.logger.info(log)
            status, log = commands.getstatusoutput('sudo systemctl restart docker')
            self.logger.info(log)
            if status > 0:
                self.logger.error('can not use systemctl to restart docker')
                print('can not use systemctl to restart docker')
                sys.exit(1)
            else:
                self.logger.info('use systemctl to restart docker ok')
        else:
            self.logger.info('use upstart to restart docker ok')


class SlaveInDocker(object):
    def __init__(self, conf_files, settings):

        self.files = conf_files
        self.setting = settings
        self.functions_dict = {
            # 'update':'scp_config_files',
            'update': self.update_config,
            'run': self.run_slave,
            'check': self.check_slave_container}
        self.functions = ['update', 'run', 'check']
        if not os.path.exists(self.setting['container_config_dir']):
            os.makedirs(self.setting['container_config_dir'])
        os.chdir(self.setting['container_config_dir'])
        self.logger = get_mylogger(self.setting['container_name'])
        self.logger.info('init  super class ok,at dir is:%s，for :%s' % (os.getcwd(), self.setting['container_name']))
        print('init  super class ok,at dir is:%s，for :%s' % (os.getcwd(), self.setting['container_name']))

    # cp source files to local
    def scp_config_files(self, files):
        self.logger.info('at scp_config and files are:%s' % str(files))
        source_path_ = source_path + self.setting['dir']
        localdir = work_dir + self.setting['dir']
        for f in files:
            self.logger.info(" f is :%s" % f)
            status, log = commands.getstatusoutput(
                'scp -r %s@%s:%s/%s %s' % (username, source_host_ip, source_path_, f, localdir))
            self.logger.info(log)
            if status > 0:
                sys.exit(1)

    # cp or update container yml config files
    def update_config(self):
        self.logger.info('at update_config')
        self.scp_config_files(self.files)

    def run_slave(self, pre_proccess=None):
        self.logger.info('at run_slave in docker container , at dir is:%s' % os.getcwd())
        if pre_proccess is not None:
            pre_proccess()
        log = commands.getoutput('sudo docker rm -f %s' % self.setting['container_name'])
        # log = commands.getoutput('sudo docker stop -t 3 %s' % self.setting['container_name'])
        self.logger.info(log)
        still_runnig = commands.getoutput('sudo docker ps -aq')
        self.logger.info('still running container is %s' %
                         str(still_runnig))
        # if len(still_runnig) is not 0:
        #     force_clean_runnig()
        status, log = commands.getstatusoutput('sudo docker-compose -f %s pull' % self.setting['compose-file'])
        self.logger.info(log)
        if status > 0:
            sys.exit(1)
        status, log = commands.getstatusoutput(
            'sudo docker-compose -f %s up --force-recreate -d' % self.setting['compose-file'])
        self.logger.info(log)
        if status > 0:
            sys.exit(1)

    def check_slave_container(self):
        self.logger.info('at check_container')
        info = commands.getoutput('sudo docker ps  --format "{{.Names}} {{.Status}}"')
        self.logger.info('info is:' + str(info))
        print('info is:' + str(info))
        lables_ok = (self.setting['container_name'], 'Up', 'second')
        for f in lables_ok:
            if f not in info:
                return False
        return True

    def force_clean_runnig(self):
        log = commands.getoutput('sudo docker rm -f `docker ps -aq`')
        self.logger.info('the removed containers are:' + log)
        still_runnig = commands.getoutput('sudo docker ps -a|grep %s' % self.setting['container_name'])
        self.logger.info('force_clean_runnig: still running container is %s' %
                         str(still_runnig))
        # if len(still_runnig) is not 1:
        #     log = commands.getoutput('sudo restart docker')
        #     logger.info(log)

    def update_alive_config(self, file_s, file_to):
        status, log = commands.getstatusoutput(
            'docker cp %s %s:%s' % (file_s,
                self.setting['container_name'], file_to)
        self.logger.info(log)
        if status > 0:
            sys.exit(1)


class JenkinsSlave(SlaveInDocker):
    def __init__(self, settings=jenkins_settings):
        conf_files = settings['config_files']
        super(JenkinsSlave, self).__init__(conf_files, settings)

    def pre_proccess(self):
        if not os.path.exists(self.setting['container_config_dir'] + '/__init__.py'):
            s, l = commands.getstatusoutput('touch %s' % self.setting['container_config_dir'] + '/__init__.py')
            self.logger.info('pre_proccess for create initpy file status:%s' % str(s))
            self.logger.info('pre_proccess for create initpy file log:%s' % l)
        else:
            self.logger.info('pre_proccess for create initpy exsist')
        sys.path.append(self.setting['container_config_dir'])
        import save_config
        # save_config is used to save local jenkins account config to a local file
        save_config.save_jenkins_config()

    def run_slave(self):
        super(JenkinsSlave, self).run_slave(self.pre_proccess)


class ZabbixSlave(SlaveInDocker):
    def __init__(self, settings=zabbix_settings):
        print('at init ZabbixSlave begin')
        # logger.info('at init ZabbixSlave begin')
        conf_files = settings['config_files']
        super(ZabbixSlave, self).__init__(conf_files, settings)
        print('at init ZabbixSlave end')
        # logger.info('at init ZabbixSlave end')

    def pre_proccess(self):
        print('at pre_proccess ZabbixSlave end,at dir is:%s' % os.getcwd())
        logger.info('at pre_proccess ZabbixSlave end,at dir is:%s' % os.getcwd())
        self.logger.info('at zabbix pre_proccess,at dir is:%s' % os.getcwd())
        if not os.path.exists('./tmp'):
            os.mkdir('./tmp')
            os.chmod('./tmp', 0777)

    def run_slave(self):
        print('at run_slave ZabbixSlave end,at dir is:%s' % os.getcwd())
        self.logger.info('at run_slave ZabbixSlave end,at dir is:%s' % os.getcwd())
        super(ZabbixSlave, self).run_slave(self.pre_proccess)


class HadoopSlave(SlaveInDocker):
    def __init__(self, settings=hadoop_settings):
        print('at init HadoopSlave begin')
        # logger.info('at init ZabbixSlave begin')
        conf_files = settings['config_files']
        super(HadoopSlave, self).__init__(conf_files, settings)
        print('at init HadoopSlave end')
        # logger.info('at init ZabbixSlave end')

    def pre_proccess(self):
        print('at pre_proccess HadoopSlave end,at dir is:%s' % os.getcwd())
        logger.info('at pre_proccess HadoopSlave end,at dir is:%s' % os.getcwd())
        self.logger.info('at hadoop pre_proccess,at dir is:%s' % os.getcwd())
        if not os.path.exists('./data'):
            os.mkdir('./data')
            os.chmod('./data', 0777)

    def run_slave(self):
        print('at run_slave HadoopSlave end,at dir is:%s' % os.getcwd())
        self.logger.info('at run_slave HadoopSlave end,at dir is:%s' % os.getcwd())
        super(HadoopSlave, self).run_slave(self.pre_proccess)


class RegistrySlave(SlaveInDocker):
    def __init__(self, settings=registry_settings):
        conf_files = settings['config_files']
        super(JenkinsSlave, self).__init__(conf_files, settings)


parse2class_dicts = {'docker': DockerNode,'jenkins': JenkinsSlave,
                     'hadoop':HadoopSlave,'zabbix': ZabbixSlave, 'registry': RegistrySlave}


def parse2slave(args=sys.argv[1:]):
    opts = argv_parse(args)
    # opts = argv_parse(['docker', '-check'])
    # opts = argv_parse(['init'])
    opts_dict = opts.__dict__
    class_obj_ = opts_dict['object']
    if class_obj_ == 'init':
        print('init user dock')
        InitTool.init_user_config()
        return
    if class_obj_ == 'autoinit':
        print('init user dock')
        InitTool.auto_init()
        return
    if class_obj_ != 'docker':
        print('not isinstance(class_obj,DockerNode)')
        InitTool.init()
    if class_obj_ in parse2class_dicts.keys():
        class_obj = parse2class_dicts[class_obj_]()
        print('action on:%s !!!' % class_obj_)
        class_obj.logger.info('action on:%s !!!' % class_obj_)
    for mtd in class_obj.functions:
        if opts_dict[mtd] is True:
            print('action on:%s, function is:%s' % (class_obj_, mtd))
            class_obj.logger.info('action on:%s, function is:%s' % (class_obj_, mtd))
            class_obj.functions_dict[mtd]()


if __name__ == "__main__":
    parse2slave()
    # ansible -i hosts 225 -m script -a './deploy.py jenkins -update -run -check'
    # ansible -i groups.py all -m script -a './deploy.py docker -install -run'

    # readme：
    # 第一次部署的时候得手动到远程机器上用root去创建账号（默认jenkins），拷贝pub到auth里
    # python ./deploy.py init && su dock & cd ~ & scp -r dock@172.26.35.211:~/.ssh . $ ls -al /data/dock/docker_test
    # sudo cp /root/deploy.py . python ./deploy.py docker -install -update -run -check
    # python ./deploy.py zabbix -update -run -check
