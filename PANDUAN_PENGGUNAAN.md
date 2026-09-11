# Panduan Penggunaan Tokopedia Scraper

Proyek ini berisi dua scraper Python untuk mengambil data toko dan detail produk Tokopedia.

## Persyaratan

- Python 3.10 atau lebih baru
- Koneksi internet
- Tidak ada library pihak ketiga yang diperlukan

File dependensi tersedia di `requirements.txt`.

## Struktur File

- `tokopedia_store_scraper.py`
  Mengambil daftar produk dari halaman toko.
- `tokopedia_product_details.py`
  Mengambil detail setiap produk berdasarkan daftar URL produk.
- `products.json`
  Daftar produk dari scraper toko.
- `product-details.json`
  Detail produk dari scraper produk.
- `requirements.txt`
  Daftar dependensi Python.

## 1. Mengambil Daftar Produk Toko

Format URL toko yang digunakan:

```text
https://www.tokopedia.com/<nama-toko>/product
```

Contoh:

```bash
python3 tokopedia_store_scraper.py \
  "https://www.tokopedia.com/enchenmenscare/product" \
  --pages 2 \
  --output products.json
```

Parameter:

- URL toko, wajib jika tidak menggunakan `STORE_URL` di dalam script.
- `--pages`, jumlah halaman yang ingin diambil.
- `--output`, nama file JSON hasil scraper.
- `--csv`, opsional, nama file CSV tambahan.

Contoh dengan output JSON dan CSV:

```bash
python3 tokopedia_store_scraper.py \
  "https://www.tokopedia.com/enchenmenscare/product" \
  --pages 2 \
  --output products.json \
  --csv products.csv
```

Scraper menggunakan ukuran halaman maksimum yang tersedia dari halaman toko. Jika satu halaman berisi 80 produk dan halaman terakhir berisi 29 produk, hasil akhirnya akan digabungkan ke satu file JSON.

## Konfigurasi Langsung di Dalam Script

Jika tidak ingin memasukkan parameter URL melalui command line, ubah nilai berikut di bagian atas `tokopedia_store_scraper.py`:

```python
STORE_URL = "https://www.tokopedia.com/enchenmenscare/product"
PAGES = 2
OUTPUT_JSON = Path("products.json")
```

Setelah itu jalankan:

```bash
python3 tokopedia_store_scraper.py
```

## 2. Mengambil Detail Produk

Scraper detail membaca URL produk dari `products.json`.

Jalankan dengan konfigurasi default:

```bash
python3 tokopedia_product_details.py
```

Perintah tersebut membaca `products.json` dan menghasilkan:

```text
product-details.json
```

Untuk menentukan nama file secara manual:

```bash
python3 tokopedia_product_details.py \
  --input products.json \
  --output product-details.json
```

Parameter:

- `--input`, file JSON yang berisi daftar produk.
- `--output`, file JSON untuk hasil detail produk.
- `--delay`, jeda antar-request dalam detik.

Contoh dengan jeda dua detik:

```bash
python3 tokopedia_product_details.py \
  --input products.json \
  --output product-details.json \
  --delay 2
```

Konfigurasi default juga dapat diubah langsung di bagian atas script:

```python
INPUT_JSON = Path("products.json")
OUTPUT_JSON = Path("product-details.json")
DELAY = 0.5
```

## Data yang Dihasilkan

### `products.json`

Setiap produk berisi:

```json
{
  "name": "Nama produk",
  "link": "https://www.tokopedia.com/...",
  "price": 199000,
  "sold": 1,
  "star": 5.0
}
```

### `product-details.json`

Setiap produk berisi:

- `name`, nama produk pada halaman detail.
- `link`, URL produk.
- `sold`, jumlah produk terjual.
- `star`, rating rata-rata produk.
- `price`, harga yang sedang ditampilkan.
- `discounted_price`, harga diskon jika tersedia.
- `product_detail_items`, detail seperti kondisi, kategori, dan pemesanan minimum.
- `available_stock`, stok yang tersedia.
- `total_review_by_star`, jumlah ulasan berdasarkan rating bintang 1 sampai 5.

Contoh struktur:

```json
{
  "name": "Nama produk",
  "link": "https://www.tokopedia.com/...",
  "sold": 1,
  "star": 5.0,
  "price": 199000,
  "discounted_price": 199000,
  "product_detail_items": [
    {
      "title": "Kondisi",
      "value": "Baru"
    },
    {
      "title": "Pemesanan Minimum",
      "value": "1 Buah"
    }
  ],
  "available_stock": 145,
  "total_review_by_star": {
    "1": 0,
    "2": 0,
    "3": 0,
    "4": 0,
    "5": 1
  }
}
```

## Alur Penggunaan Lengkap

```bash
python3 tokopedia_store_scraper.py \
  "https://www.tokopedia.com/enchenmenscare/product" \
  --pages 2 \
  --output products.json

python3 tokopedia_product_details.py \
  --input products.json \
  --output product-details.json
```

Hasil akhirnya tersedia di:

```text
products.json
product-details.json
```

## Catatan

- Data bergantung pada informasi yang tersedia secara publik di halaman Tokopedia.
- Nilai yang tidak diberikan Tokopedia akan ditulis sebagai `null`, `0`, atau string kosong sesuai struktur datanya.
- Jangan mengirim request terlalu cepat. Gunakan nilai `--delay` yang lebih besar jika diperlukan.
- Struktur HTML dan payload Tokopedia dapat berubah sewaktu-waktu, sehingga scraper mungkin perlu diperbarui jika format halaman berubah.
