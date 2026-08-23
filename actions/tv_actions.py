import json
import os

import requests
from actions.base import outcome

# ---------------------------------------------------------------------------
# EYLEM TANIMLAMALARI (ACTION METADATA)
# ---------------------------------------------------------------------------
ACTION_NAME = "tv_control"

TRIGGERS = (
    "tv aç", "tvyi aç", "tv'yi aç", "televizyonu aç", "televizyon aç",
    "tv kapat", "tvyi kapat", "tv'yi kapat", "televizyonu kapat", "televizyon kapat"
)

# ---------------------------------------------------------------------------
# SMARTTHINGS API VE CIHAZ AYARLARI
# ---------------------------------------------------------------------------
def _get_setting(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value

    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                return str(value)
        except (ImportError, OSError):
            pass

    return ""


SMARTTHINGS_TOKEN = _get_setting("SMARTTHINGS_TOKEN")
TV_DEVICE_ID = _get_setting("SMARTTHINGS_TV_DEVICE_ID")


def get_smartthings_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SMARTTHINGS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_tv_switch_state() -> tuple[str | None, str | None]:
    if not SMARTTHINGS_TOKEN or not TV_DEVICE_ID:
        return None, "SMARTTHINGS_TOKEN veya SMARTTHINGS_TV_DEVICE_ID ayarlanmamis."

    url = f"https://api.smartthings.com/v1/devices/{TV_DEVICE_ID}/status"
    try:
        response = requests.get(url, headers=get_smartthings_headers(), timeout=8)
        if response.status_code != 200:
            return None, f"Durum sorgusu HTTP {response.status_code}: {response.text}"

        switch = response.json()["components"]["main"]["switch"]["switch"]["value"]
        return switch, None
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"TV durum yaniti beklenen formatta degil: {exc}"
    except requests.RequestException as exc:
        return None, f"Durum sorgusu ag hatasi: {exc}"


def send_smartthings_command(command: str) -> tuple:
    """
    SmartThings API üzerinden cihaz durum çakışmalarını (ConflictError) 
    minimize edecek şekilde komut iletir.
    """
    url = f"https://api.smartthings.com/v1/devices/{TV_DEVICE_ID}/commands"
    
    if not SMARTTHINGS_TOKEN or not TV_DEVICE_ID:
        return False, "SMARTTHINGS_TOKEN veya SMARTTHINGS_TV_DEVICE_ID ayarlanmamis."

    payload = {
        "commands": [{
            "component": "main",
            "capability": "switch",
            "command": command
        }]
    }
    
    try:
        response = requests.post(
            url,
            headers=get_smartthings_headers(),
            json=payload,
            timeout=8,
        )

        if response.status_code in (200, 202):
            return True, "İşlem başarılı."

        if response.status_code == 409:
            return False, (
                "SmartThings TV komutunu mevcut cihaz durumunda kabul etmedi "
                f"(ConflictError): {response.text}"
            )

        
        
        else:
            try:
                error_data = response.json()
                error_msg = json.dumps(error_data, indent=2)
            except ValueError:
                error_msg = response.text
                
            return False, f"HTTP {response.status_code} Hatası:\n{error_msg}"
            
    except requests.RequestException as exc:
        return False, f"Ağ/Bağlantı Hatası: {exc}"


def run(context, text: str) -> dict:
    """
    Kullanıcı komutunu işler ve SmartThings API'yi tetikler.
    """
    clean_text = text.replace("I", "ı").replace("İ", "i").lower()
    
    ON_KEYWORDS = ["aç", "ac", "açar", "calistir", "çalıştır"]
    OFF_KEYWORDS = ["kapat", "kapa", "kapatır", "söndür", "sondur"]

    wants_on = any(keyword in clean_text for keyword in ON_KEYWORDS)
    wants_off = any(keyword in clean_text for keyword in OFF_KEYWORDS)
    if not wants_on and not wants_off:
        return outcome("Televizyon için ne yapmam gerektiğini anlayamadım.", exit=False, speak=True)

    desired_state = "on" if wants_on else "off"
    current_state, state_error = get_tv_switch_state()
    if current_state == desired_state:
        return outcome(
            f"Televizyon zaten {'açık' if desired_state == 'on' else 'kapalı'}.",
            exit=False,
            speak=True,
        )

    if state_error:
        context.controller.log_status(f"SmartThings durum uyarisi: {state_error}")

    # Açma Komutu
    if wants_on:
        context.controller.log_status("SmartThings: TV açılma komutu gönderiliyor...")
        success, message = send_smartthings_command("on")
        
        if success:
            return outcome("Televizyon açılıyor.", exit=False, speak=True)
        else:
            context.controller.log_status(f"HATA DETAYI:\n{message}")
            return outcome("Televizyon kapalı olduğu için bulut komutu reddetti. Lütfen TV'nin ağda bekleme modunda olduğundan emin ol.", exit=False, speak=True)

    # Kapatma Komutu
    else:
        context.controller.log_status("SmartThings: TV kapatılma komutu gönderiliyor...")
        success, message = send_smartthings_command("off")
        
        if success:
            return outcome("Televizyon kapatıldı.", exit=False, speak=True)
        else:
            context.controller.log_status(f"HATA DETAYI:\n{message}")
            return outcome("Televizyon kapatılırken hata oluştu. Terminali kontrol edebilir misin?", exit=False, speak=True)
