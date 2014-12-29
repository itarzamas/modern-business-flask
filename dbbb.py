# coding: utf-8
from sqlite3 import Connection


sql = "update pages set body_content = '{1}' where slug = '{0}'"

conn1 = Connection('xxx.db')
conn2 = Connection('ttt.db')

cur1 = conn1.cursor()
cur2 = conn2.cursor()

cur1.execute('select slug, body_content from pages')
pages = cur1.fetchall()

cmds = []
for p in pages:
    p = list(p)
    cmd = sql.format(*p)
    cmds.append(cmd)

for c in cmds:
    cur2.execute(c)
