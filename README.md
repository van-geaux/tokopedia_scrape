# Tokopedia Scraper

Scraper Python sederhana untuk mengambil data produk dari toko Tokopedia dan detail setiap produk.

## Fitur

- Mengambil seluruh produk dari halaman toko.
- Menggunakan ukuran halaman maksimum yang tersedia pada halaman toko.
- Mengambil nama, URL, harga, jumlah terjual, dan rating.
- Mengambil detail produk, stok, harga diskon, dan jumlah ulasan berdasarkan bintang.
- Menggabungkan hasil setiap halaman ke satu file JSON.
- Tidak membutuhkan library pihak ketiga.

## Persyaratan

- Python 3.10 atau lebih baru
- Koneksi internet

## Instalasi

Clone repository ini, kemudian masuk ke direktorinya:

```bash
git clone git@github.com:van-geaux/tokopedia_scrape.git
cd tokopedia_scrape
```

Dependensi Python saat ini hanya standard library. File dependensi tetap tersedia di:

```text
requirements.txt
```

## Mengambil Daftar Produk Toko

Contoh untuk toko ENCHEN PERSONAL CARE:

```bash
python3 tokopedia_store_scraper.py \
  "https://www.tokopedia.com/enchenmenscare/product" \
  --pages 2 \
  --output products.json
```

Parameter yang tersedia:

- URL toko, dalam format `https://www.tokopedia.com/<nama-toko>/product`.
- `--pages`, jumlah halaman yang diambil.
- `--output`, file JSON hasil.
- `--csv`, file CSV opsional.

Contoh dengan CSV:

```bash
python3 tokopedia_store_scraper.py \
  "https://www.tokopedia.com/enchenmenscare/product" \
  --pages 2 \
  --output products.json \
  --csv products.csv
```

Konfigurasi default dapat diubah langsung di bagian atas `tokopedia_store_scraper.py`:

```python
STORE_URL = "https://www.tokopedia.com/enchenmenscare/product"
PAGES = 1
OUTPUT_JSON = Path("products.json")
```

## Mengambil Detail Produk

Setelah `products.json` tersedia, jalankan:

```bash
python3 tokopedia_product_details.py \
  --input products.json \
  --output product-details.json
```

Untuk menambah jeda antar-request:

```bash
python3 tokopedia_product_details.py \
  --input products.json \
  --output product-details.json \
  --delay 2
```

Konfigurasi default dapat diubah di bagian atas `tokopedia_product_details.py`:

```python
INPUT_JSON = Path("products.json")
OUTPUT_JSON = Path("product-details.json")
DELAY = 0.5
```

## Struktur Data

`products.json` berisi:

```json
{
  "name": "Nama produk",
  "link": "https://www.tokopedia.com/...",
  "price": 199000,
  "sold": 1,
  "star": 5.0
}
```

`product-details.json` berisi:

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

## File yang Tidak Dipush

File hasil scraping dan cache lokal dikecualikan melalui `.gitignore`, termasuk:

- `products.json`
- `products-all-pages.json`
- `product-details.json`
- `result.json`
- `result.csv`
- `result-2pages.json`
- `products.csv`
- `__pycache__/`

## Catatan

- Data diambil dari halaman publik Tokopedia.
- Struktur halaman dan payload Tokopedia dapat berubah sewaktu-waktu.
- Nilai yang tidak tersedia akan ditulis sebagai `null`, `0`, atau string kosong sesuai payload Tokopedia.
- Gunakan jeda request yang wajar untuk mengurangi risiko pembatasan akses.
