import random
import psycopg2
from textual import on
from textual.widgets import Button, Input
from database import connectDB
from ui import TampilanLogin, TampilanRegister, pastikan_kolom_password_diubah
from dashboard_mahasiswa import MahasiswaScreen
from dashboard_orangtua import OrangTuaScreen


# =====================================================================
# 1. FITUR LOGIN
# =====================================================================
class LoginScreen(TampilanLogin):
    @on(Button.Pressed, "#btn-register")
    def ke_register(self):
        self.app.push_screen(RegisterScreen())

    @on(Button.Pressed, "#btn-login")
    def login(self):
        username = self.query_one("#login-user", Input).value.strip()
        password = self.query_one("#login-pass", Input).value.strip()

        if not username or not password or " " in username or " " in password:
            self.notify("Username dan password wajib diisi tanpa spasi!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute(
                """
                SELECT p.id_pengguna, p.nama_pengguna, r.nama_role, p.id_orang_tua
                FROM pengguna p
                JOIN role r ON p.id_role = r.id_role
                WHERE p.nama_pengguna = %s AND p.kata_sandi = %s;
                """,
                (username, password)
            )
            user = cur.fetchone()

            if not user:
                self.notify("Username atau password salah!", severity="error")
                return

            data_user = {
                "id_pengguna": user[0],
                "nama_pengguna": user[1],
                "role": user[2],
                "id_orang_tua": user[3]
            }
            self.query_one("#login-pass", Input).value = ""

            if data_user["role"] == "mahasiswa":
                self.app.push_screen(MahasiswaScreen(data_user))
            else:
                self.app.push_screen(OrangTuaScreen(data_user))

        except Exception as e:
            self.notify(f"Terjadi kesalahan: {e}", severity="error")
        finally:
            cur.close()
            conn.close()


# =====================================================================
# 2. FITUR REGISTRASI AKUN
# =====================================================================
class RegisterScreen(TampilanRegister):
    @on(Button.Pressed, "#btn-batal")
    def kembali(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-daftar")
    @on(Button.Pressed, "#btn-daftar-ortu")
    def register(self, event: Button.Pressed):
        username = self.query_one("#reg-user", Input).value.strip()
        password = self.query_one("#reg-pass", Input).value.strip()

        if len(username) < 3 or len(password) < 4 or " " in username or " " in password:
            self.notify("Username min 3 & password min 4 karakter tanpa spasi!", severity="error")
            return

        if username.isdigit():
            self.notify("Username tidak boleh hanya berisi angka!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_password_diubah(cur, conn)

            cur.execute(
                "INSERT INTO pengguna (id_role, nama_pengguna, kata_sandi) VALUES (1, %s, %s) RETURNING id_pengguna;",
                (username, password)
            )
            id_mhs = cur.fetchone()[0]
            pesan = "Registrasi mahasiswa berhasil!"

            if event.button.id == "btn-daftar-ortu":
                user_ortu = f"ortu_{username}"
                pass_ortu = f"ortu{random.randint(1000, 9999)}"
                cur.execute(
                    "INSERT INTO pengguna (id_role, nama_pengguna, kata_sandi, password_diubah) VALUES (2, %s, %s, FALSE) RETURNING id_pengguna;",
                    (user_ortu, pass_ortu)
                )
                id_ortu = cur.fetchone()[0]
                cur.execute("UPDATE pengguna SET id_orang_tua = %s WHERE id_pengguna = %s;", (id_ortu, id_mhs))
                pesan = f"Registrasi berhasil! Akun Ortu: {user_ortu} | Pass: {pass_ortu}"

            conn.commit()
            self.notify(pesan, timeout=10)
            self.app.pop_screen()

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            self.notify("Username sudah digunakan, coba yang lain!", severity="error")
        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal mendaftar: {e}", severity="error")
        finally:
            cur.close()
            conn.close()