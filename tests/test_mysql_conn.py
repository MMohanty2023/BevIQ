import pymysql

def main():
    passwords_to_try = ['', 'root', 'password', '123456', 'admin', 'root123', 'mysql']
    success = False

    for pwd in passwords_to_try:
        try:
            conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password=pwd, connect_timeout=3)
            print(f"SUCCESS: Connected to MySQL on port 3307 with user='root' and password='{pwd}'!")
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                print("MySQL Version:", cur.fetchone())
                cur.execute("SHOW DATABASES")
                print("Databases:", [row[0] for row in cur.fetchall()])
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


if __name__ == '__main__':
    main()
