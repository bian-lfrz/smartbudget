import psycopg2

def connectDB():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="P@ssw0rd",
            dbname="cli_sb"
        )
        cur = conn.cursor()
        return conn, cur

    except Exception as error:
        print("Koneksi database gagal:", error)
        return None, None