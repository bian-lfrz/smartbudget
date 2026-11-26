from datetime import date
import math
import random
from rich.text import Text
from textual import on
from textual.widgets import Button, Input, Label, DataTable, Static, Select
from database import connectDB
from ui import (
    TampilanMahasiswa, format_rupiah, validasi_tanggal,
    buat_bar_visual, reset_select, is_select_kosong,
    pastikan_kolom_password_diubah, pastikan_kolom_periode
)


class MahasiswaScreen(TampilanMahasiswa):
    def __init__(self, user: dict):
        super().__init__(user)

    def on_mount(self):
        tbl_keluar = self.query_one("#tabel-pengeluaran", DataTable)
        tbl_keluar.cursor_type = "row"
        tbl_keluar.add_columns("ID", "Tanggal", "Kategori", "Nominal", "Deskripsi", "Pesan Orang Tua")

        tbl_masuk = self.query_one("#tabel-pemasukan", DataTable)
        tbl_masuk.cursor_type = "row"
        tbl_masuk.add_columns("ID", "Tanggal", "Sumber", "Nominal")

        tbl_ang = self.query_one("#tabel-anggaran", DataTable)
        tbl_ang.cursor_type = "row"
        tbl_ang.add_columns("Kategori", "Tipe", "Bulan", "Batas", "Status")

        self.muat_data()

    @on(Button.Pressed, "#btn-logout")
    def logout(self):
        self.app.pop_screen()

    # =====================================================================
    # 1. FITUR LAPORAN, GRAFIK & RIWAYAT TRANSAKSI
    # =====================================================================
    @on(Button.Pressed, "#btn-filter-bulan-ini")
    @on(Button.Pressed, "#btn-filter-semua")
    def filter_cepat(self, event: Button.Pressed):
        self.query_one("#filter-bulan", Input).value = date.today().strftime("%Y-%m") if event.button.id == "btn-filter-bulan-ini" else ""
        self.muat_data()

    @on(Button.Pressed, "#btn-muat")
    def muat_data(self):
        periode = self.query_one("#filter-bulan", Input).value.strip()
        if periode and not validasi_tanggal(periode, "%Y-%m"):
            self.notify("Format filter bulan salah! Gunakan YYYY-MM.", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_periode(cur, conn)
            pastikan_kolom_password_diubah(cur, conn)

            uid = self.user["id_pengguna"]
            kondisi_tgl = "AND TO_CHAR(tanggal_transaksi, 'YYYY-MM') = %s" if periode else ""
            params = (uid, periode) if periode else (uid,)

            # A. Ringkasan KPI & Batas Orang Tua
            cur.execute("SELECT batas_pengeluaran FROM pengguna WHERE id_pengguna = %s;", (uid,))
            batas_ortu = cur.fetchone()[0]

            cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pemasukan WHERE id_pengguna = %s {kondisi_tgl};", params)
            masuk = float(cur.fetchone()[0])

            cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s {kondisi_tgl};", params)
            keluar = float(cur.fetchone()[0])

            self.query_one("#lbl-user", Label).update(f"Mahasiswa: {self.user['nama_pengguna']}  |  {f'Periode {periode}' if periode else 'Semua Waktu'}")
            self.query_one("#val-masuk", Label).update(format_rupiah(masuk))
            self.query_one("#val-keluar", Label).update(format_rupiah(keluar))
            self.query_one("#val-saldo", Label).update(format_rupiah(masuk - keluar))
            self.query_one("#val-batas", Label).update(f"{format_rupiah(batas_ortu)} / bln" if batas_ortu is not None else "Tidak dibatasi")

            # B. Grafik Batang Distribusi Pengeluaran per Kategori
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
            self.query_one("#chart-kategori", Static).update(chart_text)

            # C. Isi Tabel Pengeluaran & Pemasukan
            tbl_keluar = self.query_one("#tabel-pengeluaran", DataTable)
            tbl_keluar.clear()
            cur.execute(
                f"SELECT id_pengeluaran, tanggal_transaksi, kategori, nominal, deskripsi, COALESCE(komentar_orang_tua, '-') FROM pengeluaran WHERE id_pengguna = %s {kondisi_tgl} ORDER BY tanggal_transaksi DESC;",
                params
            )
            for r in cur.fetchall():
                komen = Text(r[5], style="bold #fbbf24") if r[5] != "-" else Text("-", style="dim")
                tbl_keluar.add_row(Text(str(r[0]), style="dim"), str(r[1]), Text(r[2], style="bold #38bdf8"), Text(f"- {format_rupiah(r[3])}", style="bold #f43f5e"), r[4], komen, key=str(r[0]))

            tbl_masuk = self.query_one("#tabel-pemasukan", DataTable)
            tbl_masuk.clear()
            cur.execute(
                f"SELECT id_pemasukan, tanggal_transaksi, sumber, nominal FROM pemasukan WHERE id_pengguna = %s {kondisi_tgl} ORDER BY tanggal_transaksi DESC;",
                params
            )
            for r in cur.fetchall():
                tbl_masuk.add_row(Text(str(r[0]), style="dim"), str(r[1]), r[2], Text(f"+ {format_rupiah(r[3])}", style="bold #10b981"), key=str(r[0]))

            # D. Isi Tabel Anggaran & Progres Kesehatan Arus Kas
            tbl_ang = self.query_one("#tabel-anggaran", DataTable)
            tbl_ang.clear()
            kondisi_ang = "AND TO_CHAR(awal_bulan, 'YYYY-MM') = %s" if periode else ""
            cur.execute(
                f"SELECT kategori, COALESCE(periode, 'bulanan'), awal_bulan, batas_nominal FROM anggaran WHERE id_pengguna = %s {kondisi_ang} ORDER BY awal_bulan DESC;",
                params
            )

            ringkasan = Text()
            rasio_arus = (keluar / masuk) if masuk > 0 else (1.0 if keluar > 0 else 0.0)
            warna_arus = "#10b981" if rasio_arus < 0.7 else ("#fbbf24" if rasio_arus < 1.0 else "#f43f5e")
            ringkasan.append(f"Rasio Pengeluaran   {rasio_arus * 100:>3.0f}%  ", style=f"bold {warna_arus}")
            ringkasan.append(buat_bar_visual(rasio_arus), style=f"bold {warna_arus}")
            ringkasan.append(f"  (Sisa: {format_rupiah(masuk - keluar)})\n", style="#e5e5e5")

            rows_ang = cur.fetchall()
            ringkasan.append("\nProgres Batas Anggaran:\n" if rows_ang else "\nBelum ada batas anggaran kategori.", style="bold #a3a3a3" if rows_ang else "dim")

            cek_pakai = {
                "harian": ("Harian", "/ hr", "tanggal_transaksi = CURRENT_DATE", ()),
                "mingguan": ("Mingguan", "/ mgg", "DATE_TRUNC('week', tanggal_transaksi) = DATE_TRUNC('week', CURRENT_DATE)", ()),
                "bulanan": ("Bulanan", "/ bln", "DATE_TRUNC('month', tanggal_transaksi) = DATE_TRUNC('month', %s::date)", None),
            }
            for kat_ang, tipe_ang, awal_bln, batas_nom in rows_ang:
                batas_nom = float(batas_nom)
                lbl_tipe, satuan, sql_w, extra = cek_pakai.get(tipe_ang, cek_pakai["bulanan"])
                q_params = (uid, kat_ang, awal_bln) if extra is None else (uid, kat_ang)
                cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s AND kategori = %s AND {sql_w};", q_params)
                terpakai = float(cur.fetchone()[0])

                persen = (terpakai / batas_nom * 100) if batas_nom > 0 else 0
                warna_a = "#f43f5e" if persen >= 100 else ("#fbbf24" if persen >= 75 else "#10b981")
                label_st = "PENUH" if persen >= 100 else ("WASPADA" if persen >= 75 else "AMAN")

                ringkasan.append(f"{kat_ang:<18} ", style="bold #38bdf8")
                ringkasan.append(f"{persen:>3.0f}%  ", style=f"bold {warna_a}")
                ringkasan.append(buat_bar_visual(persen / 100.0, 12), style=f"bold {warna_a}")
                ringkasan.append(f"  {format_rupiah(terpakai)} / {format_rupiah(batas_nom)}\n", style="#d4d4d4")
                tbl_ang.add_row(Text(kat_ang, style="bold #38bdf8"), lbl_tipe, str(awal_bln), f"{format_rupiah(batas_nom)} {satuan}", Text(f"{label_st} ({persen:.0f}%)", style=f"bold {warna_a}"), key=f"{kat_ang}|{awal_bln}")

            self.query_one("#ringkasan-keuangan", Static).update(ringkasan)

            # E. Update Info Koneksi Akun Orang Tua
            if self.user["id_orang_tua"]:
                cur.execute("SELECT nama_pengguna, kata_sandi, COALESCE(password_diubah, FALSE) FROM pengguna WHERE id_pengguna = %s;", (self.user["id_orang_tua"],))
                ortu = cur.fetchone()
                if ortu:
                    info_pw = f"Password Awal      : {ortu[1]}\n(Akan disembunyikan otomatis setelah Orang Tua menggantinya)" if not ortu[2] else "Password           : ******** (Sudah diubah oleh Orang Tua)"
                    self.query_one("#info-ortu", Static).update(f"Status Koneksi     : Terhubung\nUsername Orang Tua : {ortu[0]}\n{info_pw}")
                    self.query_one("#btn-buat-ortu", Button).disabled = True
            else:
                self.query_one("#info-ortu", Static).update("Status Koneksi: Belum terhubung dengan akun Orang Tua.")

        finally:
            cur.close()
            conn.close()

    @on(DataTable.RowHighlighted)
    @on(DataTable.RowSelected)
    def pilih_baris_tabel(self, event):
        target_map = {
            "tabel-pengeluaran": "#hapus-keluar-id",
            "tabel-pemasukan": "#hapus-masuk-id",
            "tabel-anggaran": "#hapus-ang-key",
        }
        target_id = target_map.get(event.data_table.id)
        if target_id and event.data_table.has_focus and event.row_key and event.row_key.value is not None:
            self.query_one(target_id, Input).value = str(event.row_key.value)

    @on(Button.Pressed, "#btn-hapus-keluar")
    @on(Button.Pressed, "#btn-hapus-masuk")
    def hapus_transaksi(self, event: Button.Pressed):
        is_keluar = event.button.id == "btn-hapus-keluar"
        inp = self.query_one("#hapus-keluar-id" if is_keluar else "#hapus-masuk-id", Input)
        id_str = inp.value.strip()

        if not id_str.isdigit():
            self.notify("Pilih baris di tabel atau masukkan ID yang valid!", severity="error")
            return

        tabel, kolom = ("pengeluaran", "id_pengeluaran") if is_keluar else ("pemasukan", "id_pemasukan")
        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute(f"DELETE FROM {tabel} WHERE {kolom} = %s AND id_pengguna = %s;", (int(id_str), self.user["id_pengguna"]))
            if cur.rowcount == 0:
                conn.rollback()
                self.notify("ID tidak ditemukan!", severity="error")
                return

            conn.commit()
            inp.value = ""
            self.notify(f"Data {tabel} berhasil dihapus!")
            self.muat_data()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal menghapus: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    @on(Button.Pressed, "#btn-hapus-ang")
    def hapus_anggaran(self):
        inp = self.query_one("#hapus-ang-key", Input)
        key_str = inp.value.strip()

        if "|" not in key_str:
            self.notify("Pilih baris anggaran atau gunakan format Kategori|YYYY-MM-01!", severity="error")
            return

        kat, awal_bln = [x.strip() for x in key_str.split("|", 1)]
        if not kat or not validasi_tanggal(awal_bln, "%Y-%m-%d"):
            self.notify("Format anggaran tidak valid!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute("DELETE FROM anggaran WHERE id_pengguna = %s AND kategori = %s AND awal_bulan = %s::date;", (self.user["id_pengguna"], kat, awal_bln))
            if cur.rowcount == 0:
                conn.rollback()
                self.notify("Data anggaran tidak ditemukan!", severity="error")
                return

            conn.commit()
            inp.value = ""
            self.notify("Data anggaran berhasil dihapus!")
            self.muat_data()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal menghapus anggaran: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    # =====================================================================
    # 2. FITUR CATAT PEMASUKAN
    # =====================================================================
    @on(Button.Pressed, "#btn-simpan-masuk")
    def simpan_pemasukan(self):
        tgl = self.query_one("#masuk-tgl", Input).value.strip()
        nom_str = self.query_one("#masuk-nom", Input).value.strip()
        sumber_sel = self.query_one("#masuk-sumber", Select)

        if not validasi_tanggal(tgl, "%Y-%m-%d") or is_select_kosong(sumber_sel.value):
            self.notify("Lengkapi tanggal (YYYY-MM-DD) dan sumber pemasukan!", severity="error")
            return

        try:
            nominal = float(nom_str)
            if not math.isfinite(nominal) or nominal <= 0:
                raise ValueError
        except ValueError:
            self.notify("Nominal harus berupa angka lebih dari 0!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            cur.execute(
                "INSERT INTO pemasukan (id_pengguna, tanggal_transaksi, nominal, sumber) VALUES (%s, %s, %s, %s);",
                (self.user["id_pengguna"], tgl, nominal, str(sumber_sel.value))
            )
            conn.commit()
            self.query_one("#masuk-nom", Input).value = ""
            reset_select(sumber_sel)
            self.notify("Pemasukan berhasil dicatat!")
            self.muat_data()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal menyimpan pemasukan: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    # =====================================================================
    # 3. FITUR CATAT PENGELUARAN
    # =====================================================================
    @on(Button.Pressed, "#btn-simpan-keluar")
    def simpan_pengeluaran(self):
        tgl = self.query_one("#keluar-tgl", Input).value.strip()
        nom_str = self.query_one("#keluar-nom", Input).value.strip()
        kat_sel = self.query_one("#keluar-kat", Select)
        desk = self.query_one("#keluar-desk", Input).value.strip()

        if not validasi_tanggal(tgl, "%Y-%m-%d") or is_select_kosong(kat_sel.value) or not desk:
            self.notify("Lengkapi tanggal, kategori, dan deskripsi!", severity="error")
            return

        try:
            nominal = float(nom_str)
            if not math.isfinite(nominal) or nominal <= 0:
                raise ValueError
        except ValueError:
            self.notify("Nominal harus berupa angka lebih dari 0!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_periode(cur, conn)
            uid, kat = self.user["id_pengguna"], str(kat_sel.value)

            # A. Validasi Batas Bulanan Orang Tua
            cur.execute("SELECT batas_pengeluaran FROM pengguna WHERE id_pengguna = %s;", (uid,))
            batas_ortu = cur.fetchone()[0]
            if batas_ortu is not None:
                cur.execute("SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s AND DATE_TRUNC('month', tanggal_transaksi) = DATE_TRUNC('month', %s::date);", (uid, tgl))
                if float(cur.fetchone()[0]) + nominal > float(batas_ortu):
                    self.notify(f"DITOLAK! Melebihi batas bulanan Orang Tua ({format_rupiah(batas_ortu)}).", severity="error")
                    return

            # B. Validasi Batas Anggaran Kategori
            cur.execute("SELECT batas_nominal, COALESCE(periode, 'bulanan') FROM anggaran WHERE id_pengguna = %s AND kategori = %s AND DATE_TRUNC('month', awal_bulan) = DATE_TRUNC('month', %s::date) LIMIT 1;", (uid, kat, tgl))
            row_ang = cur.fetchone()
            if row_ang:
                batas_kat, tipe = float(row_ang[0]), row_ang[1]
                aturan_waktu = {
                    "harian": ("tanggal_transaksi = %s::date", f"hari ini ({tgl})"),
                    "mingguan": ("DATE_TRUNC('week', tanggal_transaksi) = DATE_TRUNC('week', %s::date)", "minggu ini"),
                    "bulanan": ("DATE_TRUNC('month', tanggal_transaksi) = DATE_TRUNC('month', %s::date)", "bulan ini"),
                }
                kondisi_w, ket_w = aturan_waktu.get(tipe, aturan_waktu["bulanan"])
                cur.execute(f"SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran WHERE id_pengguna = %s AND kategori = %s AND {kondisi_w};", (uid, kat, tgl))
                terpakai = float(cur.fetchone()[0])
                if terpakai + nominal > batas_kat:
                    self.notify(f"DITOLAK! Melebihi anggaran {tipe} '{kat}' {ket_w} (Batas: {format_rupiah(batas_kat)}, Terpakai: {format_rupiah(terpakai)}).", severity="error")
                    return

            # C. Simpan Pengeluaran ke Database
            cur.execute(
                "INSERT INTO pengeluaran (id_pengguna, tanggal_transaksi, nominal, kategori, deskripsi) VALUES (%s, %s, %s, %s, %s);",
                (uid, tgl, nominal, kat, desk)
            )
            conn.commit()
            self.query_one("#keluar-nom", Input).value = ""
            self.query_one("#keluar-desk", Input).value = ""
            reset_select(kat_sel)
            self.notify("Pengeluaran berhasil dicatat!")
            self.muat_data()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal menyimpan pengeluaran: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    # =====================================================================
    # 4. FITUR ATUR ANGGARAN KATEGORI
    # =====================================================================
    @on(Button.Pressed, "#btn-simpan-ang")
    def simpan_anggaran(self):
        kat_sel = self.query_one("#ang-kat", Select)
        periode_sel = self.query_one("#ang-periode", Select)
        tgl = self.query_one("#ang-tgl", Input).value.strip()
        nom_str = self.query_one("#ang-nom", Input).value.strip()

        if is_select_kosong(kat_sel.value) or is_select_kosong(periode_sel.value) or not validasi_tanggal(tgl, "%Y-%m-01"):
            self.notify("Pilih kategori, tipe batas, dan bulan berlaku (YYYY-MM-01)!", severity="error")
            return

        try:
            nominal = float(nom_str)
            if not math.isfinite(nominal) or nominal <= 0:
                raise ValueError
        except ValueError:
            self.notify("Nominal batas harus lebih dari 0!", severity="error")
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_periode(cur, conn)
            uid, kat, tipe = self.user["id_pengguna"], str(kat_sel.value), str(periode_sel.value)

            cur.execute("UPDATE anggaran SET batas_nominal = %s, periode = %s WHERE id_pengguna = %s AND kategori = %s AND awal_bulan = %s::date;", (nominal, tipe, uid, kat, tgl))
            if cur.rowcount == 0:
                cur.execute("INSERT INTO anggaran (id_pengguna, kategori, awal_bulan, periode, batas_nominal) VALUES (%s, %s, %s, %s, %s);", (uid, kat, tgl, tipe, nominal))

            conn.commit()
            reset_select(kat_sel)
            periode_sel.value = "bulanan"
            self.query_one("#ang-nom", Input).value = ""
            self.notify("Anggaran berhasil disimpan!")
            self.muat_data()

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal menyimpan anggaran: {e}", severity="error")
        finally:
            cur.close()
            conn.close()

    # =====================================================================
    # 5. FITUR KONEKSI AKUN ORANG TUA
    # =====================================================================
    @on(Button.Pressed, "#btn-buat-ortu")
    def buat_ortu(self):
        if self.user["id_orang_tua"] is not None:
            return

        conn, cur = connectDB()
        if not conn:
            self.notify("Koneksi database gagal!", severity="error")
            return

        try:
            pastikan_kolom_password_diubah(cur, conn)
            user_ortu = f"ortu_{self.user['nama_pengguna']}"
            pass_ortu = f"ortu{random.randint(1000, 9999)}"

            cur.execute("INSERT INTO pengguna (id_role, nama_pengguna, kata_sandi, password_diubah) VALUES (2, %s, %s, FALSE) RETURNING id_pengguna;", (user_ortu, pass_ortu))
            id_ortu = cur.fetchone()[0]
            cur.execute("UPDATE pengguna SET id_orang_tua = %s WHERE id_pengguna = %s;", (id_ortu, self.user["id_pengguna"]))

            conn.commit()
            self.user["id_orang_tua"] = id_ortu
            self.muat_data()
            self.notify(f"Akun Ortu dibuat! User: {user_ortu} | Pass: {pass_ortu}", timeout=10)

        except Exception as e:
            conn.rollback()
            self.notify(f"Gagal membuat akun orang tua: {e}", severity="error")
        finally:
            cur.close()
            conn.close()