from os import path
import os, time
from pyinotify import WatchManager, Notifier, ProcessEvent, ExcludeFilter, IN_DELETE, IN_CREATE, IN_MODIFY
import logging
import random

data_path = '/home/thli/workspace/Documents/docker_test/nextcloud/data/Documents'
data_bak = '/home/thli/workspace/Documents/docker_test/nextcloud/data_bak'
clock_time = 4
log_dir = './sync'


# scaned = False
# notifier = None

def getMyLogger(name, level='info'):
    logger = logging.getLogger(name)
    filename = './sync/sync.log'
    lelel_dict = {'info': logging.INFO, 'debug': logging.DEBUG, 'error': logging.ERROR}
    logger.setLevel(lelel_dict[level])
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    fh = logging.FileHandler(filename=filename)  # , backupCount=2
    fh.suffix = "%Y-%m-%d.log"
    fm = logging.Formatter('[%(levelname)s] %(message)s %(filename)s[line:%(lineno)d] time:%(asctime)s')
    fm.datefmt = '%d %H:%M:%S'
    fh.setFormatter(fm)
    logger.addHandler(fh)
    return logger


logger = getMyLogger('sync')


def full_scan_sync(dir_):
    logger.info('another_call, dir_ is:' + dir_)
    dir_p = path.join(data_path, dir_)
    dir_b = path.join(data_bak, dir_)
    dirs_p = os.listdir(dir_p)
    dirs_b = os.listdir(dir_b)
    files_change_p = {}
    files_change_b = {}
    need_recurse_dirs = []
    for f in dirs_p:
        if f.endswith('.swp') or f.endswith('.swpx') or f.endswith('~'):
            continue
        if f not in dirs_b:
            cmd = 'cp -rf --preserve="timestamps" %s %s' % (path.join(dir_p, f), dir_b)
            os.system(cmd)
            logger.info('cmd is:' + cmd)
            # cmd = 'chmod 777 %s' % path.join(dir_b, f)
            # os.system(cmd)
            # logger.info('cmd is:' + cmd)
            continue
        if path.isfile(path.join(dir_p, f)):
            files_change_p[f] = (path.getmtime(path.join(dir_p, f)))
        else:
            need_recurse_dirs.append(f)
    for f in dirs_b:
        if f.endswith('.swp') or f.endswith('.swpx') or f.endswith('~'):
            continue
        if f not in dirs_p:
            cmd = 'sudo cp -rH --preserve="timestamps" %s %s' % (path.join(dir_b, f), dir_p)
            os.system(cmd)
            logger.info('cmd is:' + cmd)
            continue
        if path.isfile(path.join(dir_b, f)):
            files_change_b[f] = (path.getmtime(path.join(dir_b, f)))
    for f in files_change_p.keys():
        clock = files_change_p[f] - files_change_b[f]
        if clock > clock_time:
            cmd = 'cp -rf --preserve="timestamps" %s %s' % (path.join(dir_p, f), dir_b)
            os.system(cmd)
            logger.info('cmd is:' + cmd)
            # cmd = 'chmod 777 %s' % path.join(dir_b, f)
            # os.system(cmd)
            # logger.info('cmd is:' + cmd)
        elif -clock > clock_time:
            cmd = 'sudo cp -rH --preserve="timestamps" %s %s' % (path.join(dir_b, f), dir_p)
            os.system(cmd)
            logger.info('cmd is:' + cmd)
    del dir_p, dir_b, dirs_b, dirs_p, files_change_p, files_change_b
    for d in need_recurse_dirs:
        full_scan_sync(path.join(dir_, d))


class EventHandler(ProcessEvent):
    def process_IN_CREATE(self, event):
        # return
        name = str(event.name)
        if name.endswith('.swp') or name.endswith('.swpx') or name.endswith('~'):
            print('no need to backup')
            return
        logger.info('process_IN_CREATE: event.path is:%s, event.name is:%s' % (event.path, name))
        file_p = path.join(event.path, name)
        if os.path.islink(file_p):
            if data_bak in event.path:
                file_dir = path.join(data_path, path.relpath(event.path, data_bak))
                os.system('sudo cp -rHf --preserve="timestamps" %s %s' % (file_p, file_dir))
        print "Create file:%s." % path.join(event.path, event.name)

    def process_IN_DELETE(self, event):
        return
        logger.info('process_IN_DELETE: event.path is:%s, event.name is:%s' % (event.path, event.name))
        name = str(event.name)
        if name.endswith('.swp') or name.endswith('.swpx') or name.endswith('~'):
            print('no need to backup')
            return
        if data_path in event.path:
            data_b = data_bak
            data_p = data_path
        else:
            data_b = data_path
            data_p = data_bak
        file_dir = path.join(data_b, path.relpath(event.path, data_p))
        os.system('rm -rf %s' % path.join(file_dir, event.name))
        print "Delete file:%s." % path.join(event.path, event.name)

    def process_IN_MODIFY(self, event):
        if not os.path.exists(data_path):
            return
        logger.info('process_IN_MODIFY: event.path is:%s, event.name is:%s' % (event.path, event.name))
        name = str(event.name)
        if name.endswith('.swp') or name.endswith('.swpx') or name.endswith('~'):
            print('no need to backup')
            return
        if data_path in event.path:
            data_b = data_bak
            data_p = data_path
        else:
            data_b = data_path
            data_p = data_bak
        file_dir = path.join(data_b, path.relpath(event.path, data_p))
        file_m = path.join(event.path, name)
        file_b = path.join(file_dir, name)
        if not path.isfile(file_m):
            logger.info('a dir')
            return
        if path.exists(file_b):
            changed_time_b = path.getmtime(file_b)
            changed_time_m = path.getmtime(file_m)
            if changed_time_b == changed_time_m:
                logger.info('time equaled,changed_time_b is:%f, changed_time_m%f' % (changed_time_b, changed_time_m))
                return
            else:
                logger.info(
                    'time not equaled,changed_time_b is:%f, changed_time_m%f' % (changed_time_b, changed_time_m))
        if data_path in event.path:
            if not path.exists(file_dir):
                os.system('mkdir -p %s' % file_dir)
            os.system('cp -Hf --preserve="timestamps" %s %s' % (file_m, file_dir))
        else:
            if not path.exists(file_dir):
                os.system('sudo mkdir -p %s' % file_dir)
            os.system('sudo cp -Hf --preserve="timestamps" %s %s' % (file_m, file_dir))
        logger.info("Modify file:%s." % path.join(event.path, name))


def FsMonitor(path='./', path_bak='bak'):
    mask = IN_MODIFY
    # # mask = IN_DELETE | IN_CREATE | IN_MODIFY
    # # exclude_filter = ExcludeFilter(['^'+data + '/' + "abb", "^.*.swp", "^.*.swpx", 'acc'])
    logger.info("now starting monitor %s." % path)
    # notifier.loop(timeout=10)
    notifier = None
    wm = None
    scaned = 0
    while True:
        try:
            # ran = random.randint(0, 10)
            # if ran >= 5:
            if not os.path.exists(data_path):
                scaned = 1
                if notifier is not None:
                    notifier.stop()
                    del notifier
                    del wm
                    notifier = None
                    wm = None
                time.sleep(60)
                continue
            else:
                if scaned <= 1:
                    full_scan_sync('')
                    scaned = 2
                    wm = WatchManager()
                    wm.add_watch(path, mask, auto_add=True, rec=True)
                    wm.add_watch(path_bak, mask, auto_add=True, rec=True)
                    notifier = Notifier(wm, EventHandler())
                    notifier.coalesce_events()
            if notifier.check_events():
                print "check event true."
                notifier.read_events()
                notifier.process_events()
                print "process_events."
            else:
                print "check event false."
            print "sleeping."
            time.sleep(1)
        except KeyboardInterrupt:
            print "keyboard Interrupt."
            notifier.stop()
            break


if __name__ == "__main__":
    FsMonitor(data_path, data_bak)

    # #apt-get install davfs2
    # sudo mount -t davfs http://172.26.35.47:8087/remote.php/webdav/ /home/thli/workspace/Documents/docker_test/nextcloud/nextcloud_data
