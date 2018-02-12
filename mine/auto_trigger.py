# -*- coding: utf-8 -*-
from task import task_queue
import patch_system.views
import logger, config, sys, os
import department_config
# from django.db import connection
import json
import commands
import jenkins
# import remote_call
from patch_system import models

sys.path.append(config.zeus_tool_path + "/lib")
sys.path.append(config.zeus_tool_path + "/patching/config")
import send_mail

id_dict = {}
platform_patch_dict = {}
patch_id_wait_bak = set()
con_times = 0
object_connection = models.Patching_DB.objects
myLogger = logger.getMyLogger('trigger')


def add_patch(patch_params):
    info_path = '/home/thli/src/patches/'
    myLogger.info('get new add_patch action:' + str(patch_params))
    platform = patch_params['platform_name']
    action = patch_params['action']
    library = patch_params['library']
    try:
        platform_info = models.Platform.objects.get(platform_name=platform)
    except Exception as e:
        if action == 'new':
            models.Platform.objects.create(platform_name=platform, type='new',
                                           patch_package_dir='%s/patch' % platform,
                                           code_lib='http://172.26.32.15/%s' % platform,
                                           download_gerrit='%s/manifests_cd.git' % platform)
            return 'platform_name:'+platform+';at:'+info_path
        else:
            return 'error, you gave action on new platform should only be new!!!'
    last_patch = None
    if action == 'new':
        return 'platform_name:'+platform+';at:'+info_path
    try:
        last_patch = platform_info.platform_patch_library.all().order_by('-id')[0]
        last_num = last_patch.patch_num + 1
    except Exception as e:
        myLogger.warn('get the last patch in platform:%s failed,reason is:%s' % (platform, e.message))
        last_num = 1
    patch_package_src = department_config.swd1['mount_dir']
    patch_path = patch_package_src + '/' + platform_info.patch_package_dir
    if action == 'do':
        ret = import_patch(info_path, platform_info, last_num)
    elif action == 'email_notify':
        if not last_patch:
            return 'no librarys to monitor'
        email_addrs = {'clibrary1test': 'tenghui.li@tcl.com'}
        ret = email_notify(last_patch, email_addrs)
    elif action == 'active':
        if not last_patch:
            return 'no librarys to active'
        account = patch_params['account']
        commit_id = patch_params['commit_id']
        ret = active_library(last_patch, library, account, commit_id)
    # elif action == 'verified':
    #     ret = verify_library(platform_info, library, 'ok')
    # elif action == 'close' or action == 'open':
    #     ret = turn_patch(last_patch, action)
    else:
        ret = 'you gave a wrong action,please check it,it should be new,do,active,verified or open/close'
    return ret


def email_notify(last_patch, email_addrs):
    librarys = last_patch.patch_library.all()
    not_in = []
    for f in librarys:
        m = email_addrs.get(f.library)
        if not m:
            not_in.append(f.library)
        else:
            f.email = email_addrs.get(f.library)
            f.save()
    send_mail_(email_addrs.values())
    if len(not_in) == 0:
        return 'send emails ok'
    else:
        return 'some librarys:%s did not assign to anyone' % str(not_in)


def send_mail_(emails, messages):
    # myLogger.info("send_restart_mail")
    From = "cd.int@tcl.com"
    domain = "cd.int"
    domain_passwd = "Cd123456"
    to_list = emails
    # to_list = ['tenghui.li@tcl.com']
    cc_list = ['tenghui.li@tcl.com']
    # myLogger.info("who is:" + str(who))
    mail_subject = "冲突库对应负责人， 这是一个测试！！！"
    setMailContent = messages
    try:
        send_mail.send_mail(domain, From, mail_subject, setMailContent, to_list, domain,
                            domain_passwd, cc_list=cc_list)
        myLogger.info("Send e-mail Successed! ")
        print "Send e-mail Successed!"
        return True
    except Exception as e:
        myLogger.error("Send e-mail Failed! , error mes is:" + str(e))
        print("Send e-mail Failed!")
        print(e)
        return False


def import_patch(info_path, platform_info, last_num):
    new_path = info_path + '/' + platform_info.platform_name
    try:
        if not os.path.exists(new_path):
            s, l = commands.getstatusoutput('mkdir -p %s' % new_path)
            myLogger.info('mkdir ap,status is:%s,log is:%s' % (str(s), l))
        s, l = commands.getstatusoutput('tar -xzvf %s.tar.zg -C %s' % (new_path, new_path))
        myLogger.info('tar -xzvf info,status is:%s,log is:%s' % (str(s), l))
        if s < 1:
            patch_infos1 =dict()
            with open(new_path + '/ap.txt', 'r') as fn:
                lines = fn.read()
                # patch_infos1 = json.loads(lines)
            all = lines.split('[')
            for a in all:
                k,v = a.split(']\n')[0:2]
                v_ = v.split('\n')[:-1]
                if ':' in v:
                    patch_infos1[k] = dict()
                    for vv in v_:
                        patch_infos1[k][vv.split(':')[0]] = vv.split(':')[1]
                else:
                    if len(v_) > 1:
                        patch_infos1[k] = []
                        for vv in v_:
                            patch_infos1[k].append(vv)
                    elif len(v_) == 1:
                        patch_infos1[k] = v_
        else:
            myLogger.error('tar -xzvf info,status is:%s,log is:%s' % (str(s), l))
        # cloud_mnt_path = '/cloud_mtkpatch/SW_share_folder/patchmanagement/MtkProjects/'
        cloud_mnt_path = '/cloud_mtkpatch/int_test/'
        ap_path = '%s/%s/AP/' % (cloud_mnt_path, platform_info.patch_package_dir)
        modem_path = '%s/%s/Modem/' % (cloud_mnt_path, platform_info.patch_package_dir)
        if not os.path.exists(ap_path):
            s, l = commands.getstatusoutput('mkdir -p %s' % ap_path)
            myLogger.info('mkdir ap,status is:%s,log is:%s' % (str(s), l))
        s, l = commands.getstatusoutput('mv %s/*ap* %s' % (new_path, ap_path))
        myLogger.info('mv ap info,status is:%s,log is:%s' % (str(s), l))
        if not os.path.exists(modem_path):
            s, l = commands.getstatusoutput('mkdir -p %s' % modem_path)
            myLogger.info('mkdir modem,status is:%s,log is:%s' % (str(s), l))
        s, l = commands.getstatusoutput('mv %s/*modem* %s/modem_%d.txt' % (new_path, modem_path, last_num))
        myLogger.info('mv modem info,status is:%s,log is:%s' % (str(s), l))

    except Exception as e:
        mes = 'read and load json file failed'
        myLogger.info('occur some errors:' + mes)
        return mes
    # patch_info_dict = {'platform': 'platform_new', 'tmp': 'base_branch1', 'patch_num': 1,
    #                    'library': 'library1,library2,library3,library4'}
    # librarys = [{'library': 'clibrary1test', 'email': 'tenghui.li@tcl.com', 'status': '0'},
    #             {'library': 'clibrary2test', 'email': 'dechao.dai@tcl.com', 'status': '1'},
    #             {'library': 'clibrary3test', 'email': 'yunzhou.song@tcl.com', 'status': '2'}]
    # patch_info_dict = patch_infos1['patch_info']
    conflictLibrarys = patch_infos1['conflictLibraryPaths']
    base = [f for f in patch_infos1['baselineInfo']]
    base = ':'.join(base)
    librarys = ':'.join(patch_infos1['upgradeLibraryPaths'])
    new_patch = models.Patch_Library.objects.create(platform=platform_info, base=base,
                                                    tmp=patch_infos1['upgradeTempBranch'],
                                                    library=librarys,
                                                    patch_num=last_num)
    mes = 'platform:%s\n;mtk-branch:%s\n;temp-branch:%s\n.' % (
        platform_info.platform_name, base, patch_infos1['upgradeTempBranch'])
    mes += 'conflict librarys:\n'
    url_ = '%s/?p=%s.git;a=commit;h=%s'
    for l in conflictLibrarys:
        models.Library_Status.objects.create(
            patch_library=new_patch, library=l,
            # email=l['email'],
            commit=conflictLibrarys[l],
            commit_url=url_ % (platform_info.code_lib, l, conflictLibrarys[l]),
            changed_times=0)
        # to_list.add(l['email'])
        # mes += '%s:%s' % (l['library'], l['email'])
    # send_mail_(to_list, mes)
    return 'ok'


def active_library(last_patch, library, account, commit_id):
    # platform = platform_info.platform_name
    # last_patch = platform_info.platform_patch_library.all().order_by('-id')[0]
    library_info = last_patch.patch_library.filter(library=library)
    if len(library_info) == 0:
        return 'you gave library:%s dose not in monitor list' % library
    else:
        library_info = library_info[0]
    library_info.changed_times += 1
    library_info.save()
    models.Change_History.objects.create(library=library_info, email=account, commit_id=commit_id)
    library_not_ok = last_patch.patch_library.filter(changed_times=0)
    if len(library_not_ok) == 0:
        # param_test = 'ADD_VERSION=force MINI=true  Build_server=%s   ' \
        #              'BASELINE_MANIFEST=verygood,the this is a test from web' % '172.26.35.123_2'
        # s, l = commands.getstatusoutput(
        #     'ssh jenkins@172.26.35.81 "zeus/lib/jenkins_trigger.pl %s %s"' % (platform, param_test))
        # myLogger.info('ssh remote execute info,status is:%s,log is:%s' % (str(s), l))
        ret = 'all library on this patch had actived once,so it will trigger once compile'
    else:
        librarys = [f.library for f in library_not_ok]
        ret = 'but still some librarys:%s blocked' % str(librarys)
    return 'active library:%s ok,' % library + ret


    #
    # def turn_patch(last_patch, action):
    #     last_patch.open_status = action
    #     last_patch.save()
    #     return 'ok'
    # def verify_library(platform_info, library, status):
    #     myLogger.info('verify_library:platform:%s, library:%s, status:%s' % (platform_info.platform_name, library, status))
    #     return 'ok'

    # sudo mount -t davfs http://172.26.35.47:8087/remote.php/webdav/ /home/thli/workspace/Documents/docker_test/nextcloud/nextcloud_data
