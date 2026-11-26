from datetime import date
from rich.text import Text
from textual import on
from textual.widgets import Button, Input, Label, DataTable, Static
from database import connectDB
from ui import TampilanOrangTua, format_rupiah, validasi_tanggal, buat_bar_visual


class OrangTuaScreen(TampilanOrangTua):
    def __init__(self, user: dict):
        super().__init__(user)
        self.id_anak = None

    def on_mount(self):
        tbl_anak = self.query_one("#tabel-anak", DataTable)
        tbl_anak.cursor_type = "row"
        tbl_anak.add_columns("ID", "Tanggal", "Kategori", "Nominal", "Deskripsi", "Komentar Anda")

        tbl_masuk = self.query_one("#tabel-masuk-anak", DataTable)
        tbl_masuk.cursor_type = "row"
        tbl_masuk.add_columns("ID", "Tanggal", "Sumber Pemasukan", "Nominal")

        self.muat_data_anak()

    @on(Button.Pressed, "#btn-logout-ortu")
    def logout(self):
        self.app.pop_screen()

    # =====================================================================
    # 1. FITUR PEMANTAUAN KEUANGAN & KOMENTAR
    # =====================================================================
    @on(Button.Pressed, "#btn-ortu-bulan-ini")
    @on(Button.Pressed, "#btn-ortu-semua")
    def filter_cepat(self, event: Button.Pressed):
        self.query_one("#ortu-filter-bulan", Input).value = date.today().strftime("%Y-%m") if event.button.id == "btn-ortu-bulan-ini" else ""
        self.muat_data_anak()

    @on(Button.Pressed, "#btn-ortu-muat")
    def muat_data_anak(self):
        periode = self.query_one("#ortu-filter-bulan", Input).value.strip()
        if periode and not validasi_tanggal(periode, "%Y-%m"):
            self.notify("Format filter bulan salah! Gunakan YYYY-MM.", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute("SELECT id_pengguna, nama_pengguna, batas_pengeluaran FROM pengguna WHERE id_orang_tua = %s;", (self.user["id_pengguna"],))
            anak = cur.fetchone()
            if not anak:
                self.notify("Belum terhubung dengan akun mahasiswa!", severity="error")
                return

            self.id_anak = anak[0]
            batas_ortu = float(anak[2]) if anak[2] is not None else None
            kondisi_tgl = "AND TO_CHAR(tanggal_transaksi, 'YYYY-MM') = %s" if periode else ""
            params = (self.id_anak, periode) if periode else (self.id_anak,)

            # A. Ringkasan Pemasukan, Pengeluaran & Sisa Saldo Mahasiswa
            cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pemasukan WHERE id_pengguna = %s {kondisi_tgl};", params)
            masuk = float(cur.fetchone()[0])

            cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s {kondisi_tgl};", params)
            keluar = float(cur.fetchone()[0])

            self.query_one("#lbl-info-ortu", Label).update(f"Orang Tua: {self.user['nama_pengguna']}  |  Mahasiswa: {anak[1]}  |  {f'Periode {periode}' if periode else 'Semua Waktu'}")
            self.query_one("#val-ortu-masuk", Label).update(format_rupiah(masuk))
            self.query_one("#val-ortu-keluar", Label).update(format_rupiah(keluar))
            self.query_one("#val-ortu-saldo", Label).update(format_rupiah(masuk - keluar))
            self.query_one("#val-ortu-batas", Label).update(f"{format_rupiah(batas_ortu)} / bln" if batas_ortu is not None else "Tidak dibatasi")

            # B. Grafik Distribusi Pengeluaran Mahasiswa per Kategori
            cur.execute(
                f"SELECT kategori, COALESCE(SUM(nominal), 0) AS total FROM pengeluaran WHERE id_pengguna = %s {kondisi_tgl} GROUP BY kategori ORDER BY total DESC;",
                params
            )
            chart_text = Text()
            rows_kat = cur.fetchall()
            if not rows_kat or keluar <= 0:
                chart_text.append("Belum ada transaksi pengeluaran pada periode ini.", style="dim")
            else:
                warna_list = ["#38bdf8", "#a855f7", "#10b981", "#fbbf24", "#f43f5e", "#94a3b8"]
                for i, (kat_nama, tot_kat) in enumerate(rows_kat):
                    tot = float(tot_kat)
                    warna = warna_list[i % len(warna_list)]
                    if i > 0:
                        chart_text.append("\n")
                    chart_text.append(f"{kat_nama:<20} ", style="bold #e5e5e5")
                    chart_text.append(f"{(tot / keluar) * 100:>3.0f}%  ", style="bold #a3a3a3")
                    chart_text.append(buat_bar_visual(tot / keluar), style=f"bold {warna}")
                    chart_text.append(f"  {format_rupiah(tot)}", style="#f5f5f5")
            self.query_one("#ortu-chart-kategori", Static).update(chart_text)

            # C. Ringkasan Rasio Pengeluaran & Pemakaian Batas Bulanan
            ringkasan = Text()
            rasio_arus = (keluar / masuk) if masuk > 0 else (1.0 if keluar > 0 else 0.0)
            warna_arus = "#10b981" if rasio_arus < 0.7 else ("#fbbf24" if rasio_arus < 1.0 else "#f43f5e")
            ringkasan.append(f"Rasio Pengeluaran   {rasio_arus * 100:>3.0f}%  ", style=f"bold {warna_arus}")
            ringkasan.append(buat_bar_visual(rasio_arus), style=f"bold {warna_arus}")
            ringkasan.append(f"  (Sisa: {format_rupiah(masuk - keluar)})\n", style="#e5e5e5")

            if batas_ortu is not None and batas_ortu > 0:
                cur.execute("SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s AND DATE_TRUNC('month', tanggal_transaksi) = DATE_TRUNC('month', CURRENT_DATE);", (self.id_anak,))
                keluar_bln = float(cur.fetchone()[0])
                rasio_bts = keluar_bln / batas_ortu
                warna_bts = "#10b981" if rasio_bts < 0.75 else ("#fbbf24" if rasio_bts < 1.0 else "#f43f5e")
                ringkasan.append("\nPemakaian Batas Bulan Ini:\n", style="bold #a3a3a3")
                ringkasan.append(f"Batas Bulanan       {rasio_bts * 100:>3.0f}%  ", style=f"bold {warna_bts}")
                ringkasan.append(buat_bar_visual(rasio_bts), style=f"bold {warna_bts}")
                ringkasan.append(f"  {format_rupiah(keluar_bln)} / {format_rupiah(batas_ortu)}", style="#d4d4d4")
            else:
                ringkasan.append("\nBatas pengeluaran bulanan belum diaktifkan.", style="dim")
            self.query_one("#ortu-ringkasan", Static).update(ringkasan)

            # D. Isi Tabel Pengeluaran & Pemasukan Mahasiswa
            tbl_keluar = self.query_one("#tabel-anak", DataTable)
            tbl_keluar.clear()
            cur.execute(
                f"SELECT id_pengeluaran, tanggal_transaksi, kategori, nominal, deskripsi, COALESCE(komentar_orang_tua, '-') FROM pengeluaran WHERE id_pengguna = %s {kondisi_tgl} ORDER BY tanggal_transaksi DESC;",
                params
            )
            for r in cur.fetchall():
                komen = Text(r[5], style="bold #fbbf24") if r[5] != "-" else Text("-", style="dim")
                tbl_keluar.add_row(Text(str(r[0]), style="dim"), str(r[1]), Text(r[2], style="bold #38bdf8"), Text(f"- {format_rupiah(r[3])}", style="bold #f43f5e"), r[4], komen, key=str(r[0]))

            tbl_masuk = self.query_one("#tabel-masuk-anak", DataTable)
            tbl_masuk.clear()
            cur.execute(
                f"SELECT id_pemasukan, tanggal_transaksi, sumber, nominal FROM pemasukan WHERE id_pengguna = %s {kondisi_tgl} ORDER BY tanggal_transaksi DESC;",
                params
            )
            for r in cur.fetchall():
                tbl_masuk.add_row(Text(str(r[0]), style="dim"), str(r[1]), r[2], Text(f"+ {format_rupiah(r[3])}", style="bold #10b981"), key=str(r[0]))

        finally:
            cur.close()
            conn.close()

    @on(DataTable.RowHighlighted, "#tabel-anak")
    @on(DataTable.RowSelected, "#tabel-anak")
    def pilih_baris_anak(self, event):
        if event.data_table.has_focus and event.row_key and event.row_key.value is not None:
            self.query_one("#komen-id", Input).value = str(event.row_key.value)

    @on(Button.Pressed, "#btn-kirim-komen")
    def kirim_komentar(self):
        id_str = self.query_one("#komen-id", Input).value.strip()
        komentar = self.query_one("#komen-teks", Input).value.strip()

        if not id_str.isdigit() or not komentar:
            self.notify("Pilih baris pengeluaran atau isi ID dan komentar yang valid!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute(
                "UPDATE pengeluaran SET komentar_orang_tua = %s WHERE id_pengeluaran = %s AND id_pengguna = %s;",
                (komentar, int(id_str), self.id_anak)
            )
            if cur.rowcount == 0:
                conn.rollback()
                self.notify("ID Pengeluaran tidak ditemukan!", severity="error")
                return

            conn.commit()
            self.query_one("#komen-id", Input).value = ""
            self.query_one("#komen-teks", Input).value = ""
            self.notify("Komentar berhasil dikirim!")
            self.muat_data_anak()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal mengirim komentar: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    # =====================================================================
    # 2. FITUR ATUR BATAS PENGELUARAN BULANAN
    # =====================================================================
    @on(Button.Pressed, "#btn-simpan-batas")
    def simpan_batas(self):
        raw = self.query_one("#input-batas", Input).value.strip()
        try:
            batas = float(raw)
            if batas < 0:
                raise ValueError
        except ValueError:
            self.notify("Masukkan angka batas yang valid (>= 0)!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute(
                "UPDATE pengguna SET batas_pengeluaran = %s WHERE id_pengguna = %s;",
                (None if batas == 0 else batas, self.id_anak)
            )
            conn.commit()
            self.query_one("#input-batas", Input).value = ""
            self.notify("Batas pengeluaran bulanan berhasil diperbarui!")
            self.muat_data_anak()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal memperbarui batas: {e}", severity="error")
        finally:
            cur.close()
            conn.close()