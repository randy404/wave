# 🔐 Konfigurasi Streamlit Cloud Secrets

Untuk menjalankan aplikasi dengan fitur WhatsApp dan SMS notifikasi, Anda perlu mengkonfigurasi **Secrets** di Streamlit Cloud.

## Langkah-langkah:

### 1. Buka Streamlit Cloud App Settings
- Pergi ke: https://share.streamlit.io/
- Pilih aplikasi Anda
- Klik **"⋮"** (menu) di kanan bawah
- Pilih **"Settings"**
- Pilih tab **"Secrets"**

### 2. Copy & Paste Secrets Configuration

Copy konfigurasi di bawah ini dan paste ke dalam **Secrets editor**:

```toml
# Twilio Credentials
# Ganti dengan credentials Anda dari https://console.twilio.com/
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_here"

# WhatsApp Configuration (Twilio Sandbox default)
# Untuk testing: gunakan Twilio Sandbox WhatsApp
# URL: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
WHATSAPP_TO = "whatsapp:+6281234567890"

# SMS Configuration
# Ganti dengan nomor Twilio Anda yang sudah terverifikasi
# Untuk trial account: hanya bisa kirim ke nomor yang sudah diverifikasi
TWILIO_SMS_FROM = "+12025550123"
SMS_TO = "+6281234567890"

# Tsunami Alert Configuration
# Gunakan nomor Twilio yang sama atau nomor lain yang sudah terverifikasi
TWILIO_TSUNAMI_FROM = "+12025550123"
TSUNAMI_ALERT_TO = "+6281234567890"

# Camera Location (opsional)
CAMERA_LOCATION = "Pantai Monitoring"

# RTSP Configuration (opsional - untuk live camera feed)
RTSP_URL = "rtsp://admin:admin@192.168.1.100:8554/stream"
```

### 3. Update Nomor Telepon

⚠️ **PENTING**: Update nomor-nomor berikut dengan nomor Anda yang sebenarnya:

- **WHATSAPP_TO**: Nomor WhatsApp tujuan (format: `whatsapp:+62xxx`)
- **SMS_TO**: Nomor HP tujuan SMS (format: `+62xxx`)
- **TSUNAMI_ALERT_TO**: Nomor untuk alert tsunami (format: `+62xxx`)
- **TWILIO_SMS_FROM**: Nomor Twilio Anda (lihat di [Twilio Console](https://console.twilio.com/))
- **TWILIO_TSUNAMI_FROM**: Sama dengan TWILIO_SMS_FROM atau nomor Twilio lainnya

### 4. Setup Twilio WhatsApp Sandbox (Untuk Testing)

Sebelum bisa menerima WhatsApp, Anda harus join Twilio Sandbox:

1. Buka: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. Kirim pesan WhatsApp ke nomor yang ditampilkan (biasanya `+1 415 523 8886`)
3. Kirim kode yang diberikan (misal: `join xxxxx-xxxxx`)
4. Tunggu konfirmasi dari Twilio
5. Sekarang nomor WhatsApp Anda sudah bisa menerima notifikasi!

### 5. Verifikasi Nomor untuk SMS (Trial Account)

Jika menggunakan Twilio Trial Account:

1. Buka: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Klik **"Add a new number"**
3. Masukkan nomor HP Anda (yang akan menerima SMS)
4. Verifikasi dengan kode yang dikirim via SMS
5. Sekarang nomor tersebut bisa menerima SMS dari aplikasi!

### 6. Save & Reboot

- Klik **"Save"** di Streamlit Cloud
- Aplikasi akan otomatis restart dengan konfigurasi baru
- Coba test fitur WhatsApp/SMS dari dashboard!

---

## 📝 Catatan Penting:

### Trial vs Production Account

**Twilio Trial Account** (Gratis):
- ✅ Bisa kirim WhatsApp via Sandbox
- ✅ Bisa kirim SMS ke nomor yang sudah diverifikasi
- ⚠️ Pesan akan ada prefix "[Sent from your Twilio trial account]"
- ⚠️ Terbatas jumlah pesan

**Twilio Production Account** (Berbayar):
- ✅ Tidak ada prefix
- ✅ Unlimited verified numbers
- ✅ Bisa kirim ke nomor manapun
- ✅ WhatsApp Business API (perlu approval)

### Security

⚠️ **JANGAN commit file `.streamlit/secrets.toml` ke GitHub!**
- File ini sudah masuk `.gitignore` untuk keamanan
- Hanya configure secrets di Streamlit Cloud web interface
- Credentials Anda aman dan tidak akan public

---

## 🧪 Testing

Setelah konfigurasi selesai:

1. Buka aplikasi Streamlit Cloud Anda
2. Scroll ke bagian **"WhatsApp Alert"**
3. Klik tombol **"Kirim Tes WA"**
4. Cek WhatsApp Anda - seharusnya ada pesan dari Twilio!
5. Ulangi untuk test SMS

Jika ada error, cek:
- Apakah credentials sudah benar?
- Apakah sudah join Twilio WhatsApp Sandbox?
- Apakah nomor HP sudah diverifikasi untuk SMS?

---

## 🆘 Troubleshooting

### Error: "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN are not set"
➡️ Pastikan sudah copy-paste secrets ke Streamlit Cloud Settings > Secrets

### WhatsApp tidak terkirim
➡️ Pastikan sudah join Twilio WhatsApp Sandbox (lihat langkah 4)

### SMS tidak terkirim (Trial Account)
➡️ Verifikasi nomor tujuan di Twilio Console (lihat langkah 5)

### Error: "Unable to create record"
➡️ Cek format nomor telepon (harus E.164: +62xxx untuk Indonesia)

---

**Need help?** Check [Twilio Documentation](https://www.twilio.com/docs) atau contact support.

