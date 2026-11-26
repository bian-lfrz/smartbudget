CREATE TABLE role (
    id_role SERIAL PRIMARY KEY,
    nama_role VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE pengguna (
    id_pengguna SERIAL PRIMARY KEY,
    id_role INTEGER NOT NULL REFERENCES role(id_role),
    nama_pengguna VARCHAR(50) NOT NULL UNIQUE,
    kata_sandi VARCHAR(100) NOT NULL,
    id_orang_tua INTEGER NULL REFERENCES pengguna(id_pengguna) ON DELETE SET NULL,
    batas_pengeluaran NUMERIC(15, 2) NULL,
    password_diubah BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE pemasukan (
    id_pemasukan SERIAL PRIMARY KEY,
    id_pengguna INTEGER NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    tanggal_transaksi DATE NOT NULL,
    nominal NUMERIC(15, 2) NOT NULL CHECK (nominal > 0),
    sumber VARCHAR(100) NOT NULL
);

CREATE TABLE pengeluaran (
    id_pengeluaran SERIAL PRIMARY KEY,
    id_pengguna INTEGER NOT NULL REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
    tanggal_transaksi DATE NOT NULL,
    nominal NUMERIC(15, 2) NOT NULL CHECK (nominal > 0),
    kategori VARCHAR(100) NOT NULL,
    deskripsi TEXT NOT NULL,
    komentar_orang_tua TEXT NULL
);

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