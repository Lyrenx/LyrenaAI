# Lyrena AI

Lyrena AI, koyu temali, yerel calisan ve moduler bir Turkce sesli asistan projesidir. Uygulama wake word ile aktif olur, Vosk ile ses tanir, Edge TTS ile konusur ve `actions/` klasorune yeni dosya ekleyerek kolayca genisletilir.

## One-line summary

Sesli komutlarla calisan, terminal loglari olan, tam ekran ve pencere modu destekli bir masaustu asistan kabugu.

## Ozellikler

- Koyu temali PyQt6 tabanli HUD
- Merkezde animasyonlu AI orb
- Pencere modu ve tam ekran modu
- `Hey Bot` ve `Ok Bot` wake word destegi
- Turkce Vosk STT altyapisi
- Edge TTS ile bellekte ses cikisi
- TTS calisirken mikrofonu gecici duraklatma
- YouTube arama, WhatsApp mesaj, hava durumu ve sistem telemetrisi
- Terminalde heard / partial / spoke loglari
- Debug modu ile STT kapali, terminalden dogrudan komut girisi

## Hızli Baslangic

### 1) Bagimliliklari kur

```bash
pip install -r requirements.txt
```

### 2) Turkce STT modelini yerlestir

`voicemodel/vosk-model-small-tr-0.3/` klasoru proje icinde hazir olmalidir.

### 3) Lyrena'yi baslat

```bash
python main.py
```

### 4) Debug modunu baslat

```bash
python debug.py
```

Debug modunda STT kapali calisir. Komutlari terminale yazarsin.

## Temel kullanim

- `Hey Bot` veya `Ok Bot` diyerek komut penceresini ac
- Ardindan komutunu soyle
- `kapat` -> Lyrena kapanir
- `yeniden baslat` -> Lyrena yeniden baslar
- `gizlen` -> pencere gizlenir
- `tam ekran` -> tam ekran moda gecilir
- `hava ne` -> hava durumunu okur
- `Youtube tarkan ara` -> YouTube'da `tarkan` arar
- `Whatsapp annem kisisine merhaba mesajini gonder` -> rehberden annem'i bulur ve mesaj linki acar

## WhatsApp rehberi

WhatsApp kisi eslesmesi yerel bir JSON dosyasindan okunur:

- `config/whatsapp_contacts.example.json` - ornek dosya
- `config/whatsapp_contacts.json` - senin yerel rehberin

Numara formatlari:

- `05321234567`
- `+905321234567`

Sistem numarayi otomatik olarak `+90` formatina cevirir.

## Dosya yapisi

### Kök dosyalar

- `main.py` - normal uygulama giris noktasi
- `debug.py` - STT kapali terminal komut modu
- `ui.py` - ana PyQt6 pencere, ses akisi ve debug komutlari
- `requirements.txt` - Python bagimliliklari
- `.gitignore` - gecici dosyalar ve yerel veri dislama kurallari
- `README.md` - proje tanimi ve kullanim rehberi

### `core/`

- `core/config.py` - uygulama sabitleri, model yolu, renkler ve sureler
- `core/router.py` - metni action'lara dagitan komut yonlendirici
- `core/state.py` - asistanin ekran modu, durum ve komut hafizasi
- `core/text.py` - metin normalize etme ve wake word yardimcilari
- `core/terminal.py` - terminal log cikisi
- `core/app.py` - hafif baslatma sarmalayıcisi

### `actions/`

- `actions/base.py` - action context ve ortak outcome yapisi
- `actions/loader.py` - klasordeki action dosyalarini otomatik yukler
- `actions/close.py` - Lyrena uygulamasini kapatir
- `actions/fullscreen.py` - tam ekran moda gecirir
- `actions/hide.py` - pencereyi gizler
- `actions/phonecall.py` - arama icin `tel:` baglantisi acar
- `actions/restart.py` - Lyrena uygulamasini yeniden baslatir
- `actions/restartcomputer.py` - bilgisayari yeniden baslatma komutu verir
- `actions/shutdowncomputer.py` - bilgisayari kapatma komutu verir
- `actions/weather.py` - hava durumu cevabi uretir
- `actions/whatsappmessage.py` - kisi + mesaj ayiklar ve WhatsApp linki acar
- `actions/windowed.py` - pencere moduna dondurur
- `actions/youtube_search.py` - YouTube aramasi icin sorgu uretir

### `services/`

- `services/system_info.py` - CPU, RAM ve sicaklik telemetrisi toplar
- `services/weather.py` - dis hava durumu verisini cekiyor
- `services/contacts/whatsapp_contacts.py` - WhatsApp kisi rehberi ve numara normalizasyonu
- `services/tts/engine.py` - TTS motor secimi
- `services/tts/edge_engine.py` - Edge TTS ile in-memory ses oynatma
- `services/tts/sapi_engine.py` - Windows SAPI yedek motoru
- `services/tts/fallback_engine.py` - sessiz yedek motor
- `services/voice/engine.py` - STT motor secimi
- `services/voice/vosk_engine.py` - Turkce Vosk STT motoru
- `services/voice/fallback_engine.py` - sessiz yedek STT motoru

### `webui/`

- `webui/index.html` - HUD iskeleti
- `webui/style.css` - dark theme ve yerlesim stilleri
- `webui/app.js` - Python'dan gelen durumlari ekrana basar

### `config/`

- `config/README.md` - config klasoru aciklamasi
- `config/whatsapp_contacts.example.json` - ornek kisi rehberi
- `config/whatsapp_contacts.json` - yerel kisi rehberi, git'e dahil edilmez

### `voicemodel/`

- `voicemodel/README.md` - model klasoru notlari
- `voicemodel/vosk-model-small-tr-0.3/` - Turkce Vosk modeli

### `UI/`

- `UI/main_window.py` - eski Tkinter tabanli arayuz
- `UI/theme.py` - eski arayuz renkleri
- `UI/widgets.py` - eski arayuz widget'lari

Bu klasor aktif akista kullanilmiyor; ana uygulama `ui.py` + `webui/` uzerinden calisiyor.

## Yeni action ekleme

1. `actions/` altina yeni bir `.py` dosyasi ekle.
2. Dosyada `ACTION_NAME`, `TRIGGERS` ve `run(context, text)` tanimla.
3. `actions/loader.py` action'u acilisda otomatik bulur.

Ornek:

```python
ACTION_NAME = "my_action"
TRIGGERS = ("bir sey yap", "ornegi ac")

def run(context, text: str) -> dict:
    return outcome("Yapildi")
```

## Mevcut action duzenleme

Dogru dosyayi bulup sadece onu degistirmen yeterli:

- YouTube arama: `actions/youtube_search.py`
- WhatsApp mesaj: `actions/whatsappmessage.py`
- Kapatma: `actions/close.py`
- Bilgisayar kapatma: `actions/shutdowncomputer.py`
- Bilgisayar yeniden baslatma: `actions/restartcomputer.py`

## Notlar

- Uygulama, model veya WhatsApp rehberi eksik olsa bile acilir.
- Eksik parca varsa sadece ilgili ozellik pasif kalir.
- TTS calisirken mikrofon gecici olarak durur; bu, botun kendi sesini tekrar dinlemesini azaltir.
- Debug modu, STT olmadan komut test etmek icin vardir.
