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

## Retry Otomatis

Request yang gagal karena gangguan jaringan atau status HTTP sementara akan dicoba ulang otomatis. Pola jedanya eksponensial dan maksimum 30 detik untuk setiap jeda:

```text
2 detik, 4 detik, 8 detik, 16 detik, 30 detik
```

Setiap URL memiliki maksimal 6 percobaan. Status permanen seperti HTTP 404 tidak dicoba ulang. Pada scraper detail, jika semua percobaan gagal, URL dicatat sebagai kegagalan dan proses tetap melanjutkan produk berikutnya.

## Konfigurasi Proxy Opsional

Kedua scraper mendukung proxy HTTP/HTTPS dengan autentikasi. Koneksi langsung digunakan sebagai mode awal. Proxy baru diaktifkan jika terjadi status pemicu seperti `429`, lalu digunakan selama cooldown, default 30 menit. Setelah cooldown, scraper mencoba koneksi langsung kembali.

Salin konfigurasi non-rahasia:

```bash
cp config.yml.example config.yml
```

Edit `config.yml`:

```yaml
proxy:
  enabled: true
  scheme: http
  host: proxy.example.com
  port: 8080
  cooldown_seconds: 1800
  trigger_statuses: [429, 503, 504]

retry:
  max_attempts: 6
  initial_delay_seconds: 2
  max_delay_seconds: 30

request:
  timeout_seconds: 60
  delay_between_requests_seconds: 0.5
```

Jika `403` juga perlu mengaktifkan proxy, tambahkan ke daftar:

```yaml
trigger_statuses: [403, 429, 503, 504]
```

Simpan kredensial hanya di `.env`:

```bash
cp .env.example .env
```

Isi `.env`:

```dotenv
PROXY_USERNAME=username_proxy
PROXY_PASSWORD=password_proxy
```

File `config.yml` dan `.env` tidak boleh dipush. Keduanya sudah dikecualikan oleh `.gitignore`. `config.yml.example` dan `.env.example` aman untuk dibagikan.

Install dependensi konfigurasi:

```bash
python3 -m pip install -r requirements.txt
```

Setelah konfigurasi selesai, jalankan scraper seperti biasa:

```bash
python3 tokopedia_store_scraper.py --pages 2 --output products.json
python3 tokopedia_product_details.py --input products.json --output product-details.json
```

Jika proxy tidak digunakan, biarkan `proxy.enabled: false`.

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
