from models import *
import sys
sys.path.append("../../")
from script import query_ldap

class LDAP_Import():
    """
    from LADP server import member information:
    and creat person, creat team
    
    """
    def __init__(self):
        self.info = query_ldap.get_users_baseinfo()

    def creat_user(self):
        """
        record info:
                record['name'] => sAMAccountName
                record['mobile'] => mobile
                record['email'] => mail
                record['tel'] => telephonenumber
                record['dn'] => distinguishedName
                record['team_name'] => department
                record['leader'] => manager     
                record['role'] => 'member' is default
        Person field
        _id,name,email,team_name(f),....role,phone,tel
        """
        user_records = self.info
        # print user_records
        per = Persons()

        for record in user_records:
            print record
            search_p = per.get_one({'name':record['name']})
            print search_p
            if search_p is None:
                per.insert_one(record)
            else:
                per.update_one({'name':record['name'],'team_name':record['team_name'],'email':record['email']},record,cover=True)


    def update_role(self):
        """
        update leader's role in person collection 
        """
        all_leader = []
        user_records = self.info
        per = Persons()
        for record in user_records:
            if record['leader'] not in all_leader:
                all_leader.append(record['leader'])
        # print len(all_leader)
        # print all_leader
        for leader in all_leader:
            # print leader
            fil = per.get_one({'dn':leader})
            # print fil
            if fil is None:
                print 'this leader %s is not in our db,please check' % leader
            else:
                per.update_one({'dn':leader},{'role':'leader'})

    def creat_team(self):
        """            
        Teams field
        _id,name,leader_email, person_emails([]),emails(f)
        """
        te = Teams()
        per = Persons()
        teamlist = []
        for one in per.find({'role':'leader'},{'team_name'}):
            if one['team_name'] not in teamlist:
                teamlist.append(one['team_name'])
        # print len(teamlist)
        for team in teamlist:
            tmp = {'name': '', 'leader_email': '', 'person_emails': []}
            tmp['name'] = team
            tmp['leader_email'] = per.get_one({'team_name':team,'role':'leader'})['email']
            for one in per.find({'team_name':team},{'email'}):
                tmp['person_emails'].append(one['email'])
            print tmp
            search_t = te.get_one({'name':team})
            if search_t is None:
                te.insert_one(tmp)
            else:
                te.update_one({'name':team,'leader_email':'','person_emails':''},tmp,cover=True)

# test = LDAP_Import()
# test.creat_user()
# test.update_role()
# test.creat_team()


