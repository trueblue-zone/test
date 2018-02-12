# -*- coding: utf-8 -*-
# !/usr/bin/env python
# from logger import getMyLogger
# mylogger = getMyLogger('static_time')
import time


class Record():
    # records = [['fun_name','time_start','time_end','duration']]
    record = 1
    # .len_circle = 30
    records = []  #记录时刻的原本
    # records_ = []
    host_ip = '172.56.89.122'
    on_wh = 0
    # num_records = 0
    # on_record = 0
    records.append(['record_start', time.time(), '', ''])


    @classmethod
    def record_now(cls, name, start_flag=True):
        # 记录当前时刻， 传入name是当前的函数名字，start——falg表示是否是开始
        # 每次记录都产生一条记录，而后在原本的基础上整理
        # mylogger.info('record_now ,name is:'+name)
        # if name == 'record_start':
        # num_records += 1
        # on_record = len(records)
        # print('records is:'+str(Record.records))
        # print('onwh is:'+str(Record.on_wh))
        if len(Record.records) == 0:
            Record.records.append(['record_start', time.time(), '', ''])
        if start_flag:
            Record.records.append([name, time.time(), '', ''])
        else:
            if name == Record.records[Record.on_wh][0]:
                Record.records[Record.on_wh][2] = time.time()
            else:
                Record.records.append([name, '', time.time(), ''])

        Record.on_wh = len(Record.records) - 1
        # print('records2 is:'+str(Record.records))
        # print('onwh2 is:'+str(Record.on_wh))
        # if on_wh > len_circle:
        # if num_records >= 2:

    @classmethod
    def get_records(cls):
        # mylogger.info('----------------------------------')
        Record.record_now('record_start', False)
        records_loss = []  #用于记录end字段为空的地方，即在原本上的索引
        re_record = []
        # mylogger.info('get_records ,records_loss is:'+str(records_loss))
        # mylogger.info('get_records ,Record.records is:'+str(Record.records))
        wh = -1
        wh_r = -1
        # 开始整理记录，包括时间显示格式（只剩分钟及后面的时间），入口出口合并
        for record in Record.records:
            wh_r += 1
            if record[1] != '':
                wh += 1
                re_record.append([record[0], int(record[1] % 3600), '', ''])
                re_record[wh][1] = str(re_record[wh][1] / 60) + ':' + str(re_record[wh][1] % 60)
                if record[2] == '':
                    # mylogger.info('apend ,records_loss is:'+str(records_loss))
                    records_loss.append((wh_r, wh))
            if record[2] != '':
                if record[1] == '':
                    # 这一段是做合并，填补前面那些end字段是空的地方
                    # mylogger.info('pop ,records_loss is:'+str(records_loss))
                    last_r, last = records_loss.pop()
                    re_record[last][2] = int(record[2] % 3600)
                    re_record[last][2] = str(re_record[last][2] / 60) + ':' + str(re_record[last][2] % 60)
                    re_record[last][3] = '%.3f'%(record[2] - Record.records[last_r][1])
                else:
                    re_record[wh][2] = int(record[2] % 3600)
                    re_record[wh][2] = str(re_record[wh][2] / 60) + ':' + str(re_record[wh][2] % 60)
                    re_record[wh][3] = '%.3f'%(record[2] - record[1])
        re_record[0][2] = int(time.time()% 3600)
        re_record[0][2] = str(re_record[0][2] / 60) + ':' + str(re_record[0][2] % 60)
        re_record[0][3] = '%.3f'%(time.time() - Record.records[0][1])
        # 这三句是给start做合并和处理时间格式
        re_record.insert(0, [Record.records[0][1],time.time(), time.time()-Record.records[0][1]])
        # start的副本，放的时间戳那样的时间，前端页面是不显示的
        print('time_records:'+str(re_record))
        # mylogger.info('get_records2 ,records_loss is:'+str(records_loss))
        # mylogger.info('get_records2 ,Record.records is:'+str(Record.records))
        Record.on_wh = 0
        del Record.records[:]
        del records_loss[:]
        # mylogger.info('get_records3 ,records_loss is:'+str(records_loss))
        # mylogger.info('get_records3 ,Record.records is:'+str(Record.records))
        return {'host_ip': Record.host_ip, 'time_records': re_record}

def test_timer():
    Record.record_now('a')
    # time.sleep(1)
    Record.record_now('b')
    # time.sleep(1.2)
    Record.record_now('b', False)
    # time.sleep(1.2)
    Record.record_now('c')
    # time.sleep(1.7)
    Record.record_now('d')
    Record.record_now('d', False)
    Record.record_now('c', False)
    Record.record_now('a', False)

    print Record.get_records()


test_timer()