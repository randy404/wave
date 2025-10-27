#!/usr/bin/env python3
"""
Modul untuk mengirim notifikasi gempa via WhatsApp dan SMS
"""

import os
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv

# Import modul notifikasi yang sudah ada
try:
    from notify_whatsapp import send_whatsapp
    SEND_WA_AVAILABLE = True
except ImportError:
    SEND_WA_AVAILABLE = False
    print("⚠️ Modul notify_whatsapp.py tidak ditemukan")

try:
    from notify_sms import send_sms
    SEND_SMS_AVAILABLE = True
except ImportError:
    SEND_SMS_AVAILABLE = False
    print("⚠️ Modul notify_sms.py tidak ditemukan")

# Import modul gempa BMKG
try:
    from earthquake_bmkg import BMKGEarthquakeAPI
    BMKG_API_AVAILABLE = True
except ImportError:
    BMKG_API_AVAILABLE = False
    print("⚠️ Modul earthquake_bmkg.py tidak ditemukan")

load_dotenv()

def send_earthquake_alert_whatsapp(earthquake_data: dict, 
                                 alert_level: str = "EARTHQUAKE",
                                 to: Optional[str] = None) -> List[str]:
    """
    Kirim alert gempa via WhatsApp
    
    Args:
        earthquake_data: Data gempa yang sudah di-parse
        alert_level: Level alert (EARTHQUAKE, TSUNAMI)
        to: Nomor tujuan WhatsApp (opsional)
    
    Returns:
        List[str]: List SID dari pesan yang berhasil dikirim
    """
    if not SEND_WA_AVAILABLE:
        print("❌ Modul WhatsApp tidak tersedia")
        return []
    
    try:
        # Tentukan emoji dan header berdasarkan level alert
        if alert_level == "TSUNAMI":
            emoji = "🌊"
            header = "🚨 *ALERT TSUNAMI POTENSIAL!* 🚨"
            urgency = "⚠️ *SEGERA EVAKUASI KE TEMPAT TINGGI!* ⚠️"
        else:
            emoji = "🌍"
            header = "⚠️ *ALERT GEMPA!* ⚠️"
            urgency = "📢 *WASPADA DAN SIAP SIAGA!* 📢"
        
        # Format pesan alert gempa
        message = f"""{header}

{emoji} *INFORMASI GEMPA TERBARU*

*Waktu:* {earthquake_data.get('datetime_str', 'N/A')}
*Magnitude:* M{earthquake_data.get('magnitude', 'N/A')}
*Kedalaman:* {earthquake_data.get('kedalaman', 'N/A')}
*Lokasi:* {earthquake_data.get('wilayah', 'N/A')}
*Koordinat:* {earthquake_data.get('coordinates', 'N/A')}

*Potensi Tsunami:* {earthquake_data.get('potensi_tsunami', 'N/A')}
*Dirasakan:* {earthquake_data.get('dirasakan', 'N/A')}

{urgency}

📡 *Sumber:* BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)
🕐 *Update:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

_Sistem Monitoring Gempa Otomatis_"""
        
        # Kirim via WhatsApp
        return send_whatsapp(message, to)
        
    except Exception as e:
        print(f"❌ Error mengirim alert gempa WhatsApp: {e}")
        return []

def send_earthquake_alert_sms(earthquake_data: dict, 
                            alert_level: str = "EARTHQUAKE",
                            to: Optional[str] = None) -> List[str]:
    """
    Kirim alert gempa via SMS
    
    Args:
        earthquake_data: Data gempa yang sudah di-parse
        alert_level: Level alert (EARTHQUAKE, TSUNAMI)
        to: Nomor tujuan SMS (opsional)
    
    Returns:
        List[str]: List SID dari pesan yang berhasil dikirim
    """
    if not SEND_SMS_AVAILABLE:
        print("❌ Modul SMS tidak tersedia")
        return []
    
    try:
        # Tentukan header berdasarkan level alert
        if alert_level == "TSUNAMI":
            header = "🚨 ALERT TSUNAMI POTENSIAL! 🚨"
            urgency = "⚠️ SEGERA EVAKUASI KE TEMPAT TINGGI! ⚠️"
        else:
            header = "⚠️ ALERT GEMPA! ⚠️"
            urgency = "📢 WASPADA DAN SIAP SIAGA! 📢"
        
        # Format pesan alert gempa (SMS lebih singkat)
        message = f"""{header}

INFORMASI GEMPA TERBARU

Waktu: {earthquake_data.get('datetime_str', 'N/A')}
Magnitude: M{earthquake_data.get('magnitude', 'N/A')}
Kedalaman: {earthquake_data.get('kedalaman', 'N/A')}
Lokasi: {earthquake_data.get('wilayah', 'N/A')}

Potensi Tsunami: {earthquake_data.get('potensi_tsunami', 'N/A')}
Dirasakan: {earthquake_data.get('dirasakan', 'N/A')}

{urgency}

Sumber: BMKG
Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Sistem Monitoring Gempa Otomatis"""
        
        # Kirim via SMS
        return send_sms(message, to)
        
    except Exception as e:
        print(f"❌ Error mengirim alert gempa SMS: {e}")
        return []

def send_earthquake_alert(earthquake_data: dict, 
                        alert_level: str = "EARTHQUAKE",
                        enable_whatsapp: bool = True,
                        enable_sms: bool = True,
                        wa_to: Optional[str] = None,
                        sms_to: Optional[str] = None) -> dict:
    """
    Kirim alert gempa via WhatsApp dan/atau SMS
    
    Args:
        earthquake_data: Data gempa yang sudah di-parse
        alert_level: Level alert (EARTHQUAKE, TSUNAMI)
        enable_whatsapp: Enable notifikasi WhatsApp
        enable_sms: Enable notifikasi SMS
        wa_to: Nomor tujuan WhatsApp (opsional)
        sms_to: Nomor tujuan SMS (opsional)
    
    Returns:
        dict: Hasil pengiriman notifikasi
    """
    result = {
        'success': False,
        'whatsapp_sent': False,
        'sms_sent': False,
        'whatsapp_sids': [],
        'sms_sids': [],
        'errors': []
    }
    
    try:
        # Kirim via WhatsApp
        if enable_whatsapp and SEND_WA_AVAILABLE:
            try:
                wa_sids = send_earthquake_alert_whatsapp(earthquake_data, alert_level, wa_to)
                if wa_sids:
                    result['whatsapp_sent'] = True
                    result['whatsapp_sids'] = wa_sids
                    print(f"✅ Alert gempa WhatsApp berhasil dikirim: {len(wa_sids)} pesan")
                else:
                    result['errors'].append("Gagal mengirim alert gempa WhatsApp")
            except Exception as e:
                result['errors'].append(f"Error WhatsApp: {e}")
        
        # Kirim via SMS
        if enable_sms and SEND_SMS_AVAILABLE:
            try:
                sms_sids = send_earthquake_alert_sms(earthquake_data, alert_level, sms_to)
                if sms_sids:
                    result['sms_sent'] = True
                    result['sms_sids'] = sms_sids
                    print(f"✅ Alert gempa SMS berhasil dikirim: {len(sms_sids)} pesan")
                else:
                    result['errors'].append("Gagal mengirim alert gempa SMS")
            except Exception as e:
                result['errors'].append(f"Error SMS: {e}")
        
        # Tentukan success
        result['success'] = result['whatsapp_sent'] or result['sms_sent']
        
        return result
        
    except Exception as e:
        result['errors'].append(f"Error umum: {e}")
        return result

def test_earthquake_notification():
    """Test function untuk notifikasi gempa"""
    print("🔍 Testing Earthquake Notification...")
    
    # Data gempa dummy untuk testing
    dummy_earthquake = {
        'datetime_str': '2024-01-15 14:30:25',
        'magnitude': 6.2,
        'kedalaman': '10 km',
        'wilayah': 'Laut Banda, Maluku',
        'coordinates': '4.5 LS, 129.2 BT',
        'potensi_tsunami': 'Tidak berpotensi tsunami',
        'dirasakan': 'Dirasakan di Ambon, Tual'
    }
    
    print("\n1. Testing alert gempa biasa...")
    result = send_earthquake_alert(
        dummy_earthquake, 
        alert_level="EARTHQUAKE",
        enable_whatsapp=True,
        enable_sms=True
    )
    print(f"   Success: {result['success']}")
    print(f"   WhatsApp: {result['whatsapp_sent']}")
    print(f"   SMS: {result['sms_sent']}")
    
    print("\n2. Testing alert tsunami...")
    dummy_tsunami = dummy_earthquake.copy()
    dummy_tsunami['magnitude'] = 7.5
    dummy_tsunami['potensi_tsunami'] = 'Berpotensi tsunami'
    
    result = send_earthquake_alert(
        dummy_tsunami, 
        alert_level="TSUNAMI",
        enable_whatsapp=True,
        enable_sms=True
    )
    print(f"   Success: {result['success']}")
    print(f"   WhatsApp: {result['whatsapp_sent']}")
    print(f"   SMS: {result['sms_sent']}")
    
    print("\n✅ Test Earthquake Notification selesai!")

if __name__ == "__main__":
    test_earthquake_notification()
