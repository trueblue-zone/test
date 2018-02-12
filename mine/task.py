# -*- coding: utf-8 -*-
import threading, time, Queue, copy
import patch_system.views
import logger, config, sys
import department_config
import remote_call

sys.path.append(config.zeus_tool_path + "/lib")
sys.path.append(config.zeus_tool_path + "/patching/config")
import send_mail

task_queue = Queue.Queue(maxsize=100)
mes_queue = Queue.Queue(maxsize=4)

myLogger = logger.getMyLogger('task', level='debug')
id_dict = {}
platform_patch_dict = {}
patch_id_wait_bak = set()
con_times = 0
object_connection = patch_system.models.Patching_DB.objects


class PatchTask(threading.Thread):
    def __new__(cls, *args, **kw):
        myLogger.info('__new__')
        if not hasattr(cls, '_instance'):
            orig = super(PatchTask, cls)
            cls._instance = orig.__new__(cls, *args, **kw)
            cls._instance.patch_thread = 0
            cls._instance.tasks_running = set()
            cls._instance.tasks_wait = set()
            cls._instance.tasks_request = set()
            cls._instance.restart_flag = 0
            cls._instance.service_state = 'task init'
        return cls._instance

    def __init__(self, name=''):
        myLogger.info('__init__')
        threading.Thread.__init__(self)
        self.name = name

    def start_patch_tasks(self):
        myLogger.info('start_patch_tasks')
        patch_info_list = classification(self.tasks_wait, self.tasks_running)
        # patch_info_list = classification(self.tasks_wait, platform_patch_dict, patch_id_wait_bak, self.tasks_running)
        if not self.check_patchs(patch_info_list[1]):
            mes = 'can not go on to start a new thread for platform:' + str(patch_info_list[0])
            myLogger.error(mes)
            self.tasks_error = copy.copy(self.tasks_running)
            self.tasks_running = set()
            return mes
        myLogger.info('start_patch_tasks len is:' + str(len(patch_info_list[1])))
        patch_thread = threading.Thread(target=patch_system.views.do_patching_list, args=(patch_info_list[1],))
        # patch_thread.setDaemon(True)
        patch_thread.start()
        self.patch_thread = patch_thread

    def check_patchs(self, patch_info_list):
        patch_num_list = []
        patch_id_list = []
        for patch in patch_info_list:
            patch_num_list.append(patch.patch_num)
            patch_id_list.append(patch.id)
            platform_name = patch.platform.platform_name
            if platform_name in department_config.others['platform']:
                return True
        patch_num_list.sort()
        patch_id_list.sort()
        myLogger.debug('patch_num_list is:' + str(patch_num_list))
        myLogger.debug('patch_id_list is:' + str(patch_id_list))
        len_judge = len(patch_num_list) + patch_num_list[0] - 1 - patch_num_list[-1]
        myLogger.debug('len_judge is:' + str(len_judge))
        if len_judge != 0:
            myLogger.error('len_judge is not ok')
            return False
        if patch_num_list[0] != 1:
            # check_mysql_connection()
            former_patch = object_connection.filter(platform_id=patch_info_list[0].platform_id). \
                filter(patch_type=patch_info_list[0].patch_type).filter(patch_num=patch_num_list[0] - 1)
            myLogger.debug('the len of former_patch is:%d' % len(former_patch))
            if former_patch[0].validate_status != '3':
                myLogger.error('the former patch did not verify ok!')
                return False
        return True

    def start_tasks(self):
        if not hasattr(self, 'running_flag'):
            self.running_flag = 1
            self.start()

    def run(self):
        task_flag = True
        while 1:
            myLogger.info("restart flag is:" + str(self.restart_flag))
            tasks_request = set(task_queue.get())
            print "restart flag is:" + str(self.restart_flag)
            check_mysql_connection()
            if 'task over' in tasks_request:
                task_flag = True
                myLogger.info('task run over:' + str(patch_id2num(self.tasks_running)))
                self.tasks_running = set()
            if self.restart_flag >= 2:
                mes = "the service will restart!,the task_running will not be drop' \
                                         ',the task_wait will be drop\n"
                if task_flag:
                    self.service_state = 'task is over'
                else:
                    self.service_state = 'task is running but locked'
                if len(self.tasks_running) != 0:
                    mes += ',the task_running:' + str(patch_id2num(self.tasks_running))
                if len(self.tasks_wait) != 0:
                    mes += ',the task_wait:' + str(patch_id2num(self.tasks_wait))
                if 'task over' not in tasks_request:
                    mes_queue.put(mes)
                    mes_queue.task_done()
                elif self.restart_flag >= 3:
                    # send_restart_mail(mes)
                    restart('the service restart ok!')
                continue
            if 'task over' not in tasks_request:
                new_tasks = tasks_request - self.tasks_running
                tasks_wait = new_tasks - self.tasks_wait
                double_tasks = tasks_request - tasks_wait
                self.tasks_wait |= tasks_wait
                return_mes = {"tasks_wait": str(patch_id2num(self.tasks_wait)),
                              "double_tasks": str(patch_id2num(double_tasks)),
                              "tasks_running": str(patch_id2num(self.tasks_running))}
                myLogger.info('get new request is:' + str(patch_id2num(tasks_request)))
            if task_flag is True and len(self.tasks_wait) != 0:
                mes = self.start_patch_tasks()
                if mes is not None:
                    myLogger.info('tasks_error list is:' + str(patch_id2num(self.tasks_error)))
                    return_mes = {"message is": mes, "tasks_error": str(patch_id2num(self.tasks_error))}
                    task_flag = True
                else:
                    myLogger.info('running task list is:' + str(patch_id2num(self.tasks_running)))
                    myLogger.info('waiting task list is:' + str(patch_id2num(self.tasks_wait)))
                    return_mes = {"tasks_running": str(patch_id2num(self.tasks_running))}
                    task_flag = False
            if 'task over' not in tasks_request:
                myLogger.debug('return_mes is:' + str(return_mes))
                mes_queue.put(return_mes)
                mes_queue.task_done()
                # myLogger.info('the new request return mes is:' + str(return_mes))

    def restart_sever_request(self, cmd):
        myLogger.info('restart_sever_request cmd is:' + str(cmd))
        if cmd == 'get_un':
            return "there are some un verify ok patchs:\n" + str(get_unverify_patch())
        if cmd == 'restart':
            self.restart_flag = 3
        elif cmd == 'lock':
            self.restart_flag = 2
        elif cmd == 'unlock':
            self.restart_flag = 1
        else:
            self.restart_flag = 0
        if self.restart_flag > 1 and not self.is_alive():
            # self.flag = 0
            self.service_state = 'task is locked'
        mes = ''
        mes1 = ''
        if self.restart_flag >= 2:
            mes = "sorry, the service will restart!\n," \
                  "the task_running will not be drop, the task_wait will be drop\n"
        if len(self.tasks_wait) != 0:
            mes1 += ',task_wait:' + str(patch_id2num(self.tasks_wait))
        if len(self.tasks_running) != 0:
            mes1 += ',task_running :' + str(patch_id2num(self.tasks_running))
        elif self.restart_flag >= 3:
            mes1 = "the service restart ok!\n," \
                   "the task_wait will be drop\n" + mes1
            restart(mes1)
        if cmd == 'restartt1':
            # check_mysql_connection()
            patch_list_info1 = object_connection.filter(
                id__in=list(self.tasks_wait))
            myLogger.debug('len of patch_list_info is:' + str(len(patch_list_info1)))
        return mes + mes1

    def get_state(self):
        return self.service_state


def patch_id2num(patch_id_list):
    myLogger.debug('start use patch_id2num')
    myLogger.debug('the dict for patchid is:' + str(id_dict))
    patch_num_list = []
    list_need_add = []
    for patch_id in patch_id_list:
        if patch_id in id_dict:
            patch_num_list.append(id_dict[patch_id])
        else:
            list_need_add.append(patch_id)
    if len(list_need_add) != 0:
        # check_mysql_connection()
        patch_list_info = object_connection.filter(
            id__in=list_need_add)
        for patch in patch_list_info:
            id_dict[patch.id] = patch.patch_num
            patch_num_list.append(patch.patch_num)
    myLogger.debug('the dict for oked patchid is:' + str(id_dict))
    return patch_num_list


def send_restart_mail(message, who=None):
    myLogger.info("send_restart_mail")
    From = "cd.int@tcl.com"
    domain = "cd.int"
    domain_passwd = "Cd123456"
    to_list = ['tenghui.li@tcl.com', 'shuting.wang@tcl.com', 'yongli.zhao@tcl.com']
    cc_list = ['yunwei.wang@tcl.com']
    myLogger.info("who is:" + str(who))
    if who is not None:
        to_list = [who]
        cc_list = to_list
        myLogger.info("to_list and to_list is all same:" + str(to_list))
    mail_subject = "restart server ok"
    setMailContent = message
    try:
        send_mail.send_mail(domain, From, mail_subject, setMailContent, to_list, domain,
                            domain_passwd, cc_list=cc_list)
        myLogger.info("Send e-mail Successed! ")
        print "Send e-mail Successed!"
        return True
    except Exception as e:
        myLogger.error("Send e-mail Failed!")
        myLogger.error(e)
        return False


# 用于给待打的patch根据项目名称分类聚合
def classification(patch_id_wait_list, task_running):
    # platform_patch_dict
    if len(patch_id_wait_list) == 0:
        return
    list_need_add = patch_id_wait_list - patch_id_wait_bak
    # list_need_add是计算出platform_patch_dict中不存在的patch id，用这些patch id去数据库查询
    list_need_add = list(list_need_add)
    myLogger.debug('patch_id_wait_list is:' + str(patch_id_wait_list))
    myLogger.debug('platform_patch_dict is:' + str(platform_patch_dict))
    myLogger.debug('patch_id_wait_bak is:' + str(patch_id_wait_bak))
    myLogger.debug('list_need_add is:' + str(list_need_add))
    if len(list_need_add) != 0:
        myLogger.info('more new to add to platform_patch_dict')
        # check_mysql_connection()
        patch_list_info1 = object_connection.filter(
            id__in=list_need_add)
        myLogger.debug('len of patch_list_info is:' + str(len(patch_list_info1)))
        patch_list_info = patch_list_info1.order_by('patch_num')
        myLogger.debug('len of patch_list_info is:' + str(len(patch_list_info1)))
        for patch in patch_list_info:
            myLogger.debug('len of patch_list_info is:' + str(len(patch_list_info)))
            if not platform_patch_dict.has_key(patch.platform.platform_name):
                myLogger.debug('patch.platform.platform_name is:' + str(patch.platform.platform_name))
                platform_patch_dict[patch.platform.platform_name] = []
            myLogger.debug('len of platform_patch_dict key of %s is:%s' % (
                patch.platform.platform_name, str(len(platform_patch_dict[patch.platform.platform_name]))))
            platform_patch_dict[patch.platform.platform_name].append(patch)
        for platform_name in platform_patch_dict.keys():
            myLogger.debug('platform_name is:' + str(platform_name))
            if len(platform_patch_dict[platform_name]) == 0:
                platform_patch_dict.pop(platform_name)
    if len(platform_patch_dict) == 0:
        myLogger.error('platform_patch_dict should never be null')
        return False
        # print "len(platform_patch_dict) is null"
    task_ = platform_patch_dict.popitem()
    # 从platform_patch_dict中随机选在一个platform的patchs去打
    # task = list(task_)
    task = []
    task.append(task_[0])
    task.append('')
    task[1] = sorted(task_[1], key=lambda ob: ob.patch_num)
    # 他叔项目的patch，qcom的只能一次打一个patch，所以拿多了还得放回去
    if task[0] in department_config.others['platform']:
        if len(task[1]) > 1:
            platform_patch_dict[task[0]] = task[1][1:]
            task[1] = task[1][:1]
    task_running.clear()
    for patch in task[1]:
        task_running.add(patch.id)
    # task_running和task其实放的信息是一样的
    patch_id_wait_bak.clear()
    patch_id_wait_list.clear()
    for platform_name in platform_patch_dict.keys():
        myLogger.debug('platform_name is:' + str(platform_name))
        for patch in platform_patch_dict[platform_name]:
            myLogger.debug('platform_id is:' + str(patch.id))
            patch_id_wait_bak.add(patch.id)
            patch_id_wait_list.add(patch.id)
    myLogger.debug('task:' + str(task))
    myLogger.debug('patch_id_wait_list is:' + str(patch_id_wait_list))
    myLogger.debug('platform_patch_dict is:' + str(platform_patch_dict))
    myLogger.debug('patch_id_wait_bak is:' + str(patch_id_wait_bak))
    return task


def restart(mes1, who=None):
    import os
    # os.system('cd %s && git pull' % config.project_path)
    myLogger.info('restart_sever_request')
    send_restart_mail(mes1, who)
    with open('%s/manage.py' % config.project_path, 'a') as f:
        f.write('\n')
    myLogger.info('restart_sever_request ok')


def get_unverify_patch():
    # check_mysql_connection()
    ups = object_connection.exclude(validate_status=3)
    # "0:wait 1:ready 2:doing 3:success 4:faild"
    pns = {"wait": [p.__str__() for p in ups.filter(validate_status=0)],
           "ready": [p.__str__() for p in ups.filter(validate_status=1)],
           "doing": [p.__str__() for p in ups.filter(validate_status=2)],
           "failed": [p.__str__() for p in ups.filter(validate_status=4)]}
    myLogger.info('pns is:' + str(pns))
    return pns


def check_mysql_connection():
    from django.db import connection
    try:
        myLogger.info('ping')
        connection.connection.ping()
        myLogger.info('ping ok')
    except:
        myLogger.info('closing ')
        connection.close()
        myLogger.info('close ok')
    else:
        return True


def remote_callback(patch_params):
    patch_name = patch_params['platform_name']
    status = patch_params['status']
    patch_name = patch_params['patch_name']
    patch_name = patch_name.split('_')
    patch_type = patch_name[0]
    patch_num = patch_name[1]
    patch_id = patch_name[2]
    return patch_params
