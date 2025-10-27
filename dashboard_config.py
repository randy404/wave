# dashboard_config.py - Persistent Configuration untuk Dashboard
# Menyimpan dan memuat konfigurasi dashboard secara otomatis

import json
import os
from typing import Dict, Any

CONFIG_FILE = "dashboard_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "csv_path": "deteksi_ombak.csv",
    "sample_every_sec": 2,
    "video_source_type": "RTSP/HTTP Stream",
    "video_file": "",
    "rtsp_url": "",
    "resize_width": 960,
    "camera_location": "",
    "garis_extreme_y": 180,
    "garis_sangat_tinggi_y": 210,
    "garis_tinggi_y": 230,
    "garis_sedang_y": 250,
    "garis_rendah_y": 280,
    "line_thickness": 1,
    "peak_thickness": 2,
    "font_scale": 0.7,
    "font_thickness": 2,
    "enable_wa": False,
    "wa_cooldown_sec": 300,
    "enable_sms": False,
    "sms_cooldown_sec": 300,
    "extreme_threshold": 12,
    "alert_cooldown_min": 30,
    "enable_tsunami_alert": False,
    "wa_to_override": "",
    "sms_to_override": "",
    "tsunami_wa_to_override": "",
    # Earthquake monitoring configuration
    "enable_earthquake_monitoring": False,
    "magnitude_threshold": 5.0,
    "tsunami_threshold": 6.0,
    "earthquake_check_interval": 300,
    "enable_earthquake_wa": True,
    "enable_earthquake_sms": True
}

def load_config() -> Dict[str, Any]:
    """Load konfigurasi dari file JSON."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge dengan default config untuk memastikan semua key ada
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
        else:
            # Jika file tidak ada, buat dengan default config
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> bool:
    """Simpan konfigurasi ke file JSON."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def update_config(key: str, value: Any) -> bool:
    """Update satu nilai konfigurasi."""
    try:
        config = load_config()
        config[key] = value
        return save_config(config)
    except Exception as e:
        print(f"Error updating config: {e}")
        return False

def get_config_value(key: str, default: Any = None) -> Any:
    """Ambil satu nilai konfigurasi."""
    try:
        config = load_config()
        return config.get(key, default)
    except Exception as e:
        print(f"Error getting config value: {e}")
        return default

def reset_config() -> bool:
    """Reset konfigurasi ke default."""
    try:
        return save_config(DEFAULT_CONFIG)
    except Exception as e:
        print(f"Error resetting config: {e}")
        return False

def export_config() -> str:
    """Export konfigurasi sebagai string JSON."""
    try:
        config = load_config()
        return json.dumps(config, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error exporting config: {e}")
        return "{}"

def import_config(config_json: str) -> bool:
    """Import konfigurasi dari string JSON."""
    try:
        config = json.loads(config_json)
        # Validasi dan merge dengan default
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return save_config(merged_config)
    except Exception as e:
        print(f"Error importing config: {e}")
        return False

if __name__ == "__main__":
    # Test functions
    print("Testing dashboard config...")
    
    # Test load
    config = load_config()
    print(f"Loaded config: {len(config)} keys")
    
    # Test update
    update_config("test_key", "test_value")
    value = get_config_value("test_key")
    print(f"Updated value: {value}")
    
    # Test export
    exported = export_config()
    print(f"Exported config length: {len(exported)} chars")
    
    print("Config test completed!")
