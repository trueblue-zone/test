# coding=utf-8
from pymongo import MongoClient, collection, database, ReadPreference
import warnings
import pymongo
import config
from bson.objectid import ObjectId


class MongoObject(object):
    """pymongo的操作结合业务的封装类，封装了pymongo的一系列基本操作，
    以提供既灵活又简便的操作为基旨，和一般的类封装有个显著的区别，那就是它以及它的子类
    只提供对数据的操作，数据全部都用json格式的数据，
    而且只维护表间关系以及一些必要的数据结构和对业务无关却很有用的字段，
    实例不保存任何数据！！！，所以插入查询的一些操作，
    需要api的使用者知道一些数据字段的名字但不用了解过多的数据间关系

    使用通则：
        1 函数传参时，未缀带s的参数多是表示传入的是多个实体表示的数组，不带s的是单个个体，而且这两者的区别多用one和many；
        2 查询类的方法用one和many未缀来区别返回的是多个实体还是单个，如果返回的是单体，那单个实体基本都是dict类型；
        3 返回多个实体的时候返回的就是cursor对象而不是数组，但是它有和数组相似的方法，比如可以用in但不能用[]，
          还有其他更好用的方法比如skip,limit,next,这类方法会在cursor对象里没有数据可取的时候抛出异常；
        4 由于要把MongoObject作为mongodb操作的基类，而且成员函数只是一些逻辑和业务间接相关，所以传入的参数都是对mongodb端比较友好
          的字典类型，这样做是为了能给子类提供非常灵活的传参而不受限于要操作的表结构和表内的字段名；而子类函数为了能有较好使用体验
          传参多是面向python友好的，增改类的函数由于要让api的使用者清楚该传入什么参数，所以就多是用了python封装函数常用的形式，
          这样做就失掉了很多灵活性和扩展性，这点比较难于取舍；不过子类也还是保留了部分使用dict传参形式的函数，那些多是查询相关的函数，是为了能提供多种查询
          条件的可能而不受限于字段名，这样做既灵活又可以兼容后面的升级，不过基类的函数子类的对象依然可以正常调用，只不过使用者
          要多对了解些相关的表结构
    """
    client = MongoClient(config.mongodb_uri)
    dba = database.Database(client, 'admin')
    dba.authenticate(config.user_name, config.user_pwd)
    db = database.Database(client, config.database_name)
    _instance = None

    def __new__(cls, *args, **kw):
        """单列模式"""
        if not cls._instance:
            cls._instance = super(MongoObject, cls).__new__(cls, *args, **kw)
            cls._instance.__table__ = None
        return cls._instance

    def __init__(self, table, keys, read_preference=ReadPreference.PRIMARY_PREFERRED):

        """得到一个MongoObject操作类的对象,单例

        :参数:
          - `table`: 维护的表的名字，表在mongodb里称作集合
          - `keys`: 维护的表的结构信息,包括:
                必要字段（keys['required_keys']），集合类型
                外键字段（keys['foreign_keys']） ，字典类型
                索引字段（keys['index_keys']），建了索引的查询效率会很高，
                但是太多了会对效率和存储空间有反面影响，三维数组类型
                数组类型的字段（keys['list_keys']）,是为了给数组类型的字段预留空间的，
                可以提高mongodb效率，字典类型
        ：例子：
          - keys={"required_keys": {'name', 'project', 'leader_email'},
                "foreign_keys": {'person': 'email'},
                "index_keys": (([('name', pymongo.ASCENDING)], {'unique': True}),),
                "list_keys": {'person_emails': pre_size}
                }
        """

        if self.__table__:
            return
        self.__table__ = collection.Collection(MongoObject.db, table, read_preference=read_preference)
        self.__keys__ = keys.get("required_keys", None)
        self.__fkeys__ = keys.get("foreign_keys", None)
        self.__ikeys__ = keys.get("index_keys", None)
        self.__lkeys__ = keys.get("list_keys", None)
        if self.__ikeys__ is not None:
            for index_k in self.__ikeys__:
                unique_flag = index_k[1].get('unique', False)
                self.__table__.create_index(index_k[0], unique=unique_flag)

    def check_keys(self, func):
        pass

    def _check_value(self, value):
        """检验数组类型字段，给数组字段预留空间，就是给这个字段初始赋值一些垃圾信息，
        value是传入的要增加到表里的记录"""
        value_ = value.copy()
        if self.__lkeys__ is not None:
            for k in self.__lkeys__.keys():
                if k not in value_.keys():
                    value_[k] = self.__lkeys__[k] * '*'
        return value_

    def _check_m_value(self, values):
        """检验多条记录的数组类型字段，给数组字段预留空间，就是给这个字段初始赋值一些垃圾信息，
        ：参数：
            values是传入的要增加到表里的多条记录，会在这个内容上增加需要预留空间的字段的值
         ：返回：
            返回修改或是没修改内容但是是深拷贝了的新对象"""
        values_ = [item.copy() for item in values]
        if self.__lkeys__ is not None:
            for k in self.__lkeys__.keys():
                for value in values_:
                    if k not in value.keys():
                        value[k] = self.__lkeys__[k] * '*'
        return values_

    def get_one(self, primary_value, value_filter=None):
        """根据可以作为主键的字段值查询出一条记录，这里不做检验primary_value是否
        有主键的资格，如果对应的记录有多条也只会返回查询到的第一条记录，
        这类的查询插入操作的数据有一些固定的格式，本是应该校验传入的数据类型，但是这样做逻辑非常繁琐效率也低，
        而且这样简单的约束和代码质量应该用文档和完备的测试做保障，即我相信你，但即使是传入值的有误，
        最终也会有exception抛出
        ：参数：
            primary_value: 查询条件，主键键值对，字典类型， {'name':'name','email':'xx@tcl.com'}；
            value_filter: 结果过滤器，默认为None，即该记录的所有字段都取出，但是如果确切知道
            只需要哪些字段的值，应该使用只带有这些字段的过滤器，这样可以提高效率也可使数据简洁明了，
            {'name','email'}或是 ['name','email'],可迭代类型的对象里面有的字段名是要取出的，
            没有的就不会取出，但是_id是一直会取出的
         :返回:
            一个记录对象，dict类型，可以通过[]运算符取得属性值"""
        # if not isinstance(primary_value, dict):
        #     raise TypeError('you gave primary_value should be a dict like {"name": -1,"id":1}')
        if value_filter is not None:
            value_filter = {f: 1 for f in value_filter}
        obj = self.__table__.find_one(primary_value, value_filter)
        # print(obj)
        return obj

    def find(self, value, value_filter=None):
        """根据记录的相关字段值是否符合来查询符合条件的记录
        ：参数：
            value: 查询条件， {'name':'name','email':'xx@tcl.com'，'addr':'addr'}；
            value_filter: 结果过滤器，默认为None，即该记录的所有字段都取出，但是如果确切知道，
            只需要哪些字段的值，应该使用只带有这些字段的过滤器，这样可以提高效率也可是数据简介明了，
            {'name','email'}或是 ['name','email'],可迭代类型的对象里面有的字段名是要取出的，
            没有的就不会取出，但是_id是一直会取出的
        :返回:
            多个记录的cursor对象，可以通过next函数取得每个记录对象，每个对象是个dict类型"""
        if value_filter is not None:
            value_filter = {f: 1 for f in value_filter}
        objs = self.__table__.find(value, value_filter)
        return objs

    def get_w_foregin(self, primary_value, value_filter=None, table_other=None, key=None, key_other=None):
        """根据可以作为主键的字段值查询出一条记录，同样不做检验primary_value是否
        有主键的资格，如果对应的记录有多条也只会返回查询到的第一条记录，和get_one的作用大体相同，
        和它不同的是，如果参数table_other给定了另一个MongoObject子类，那就还会去根据给定的字段
        名字去另一张表里面去取和本记录相关的所有记录，并把得到的结果插入当前结果中，成为其一个键值对
        ：参数：
            value: 查询条件， {'name':'name','email':'xx@tcl.com'，'addr':'addr'}；
            value_filter: 结果过滤器，默认为None，即该记录的所有字段都取出，但是如果确切知道；
            只需要哪些字段的值，应该使用只带有这些字段的过滤器，这样可以提高效率也可是数据简介明了；
            {'name','email'}或是 ['name','email'],可迭代类型的对象里面有的字段名是要取出的，
            没有的就不会取出，但是_id是一直会取出的
            key: 本记录和另一个表所关联的字段；
            key_other：是关联的另一张表的字段
         :返回:
            一个记录的对象，dict类型"""
        if value_filter is not None:
            value_filter = {f: 1 for f in value_filter}
            value_filter[key] = 1
        obj = self.__table__.find_one(primary_value, value_filter)
        if table_other is not None:
            if key is None or key_other is None:
                raise AttributeError('the key and key_other parameter should not be None when table_other is not None')
            if not issubclass(table_other, MongoObject):
                raise Exception('table_other should be the subclass of MongoObject')
            if type(obj[key]) is list:
                obj_other = table_other().find({key_other: {'$in': obj[key]}})
                obj_other = [objone for objone in obj_other]
            else:
                obj_other = table_other().get_one({key_other: obj[key]})
            obj[table_other.__name__] = obj_other
        return obj

    def insert_one(self, value):
        """检验是否存在必要字段，是则插入一条新记录，建立了索引的字段要满足唯一性约束，不然会插入失败，
        数组类型的字段会在记录的生成之初检验是否有值保存进来，没有的话，会默认给它一串垃圾数据去
        占给这个字段预留空间，具体预留多少空间，是MongoObject子类定义的时候的pre_size给定的值。
        所以这种数组类型的字段的写操作尽量一次完成，不然会造成这个字段的空间不够时去频繁的移动位置，导致mongodb效率低
        ：参数：
            value: 插入的数据， {'name':'name','email':'xx@tcl.com'，'addr':'addr'}；
         :返回:
            新插入成功的一条记录的信息"""
        value_key = set(value.keys())
        lost_keys = self.__keys__ - value_key
        if len(lost_keys) > 0:
            warn_mes = 'lost keys:' + str(lost_keys)
            raise Exception(warn_mes)
        value_ = self._check_value(value)
        return self.__table__.insert_one(value_)

    def insert_many(self, values):
        """检验每条记录是否存在必要字段，是则插入所有新记录，建立了索引的字段要满足唯一性约束，不然会插入失败，
        数组类型的字段会在记录的生成之初检验是否有值保存进来，没有的话，会默认给它一串垃圾数据去
        占用一定的空间类给这个字段预留空间，具体预留多少空间，是MongoObject子类定义的时候的pre_size给定的值。
        所以这中数组类型的字段的写操作尽量一次完成，不然会造成这个字段的空间不够时去频繁的移动位置，导致mongodb效率低
        ：参数：
            values: 插入的数据， [{'name':'name','email':'xx@tcl.com'，'addr':'addr'},
                {'name':'name','email':'xx@tcl.com'，'addr':'addr'}]；
         :返回:
            新插入成功的多条记录的信息"""
        lost_keys = None
        if type(values) is list:
            wh_ = -1
            for v in values:
                value_key = set(v.keys())
                lost_keys = self.__keys__ - value_key
                wh_ += 1
                if len(lost_keys) > 0:
                    break
        else:
            raise TypeError('you gave the values should be a dict list')
        if len(lost_keys) > 0:
            warn_mes = 'lost keys:%s, at the %d place of value array' % (str(lost_keys), wh_)
            raise Exception(warn_mes)
        values_ = self._check_m_value(values)
        return self.__table__.insert_many(values_)

    def update_one(self, primary_value, new_value, cover=False):
        """查询符合条件的一条记录做更新
        ：参数：
            primary_value: 符合的条件， {'name':'name','email':'xx@tcl.com'，'addr':'addr'}
            new_value： 需要更新的字段或是增减的字段，{'name':'name','email':'xx@tcl.com'，'addr':'addr'}
            cover： 是否覆盖更新，覆盖更新时new_value里有的字段会成为该记录的现有字段，不覆盖时，
                new_value和现有字段都有的就会更新为new_value里的字段值，只有new_value有的字段则会增加，
                只有现有字段有的会保持不动
         :返回:
            更新成功的一条记录的信息"""
        if cover:
            value_key = set(primary_value.keys())
            lost_keys = self.__keys__ - value_key
            if len(lost_keys) > 0:
                raise Exception('lost keys:' + str(lost_keys))
            new_value_ = self._check_value(new_value)
            return self.__table__.update(primary_value, new_value_, manipulate=False)
        return self.__table__.update_one(primary_value, {'$set': new_value})

    def update_many(self, values, new_value, cover=False):
        """查询符合条件的多条记录做更新
        ：参数：
            values: 符合的条件， {'name':'name','email':'xx@tcl.com'，'addr':'addr'}
            new_value： 需要更新的字段或是增减的字段，{'name':'name','email':'xx@tcl.com'，'addr':'addr'}
            cover： 是否覆盖更新，覆盖更新时new_value里有的字段会成为该记录的现有字段，不覆盖时，
                new_value和现有字段都有的就会更新为new_value里的字段值，只有new_value有的字段则会增加，
                只有现有字段有的会保持不动
         :返回:
            更新成功的多条记录的信息"""
        if cover:
            value_key = set(values.keys())
            lost_keys = self.__keys__ - value_key
            if len(lost_keys) > 0:
                raise Exception('lost keys:' + str(lost_keys))
            new_value_ = self._check_value(new_value)
            return self.__table__.update(values, new_value_, manipulate=True)
        return self.__table__.update_many(values, {'$set': new_value})

    def delete_one(self, primary_value):
        """删除符合条件的一条记录
        ：参数：
            primary_value: 删除的条件，主键键值对，字典类型， {'name':'name','email':'xx@tcl.com'}；

         :返回:
            删除成功的一条记录的信息"""
        if primary_value is not {}:
            return self.__table__.delete_one(primary_value)
        else:
            warnings.warn('you delete none')
            return False
            # def get_w_foregin(self, table_other, key_other):

    def delete_many(self, value):
        """删除符合条件的一条记录
        ：参数：
            value: 删除的条件，键值对，字典类型， {'age':20}；

         :返回:
            删除成功的多条记录的信息"""
        if value is not {}:
            return self.__table__.delete_many(value)
        else:
            warnings.warn('you delete none')
            return False
            # def get_w_foregin(self, table_other, key_other):

    def value_one_push(self, primary_value, values, is_out=False):
        """往符合条件的一条记录的指定字段（数组类型）增加一个或多个值
        ：参数：
            primary_value: 条件，主键键值对，用于查询要做操作的记录，字典类型， {'name':'name'}；
            values: 增加的值，键值对，字典类型， {'person_emails':'ss@tcl.com'}格式
            或是{'person_emails':['ss@tcl.com','ss1@tcl.com']}格式；

         :返回:
            操作成功的一条记录的信息"""
        k_values = self.get_one(primary_value, values.keys())
        if k_values is None:
            raise ValueError('you gave primary_value could not find any record')
        if is_out:
            action = '$pull'
        else:
            action = '$addToSet'
        for k in values.keys():
            if k not in k_values:
                self.__table__.update_one(primary_value, {'$set': {k: '*' * 200}})
                k_values[k] = '*'
            if type(k_values[k]) is not list:
                self.__table__.update_one(primary_value, {'$set': {k: []}})
            if type(values[k]) is list or type(values[k]) is tuple:
                if is_out:
                    return self.__table__.update_one(primary_value, {'$pullAll': {k: values[k]}})
                return self.__table__.update_one(primary_value, {action: {k: {'$each': values[k]}}})
            else:
                return self.__table__.update_one(primary_value, {action: {k: values[k]}})

    def value_many_push(self, wh_values, values, is_out=False):
        """往符合条件的多条记录的指定字段（数组类型）增加一个或多个值
        ：参数：
            wh_values: 条件，键值对，用于查询要做操作的记录，字典类型， {'age':20}；
            values: 增加的值，键值对，字典类型， {'person_emails':'ss@tcl.com'}格式
            或是{'person_emails':['ss@tcl.com','ss1@tcl.com']}格式；

         :返回:
            操作成功的多条记录的信息"""
        k_values = [v for v in self.find(wh_values, values)]
        if len(k_values) < 1:
            raise ValueError('you gave wh_values could not find any record')
        if is_out:
            action = '$pull'
        else:
            action = '$addToSet'
        for k in values.keys():
            for k_value in k_values:
                if k not in k_value:
                    self.__table__.update_one({'_id': k_value['_id']}, {'$set': {k: '*' * 200}})
                    k_value[k] = '*'
                if type(k_value[k]) is not list:
                    self.__table__.update_one({'_id': k_value['_id']}, {'$set': {k: []}})
            if type(values[k]) is list:
                if is_out:
                    return self.__table__.update_many(wh_values, {'$pullAll': {k: values[k]}})
                return self.__table__.update_many(wh_values, {action: {k: {'$each': values[k]}}})
            else:
                return self.__table__.update_many(wh_values, {action: {k: values[k]}})

    def get_in_range(self, primary_value_from=None, primary_value_to=None, value_filter=None):
        from_id = None
        query = {}
        if primary_value_from is not None:
            from_id = self.__table__.find_one(primary_value_from, {'_id': 1})
            if from_id is None:
                raise AttributeError('you gave primary_value_from could not match any record')
            query['$gte'] = from_id['_id']
        if primary_value_to is not None:
            to_id = self.__table__.find_one(primary_value_to, {'_id': 1})
            if to_id is None:
                raise AttributeError('you gave primary_value_to could not match any record')
            query['$lte'] = to_id['_id']
            if from_id is not None:
                if from_id['_id'] > to_id['_id']:
                    query = {'$lte': from_id['_id'], '$gte': to_id['_id']}
        if len(query) is 0:
            raise AttributeError('you must primary_value_to or primary_value_to to match a record')
        return self.__table__.find({'_id': query}, value_filter)


class Tools(object):
    sync_info = {
        'start': 0,
        'pairs': []
        # (('_project_tasks','change','name', 'total','ongoing'),('projects','name', 'total','ongoing')),
    }

    @classmethod
    def timer_sync_start(cls, delay=60):
        cls.sync_info['start'] += 1
        if cls.sync_info['start'] > 1:
            return 'it already started'
        if len(cls.sync_info['pairs']) == 0:
            return 'there is nothing to sync'
        import threading
        import time

        def start_task():
            time.sleep(delay)
            while True:
                for sync in cls.sync_info['pairs']:
                    (from_table_, to_table_) = sync
                    (from_table, from_change, from_mainkey) = from_table_[:3]
                    (to_table, to_mainkey) = to_table_[:2]
                    if not isinstance(from_table, MongoObject) or not isinstance(to_table, MongoObject):
                        raise TypeError('you gave the param in array at 0 and 4 should be a obj of MongoObject')
                    cursor = from_table.find({from_change: 'yes'}, {attr: 1 for attr in from_table_[2:]})
                    for obj in cursor:
                        attrs = {}
                        len_ = len(from_table_[3:])
                        for i in range(0, len_):
                            attrs[to_table_[i + 2]] = obj[from_table_[i + 3]]
                        to_table.update_one({to_mainkey: obj[to_mainkey]}, attrs)
                        from_table.update_one({from_mainkey: obj[from_mainkey]}, {from_change: 'no'})
                time.sleep(5)

        sync_thread = threading.Thread(target=start_task)
        sync_thread.start()
