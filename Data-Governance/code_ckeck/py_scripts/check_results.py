import pymysql
import json

with open('configs/db_config.json', 'r') as f:
    config = json.load(f)

db = config.get('target_db', config)

conn = pymysql.connect(
    host=db['host'],
    port=db['port'],
    user=db['user'],
    password=db['password'],
    database=db['database'],
    charset=db['charset']
)

cursor = conn.cursor()

# Show summary
cursor.execute("SELECT check_status, COUNT(*) as cnt FROM code_check_result GROUP BY check_status")
print('Summary:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Show failed results
print('\nFailed checks:')
cursor.execute("SELECT task_name, rule_id, rule_name, rule_severity FROM code_check_result WHERE check_status = 'FAIL' LIMIT 10")
for row in cursor.fetchall():
    print(f'  {row[0]} - {row[1]}: {row[2]} ({row[3]})')

cursor.close()
conn.close()
