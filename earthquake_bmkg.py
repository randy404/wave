#!/usr/bin/env python3
"""
Modul untuk mengambil data gempa dari API BMKG
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

class BMKGEarthquakeAPI:
    """Class untuk mengambil data gempa dari API BMKG"""
    
    def __init__(self):
        self.base_url = "https://data.bmkg.go.id/DataMKG/TEWS"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_earthquake_data(self) -> Optional[Dict]:
        """
        Ambil data gempa terbaru dari BMKG
        
        Returns:
            Dict: Data gempa terbaru atau None jika gagal
        """
        try:
            # URL untuk data gempa terbaru
            url = f"{self.base_url}/autogempa.json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Infogempa' in data and 'gempa' in data['Infogempa']:
                return data['Infogempa']['gempa']
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error mengambil data gempa: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return None
        except Exception as e:
            print(f"Error tidak terduga: {e}")
            return None
    
    def get_earthquake_list(self, limit: int = 10) -> List[Dict]:
        """
        Ambil daftar gempa terbaru dari BMKG
        
        Args:
            limit: Jumlah gempa yang diambil (default: 10)
            
        Returns:
            List[Dict]: Daftar gempa terbaru
        """
        try:
            # URL untuk daftar gempa
            url = f"{self.base_url}/gempaterkini.json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Infogempa' in data and 'gempa' in data['Infogempa']:
                earthquakes = data['Infogempa']['gempa']
                return earthquakes[:limit] if len(earthquakes) > limit else earthquakes
            
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"Error mengambil daftar gempa: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return []
        except Exception as e:
            print(f"Error tidak terduga: {e}")
            return []
    
    def parse_earthquake_data(self, earthquake_data: Dict) -> Dict:
        """
        Parse data gempa dari BMKG ke format yang lebih mudah digunakan
        
        Args:
            earthquake_data: Data gempa mentah dari BMKG
            
        Returns:
            Dict: Data gempa yang sudah di-parse
        """
        try:
            # Parse tanggal dan waktu
            tanggal = earthquake_data.get('Tanggal', '')
            jam = earthquake_data.get('Jam', '')
            
            # Gabungkan tanggal dan jam
            datetime_str = f"{tanggal} {jam}"
            try:
                parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                parsed_datetime = datetime.now()
            
            # Parse koordinat
            coordinates = earthquake_data.get('Coordinates', '')
            lat, lon = self._parse_coordinates(coordinates)
            
            # Parse magnitude
            magnitude = float(earthquake_data.get('Magnitude', 0))
            
            # Parse kedalaman
            kedalaman = earthquake_data.get('Kedalaman', '')
            
            # Parse lokasi
            wilayah = earthquake_data.get('Wilayah', '')
            
            # Parse potensi tsunami
            potensi_tsunami = earthquake_data.get('Potensi', '')
            
            # Parse dirasakan
            dirasakan = earthquake_data.get('Dirasakan', '')
            
            return {
                'datetime': parsed_datetime,
                'datetime_str': datetime_str,
                'magnitude': magnitude,
                'kedalaman': kedalaman,
                'latitude': lat,
                'longitude': lon,
                'wilayah': wilayah,
                'potensi_tsunami': potensi_tsunami,
                'dirasakan': dirasakan,
                'coordinates': coordinates,
                'raw_data': earthquake_data
            }
            
        except Exception as e:
            print(f"Error parsing data gempa: {e}")
            return {}
    
    def _parse_coordinates(self, coordinates: str) -> tuple:
        """
        Parse koordinat dari string BMKG
        
        Args:
            coordinates: String koordinat dari BMKG
            
        Returns:
            tuple: (latitude, longitude)
        """
        try:
            # Format: "1.23 LS, 123.45 BT"
            coords = coordinates.replace('LS', '').replace('BT', '').replace('LU', '').replace('BB', '')
            parts = coords.split(',')
            
            if len(parts) >= 2:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                
                # Konversi ke format standar (LS = negatif, BB = negatif)
                if 'LS' in coordinates:
                    lat = -lat
                if 'BB' in coordinates:
                    lon = -lon
                
                return lat, lon
            
            return 0.0, 0.0
            
        except Exception as e:
            print(f"Error parsing koordinat: {e}")
            return 0.0, 0.0
    
    def check_earthquake_alert(self, magnitude_threshold: float = 5.0, 
                             tsunami_threshold: float = 6.0) -> Dict:
        """
        Cek apakah ada gempa yang perlu di-alert
        
        Args:
            magnitude_threshold: Threshold magnitude untuk alert (default: 5.0)
            tsunami_threshold: Threshold magnitude untuk potensi tsunami (default: 6.0)
            
        Returns:
            Dict: Status alert dan data gempa
        """
        earthquake_data = self.get_earthquake_data()
        
        if not earthquake_data:
            return {
                'alert': False,
                'message': 'Tidak ada data gempa terbaru',
                'earthquake': None
            }
        
        parsed_data = self.parse_earthquake_data(earthquake_data)
        
        if not parsed_data:
            return {
                'alert': False,
                'message': 'Gagal parsing data gempa',
                'earthquake': None
            }
        
        magnitude = parsed_data.get('magnitude', 0)
        potensi_tsunami = parsed_data.get('potensi_tsunami', '')
        
        # Cek alert berdasarkan magnitude
        if magnitude >= tsunami_threshold:
            alert_level = 'TSUNAMI'
            message = f"🚨 ALERT TSUNAMI! Gempa M{magnitude} di {parsed_data.get('wilayah', '')}"
        elif magnitude >= magnitude_threshold:
            alert_level = 'EARTHQUAKE'
            message = f"⚠️ ALERT GEMPA! Gempa M{magnitude} di {parsed_data.get('wilayah', '')}"
        else:
            alert_level = 'NONE'
            message = f"ℹ️ Gempa M{magnitude} di {parsed_data.get('wilayah', '')} (tidak perlu alert)"
        
        return {
            'alert': magnitude >= magnitude_threshold,
            'alert_level': alert_level,
            'message': message,
            'earthquake': parsed_data,
            'magnitude': magnitude,
            'potensi_tsunami': potensi_tsunami
        }
    
    def get_earthquake_history(self, hours: int = 24) -> List[Dict]:
        """
        Ambil riwayat gempa dalam beberapa jam terakhir
        
        Args:
            hours: Jumlah jam ke belakang (default: 24)
            
        Returns:
            List[Dict]: Riwayat gempa
        """
        try:
            earthquakes = self.get_earthquake_list(limit=50)
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_earthquakes = []
            for eq in earthquakes:
                parsed_data = self.parse_earthquake_data(eq)
                if parsed_data and parsed_data.get('datetime', datetime.min) >= cutoff_time:
                    recent_earthquakes.append(parsed_data)
            
            return recent_earthquakes
            
        except Exception as e:
            print(f"Error mengambil riwayat gempa: {e}")
            return []

def test_bmkg_api():
    """Test function untuk API BMKG"""
    print("🔍 Testing BMKG Earthquake API...")
    
    api = BMKGEarthquakeAPI()
    
    # Test 1: Ambil data gempa terbaru
    print("\n1. Mengambil data gempa terbaru...")
    earthquake_data = api.get_earthquake_data()
    if earthquake_data:
        print("✅ Data gempa terbaru berhasil diambil")
        parsed_data = api.parse_earthquake_data(earthquake_data)
        print(f"   Magnitude: {parsed_data.get('magnitude', 'N/A')}")
        print(f"   Wilayah: {parsed_data.get('wilayah', 'N/A')}")
        print(f"   Waktu: {parsed_data.get('datetime_str', 'N/A')}")
    else:
        print("❌ Gagal mengambil data gempa terbaru")
    
    # Test 2: Cek alert
    print("\n2. Mengecek alert gempa...")
    alert_result = api.check_earthquake_alert(magnitude_threshold=4.0)
    print(f"   Alert: {alert_result['alert']}")
    print(f"   Message: {alert_result['message']}")
    
    # Test 3: Ambil daftar gempa
    print("\n3. Mengambil daftar gempa terbaru...")
    earthquake_list = api.get_earthquake_list(limit=5)
    print(f"   Jumlah gempa: {len(earthquake_list)}")
    
    # Test 4: Riwayat gempa
    print("\n4. Mengambil riwayat gempa 24 jam...")
    history = api.get_earthquake_history(hours=24)
    print(f"   Jumlah gempa 24 jam: {len(history)}")
    
    print("\n✅ Test BMKG API selesai!")

if __name__ == "__main__":
    test_bmkg_api()
