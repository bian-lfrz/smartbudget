-- 1. Tabel Role (Menyimpan hak akses: mahasiswa & orang_tua)
CREATE TABLE role (
    id_role SERIAL PRIMARY KEY,
    nama_role VARCHAR(20) NOT NULL UNIQUE
);

-- 2. Tabel Pengguna (Menyimpan akun mahasiswa dan orang tua)
CREATE TABLE pengguna (
    id_pengguna SERIAL PRIMARY KEY,
    id_role INTEGER NOT NULL REFERENCES role(id_role),
    nama_pengguna VARCHAR(50) NOT NULL UNIQUE,
    kata_sandi VARCHAR(100) NOT NULL,
    id_orang_tua INTEGER NULL REFERENCES pengguna(id_pengguna) ON DELETE SET NULL,
    batas_pengeluaran NUMERIC(15, 2) NULL,
    password_diubah BOOLEAN NOT NULL DEFAULT FALSE
);

-- 3. Tabel Pemasukan (Mencatat dana masuk mahasiswa)
CREATE TABLE pemasukan (
    id_pemasukan SERIAL PRIMARY KEY,
    id_pengguna INTEGER NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    tanggal_transaksi DATE NOT NULL,
    nominal NUMERIC(15, 2) NOT NULL CHECK (nominal > 0),
    sumber VARCHAR(100) NOT NULL
);

-- 4. Tabel Pengeluaran (Mencatat pengeluaran & komentar orang tua)
CREATE TABLE pengeluaran (
    id_pengeluaran SERIAL PRIMARY KEY,
    id_pengguna INTEGER NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    tanggal_transaksi DATE NOT NULL,
    nominal NUMERIC(15, 2) NOT NULL CHECK (nominal > 0),
    kategori VARCHAR(100) NOT NULL,
    deskripsi TEXT NOT NULL,
    komentar_orang_tua TEXT NULL
);

-- 5. Tabel Anggaran (Mencatat batas anggaran per kategori)
CREATE TABLE anggaran (
    id_pengguna INTEGER NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    kategori VARCHAR(100) NOT NULL,
    awal_bulan DATE NOT NULL,
    periode VARCHAR(15) NOT NULL DEFAULT 'bulanan',
    batas_nominal NUMERIC(15, 2) NOT NULL CHECK (batas_nominal > 0),
    PRIMARY KEY (id_pengguna, kategori, awal_bulan)
);


INSERT INTO role (id_role, nama_role) VALUES
    (1, 'mahasiswa'),
    (2, 'orang_tua');