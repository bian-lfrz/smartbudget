from datetime import datetime, date
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Center
from textual.widgets import (
    Header, Footer, Button, Input, Label,
    DataTable, TabbedContent, TabPane, Static, Select
)
from textual import on
from database import connectDB


# =====================================================================
# 1. DATA MASTER & LOGO APLIKASI
# =====================================================================
DAFTAR_SUMBER_PEMASUKAN = [
    "Kiriman Orang Tua / Uang Saku",
    "Beasiswa",
    "Gaji / Kerja Part-Time",
    "Freelance / Proyek",
    "Hadiah / Bonus",
    "Lainnya",
]

DAFTAR_KATEGORI = [
    "Makan & Minum",
    "Transportasi",
    "Kos & Tagihan",
    "Pendidikan & Tugas",
    "Belanja & Kebutuhan",
    "Hiburan & Nongkrong",
    "Kesehatan",
    "Lainnya",
]

DAFTAR_PERIODE_ANGGARAN = [
    ("Per Bulan (Bulanan)", "bulanan"),
    ("Per Minggu (Mingguan)", "mingguan"),
    ("Per Hari (Harian)", "harian"),
]

LOGO_ASCII = """[bold #38bdf8]
 ╔═╗╔╦╗╔═╗╦═╗╔╦╗╔╗ ╦ ╦╔╦╗╔═╗╔═╗╔╦╗
 ╚═╗║║║╠═╣╠╦╝ ║ ╠╩╗║ ║ ║║║ ╦║╣  ║ 
 ╚═╝╩ ╩╩ ╩╩╚═ ╩ ╚═╝╚═╝═╩╝╚═╝╚═╝ ╩ [/bold #38bdf8]
[dim]Sistem Pengelola Keuangan Bulanan Mahasiswa[/dim]"""


# =====================================================================
# 2. FUNGSI BANTUAN VALIDASI, FORMAT & DATABASE
# =====================================================================
def format_rupiah(angka) -> str:
    return f"Rp {float(angka):,.0f}".replace(",", ".")


def validasi_tanggal(teks: str, fmt: str = "%Y-%m-%d") -> bool:
    try:
        datetime.strptime(teks, fmt)
        return True
    except ValueError:
        return False


def buat_bar_visual(rasio: float, panjang: int = 14) -> str:
    rasio_aman = max(0.0, min(1.0, rasio))
    terisi = round(rasio_aman * panjang)
    if rasio > 0 and terisi == 0:
        terisi = 1
    return ("━" * terisi) + ("─" * (panjang - terisi))


def reset_select(widget: Select):
    widget.clear() if hasattr(widget, "clear") else setattr(widget, "value", Select.BLANK)


def is_select_kosong(nilai) -> bool:
    return nilai in (Select.BLANK, False, None)


def pastikan_kolom_password_diubah(cur, conn):
    cur.execute("ALTER TABLE pengguna ADD COLUMN IF NOT EXISTS password_diubah BOOLEAN DEFAULT FALSE;")
    conn.commit()


def pastikan_kolom_periode(cur, conn):
    cur.execute("ALTER TABLE anggaran ADD COLUMN IF NOT EXISTS periode VARCHAR(15) DEFAULT 'bulanan';")
    conn.commit()


# =====================================================================
# 3. FITUR GANTI PASSWORD (MAHASISWA & ORANG TUA)
# =====================================================================
class FormGantiPassword(VerticalScroll):
    def __init__(self, id_pengguna: int, id_prefix: str):
        super().__init__(classes="scroll-area")
        self.id_pengguna = id_pengguna
        self.id_prefix = id_prefix

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(classes="card-form"):
                yield Label("UBAH PASSWORD AKUN", classes="card-title")
                yield Label("Password Saat Ini:", classes="field-label")
                yield Input(placeholder="Masukkan password lama", password=True, id=f"{self.id_prefix}-pass-lama")
                yield Label("Password Baru:", classes="field-label")
                yield Input(placeholder="Minimal 4 karakter, tanpa spasi", password=True, id=f"{self.id_prefix}-pass-baru")
                yield Label("Konfirmasi Password Baru:", classes="field-label")
                yield Input(placeholder="Ulangi password baru", password=True, id=f"{self.id_prefix}-pass-konf")
                yield Button("Simpan Password Baru", variant="warning", id=f"{self.id_prefix}-btn-ganti-pass", classes="btn-full")

    @on(Button.Pressed)
    def proses_ganti_password(self, event: Button.Pressed):
        if event.button.id != f"{self.id_prefix}-btn-ganti-pass":
            return

        pass_lama = self.query_one(f"#{self.id_prefix}-pass-lama", Input).value.strip()
        pass_baru = self.query_one(f"#{self.id_prefix}-pass-baru", Input).value.strip()
        pass_konf = self.query_one(f"#{self.id_prefix}-pass-konf", Input).value.strip()

        if not pass_lama or not pass_baru or not pass_konf:
            self.app.notify("Semua kolom password wajib diisi!", severity="error")
            return
        if len(pass_baru) < 4 or " " in pass_baru:
            self.app.notify("Password baru minimal 4 karakter dan tanpa spasi!", severity="error")
            return
        if pass_baru != pass_konf:
            self.app.notify("Konfirmasi password baru tidak cocok!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.app.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_password_diubah(cur, conn)
            cur.execute("SELECT kata_sandi FROM pengguna WHERE id_pengguna = %s;", (self.id_pengguna,))
            row = cur.fetchone()

            if not row or row[0] != pass_lama:
                self.app.notify("Password lama tidak sesuai!", severity="error")
                return

            cur.execute(
                "UPDATE pengguna SET kata_sandi = %s, password_diubah = TRUE WHERE id_pengguna = %s;",
                (pass_baru, self.id_pengguna)
            )
            conn.commit()

            self.query_one(f"#{self.id_prefix}-pass-lama", Input).value = ""
            self.query_one(f"#{self.id_prefix}-pass-baru", Input).value = ""
            self.query_one(f"#{self.id_prefix}-pass-konf", Input).value = ""
            self.app.notify("Password berhasil diubah!")

        except Exception as e:
            conn.rollback()
            self.app.notify(f"Gagal mengubah password: {e}", severity="error")
        finally:
            cur.close()
            conn.close()


# =====================================================================
# 4. TEMPLATE TAMPILAN LAYAR (LOGIN, REGISTER & DASHBOARD)
# =====================================================================
class TampilanLogin(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="box"):
            yield Static(LOGO_ASCII, classes="judul")
            yield Label("Username:")
            yield Input(placeholder="Masukkan username", id="login-user")
            yield Label("Password:")
            yield Input(placeholder="Masukkan password", password=True, id="login-pass")
            with Horizontal(classes="row-btn"):
                yield Button("Masuk", variant="primary", id="btn-login")
                yield Button("Daftar Mahasiswa", variant="success", id="btn-register")
        yield Footer()


class TampilanRegister(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="box"):
            yield Label("REGISTRASI AKUN MAHASISWA", classes="judul")
            yield Label("Username Mahasiswa:")
            yield Input(placeholder="Minimal 3 karakter, tanpa spasi", id="reg-user")
            yield Label("Password Mahasiswa:")
            yield Input(placeholder="Minimal 4 karakter, tanpa spasi", password=True, id="reg-pass")
            with Horizontal(classes="row-btn"):
                yield Button("Daftar + Akun Ortu", variant="success", id="btn-daftar-ortu")
                yield Button("Daftar Saja", variant="primary", id="btn-daftar")
                yield Button("Kembali", id="btn-batal")
        yield Footer()


class TampilanMahasiswa(Screen):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user

    def compose(self) -> ComposeResult:
        opsi_sumber = [(s, s) for s in DAFTAR_SUMBER_PEMASUKAN]
        opsi_kategori = [(k, k) for k in DAFTAR_KATEGORI]

        yield Header()
        with Horizontal(id="top-bar"):
            yield Label(f"Mahasiswa: {self.user['nama_pengguna']}", id="lbl-user")
            yield Button("Logout", variant="error", id="btn-logout")

        with Horizontal(id="kpi-grid"):
            with Vertical(classes="kpi-card"):
                yield Label("TOTAL PEMASUKAN", classes="kpi-title")
                yield Label("Rp 0", id="val-masuk")
            with Vertical(classes="kpi-card"):
                yield Label("TOTAL PENGELUARAN", classes="kpi-title")
                yield Label("Rp 0", id="val-keluar")
            with Vertical(classes="kpi-card"):
                yield Label("SISA SALDO", classes="kpi-title")
                yield Label("Rp 0", id="val-saldo")
            with Vertical(classes="kpi-card"):
                yield Label("BATAS ORANG TUA", classes="kpi-title")
                yield Label("Tidak dibatasi", id="val-batas")

        with TabbedContent():
            with TabPane("Laporan & Riwayat", id="tab-laporan"):
                with Horizontal(classes="filter-bar"):
                    yield Input(placeholder="Periode YYYY-MM (kosong = semua)", id="filter-bulan")
                    yield Button("Terapkan", variant="primary", id="btn-muat")
                    yield Button("Bulan Ini", variant="default", id="btn-filter-bulan-ini")
                    yield Button("Semua Waktu", variant="default", id="btn-filter-semua")

                with VerticalScroll(classes="scroll-area"):
                    with Horizontal(classes="split-grid"):
                        with Vertical(classes="report-card"):
                            yield Label("DISTRIBUSI PENGELUARAN PER KATEGORI", classes="sub-judul")
                            yield Static("Memuat grafik...", id="chart-kategori", classes="visual-body")
                        with Vertical(classes="report-card"):
                            yield Label("KESEHATAN ARUS KAS & PROGRES ANGGARAN", classes="sub-judul")
                            yield Static("Memuat ringkasan...", id="ringkasan-keuangan", classes="visual-body")

                    with Vertical(classes="report-card-full"):
                        with Horizontal(classes="card-header-row"):
                            yield Label("RIWAYAT PENGELUARAN & PESAN ORANG TUA (Klik 1x baris untuk pilih)", classes="sub-judul-inline")
                            yield Input(placeholder="ID Pengeluaran", id="hapus-keluar-id", classes="input-id-mini")
                            yield Button("Hapus", variant="error", id="btn-hapus-keluar")
                        yield DataTable(id="tabel-pengeluaran", zebra_stripes=True)

                    with Horizontal(classes="split-grid"):
                        with Vertical(classes="report-card"):
                            with Horizontal(classes="card-header-row"):
                                yield Label("RIWAYAT PEMASUKAN", classes="sub-judul-inline")
                                yield Input(placeholder="ID Pemasukan", id="hapus-masuk-id", classes="input-id-mini")
                                yield Button("Hapus", variant="error", id="btn-hapus-masuk")
                            yield DataTable(id="tabel-pemasukan", zebra_stripes=True)

                        with Vertical(classes="report-card"):
                            with Horizontal(classes="card-header-row"):
                                yield Label("KELOLA ANGGARAN", classes="sub-judul-inline")
                                yield Input(placeholder="Kategori|YYYY-MM-01", id="hapus-ang-key", classes="input-id-mini")
                                yield Button("Hapus", variant="error", id="btn-hapus-ang")
                            yield DataTable(id="tabel-anggaran", zebra_stripes=True)

            with TabPane("Catat Pemasukan", id="tab-masuk"):
                with VerticalScroll(classes="scroll-area"):
                    with Center():
                        with Vertical(classes="card-form"):
                            yield Label("CATAT PEMASUKAN BARU", classes="card-title")
                            yield Label("Tanggal Transaksi (YYYY-MM-DD):", classes="field-label")
                            yield Input(value=date.today().strftime("%Y-%m-%d"), id="masuk-tgl")
                            yield Label("Nominal Pemasukan (Rp):", classes="field-label")
                            yield Input(placeholder="Contoh: 500000", id="masuk-nom")
                            yield Label("Sumber Pemasukan:", classes="field-label")
                            yield Select(opsi_sumber, prompt="Pilih Sumber Pemasukan", allow_blank=True, id="masuk-sumber")
                            yield Button("Simpan Pemasukan", variant="success", id="btn-simpan-masuk", classes="btn-full")

            with TabPane("Catat Pengeluaran", id="tab-keluar"):
                with VerticalScroll(classes="scroll-area"):
                    with Center():
                        with Vertical(classes="card-form"):
                            yield Label("CATAT PENGELUARAN BARU", classes="card-title")
                            yield Label("Tanggal Transaksi (YYYY-MM-DD):", classes="field-label")
                            yield Input(value=date.today().strftime("%Y-%m-%d"), id="keluar-tgl")
                            yield Label("Nominal Pengeluaran (Rp):", classes="field-label")
                            yield Input(placeholder="Contoh: 15000", id="keluar-nom")
                            yield Label("Kategori Pengeluaran:", classes="field-label")
                            yield Select(opsi_kategori, prompt="Pilih Kategori Pengeluaran", allow_blank=True, id="keluar-kat")
                            yield Label("Deskripsi Pengeluaran:", classes="field-label")
                            yield Input(placeholder="Contoh: Makan siang / Bensin", id="keluar-desk")
                            yield Button("Simpan Pengeluaran", variant="warning", id="btn-simpan-keluar", classes="btn-full")

            with TabPane("Atur Anggaran", id="tab-anggaran"):
                with VerticalScroll(classes="scroll-area"):
                    with Center():
                        with Vertical(classes="card-form"):
                            yield Label("ATUR BATAS ANGGARAN KATEGORI", classes="card-title")
                            yield Label("Kategori Anggaran:", classes="field-label")
                            yield Select(opsi_kategori, prompt="Pilih Kategori Anggaran", allow_blank=True, id="ang-kat")
                            yield Label("Tipe Batas Anggaran:", classes="field-label")
                            yield Select(DAFTAR_PERIODE_ANGGARAN, value="bulanan", allow_blank=False, id="ang-periode")
                            yield Label("Bulan Berlaku (YYYY-MM-01):", classes="field-label")
                            yield Input(value=date.today().strftime("%Y-%m-01"), id="ang-tgl")
                            yield Label("Batas Nominal Anggaran (Rp):", classes="field-label")
                            yield Input(placeholder="Contoh: 10000 (harian), 70000 (mingguan), 300000 (bulanan)", id="ang-nom")
                            yield Button("Simpan Anggaran", variant="primary", id="btn-simpan-ang", classes="btn-full")

            with TabPane("Akun Orang Tua", id="tab-ortu"):
                with VerticalScroll(classes="scroll-area"):
                    with Center():
                        with Vertical(classes="card-form"):
                            yield Label("KONEKSI AKUN ORANG TUA", classes="card-title")
                            yield Static("Memuat info akun orang tua...", id="info-ortu")
                            yield Button("Buat Akun Orang Tua Otomatis", variant="primary", id="btn-buat-ortu", classes="btn-full")

            with TabPane("Ganti Password", id="tab-pass-mhs"):
                yield FormGantiPassword(self.user["id_pengguna"], "mhs")

        yield Footer()


class TampilanOrangTua(Screen):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-bar-ortu"):
            yield Label(f"Orang Tua: {self.user['nama_pengguna']}", id="lbl-info-ortu")
            yield Button("Logout", variant="error", id="btn-logout-ortu")

        with Horizontal(id="kpi-grid-ortu"):
            with Vertical(classes="kpi-card"):
                yield Label("PEMASUKAN ANAK", classes="kpi-title")
                yield Label("Rp 0", id="val-ortu-masuk")
            with Vertical(classes="kpi-card"):
                yield Label("PENGELUARAN ANAK", classes="kpi-title")
                yield Label("Rp 0", id="val-ortu-keluar")
            with Vertical(classes="kpi-card"):
                yield Label("SISA SALDO ANAK", classes="kpi-title")
                yield Label("Rp 0", id="val-ortu-saldo")
            with Vertical(classes="kpi-card"):
                yield Label("BATAS BULANAN", classes="kpi-title")
                yield Label("Tidak dibatasi", id="val-ortu-batas")

        with TabbedContent():
            with TabPane("Pantau & Komentar", id="tab-pantau"):
                with Horizontal(classes="filter-bar"):
                    yield Input(placeholder="Periode YYYY-MM (kosong = semua)", id="ortu-filter-bulan")
                    yield Button("Terapkan", variant="primary", id="btn-ortu-muat")
                    yield Button("Bulan Ini", variant="default", id="btn-ortu-bulan-ini")
                    yield Button("Semua Waktu", variant="default", id="btn-ortu-semua")

                with VerticalScroll(classes="scroll-area"):
                    with Horizontal(classes="split-grid"):
                        with Vertical(classes="report-card"):
                            yield Label("DISTRIBUSI PENGELUARAN MAHASISWA", classes="sub-judul")
                            yield Static("Memuat grafik...", id="ortu-chart-kategori", classes="visual-body")
                        with Vertical(classes="report-card"):
                            yield Label("RINGKASAN ARUS KAS & BATAS BULANAN", classes="sub-judul")
                            yield Static("Memuat ringkasan...", id="ortu-ringkasan", classes="visual-body")

                    with Vertical(classes="report-card-full"):
                        yield Label("PENGELUARAN MAHASISWA (Klik 1x baris untuk pilih ID)", classes="sub-judul")
                        yield DataTable(id="tabel-anak", zebra_stripes=True)
                        with Horizontal(classes="komen-bar"):
                            yield Input(placeholder="ID Pengeluaran", id="komen-id")
                            yield Input(placeholder="Tulis Komentar / Arahan untuk Mahasiswa...", id="komen-teks")
                            yield Button("Kirim Komentar", variant="warning", id="btn-kirim-komen")

                    with Vertical(classes="report-card-full"):
                        yield Label("RIWAYAT PEMASUKAN MAHASISWA", classes="sub-judul")
                        yield DataTable(id="tabel-masuk-anak", zebra_stripes=True)

            with TabPane("Atur Batas Bulanan", id="tab-batas"):
                with VerticalScroll(classes="scroll-area"):
                    with Center():
                        with Vertical(classes="card-form"):
                            yield Label("BATAS PENGELUARAN BULANAN MAHASISWA", classes="card-title")
                            yield Label("Nominal Batas Maksimal Per Bulan (Rp):", classes="field-label")
                            yield Input(placeholder="Contoh: 1500000 (isi 0 untuk menghapus batas)", id="input-batas")
                            yield Button("Simpan Batas Pengeluaran", variant="primary", id="btn-simpan-batas", classes="btn-full")

            with TabPane("Ganti Password", id="tab-pass-ortu"):
                yield FormGantiPassword(self.user["id_pengguna"], "ortu")

        yield Footer()