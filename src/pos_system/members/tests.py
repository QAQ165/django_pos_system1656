from django.test import TestCase

# Create your tests here.

def num_list(num):
    return [n for i,n in enumerate(num) if i%2==0 and n%2==0]

print(num_list([1,2,2,4,5,6,8]))


str1="1232132sadasfg"

print(str1.find('321'))


from datetime import datetime,date,time,timedelta

date1=datetime.now()
# print(date1)

# print(date1.date())
# print(date1.time())


dt=datetime.strptime("2026-03-22 12:12:00","%Y-%m-%d %H:%M:%S")

print(dt.time())
print(datetime.strftime(dt,"%Y-%m-%d %H:%M"))
now_timestamp=1774367808 #datetime.now().timestamp()
print(now_timestamp)
print(datetime.fromtimestamp(now_timestamp).time())


delta=timedelta(days=5)

print(dir(datetime))