# coding=utf-8
from model_base import MongoObject, Tools
from pymongo import ASCENDING
import gridfs
import commands
import os
from settings import conf


class Persons(MongoObject):
    """记录人员的基本信息，现在字段还比较少，里记录了teams的主键name作关联"""
    """字段说明：
    'role', 默认的是没有的，特例才有这个字段，比如是leader的人
    'phone', 可以后加
    """
    table_info = {}
    table_name = 'persons'
    pre_size = 20 * 3
    main_key = 'email'
    keys = {"required_keys": {'name', main_key, 'team_name', },
            "foreign_keys": {'teams': 'name', 'groups': 'names'},
            "index_keys": (
                ([('name', ASCENDING)], {'unique': True}),
                ([(main_key, ASCENDING)], {'unique': True})),
            "list_keys": {'group_names': pre_size}}
    head_picture_path = os.path.join(conf.staticdir, conf.headpath)
    img_grd = gridfs.GridFS(MongoObject.db)

    def __init__(self):
        super(Persons, self).__init__(Persons.table_name, Persons.keys)

    def get_w_team(self, primary_value):
        """获取一个person以及所在team的信息
        ：参数：
            primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
         :返回:
            person信息以及对应的team"""
        return self.get_w_foregin(primary_value, table_other=Teams, key='team_name', key_other='name')

    def update_head_picture(self, email_identity, picture_path):
        # if not os.path.exists(self.head_picture_path):
        #     s, l = commands.getstatusoutput('mkdir -p %s' % self.head_picture_path)
        img_content = picture_path
        matchimg_check = self.img_grd.find({'filename': email_identity}).count()
        if matchimg_check != 0:
            cur = self.img_grd.find({'filename': email_identity})
            for one in cur:
                self.img_grd.delete(one._id)
        re1 = self.img_grd.put(img_content, content_type="jpg", filename=email_identity)
        # s, l = commands.getstatusoutput(
        #     'cp -f %s %s' % (picture_path, self.head_picture_path + '/' + email_identity + '.jpg'))
        # return self.head_picture_path + '/' + email_identity + '.jpg'
        return re1

    def get_head_picture(self, email_identity):
        matchimg_check = self.img_grd.find({'filename': email_identity}).count()
        if matchimg_check == 0:
            return ''
        else:
            pic_path = self.head_picture_path + '/' + email_identity + '.jpg'
            if os.path.exists(pic_path):
                os.system('rm -rf %s' % pic_path)
            pic_relate_path = conf.headpath + email_identity + '.jpg'
            if not os.path.exists(pic_path):
                if not os.path.exists(self.head_picture_path):
                    s, l = commands.getstatusoutput('mkdir -p %s' % self.head_picture_path)
                img = open(pic_path, 'wb')
                img_out = self.img_grd.get_version(email_identity)
                img.write(img_out.read())
                img.close()
            return pic_relate_path


class Teams(MongoObject):
    """一个团队的信息，成员就是person里的记录，记录了person的主键email作关联"""
    """字段说明：
    'groups', 可以后加，用于存放这个团队有哪些组，小组的名字"""
    table_name = 'teams'
    pre_size = 20 * 20
    main_key = 'name'  # 这个字段暂时用int这样的名字
    keys = {"required_keys": {main_key, 'leader_email', 'person_emails'},
            "foreign_keys": {'persons': 'email'},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'person_emails': pre_size, 'groups': pre_size}
            }

    def __init__(self):
        super(Teams, self).__init__(Teams.table_name, Teams.keys)

    def get_w_persons(self, primary_value):
        """获取一个team以及这个team下面的所有成员信息
        ：参数：
            primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
         :返回:
            team的信息以及对应的所有组员信息"""
        return self.get_w_foregin(primary_value, table_other=Persons, key='person_emails', key_other='email')

    def get_members(self, primary_value, get_detail=True):
        """获取这个team的下面的所有成员信息，
        ：参数：
            - primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
            - get_detail表示是否获取除email字段之外的信息
         :返回:
            team对应的所有组员信息"""
        team = self.get_one(primary_value, {'person_emails'})
        if team is None:
            raise ValueError('you gave primary_value could not find any matched team')
        person_emails = team['person_emails']
        if '***' in person_emails:
            return []
        if get_detail:
            persons_detail = []
            persons = Persons().find({'email': {'$in': person_emails}})
            for obj in persons:
                persons_detail.append(obj)
            return persons_detail
        else:
            return person_emails

    def add_member(self, team_name, members):
        """向这个team下面添加成员
        :参数：
            - where：操作的条件，可以以此获得对应的唯一team，字典类型，里面最好是包含主键；
            - what： 往这条记录下的那个字段增加什么值
        :返回:
            操作成功的一条记录的信息"""
        if type(members) is list:
            Persons().update_many({'email': {'$in': members}}, {'team_name': team_name})
        else:
            Persons().update_one({'email': members}, {'team_name': team_name})
        return self.value_one_push({'name': team_name}, {'person_emails': members})

    def get_groups_members(self, team_name):
        """根据小组名，获取该小组下的所有group以及各个group对应的人员
        :参数 team_name:team的主键name
        :返回:  该小组下的以group name为键各个group对应的人员的详细信息为值的键值对组成的字典
        """
        groups_details = []
        gs = Groups()
        groups = self.get_one({'name': team_name}, {'groups'})
        if groups is None:
            raise AttributeError('your gave team_name could not match any record')
        group_names = groups['groups']
        if type(group_names) is list:
            for g_name in group_names:
                pers = gs.get_members({'name': g_name}, {'name', 'phone', 'email'}, True)
                groups_details.append({g_name: [p for p in pers]})
        else:
            pers = gs.get_members({'name': group_names}, {'name', 'phone', 'email'}, True)
            groups_details.append({group_names: [p for p in pers]})
        return groups_details

    def insert_one(self, value):
        person_emails = value.get('person_emails', None)
        value['person_emails'] = Teams.pre_size * '*'
        re = super(Teams, self).insert_one(value)
        if person_emails is not None:
            return self.add_member(value['name'], person_emails)
        else:
            return re


class Groups(MongoObject):
    """一个小组的信息，成员就是person里的记录，记录了person的主键email作关联"""
    """字段说明：
    'leader_email', 暂时不需要
    'person_emails' 后面添加
    """
    table_name = 'groups'
    pre_size = 20 * 10
    main_key = 'name'  # 暂定用所在team名字+对应项目名
    keys = {"required_keys": {main_key, 'project', 'status'},
            "foreign_keys": {'persons': 'emails', 'projects': 'project'},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'person_emails': pre_size}
            }

    def __init__(self):
        super(Groups, self).__init__(Groups.table_name, Groups.keys)

    def get_w_persons(self, primary_value):
        """获取一个group以及这个team下面的所有成员信息
        ：参数：
            primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
         :返回:
            group的信息以及对应的所有组员信息"""
        return self.get_w_foregin(primary_value, key='person_emails', table_other=Persons, key_other='email')

    def get_members(self, primary_value, value_filter=None, get_detail=True):
        """获取这个team的下面的所有成员信息，
        ：参数：
            - primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
            - get_detail表示是否获取除email字段之外的信息
         :返回:
            group对应的所有组员信息"""
        group = self.get_one(primary_value)
        if group is None:
            raise ValueError('you gave primary_value could not find any matched group')
        person_emails = group['person_emails']
        if '***' in person_emails:
            return []
        if get_detail:
            persons_detail = []
            persons = Persons().find({'email': {'$in': person_emails}}, value_filter)
            for obj in persons:
                persons_detail.append(obj)
            return persons_detail
        else:
            return person_emails

    def add_member(self, group_name, members):
        """向这个team下面添加成员
        :参数：
            - where：操作的条件，可以以此获得对应的唯一group，字典类型，里面是主键；
            - what： 往这条记录下的那个字段增加什么值
        :返回:
            操作成功的一条记录的信息"""
        if type(members) is list:
            Persons().value_many_push({'email': {'$in': members}}, {'group_names': group_name})
        else:
            Persons().value_one_push({'email': members}, {'group_names': group_name})
        return self.value_one_push({'name': group_name}, {'person_emails': members})

    def add_one(self, team_name, project_name, status='activated', person_emails=None):
        group_name = team_name + '-' + project_name
        self.insert_one({'name': group_name, 'project': project_name, 'status': status})
        Teams().value_one_push({'name': team_name}, {'groups': group_name})
        if person_emails is None:
            return None
        return self.add_member(group_name, person_emails)


class Projects(MongoObject):
    """一个项目生命周期的信息，"""
    """字段说明：
    后续添加 'leader_email','groups','persons','points', 'total', 'ongoing'
    """
    table_name = 'projects'
    pre_size = 20 * 5
    main_key = 'project'
    keys = {"required_keys": {main_key, 'type', 'spm', 'status'},
            "foreign_keys": {'project_types': ['project', 'type']},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'groups': pre_size}
            }

    def __init__(self):
        super(Projects, self).__init__(Projects.table_name, Projects.keys)

    def get_w_persons(self, primary_value):
        pass

    def get_w_groups(self, primary_value, get_detail=True):
        pass

    def get_w_tasks(self, where, what):
        pass

    def insert_one(self, value):
        if 'task_infos' not in value.keys():
            value['task_infos'] = {'total': 0, 'ongoing': 0}
        if 'status' not in value.keys():
            value['status'] = 'activated'

        ProjectTypes().value_one_push({'type': value['type']}, {'projects': value['project']})
        ProjectSpms().value_one_push({'spm': value['spm']}, {'projects': value['project']})
        super(Projects, self).insert_one(value)

    @staticmethod
    def add_tasks(primary_value, task_ids):
        ProjectTasks_().add_tasks(primary_value, task_ids)

    @staticmethod
    def status_change(primary_value, finished_count):
        ProjectTasks_().status_change(primary_value, finished_count)


class ProjectTasks_(MongoObject):
    """project表的附表，用于存放大量需要频繁更新的任务信息,将这样的信息独立出来放在另一个表里与任何业务需求无关，
    所以大部分情况不需要直接访问该表，而这些信息会通过一些特殊的方式同步到主表中，这样做的目的是为了达到
    主表供高频率的读取，附表负责高频率的写，操作分开之后可以互不阻塞
    当前放一些项目对应的task信息"""
    table_name = '_project_tasks'
    pre_size = 20 * 100
    main_key = 'project'
    # 'tasks',后续添加
    keys = {"required_keys": {main_key, 'ongoing', 'total'},
            "foreign_keys": {'tasks': '_ids'},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'tasks': pre_size}
            }
    __instance = False

    def __init__(self):
        super(ProjectTasks_, self).__init__(ProjectTasks_.table_name, ProjectTasks_.keys)
        if not self.__instance:
            Tools.sync_info['pairs'].append(((self, 'changed', self.main_key, 'ongoing', 'total'),
                                             (Projects(), Projects().main_key, 'ongoing', 'total')))
            Tools.timer_sync_start()

    def get_w_persons(self, primary_value):
        pass

    def get_w_groups(self, primary_value, get_detail=True):
        pass

    def get_w_tasks(self, where, what):
        pass

    def add_tasks(self, primary_value, task_ids):
        num = len(task_ids)
        if self.get_one(primary_value, {'_id': 1}) is None:
            value = primary_value.copy()
            value['tasks'] = task_ids
            value["ongoing"] = num
            value["total"] = num
            value["changed"] = 'yes'
            self.insert_one(value)
        else:
            self.value_one_push(primary_value, {'tasks': task_ids})
            self.__table__.update_one(primary_value, {"$inc": {"ongoing": num, "total": num},
                                                      '$set': {'changed': 'yes'}})

    def status_change(self, primary_value, finished_count):
        self.__table__.update_one(primary_value, {"$inc": {"ongoing": -finished_count}, '$set': {'changed': 'yes'}})


class ProjectTypes(MongoObject):
    """项目类型的信息，"""
    """字段说明：
    'projects',后面添加
    'points', 节点信息,型如['name1','name2','name3']"""
    table_name = 'project_types'
    pre_size = 20 * 10
    main_key = 'type'
    keys = {"required_keys": {main_key},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'projects': pre_size}
            }

    def __init__(self):
        super(ProjectTypes, self).__init__(ProjectTypes.table_name, ProjectTypes.keys)

    def get_template(self, project_type):
        re = self.get_one({'type': project_type}, ('type', 'points'))
        if re is None:
            return 'no record matched'
        return re.get('points', [])


class ProjectSpms(MongoObject):
    """项目类型的信息，"""
    """字段说明：
    'projects',后面添加
    'spm', 节点信息,型如['name1','name2','name3']"""
    table_name = 'project_spms'
    pre_size = 20 * 10
    main_key = 'spm'
    keys = {"required_keys": {main_key},
            # "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'projects': pre_size}
            }

    def __init__(self):
        super(ProjectSpms, self).__init__(ProjectSpms.table_name, ProjectSpms.keys)


class Tasks(MongoObject):
    """一个任务生命周期的信息，"""
    """字段说明：
        暂不需要：'leader_email','groups','persons',
        'summary', 'finish'
        'deadline', 'workload', 'history',
        后期添加：
    """
    table_name = 'tasks'
    pre_size = 20 * 50
    main_key = '_id'
    keys = {"required_keys": {'status', 'owner', 'tag', 'project', 'attachment', 'start'},
            "foreign_keys": {'projects': 'project', 'persons': 'email'},
            # "list_keys": {'point': pre_size, 'groups': 200, 'persons': pre_size}
            }

    def __init__(self):
        super(Tasks, self).__init__(Tasks.table_name, Tasks.keys)

    def get_w_persons(self, primary_value):
        pass

    def get_w_groups(self, primary_value, get_detail=True):
        pass

    def get_my_tasks(self, where, what):
        pass

    def get_by(self, value, value_filter=None):
        return self.find(value, value_filter)

    def insert_one(self, value):
        re = super(Tasks, self).insert_one(value)
        Projects().add_tasks({'project': value['project']}, (re.inserted_id,))


class NormalTasks(MongoObject):
    """一个任务生命周期的信息，"""
    """字段说明：
        暂不需要： 'workload',
        后期添加： 'nodes'
    """
    table_name = 'normal_tasks'
    pre_size = 20 * 20
    main_key = '_id'
    keys = {"required_keys": {'tag', 'summary', 'project_type', 'attachment'},
            "foreign_keys": {'project_types': 'type'},
            # "list_keys": {'nodes': pre_size}
            }

    def __init__(self):
        super(NormalTasks, self).__init__(Tasks.table_name, Tasks.keys)

    def get_w_persons(self, primary_value):
        pass

    def get_w_groups(self, primary_value, get_detail=True):
        pass

    def get_my_tasks(self, where, what):
        pass

    def get_by(self, value, value_filter=None):
        return self.find(value, value_filter)


class PersonTasks_(MongoObject):
    """person表的附表，用于存放大量需要频繁更新的任务信息"""
    """字段说明：
    'task_infos'
    """
    table_name = '_person_tasks'
    pre_size = 20 * 100
    main_key = 'person_email'
    keys = {"required_keys": {main_key, 'tasks'},
            "foreign_keys": {'tasks': '_ids'},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'tasks': pre_size}
            }

    def __init__(self):
        super(PersonTasks_, self).__init__(PersonTasks_.table_name, PersonTasks_.keys)

    def get_w_persons(self, primary_value):
        pass

    def get_w_groups(self, primary_value, get_detail=True):
        pass

    def get_w_tasks(self, where, what):
        pass


class Emails(MongoObject):
    """包含基本的邮件信息，和邮件回复往返关系"""
    """字段说明：
    'from',存放发件人的邮箱地址
    'to', 保存的是一个列表，放所有收件人的邮箱地址；
    但是为了不放大量重复的收件人，所以简化为放增加了的收件人
    'reply_to' 回复给那个邮件，放的是邮件历史的上一个_id
    'replys' 回复了这封邮件的邮件_ids
    'head' 邮件历史的第一封邮件的_id
    datetime, content, 是邮件的常规内容

    """
    table_name = 'emails'
    pre_size = 24 * 4
    main_key = '_id'  # 暂定是email主体内容的md5值
    keys = {"required_keys": {'from'},
            # "foreign_keys": {'persons': 'emails', 'projects': 'project'},
            "index_keys": (([(main_key, ASCENDING)], {'unique': True}),),
            "list_keys": {'replys': pre_size}
            }

    def __init__(self):
        super(Emails, self).__init__(Emails.table_name, Emails.keys)

    def get_w_persons(self, primary_value):
        """获取一个group以及这个team下面的所有成员信息
        ：参数：
            primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
         :返回:
            group的信息以及对应的所有组员信息"""
        return self.get_w_foregin(primary_value, key='from', table_other=Persons, key_other='email')

    def insert_one(self, value):
        par = self.get_one({'_id': value['reply_to']}, {'head'})
        value['head'] = par['head']
        try:
            super(Emails, self).insert_one(value)
        except Exception as e:
            print(e.message)

        try:
            self.value_one_push({'_id': value['reply_to']}, {'replys': value['_id']})
        except Exception as e:
            print(e.message)


class ExternalTasks(MongoObject):
    """包含基本的邮件信息，和邮件回复往返关系"""
    """字段说明：
    'from',存放任务来源类型，email，gerrit或是alm
    'status',存放任务是否已经被导入
    'last_modify_at', 存放上次修改时间
    'history', 
    'origin', 任务源的_id，比如任务是email，那就存放对应的这个email的_id
    """
    table_name = 'external_tasks'
    pre_size = 24 * 4
    main_key = '_id'
    keys = {"required_keys": {'from', 'origin'},
            }

    def __init__(self):
        super(ExternalTasks, self).__init__(ExternalTasks.table_name, ExternalTasks.keys)

    def import_task(self):
        pass

    def cancel_task(self):
        pass
