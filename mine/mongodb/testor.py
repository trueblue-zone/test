# coding=utf-8
from models import *
import random


class Ldap_tt():
    def login(self, email, passwd):
        if email and passwd:
            return {'email': email, 'name': 'name-' + email[:-8],
                    'phone': '12345678912', 'leader': True}


ldap_tem = Ldap_tt()


class Init_test():
    leader_email = 'zy.ku@tcl.com'
    project_type_dict = {'Micker6 VF': 'Vodafone 4G', 'Pixi4-4 3G VF': 'Vodafone 3G',
                         'Pixi3-5 3G VF': 'Vodafone 3G'}
    project_owner_dict = {'Micker6 VF': '1-' + leader_email, 'Pixi4-4 3G VF': '2-' + leader_email,
                          'Pixi3-5 3G VF': '3-' + leader_email}

    # def __init__(self):
    #     project = 'agron'

    @classmethod
    def get_team(cls, leader_email, count=20):
        users = []
        for i in range(1, count + 1):
            users.append({'name': '%s-u%s' % (str(i), leader_email),
                          'email': '%s-%s' % (str(i), leader_email),
                          'phone': '222222', 'team_name': leader_email[:-8]})
        return {'users': users, 'name': leader_email[:-8]}

    @classmethod
    def init_team(cls):
        email = 'y1@tcl.com'
        passwd = '234$df!d'
        user = ldap_tem.login(email, passwd)
        if user['leader']:
            te = Teams()
            pers = Persons()
            team = cls.get_team(user['email'])
            ps = []
            pers.insert_many(team['users'])
            for p in team['users']:
                ps.append(p['email'])
            print te.insert_one({'name': team['name'], 'person_emails': ps, 'leader_email': user['email']})
            gs = Groups()
            # print gs.insert_one({'name': 'group2' + team['name'], 'project': 'project2', 'leader_email': user['email']})
            print gs.add_one({'name': 'group2' + team['name']}, ps[:3])
            #
            # print gs.insert_one({'name': 'group3' + team['name'], 'project': 'project2', 'leader_email': user['email'],
            #                'person_emails': ps[4:6]})
            # print gs.add_member({'name': 'group3' + team['name']}, ps[7])

            # gs.add_member({'name': 'group3' + team['name']}, 'xxxxxxx')
            # gs.add_member({'name': 'xxxxxx'}, 'xxxxxxx')

            # print([g for g in gs.get_members({'name': 'group2' + team['name']}, True)])
            # print([g for g in gs.get_members({'name': 'group3' + team['name']})])

            # print([g for g in gs.get_members({'name': 'xxxxx'})])
            # aa = [g for g in pers.get_in_range({'email': ps[2]}, {'email': ps[5]})]
            # print(aa)
            # gs.add_member({'name': 'group3' + team['name']}, 'xxxxxxx')
            # bb = [g for g in gs.get_members({'name': 'xxxxx'})]
            # print(bb)
            # print([g for g in pers.get_in_range({'email': ps[3]}, {'email': ps[1]})])
            # print([g for g in pers.get_in_range({'email': ps[4]})])

    @classmethod
    def team_group_person_data(cls, leader_email):
        te = Teams()
        pers = Persons()
        team = cls.get_team(leader_email)
        pers.insert_one({'name': leader_email[:-8], 'email': leader_email,
                         'phone': '1111111', 'role': 'leader', 'team_name': team['name']})
        ps = []
        pers.insert_many(team['users'])
        for p in team['users']:
            ps.append(p['email'])
        print te.insert_one({'name': team['name'], 'person_emails': ps, 'leader_email': leader_email})
        gs = Groups()
        # print gs.insert_one({'name': 'group2' + team['name'], 'project': 'project2', 'leader_email': user['email']})
        for project in cls.project_type_dict.keys():
            gs.add_one(team['name'], project, ps[:3])

    @classmethod
    def get_tasks(cls, project, owner, count=20):
        tasks = []
        date_ = random.randint(1, 30)
        mon = random.randint(1, 12)
        for i in range(1, count + 1):
            tasks.append({'owner': owner, 'tag': 'tag%d' % i, 'project': project, 'status': 'activated',
                          'summary': 'this is a summary%d' % i, 'attachment': 'this is a email%d' % i,
                          'start': '2017-%d-%d' % ((mon + i) % 12 + 1, (date_ + i) % 30 + 1),
                          'finish': '2017-%d-%d' % ((mon + i + 2) % 12 + 1, (date_ + i + 2) % 30 + 1),
                          'deadline': '2017-%d-%d' % ((mon + i + 4) % 12 + 1, (date_ + i + 4) % 30 + 1),
                          'workload': 3, 'history': 'check'})
        return tasks

    @classmethod
    def get_projects(cls, project_name_types):
        projects = []
        pt = ProjectTypes()

        for p in project_name_types.keys():
            mon = random.randint(1, 8)
            date_ = random.randint(7, 26)
            nodes = pt.get_one({'type': project_name_types[p]}, {'nodes'})['nodes']
            projects.append({'project': p, 'type': project_name_types[p], 'spm': '1spm@tcl.com',
                             'summary': 'this is a summary of %s' % p, 'attachment': 'this is a email of %s' % p,
                             'status': 'activated',
                             'points': [{'name': nodes[0], 'start': '2017-%d-%d' % (mon, date_),
                                         'end': '2017-%d-%d' % (mon + 1, date_ + 1)},
                                        {'name': nodes[1], 'start': '2017-%d-%d' % (mon + 1, date_ + 2),
                                         'end': '2017-%d-%d' % (mon + 2, date_)},
                                        {'name': nodes[2], 'start': '2017-%d-%d' % (mon + 2, date_ + 2),
                                         'end': '2017-%d-%d' % (mon + 3, date_)}
                                        ],
                             })
        return projects

    @classmethod
    def get_spms(cls, email_):
        spms = []
        for i in range(1, 6):
            spms.append({'spm': str(i) + str(email_)})
        return spms

    @classmethod
    def project_task_data(cls):
        spms = ProjectSpms()
        spms.insert_many(cls.get_spms('spm@tcl.com'))

        t = Tasks()
        pt = ProjectTypes()
        type_projects_dict = {}
        for pn in cls.project_type_dict.keys():
            ts = cls.get_tasks(pn, cls.project_owner_dict[pn])
            t.insert_many(ts)
            if cls.project_type_dict[pn] not in type_projects_dict:
                type_projects_dict[cls.project_type_dict[pn]] = []
                pt.insert_one({'type': cls.project_type_dict[pn], 'nodes': ['fsr', 'preacc', 'preacc1']})
            type_projects_dict[cls.project_type_dict[pn]].append(pn)

        pros = cls.get_projects(cls.project_type_dict)
        pro = Projects()
        pro.insert_many(pros)

    @classmethod
    def create_test_data(cls):
        cls.team_group_person_data(cls.leader_email)
        cls.project_task_data()

    @classmethod
    def get_examples(cls):
        p = Persons()  # 获取一个persons表的操作对象，用于基本的增删该查
        rs = p.get_one({'email': '3-zy.ku@tcl.com'})  # 查询的时候推荐用主键作为条件去查询，persons表的主键是email，
        # name不是主键之一, 这里指的主键是指可以唯一确定记录的字段（其实就是做了唯一索引为的字段名），和mysql里面的主键定义
        # 有一点区别，具体这个表有哪些主键可以看看这个persons类定义的keys["index_keys"]数组
        rs = p.get_one({'name': '3-uzy.ku@tcl.com'})  # 查询的时候不用主键作为条件去查询，本来可能返回多个，
        # 但是为了消除歧义和api的使用混乱就限制了这类使用，而是返回一条记录
        rs = p.find({'phone': '2222'},
                    value_filter={'name', 'phone'})  # 用这种不是主键(现在的主键都是做了唯一索引的，所以查询很快，非主键也可以做索引，但是暂时没这个需求发现)
        # 的条件去查询可以查出多条结果，而效率会比较慢，尤其是表内的内容多的时候. value_filter用于查询结果列过滤，结果中将只包含'name'和'phone'，大部分的查询类函数都有这个参数，可为空
        rs = p.get_w_team({'email': '3-zy.ku@tcl.com'})  # 获取这个人员所在的组的信息，返回dict类型

        t = Teams()  # 获取一个teams表的操作对象，用于基本的增删该查
        re = t.get_one({'name': 'teamzy.ku'})  # name在表里是做了唯一索引的一个主键，返回的结果可以自行打印出来看看结构，
        # t能用于查询的方法还有其他几个，都是从基类继承过来的
        re = t.get_members({'name': 'zy.ku'}, get_detail=False)  # 根据组名找到所有成员，但仅仅是返回成员的email
        re = t.get_groups_members('zy.ku')  # 根据team名字获取到所有小组以及对应小组的成员

        g = Groups()  # 小组信息表，一个team有多个group，一个group有多个person，
        re = g.get_one({'name': 'zy.ku-Pixi3-5 3G VF'})  # name在表里是做了唯一索引的一个主键，返回的结果可以自行打印出来看看结构，
        # g能用于查询的方法还有其他几个，都是从基类继承过来的
        re = g.get_members({'name': 'zy.ku-Pixi3-5 3G VF'}, get_detail=False)  # 根据组名找到所有成员，但仅仅是返回成员的email

        # 常用的数据都已经生成，但是其他的操作类，比如projects， tasks的查询类只能用一些封装的比较简单的查询函数，涉及到业务深层的查询还在开发中

    @classmethod
    def test_task_sync(cls):
        t = Tasks()
        tt = {
            "status": "activated",
            "finish": "2017-2-11",
            "summary": "this is a summary1",
            "project": "Pixi4-4 3G VF",
            "start": "2017-12-9",
            "workload": 3,
            "tag": "tag1",
            "deadline": "2017-4-13",
            "attachment": "this is a email1",
            "owner": "1-zy.ku@tcl.com",
            "history": "check"
        }
        t.insert_one(tt)

    @classmethod
    def test_head_picture(cls):
        p = Persons()
        # pic_path = '/home/thli/Pictures/Wallpapers/8ae4ad36af9aabbedfc28bbd8a7725a9.jpg'
        pic_path = '/home/thli/Pictures/2016-11-22 10:30:26屏幕截图.png'
        p.update_head_picture('tenghui.li1@tcl.com', pic_path)
        print(p.get_head_picture('tenghui.li1@tcl.com'))


init = Init_test()
# init.get_examples()
# init.create_test_data()
# init.test_task_sync()
init.test_head_picture()
