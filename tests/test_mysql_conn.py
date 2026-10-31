import pymysql

passwords_to_try = ['', 'root', 'password', '123456', 'admin', 'root123', 'mysql']
success = False

for pwd in passwords_to_try:
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3307,
            user='root',
            password=pwd,
            connect_timeout=3
        )
        print(f"SUCCESS: Connected to MySQL on port 3307 with user='root' and password='{pwd}'!")
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()
            print("MySQL Version:", ver)
            cur.execute("SHOW DATABASES")
            dbs = [row[0] for row in cur.fetchall()]
            print("Databases:", dbs)
        conn.close()
        success = True
        break
    except pymysql.MySQLError as e:
        print(f"Failed with password '{pwd}': {e}")
    except Exception as e:
        print(f"Connection failed: {e}")
        break

if not success:
    print("Could not connect with standard test passwords. User can specify password in .env or config.py!")
