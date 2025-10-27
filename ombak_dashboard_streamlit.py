# ombak_dashboard_streamlit.py
# Streamlit dashboard lengkap:
# - Live RTSP + deteksi (logika main.py)
# - WhatsApp Alert + Tombol "Kirim Tes WA"
# - SMS Alert + Tombol "Kirim Tes SMS"
# - WhatsApp Tsunami Alert: 12 kali EXTREME berturut-turut → Alert Tsunami
# - Tab "📈 Log & Grafik / Laporan (PDF)"
# - Persistent Configuration dengan auto-save

import os, io, time, csv, cv2, numpy as np, pandas as pd, streamlit as st
from datetime import datetime, date
from typing import Tuple
from dashboard_config import load_config, save_config

st.set_page_config(page_title="🌊 Wave Dashboard + Tsunami Alert", layout="wide")
st.title("🌊 Wave Dashboard + Tsunami Alert")

# AUTO-RECONNECTION & ERROR HANDLING UTilities

def smart_rtsp_connect(url, max_retries=1, timeout=5):
    """Smart RTSP connection - minimal and stable"""
    
    # Gunakan protocol yang sudah stabil sebelumnya atau default
    if not hasattr(st.session_state, 'working_rtsp_protocol'):
        # Protocol standard yang lebih stabil
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000"
    else:
        # Gunakan protocol yang sudah terbukti bekerja
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = st.session_state.working_rtsp_protocol
    
    os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
    
    # Coba connect dengan timeout cepat
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            # Success - simpan protocol yang bekerja
            if not hasattr(st.session_state, 'working_rtsp_protocol'):
                st.session_state.working_rtsp_protocol = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000"
            return cap
        cap.release()
    
    return None

def enhanced_error_diagnosis(rtsp_url):
    """Diagnose RTSP errors with specific solutions"""
    diagnosis = {'possible_causes': [], 'solutions': [], 'alternative_urls': []}
    
    try:
        if 'rtsp://' not in rtsp_url:
            diagnosis['solutions'].append('Wrong URL format - must start with rtsp://')
            return diagnosis
        
        if '@' in rtsp_url:
            parts = rtsp_url.split('@')
            if len(parts) == 2:
                auth, remote = parts
                if ':' in auth:
                    username, password = auth.split(':', 1)
                    ip_part = remote.split('/')[0]
                    if ':' in ip_part:
                        ip, port = ip_part.split(':', 1)
                    else:
                        ip, port = ip_part, '8554'
                    
                    if ip.startswith('192.168.1'):
                        diagnosis['alternative_urls'] = [
                            f'rtsp://{username}:{password}@{ip}:554/Streaming/Channels/401',
                            f'rtsp://{username}:{password}@{ip}:554/channel1/main/stream',
                            f'rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0',
                            f'rtsp://{ip}:554/stream1',
                            f'rtsp://{username}:{password}@{ip}:554/unicast/c1/s0/live',
                            f'rtsp://{username}:{password}@{ip}:8554/live/ch1',
                            f'rtsp://{username}:{password}@{ip}:8554/Streaming/Channels/601',
                            f'rtsp://{username}:{password}@{ip}:8554/channel1/stream1',
                            f'rtsp://admin:admin@{ip}:554/h264Preview_01_main',
                            f'rtsp://admin:admin@{ip}:8554/h264Preview_01_main'
                        ]
                        diagnosis['possible_causes'].append('Camera may use port 554 or different channel')
                        diagnosis['possible_causes'].append('Streaming path may differ (not /Streaming/Channels/101)')
                        diagnosis['possible_causes'].append('Username/password may not be admin:admin')
                    
                    diagnosis['solutions'].extend([
                        'Restart the IP Camera to refresh connection',
                        'Check ethernet cable and camera power supply',
                        'Ensure camera and PC are on the same network',
                        f'Test camera web interface in a browser: http://{ip}/',
                        'Try other username/password instead of admin:admin'
                    ])
    except Exception as e:
        diagnosis['solutions'].append(f'Error parsing URL: {e}')
    
    return diagnosis

def show_enhanced_error_message(rtsp_url):
    """Show error message with full diagnosis"""
    diagnosis = enhanced_error_diagnosis(rtsp_url)
    
    st.error(f"❌ RTSP Connection Failed: {rtsp_url}")
    st.markdown("### 🔍 Diagnosis and Troubleshooting")
    
    if diagnosis['possible_causes']:
        st.markdown("**🚨 Possible Causes:**")
        for cause in diagnosis['possible_causes']:
            st.markdown(f"• {cause}")
    
    st.markdown("**✅ Recommended Solutions:**")
    for i, solution in enumerate(diagnosis['solutions'][:5], 1):
        st.markdown(f"{i}. {solution}")
    
    if diagnosis['alternative_urls']:
        st.markdown("**🔧 Alternative RTSP URLs to Try:**")
        for i, alt_url in enumerate(diagnosis['alternative_urls'], 1):
            st.code(f"{i}. {alt_url}")
            if st.button(f"Try URL {i}", key=f"try_url_{i}"):
                st.session_state.rtsp_url_session = alt_url
                st.session_state.running = False
                st.rerun()
    
    st.markdown("**🚀 Actions:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Auto Retry", type="primary", key="btn_auto_retry"):
            st.session_state.running = False
            st.session_state.retry_count = getattr(st.session_state, 'retry_count', 0) + 1
            st.rerun()
    
    with col2:
        if st.button("📝 Edit URL", type="secondary", key="btn_edit_url"):
            st.info("Edit the RTSP URL in the left sidebar")
    
    with col3:
        if st.button("🏥 Health Check", type="secondary", key="btn_health_check"):
            ping_test_rtsp(rtsp_url)

def ping_test_rtsp(rtsp_url):
    """Test basic network connectivity to the camera IP"""
    import subprocess
    ip = rtsp_url.split('@')[1].split(':')[0] if '@' in rtsp_url else ''
    if ip:
        try:
            result = subprocess.run(['ping', '-n', '1', ip], capture_output=True, timeout=5)
            if result.returncode == 0:
                st.success(f"✅ IP {ip} is reachable via network")
            else:
                st.error(f"❌ IP {ip} is not reachable - check network connection")
        except Exception as e:
            st.warning(f"⚠️ Ping test error: {e}")
    else:
        st.error("❌ Cannot extract IP from RTSP URL")

# Connection Monitor Function
def show_connection_monitor():
    """Show connection monitor in the sidebar"""
    with st.sidebar.expander("🔍 Connection Monitor", expanded=False):
        if hasattr(st.session_state, 'running') and st.session_state.running:
            rtsp_url = st.session_state.get('rtsp_url_session', '')
            failures = getattr(st.session_state, 'consecutive_failures', 0)
            last_frame = getattr(st.session_state, 'last_frame_time', 0)
            time_since_last = time.time() - last_frame if last_frame > 0 else 0
            
            st.metric("Consecutive Failures", failures)
            st.metric("Seconds Since Last Frame", f"{time_since_last:.1f}s")
            
            if failures > 0:
                st.warning("⚠️ Connection issues detected")
            
            if st.button("🔄 Force Reconnect", key="btn_force_reconnect"):
                st.session_state.running = False
                st.rerun()

# ===== Optional WhatsApp & SMS =====
SEND_WA_AVAILABLE = False
try:
    from notify_whatsapp import send_whatsapp, send_tsunami_alert_whatsapp
    SEND_WA_AVAILABLE = True
except Exception:
    SEND_WA_AVAILABLE = False

SEND_SMS_AVAILABLE = False
try:
    from notify_sms import send_sms
    SEND_SMS_AVAILABLE = True
except Exception:
    SEND_SMS_AVAILABLE = False


# ===== Load Configuration =====
config = load_config()

# ===== Sidebar (shared) =====
st.sidebar.header("📄 Data")
csv_path = st.sidebar.text_input("CSV log path", value=config.get("csv_path", os.getenv("OMBAK_CSV_PATH","deteksi_ombak.csv")))
sample_every_sec = st.sidebar.number_input("Log write interval (seconds)", 1, 60, config.get("sample_every_sec", 2))

st.sidebar.header("🎥 Video Source (RTSP Only)")
video_source_type = "RTSP/HTTP Stream"

# Inisialisasi variabel
rtsp_url = ""
video_file = ""
available_videos = []

# RTSP/HTTP Stream (satu-satunya mode)
if "rtsp_url_session" not in st.session_state:
    st.session_state.rtsp_url_session = config.get("rtsp_url", os.getenv("RTSP_URL",""))

rtsp_url_input = st.sidebar.text_input("RTSP / HTTP URL", 
    value=st.session_state.rtsp_url_session,
    help="Example: rtsp://admin:admin@192.168.1.3:8554/Streaming/Channels/101")

# Update session state jika ada perubahan
if rtsp_url_input != st.session_state.rtsp_url_session:
    st.session_state.rtsp_url_session = rtsp_url_input

rtsp_url = st.session_state.rtsp_url_session
video_file = ""

resize_width = st.sidebar.number_input("Resize width (px, 0 = original)", 0, 3840, config.get("resize_width", 960), step=10)

st.sidebar.header("📍 Camera Location")
camera_location = st.sidebar.text_input("Camera Location", value=config.get("camera_location", os.getenv("CAMERA_LOCATION", "")),
    help="Example: Kuta Beach, Bali or a full address")

st.sidebar.header("🧭 Threshold Lines (absolute px)")
GARIS_EXTREME_Y        = st.sidebar.number_input("EXTREME (px)",        0, 4000, config.get("garis_extreme_y", 180))
GARIS_SANGAT_TINGGI_Y  = st.sidebar.number_input("4 m (VERY HIGH) (px)",   0, 4000, config.get("garis_sangat_tinggi_y", 210))
GARIS_TINGGI_Y         = st.sidebar.number_input("2.5 m (HIGH) (px)", 0, 4000, config.get("garis_tinggi_y", 230))
GARIS_SEDANG_Y         = st.sidebar.number_input("1.25 m (MEDIUM) (px)",0, 4000, config.get("garis_sedang_y", 250))
GARIS_RENDAH_Y         = st.sidebar.number_input("0.5 m (LOW) (px)", 0, 4000, config.get("garis_rendah_y", 280))

st.sidebar.header("✏️ Overlay")
line_thickness  = st.sidebar.slider("Line thickness", 1, 6, config.get("line_thickness", 1))
peak_thickness  = st.sidebar.slider("Peak line thickness", 1, 6, config.get("peak_thickness", 2))
font_scale      = st.sidebar.slider("Font size", 0.4, 2.0, config.get("font_scale", 0.7), 0.1)
font_thickness  = st.sidebar.slider("Font thickness", 1, 4, config.get("font_thickness", 2))

# ===== WhatsApp Section =====
st.sidebar.header("📣 WhatsApp")
st.sidebar.caption(f"WhatsApp module: {'✅' if SEND_WA_AVAILABLE else '❌'} (requires notify_whatsapp.py + .env)")
enable_wa = st.sidebar.checkbox("Send WhatsApp automatically when status ≥ 2.5 m", value=config.get("enable_wa", False))
wa_cooldown_sec = st.sidebar.number_input("WhatsApp cooldown (seconds)", 30, 3600, config.get("wa_cooldown_sec", 300), step=30)

with st.sidebar.expander("🔔 Send WhatsApp Test", expanded=False):
    wa_to_override = st.text_input("WhatsApp number (optional, whatsapp:+62...)", value=config.get("wa_to_override", os.getenv("WHATSAPP_TO","")), key="wa_to_override")
    wa_test_msg = st.text_area("WhatsApp test message", value="WhatsApp test from wave dashboard ✅", height=80, key="wa_test_msg")
    if st.button("Send WhatsApp Test", key="btn_send_wa_test"):
        if not SEND_WA_AVAILABLE:
            st.error("notify_whatsapp.py not found / credentials not set.")
        else:
            try:
                to_arg = wa_to_override.strip() or None
                sid = send_whatsapp(wa_test_msg, to=to_arg)
                st.success(f"WhatsApp test sent. SID: {sid}")
            except Exception as e:
                st.error(f"Failed to send WhatsApp: {e}")

# ===== SMS Section =====
st.sidebar.header("📱 SMS")
st.sidebar.caption(f"SMS module: {'✅' if SEND_SMS_AVAILABLE else '❌'} (requires notify_sms.py + .env)")
enable_sms = st.sidebar.checkbox("Send SMS automatically when status ≥ 2.5 m", value=config.get("enable_sms", False))
sms_cooldown_sec = st.sidebar.number_input("SMS cooldown (seconds)", 30, 3600, config.get("sms_cooldown_sec", 300), step=30)

with st.sidebar.expander("✉️ Send SMS Test", expanded=False):
    sms_to_override = st.text_input("SMS number (optional, E.164: +62...)", value=config.get("sms_to_override", os.getenv("SMS_TO","")), key="sms_to_override")
    sms_test_msg = st.text_area("SMS test message", value="SMS test from wave dashboard ✅", height=80, key="sms_test_msg")
    if st.button("Send SMS Test", key="btn_send_sms_test"):
        if not SEND_SMS_AVAILABLE:
            st.error("notify_sms.py not found / credentials not set.")
        else:
            try:
                to_arg = sms_to_override.strip() or None
                sids = send_sms(sms_test_msg, to=to_arg)
                st.success(f"SMS test sent. SID(s): {', '.join(sids)}")
            except Exception as e:
                st.error(f"Failed to send SMS: {e}")

# ===== WHATSAPP TSUNAMI ALERT Section =====
st.sidebar.header("🚨 WhatsApp Tsunami Alert")
st.sidebar.caption(f"WhatsApp module: {'✅' if SEND_WA_AVAILABLE else '❌'} (requires notify_whatsapp.py + .env)")

# Tsunami Alert Settings
extreme_threshold = st.sidebar.number_input("EXTREME threshold for alert", 5, 50, config.get("extreme_threshold", 12), 
    help="Number of consecutive EXTREME detections to send tsunami alert")
alert_cooldown_min = st.sidebar.number_input("Alert cooldown (minutes)", 5, 120, config.get("alert_cooldown_min", 30),
    help="Cooldown between tsunami alerts (minutes)")

enable_tsunami_alert = st.sidebar.checkbox("Send Tsunami Alert automatically when 12x EXTREME", value=config.get("enable_tsunami_alert", False))

with st.sidebar.expander("🚨 Send WhatsApp Tsunami Alert (Test)", expanded=False):
    tsunami_wa_to_override = st.text_input("WhatsApp number (optional, whatsapp:+62...)", value=config.get("tsunami_wa_to_override", os.getenv("WHATSAPP_TO","")), key="tsunami_wa_to_override")
    tsunami_test_msg = st.text_area("Tsunami Alert test message", 
        value="🚨 *TSUNAMI ALERT TEST!* 🚨\n\nWave detection system sending a test message.\n\n*Time:* " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n⚠️ *This is a test, not a real warning!* ⚠️", 
        height=120, key="tsunami_test_msg")
    if st.button("Send Tsunami Alert Test", key="btn_send_tsunami_test"):
        if not SEND_WA_AVAILABLE:
            st.error("notify_whatsapp.py not found / credentials not set.")
        else:
            try:
                to_arg = tsunami_wa_to_override.strip() or None
                sids = send_whatsapp(tsunami_test_msg, to=to_arg)
                st.success(f"Tsunami Alert test sent. SID(s): {', '.join(sids)}")
            except Exception as e:
                st.error(f"Failed to send Tsunami Alert: {e}")

# ===== Auto-Save Configuration =====
def auto_save_config():
    """Automatically save configuration."""
    try:
        current_config = {
            "csv_path": csv_path,
            "sample_every_sec": sample_every_sec,
            "rtsp_url": rtsp_url,
            "resize_width": resize_width,
            "camera_location": camera_location,
            "garis_extreme_y": GARIS_EXTREME_Y,
            "garis_sangat_tinggi_y": GARIS_SANGAT_TINGGI_Y,
            "garis_tinggi_y": GARIS_TINGGI_Y,
            "garis_sedang_y": GARIS_SEDANG_Y,
            "garis_rendah_y": GARIS_RENDAH_Y,
            "line_thickness": line_thickness,
            "peak_thickness": peak_thickness,
            "font_scale": font_scale,
            "font_thickness": font_thickness,
            "enable_wa": enable_wa,
            "wa_cooldown_sec": wa_cooldown_sec,
            "enable_sms": enable_sms,
            "sms_cooldown_sec": sms_cooldown_sec,
            "extreme_threshold": extreme_threshold,
            "alert_cooldown_min": alert_cooldown_min,
            "enable_tsunami_alert": enable_tsunami_alert,
            "wa_to_override": wa_to_override,
            "sms_to_override": sms_to_override,
            "tsunami_wa_to_override": tsunami_wa_to_override
        }
        save_config(current_config)
        return True
    except Exception as e:
        print(f"Error auto-saving config: {e}")
        return False

# ===== Configuration Management =====
st.sidebar.header("⚙️ Configuration")
with st.sidebar.expander("💾 Manage Configuration", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Configuration", key="btn_save_config"):
            if auto_save_config():
                st.success("✅ Configuration saved!")
            else:
                st.error("❌ Failed to save configuration")
    
    with col2:
        if st.button("🔄 Reset to Default", key="btn_reset_config"):
            from dashboard_config import reset_config
            if reset_config():
                st.success("✅ Configuration reset!")
                st.rerun()
            else:
                st.error("❌ Failed to reset configuration")
    
    # Export/Import
    st.subheader("📤 Export/Import")
    if st.button("📤 Export Configuration", key="btn_export_config"):
        from dashboard_config import export_config
        config_json = export_config()
        st.download_button(
            "Download Configuration",
            data=config_json,
            file_name="dashboard_config.json",
            mime="application/json",
            key="btn_download_config_file"
        )
    
    uploaded_file = st.file_uploader("📥 Import Configuration", type=['json'])
    if uploaded_file is not None:
        try:
            config_data = uploaded_file.read().decode('utf-8')
            from dashboard_config import import_config
            if import_config(config_data):
                st.success("✅ Configuration imported!")
                st.rerun()
            else:
                st.error("❌ Failed to import configuration")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Performance Control
st.sidebar.markdown("---")
verbose_debug = st.sidebar.checkbox("🔧 Verbose Debug Mode", value=False, help="Show detailed connection info")
detection_mode = st.sidebar.selectbox("Detection Performance", ["Normal (Every Frame)", "Fast (Every 2nd Frame)", "Skip Detection"], index=0)

if detection_mode == "Skip Detection":
    st.sidebar.warning("⚠️ Detection disabled - Stream only")
elif detection_mode == "Fast (Every 2nd Frame)":
    st.sidebar.info("🚀 Fast mode: 50% CPU reduction")
else:
    st.sidebar.info("⚡ Full detection: All frames processed")

if not verbose_debug:
    st.sidebar.info("🔇 Quiet mode: Minimal notifications")

# Show Connection Monitor
show_connection_monitor()

# ===== Tabs =====
TAB_LIVE, TAB_LOG, TAB_EARTHQUAKE = st.tabs(["🎥 Live RTSP + Detection + WhatsApp Tsunami Alert", "📈 Logs & Charts / Report", "🌍 BMKG Earthquake Monitoring"])

# ===== Halaman Monitoring Gempa BMKG =====
with TAB_EARTHQUAKE:
    st.subheader("🌍 BMKG Earthquake Monitoring")
    st.caption("Real-time earthquake monitoring from BMKG (Indonesian Agency)")
    
    # Import modul gempa
    try:
        from earthquake_bmkg import BMKGEarthquakeAPI
        from notify_earthquake import send_earthquake_alert
        BMKG_AVAILABLE = True
    except ImportError as e:
        st.error(f"❌ Earthquake module not available: {e}")
        BMKG_AVAILABLE = False
    
    if BMKG_AVAILABLE:
        # ===== Earthquake Monitoring Configuration =====
        st.header("⚙️ Earthquake Monitoring Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_earthquake_monitoring = st.checkbox(
                "🔍 Enable Earthquake Monitoring", 
                value=config.get("enable_earthquake_monitoring", False),
                help="Enable automatic earthquake monitoring",
                key="enable_earthquake_monitoring"
            )
            
            magnitude_threshold = st.number_input(
                "📊 Magnitude Alert Threshold", 
                min_value=1.0, 
                max_value=10.0, 
                value=config.get("magnitude_threshold", 5.0),
                step=0.1,
                help="Minimum magnitude to trigger alert",
                key="magnitude_threshold"
            )
            
            tsunami_threshold = st.number_input(
                "🌊 Tsunami Alert Threshold", 
                min_value=1.0, 
                max_value=10.0, 
                value=config.get("tsunami_threshold", 6.0),
                step=0.1,
                help="Minimum magnitude to trigger tsunami alert",
                key="tsunami_threshold"
            )
        
        with col2:
            earthquake_check_interval = st.number_input(
                "⏰ Earthquake Check Interval (seconds)", 
                min_value=30, 
                max_value=3600, 
                value=config.get("earthquake_check_interval", 300),
                step=30,
                help="Interval to fetch latest earthquakes",
                key="earthquake_check_interval"
            )
            
            enable_earthquake_wa = st.checkbox(
                "📱 Send Alert via WhatsApp", 
                value=config.get("enable_earthquake_wa", True),
                help="Send earthquake alert via WhatsApp",
                key="enable_earthquake_wa"
            )
            
            enable_earthquake_sms = st.checkbox(
                "📱 Send Alert via SMS", 
                value=config.get("enable_earthquake_sms", True),
                help="Send earthquake alert via SMS",
                key="enable_earthquake_sms"
            )
        
        # ===== Monitoring Status =====
        st.header("📊 Monitoring Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if enable_earthquake_monitoring:
                st.success("🟢 Monitoring Active")
            else:
                st.warning("🟡 Monitoring Inactive")
        
        with col2:
            st.metric("Threshold Alert", f"M{magnitude_threshold}")
        
        with col3:
            st.metric("Threshold Tsunami", f"M{tsunami_threshold}")
        
        # ===== Latest Earthquake Data =====
        st.header("🌍 Latest Earthquake Data")
        
        if st.button("🔄 Refresh Earthquake Data", type="primary", key="btn_refresh_earthquake"):
            with st.spinner("Fetching latest earthquake data..."):
                try:
                    api = BMKGEarthquakeAPI()
                    earthquake_data = api.get_earthquake_data()
                    
                    if earthquake_data:
                        parsed_data = api.parse_earthquake_data(earthquake_data)
                        
                        # Show earthquake data
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Magnitude", f"M{parsed_data.get('magnitude', 'N/A')}")
                            st.metric("Depth", parsed_data.get('kedalaman', 'N/A'))
                            st.metric("Time", parsed_data.get('datetime_str', 'N/A'))
                        
                        with col2:
                            st.metric("Location", parsed_data.get('wilayah', 'N/A'))
                            st.metric("Koordinat", parsed_data.get('coordinates', 'N/A'))
                            st.metric("Tsunami Potential", parsed_data.get('potensi_tsunami', 'N/A'))
                        
                        # Show full details
                        with st.expander("📋 Full Details of Latest Earthquake", expanded=True):
                            st.json(parsed_data)
                        
                        # Cek alert
                        alert_result = api.check_earthquake_alert(
                            magnitude_threshold=magnitude_threshold,
                            tsunami_threshold=tsunami_threshold
                        )
                        
                        if alert_result['alert']:
                            st.warning(f"⚠️ {alert_result['message']}")
                            
                            # Manual send alert button
                            if st.button("📤 Send Alert Manually", key="btn_send_alert_manually"):
                                with st.spinner("Sending alert..."):
                                    result = send_earthquake_alert(
                                        parsed_data,
                                        alert_level=alert_result['alert_level'],
                                        enable_whatsapp=enable_earthquake_wa,
                                        enable_sms=enable_earthquake_sms
                                    )
                                    
                                    if result['success']:
                                        st.success("✅ Alert sent!")
                                        if result['whatsapp_sent']:
                                            st.info(f"📱 WhatsApp: {len(result['whatsapp_sids'])} messages")
                                        if result['sms_sent']:
                                            st.info(f"📱 SMS: {len(result['sms_sids'])} messages")
                                    else:
                                        st.error("❌ Failed to send alert")
                                        for error in result['errors']:
                                            st.error(f"   - {error}")
                        else:
                            st.info(f"ℹ️ {alert_result['message']}")
                    
                    else:
                        st.error("❌ Gagal mengambil data gempa")
                        
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        # ===== Earthquake History =====
        st.header("📈 Earthquake History")
        
        col1, col2 = st.columns(2)
        
        with col1:
            history_hours = st.selectbox(
                "⏰ History Period", 
                [6, 12, 24, 48, 72], 
                index=2,
                help="Earthquake history period in hours",
                key="earthquake_history_hours"
            )
        
        with col2:
            if st.button("📊 Show History", key="btn_show_earthquake_history"):
                with st.spinner(f"Fetching earthquake history for {history_hours} hours..."):
                    try:
                        api = BMKGEarthquakeAPI()
                        history = api.get_earthquake_history(hours=history_hours)
                        
                        if history:
                            st.success(f"✅ Found {len(history)} earthquakes in the last {history_hours} hours")
                            
                            # Show history table
                            import pandas as pd
                            
                            df_data = []
                            for eq in history:
                                df_data.append({
                                    'Time': eq.get('datetime_str', 'N/A'),
                                    'Magnitude': eq.get('magnitude', 'N/A'),
                                    'Depth': eq.get('kedalaman', 'N/A'),
                                    'Location': eq.get('wilayah', 'N/A'),
                                    'Tsunami Potential': eq.get('potensi_tsunami', 'N/A')
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(df, use_container_width=True)
                            
                            # Magnitude chart
                            if len(history) > 1:
                                st.subheader("📊 Grafik Magnitude vs Waktu")
                                import plotly.express as px
                                
                                fig = px.line(df, x='Time', y='Magnitude', title=f'Earthquake Magnitude in the Last {history_hours} Hours', markers=True)
                                fig.add_hline(y=magnitude_threshold, line_dash="dash", line_color="red", 
                                            annotation_text=f"Alert Threshold (M{magnitude_threshold})")
                                fig.add_hline(y=tsunami_threshold, line_dash="dash", line_color="orange", 
                                            annotation_text=f"Tsunami Threshold (M{tsunami_threshold})")
                                
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info(f"ℹ️ No earthquakes in the last {history_hours} hours")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        
        # ===== Test Notifications =====
        st.header("🧪 Test Earthquake Notification")
        
        with st.expander("📤 Send Earthquake Alert (Test)", expanded=False):
            st.caption("Send a test earthquake notification with dummy data")
            
            col1, col2 = st.columns(2)
            
            with col1:
                test_magnitude = st.number_input(
                    "Magnitude Test", 
                    min_value=1.0, 
                    max_value=10.0, 
                    value=6.5,
                    step=0.1,
                    key="earthquake_test_magnitude"
                )
                
                test_location = st.text_input("Test Location", value="Banda Sea, Maluku", key="earthquake_test_location")
            
            with col2:
                test_alert_level = st.selectbox(
                    "Level Alert Test", 
                    ["EARTHQUAKE", "TSUNAMI"],
                    key="earthquake_test_alert_level"
                )
                
                test_potensi = st.selectbox("Tsunami Potential (Test)", ["No tsunami potential", "Tsunami potential"], key="earthquake_test_potensi") 
            
            if st.button("📤 Send Test Alert", key="btn_send_earthquake_test"):
                # Dummy earthquake data for testing
                dummy_earthquake = {
                    'datetime_str': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'magnitude': test_magnitude,
                    'kedalaman': '15 km',
                    'wilayah': test_location,
                    'coordinates': '4.5 LS, 129.2 BT',
                    'potensi_tsunami': test_potensi,
                    'dirasakan': 'Felt in surrounding area'
                }
                
                with st.spinner("Sending test alert..."):
                    result = send_earthquake_alert(
                        dummy_earthquake,
                        alert_level=test_alert_level,
                        enable_whatsapp=enable_earthquake_wa,
                        enable_sms=enable_earthquake_sms
                    )
                    
                    if result['success']:
                        st.success("✅ Test alert sent!")
                        if result['whatsapp_sent']:
                            st.info(f"📱 WhatsApp: {len(result['whatsapp_sids'])} messages")
                        if result['sms_sent']:
                            st.info(f"📱 SMS: {len(result['sms_sids'])} messages")
                    else:
                        st.error("❌ Failed to send test alert")
                        for error in result['errors']:
                            st.error(f"   - {error}")

# ===== Helpers Deteksi =====
def classify_main_style(peak_y: int, L: dict) -> Tuple[str, tuple]:
    status, warna = "Tenang", (144,238,144)
    if peak_y < L['RENDAH']:        status, warna = "0,5 Meter (Rendah)", (0,255,0)
    if peak_y < L['SEDANG']:        status, warna = "1,25 Meter (Sedang)", (0,255,255)
    if peak_y < L['TINGGI']:        status, warna = "2,5 Meter (Tinggi)", (0,165,255)
    if peak_y < L['SANGAT_TINGGI']: status, warna = "4 Meter (SANGAT TINGGI)", (0,0,255)
    if peak_y < L['EXTREME']:       status, warna = "> 4 Meter (EXTREME)", (0,0,139)
    return status, warna

def detect_peak_y_hough(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7,7), 0)
    edges = cv2.Canny(blur, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 80, minLineLength=90, maxLineGap=30)
    h = frame_bgr.shape[0]; peak_y = h
    if lines is not None:
        for l in lines:
            x1,y1,x2,y2 = l[0]
            peak_y = min(peak_y, y1, y2)
            cv2.line(frame_bgr, (x1,y1),(x2,y2),(0,0,255),2)
    return int(peak_y), lines

def draw_overlay(frame, L, peak_y, status, color, extreme_count=0, alert_sent=False):
    h,w = frame.shape[:2]
    cv2.line(frame,(0,L['EXTREME']),(w,L['EXTREME']),(0,0,139),line_thickness)
    cv2.line(frame,(0,L['SANGAT_TINGGI']),(w,L['SANGAT_TINGGI']),(0,0,255),line_thickness)
    cv2.line(frame,(0,L['TINGGI']),(w,L['TINGGI']),(0,165,255),line_thickness)
    cv2.line(frame,(0,L['SEDANG']),(w,L['SEDANG']),(0,255,255),line_thickness)
    # Garis RENDAH (hijau) disembunyikan sesuai permintaan
    cv2.line(frame,(0,peak_y),(w,peak_y),(255,255,255),peak_thickness)
    cv2.putText(frame,f"Peak Y: {peak_y}",(w-180,max(15,peak_y-6)),cv2.FONT_HERSHEY_SIMPLEX,font_scale,(255,255,255),font_thickness)
    
    # Status panel (diperbesar untuk menampung info tambahan)
    x1,y1,x2,y2 = w-300,10,w-10,120
    cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,0),-1)
    cv2.putText(frame,"STATUS GELOMBANG:",(x1+10,y1+25),cv2.FONT_HERSHEY_SIMPLEX,font_scale,(255,255,255),font_thickness)
    cv2.putText(frame,status,(x1+10,y1+55),cv2.FONT_HERSHEY_SIMPLEX,font_scale,color,font_thickness)
    
    # Extreme counter
    cv2.putText(frame,f"EXTREME: {extreme_count}/{extreme_threshold}",(x1+10,y1+80),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),2)
    
    # Alert status
    if alert_sent:
        cv2.putText(frame,"ALERT SENT!",(x1+10,y1+100),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),2)
    
    cv2.putText(frame,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),(10,h-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2)

# ===== CSV Helpers (diperbarui untuk extreme count) =====
CSV_FIELDS = [
    "timestamp","tanggal","jam","frame",
    "puncak_ombak_y","status_ombak","jumlah_garis_terdeteksi","extreme_count","alert_sent"
]

def ensure_csv_header(path: str):
    if not os.path.exists(path):
        with open(path,"w",newline="",encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def append_csv(path: str, frame_idx: int, peak_y: int, status: str, num_lines: int, extreme_count: int = 0, alert_sent: bool = False):
    """Tulis baris CSV aman (status bisa mengandung koma)."""
    ensure_csv_header(path)
    ts = datetime.now()
    row = {
        "timestamp": ts.isoformat(),
        "tanggal": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "jam": ts.strftime("%H:%M:%S"),
        "frame": frame_idx,
        "puncak_ombak_y": peak_y,
        "status_ombak": status,
        "jumlah_garis_terdeteksi": num_lines,
        "extreme_count": extreme_count,
        "alert_sent": alert_sent,
    }
    with open(path,"a",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)

# ===== Twilio Helper Functions =====
def check_tsunami_alert_condition(extreme_count: int, last_alert_time: float, cooldown_minutes: int) -> bool:
    """Cek apakah perlu mengirim alert tsunami."""
    # Cek apakah sudah mencapai threshold
    if extreme_count < extreme_threshold:
        return False
    
    # Cek cooldown
    if last_alert_time > 0:
        time_diff = time.time() - last_alert_time
        if time_diff < (cooldown_minutes * 60):
            return False
    
    return True

with TAB_LIVE:
    # Auto-save konfigurasi saat ada perubahan
    auto_save_config()
    
    c1,c2,_ = st.columns([1,1,6])
    with c1: start_btn = st.button("▶️ Start", key="btn_start_stream")
    with c2: stop_btn  = st.button("⏹ Stop", key="btn_stop_stream")
    if "running" not in st.session_state: 
        # Auto-start jika ada RTSP URL yang valid
        has_valid_rtsp = bool(rtsp_url and rtsp_url.strip())
        st.session_state.running = has_valid_rtsp
    
    if start_btn and rtsp_url: 
        st.session_state.running = True
        st.rerun()  # Refresh untuk mulai video
    if stop_btn: st.session_state.running = False

    frame_holder = st.empty(); info_holder = st.empty()
    
    # Tampilkan status auto-start
    if st.session_state.running and rtsp_url:
        st.success(f"🎥 CCTV Stream berjalan otomatis: {rtsp_url}")
    elif st.session_state.running and video_file:
        st.success(f"🎬 Video '{video_file}' berjalan otomatis!")
    elif video_source_type == "RTSP/HTTP Stream" and rtsp_url and not st.session_state.running:
        st.info(f"🔄 Mencoba connecting ke RTSP: {rtsp_url}")
    elif video_source_type == "RTSP/HTTP Stream" and not rtsp_url:
        st.warning("❌ Masukkan RTSP URL untuk auto-start CCTV")
    elif len(available_videos) > 0:
        st.info(f"📝 Video File mode: Pilih '{video_file}' dan klik Start untuk testing.")

    # Initialize session state for tracking
    if "last_log" not in st.session_state: st.session_state.last_log = 0.0
    if "last_wa_alert" not in st.session_state: st.session_state.last_wa_alert = 0.0
    if "last_sms_alert" not in st.session_state: st.session_state.last_sms_alert = 0.0
    if "last_twilio_alert" not in st.session_state: st.session_state.last_twilio_alert = 0.0
    if "frame_idx" not in st.session_state: st.session_state.frame_idx = 0
    if "extreme_count" not in st.session_state: st.session_state.extreme_count = 0
    cap = None
    source_type = ""
    source_name = ""
    
    if st.session_state.running and rtsp_url:
        # Gunakan smart connection dengan auto-retry
        cap = smart_rtsp_connect(rtsp_url, max_retries=3, timeout=10)
        if cap is None:
            # Show enhanced error message dengan diagnosa
            show_enhanced_error_message(rtsp_url)
            st.session_state.running = False
        else:
            source_type = "Stream"
            source_name = rtsp_url
            
            # Initialize connection monitoring dan detection variables
            if not hasattr(st.session_state, 'consecutive_failures'):
                st.session_state.consecutive_failures = 0
            if not hasattr(st.session_state, 'last_frame_time'):
                st.session_state.last_frame_time = time.time()
            if not hasattr(st.session_state, 'last_peak_y'):
                st.session_state.last_peak_y = 500  # Default nilai aman
            if not hasattr(st.session_state, 'last_status'):
                st.session_state.last_status = "Sedang"
            if not hasattr(st.session_state, 'last_color'):
                st.session_state.last_color = (0,255,255)
    
    
    if cap and cap.isOpened():
        if resize_width>0: cap.set(cv2.CAP_PROP_FRAME_WIDTH, resize_width)
        info_holder.success(f"✅ {source_type} berhasil terhubung: {source_name}")
        info_holder.info("Klik Stop untuk menghentikan stream")
        fail = 0
        while st.session_state.running:
            ok, frame = cap.read()
            
            # Stable connection monitoring - hanya reconnect jika benar-benar mati 1 menit
            if not ok or frame is None:
                current_time = time.time()
                
                # Initialize last_successful_frame jika belum ada
                if not hasattr(st.session_state, 'last_successful_frame'):
                    st.session_state.last_successful_frame = current_time
                
                # Update last successful frame time untuk hitung downtime
                minutes_without_frame = (current_time - st.session_state.last_successful_frame) / 60
                
                if rtsp_url:
                    # Hanya reconnect jika sudah tidak ada frame selama 1+ menit
                    if minutes_without_frame >= 1.0:
                        # Hanya show warning sekali per reconnect cycle
                        if not hasattr(st.session_state, 'reconnect_notified'):
                            st.warning(f"🔄 Connection lost for {minutes_without_frame:.1f} minutes. Reconnecting...")
                            st.session_state.reconnect_notified = True
                        
                        cap.release()
                        time.sleep(2)
                        
                        # Try reconnect dengan 1 attempt saja
                        cap = smart_rtsp_connect(rtsp_url, max_retries=1, timeout=3)
                        if cap is not None:
                            st.success("✅ Connection restored!")
                            st.session_state.last_successful_frame = current_time
                            st.session_state.reconnect_notified = False
                            continue
                        else:
                            # Tunggu 30 detik sebelum coba lagi agar tidak spam
                            time.sleep(30)
                            continue
                    else:
                        # Connection masih OK, hanya skip frame ini
                        continue
                
            else:
                # Frame berhasil dibaca - update timestamps
                st.session_state.last_successful_frame = time.time()
                if hasattr(st.session_state, 'reconnect_notified'):
                    delattr(st.session_state, 'reconnect_notified')
                
            fail = 0; st.session_state.frame_idx += 1
            h,w = frame.shape[:2]
            if resize_width>0 and w != resize_width:
                ratio = resize_width / float(w)
                frame = cv2.resize(frame,(resize_width,int(h*ratio)),interpolation=cv2.INTER_AREA)

            L = {'EXTREME':int(GARIS_EXTREME_Y),'SANGAT_TINGGI':int(GARIS_SANGAT_TINGGI_Y),
                 'TINGGI':int(GARIS_TINGGI_Y),'SEDANG':int(GARIS_SEDANG_Y),'RENDAH':int(GARIS_RENDAH_Y)}
            # Smart detection berdasarkan performance mode
            if detection_mode == "Skip Detection":
                # Skip semua detection - hanya stream
                peak_y = h//2  # Setengah layar
                status = "Detection Disabled"
                color = (128, 128, 128)
                lines = None
            elif detection_mode == "Fast (Every 2nd Frame)":
                # Process setiap 2nd frame saja
                if st.session_state.frame_idx % 2 == 0:
                    peak_y,_ = detect_peak_y_hough(frame)
                    status,color = classify_main_style(peak_y, L)
                    # Update dengan hasil terakhir untuk frame yang di-skip
                    st.session_state.last_peak_y = peak_y
                    st.session_state.last_status = status
                    st.session_state.last_color = color
                else:
                    # Gunakan hasil deteksi sebelumnya untuk frame yang di-skip
                    peak_y = st.session_state.last_peak_y
                    status = st.session_state.last_status
                    color = st.session_state.last_color
            else:
                # Full detection - process semua frame
                peak_y,_ = detect_peak_y_hough(frame)
                status,color = classify_main_style(peak_y, L)

            # ===== TWILIO TSUNAMI ALERT LOGIC =====
            alert_sent = False
            
            if "EXTREME" in status:
                st.session_state.extreme_count += 1
                print(f"🚨 EXTREME #{st.session_state.extreme_count} - Puncak Y: {peak_y}")
                
                # Cek apakah perlu kirim tsunami alert
                if (enable_tsunami_alert and SEND_WA_AVAILABLE and 
                    check_tsunami_alert_condition(st.session_state.extreme_count, st.session_state.last_twilio_alert, alert_cooldown_min)):
                    
                    try:
                        sids = send_tsunami_alert_whatsapp(st.session_state.extreme_count, peak_y, st.session_state.frame_idx, location=camera_location)
                        st.session_state.last_twilio_alert = time.time()
                        alert_sent = True
                        st.sidebar.success(f"🚨 TSUNAMI ALERT DIKIRIM! SID(s): {', '.join(sids)}")
                    except Exception as e:
                        st.sidebar.error(f"Tsunami Alert error: {e}")
            else:
                # Reset counter jika bukan extreme
                if st.session_state.extreme_count > 0:
                    print(f"✅ Status kembali normal. Extreme count direset dari {st.session_state.extreme_count}")
                st.session_state.extreme_count = 0

            draw_overlay(frame,L,peak_y,status,color,st.session_state.extreme_count,alert_sent)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_holder.image(rgb, channels="RGB", width="stretch")

            now = time.time()
            if now - st.session_state.last_log >= sample_every_sec:
                    append_csv(csv_path, st.session_state.frame_idx, peak_y, status, 0, 
                             st.session_state.extreme_count, alert_sent)

                    # ===== WA alert =====
                    if enable_wa and SEND_WA_AVAILABLE and status in ["2,5 Meter (Tinggi)","4 Meter (SANGAT TINGGI)","> 4 Meter (EXTREME)"]:
                        if now - st.session_state.last_wa_alert >= wa_cooldown_sec:
                            try:
                                send_whatsapp(
                                    "⚠️ *PERINGATAN OMBAK TINGGI*\\n\\n"
                                    f"Status: *{status}*\\nWaktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                                    f"Frame: {st.session_state.frame_idx}\\nPuncak Ombak (Y): {peak_y}\\n"
                                    f"Extreme Count: {st.session_state.extreme_count}"
                                )
                                st.session_state.last_wa_alert = now
                            except Exception as e:
                                st.sidebar.error(f"WA error: {e}")

                    # ===== SMS alert =====
                    if enable_sms and SEND_SMS_AVAILABLE and status in ["2,5 Meter (Tinggi)","4 Meter (SANGAT TINGGI)","> 4 Meter (EXTREME)"]:
                        if now - st.session_state.last_sms_alert >= sms_cooldown_sec:
                            try:
                                msg = (
                                    "PERINGATAN OMBAK TINGGI!\n"
                                    f"Status: {status}\n"
                                    f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    f"Frame: {st.session_state.frame_idx}\n"
                                    f"PeakY: {peak_y}\n"
                                    f"Extreme Count: {st.session_state.extreme_count}"
                                )
                                send_sms(msg)
                                st.session_state.last_sms_alert = now
                            except Exception as e:
                                st.sidebar.error(f"SMS error: {e}")

            st.session_state.last_log = now
            time.sleep(0.005)
        cap.release()
        info_holder.success("Stream dihentikan.")
    else:
        if st.session_state.running == False:
            if rtsp_url:
                st.info("📝 RTSP stream siap untuk dimulai. Klik 'Start' untuk mulai.")
            else:
                st.info("📝 Masukkan RTSP URL di sidebar untuk memulai.")
        else:
            st.info("⏸️ Stream sedang loading...")


with TAB_LOG:
    import plotly.express as px
    st.subheader("📈 Log & Grafik")

    def load_df(path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            st.warning("File CSV belum ada. Mulai Live deteksi untuk menghasilkan log.")
            return pd.DataFrame()
        try:
            df = pd.read_csv(path)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df['waktu'] = df['timestamp']
            elif {'tanggal','jam'}.issubset(df.columns):
                df['waktu'] = pd.to_datetime(df['tanggal'].astype(str)+" "+df['jam'].astype(str), errors='coerce')
            else:
                df['waktu'] = pd.NaT
            return df
        except Exception as e:
            st.error(f"Gagal baca CSV: {e}")
            return pd.DataFrame()

    df = load_df(csv_path)
    if not df.empty and 'waktu' in df.columns:
        min_d = df['waktu'].min().date() if pd.notna(df['waktu'].min()) else date.today()
        max_d = df['waktu'].max().date() if pd.notna(df['waktu'].max()) else date.today()

        # ⛑️ Perbaikan: date_input aman baik satu tanggal atau rentang
        _sel = st.date_input("Rentang tanggal", value=(min_d, max_d))
        if isinstance(_sel, (list, tuple)) and len(_sel) == 2:
            d1, d2 = _sel
        else:
            d1 = d2 = _sel

        mask = (df['waktu'] >= pd.to_datetime(d1)) & (df['waktu'] <= pd.to_datetime(d2) + pd.Timedelta(days=1))
        dff = df.loc[mask].copy()
    else:
        dff = df.copy()

    colA, colB, colC, colD, colE = st.columns(5)
    if not dff.empty:
        latest = dff.sort_values('waktu').tail(1).iloc[0]
        colA.metric("Status Terbaru", str(latest.get('status_ombak','—')))
        colB.metric("Frame Terbaru", int(latest.get('frame',0)) if pd.notna(latest.get('frame',None)) else 0)
        colC.metric("Peak Y Terbaru", int(latest.get('puncak_ombak_y',0)) if pd.notna(latest.get('puncak_ombak_y',None)) else 0)
        colD.metric("Extreme Count", int(latest.get('extreme_count',0)) if pd.notna(latest.get('extreme_count',None)) else 0)
        colE.metric("Jumlah Data", len(dff))
    else:
        st.info("Belum ada data untuk ditampilkan.")

    st.divider()
    if not dff.empty:
        if 'waktu' in dff.columns and 'puncak_ombak_y' in dff.columns:
            fig_ts = px.line(dff.sort_values('waktu'), x='waktu', y='puncak_ombak_y', markers=True,
                             title="Pergerakan Puncak Ombak (Y) vs Waktu",
                             labels={'waktu':'Waktu','puncak_ombak_y':'Puncak Ombak (Y)'})
            st.plotly_chart(fig_ts, width="stretch")
        
        # Grafik Extreme Count
        if 'extreme_count' in dff.columns:
            fig_extreme = px.line(dff.sort_values('waktu'), x='waktu', y='extreme_count', markers=True,
                                 title="Extreme Count vs Waktu (Tsunami Alert Tracking)",
                                 labels={'waktu':'Waktu','extreme_count':'Extreme Count'})
            # Tambahkan garis threshold
            fig_extreme.add_hline(y=extreme_threshold, line_dash="dash", line_color="red", 
                                 annotation_text=f"Alert Threshold: {extreme_threshold}")
            st.plotly_chart(fig_extreme, width="stretch")
        
        if 'status_ombak' in dff.columns:
            status_counts = dff['status_ombak'].value_counts().reset_index()
            status_counts.columns = ['status_ombak','jumlah']
            fig_bar = px.bar(status_counts, x='status_ombak', y='jumlah', title="Distribusi Status Ombak",
                             labels={'status_ombak':'Status','jumlah':'Jumlah'})
            st.plotly_chart(fig_bar, width="stretch")

        # Alert History
        if 'alert_sent' in dff.columns:
            alerts = dff[dff['alert_sent'] == True]
            if not alerts.empty:
                st.subheader("🚨 Riwayat Alert Tsunami")
                st.dataframe(alerts[['waktu', 'status_ombak', 'puncak_ombak_y', 'extreme_count']], 
                           width="stretch", height=200)

        st.subheader("Data (terbatas 500 baris)")
        st.dataframe(dff.tail(500), width="stretch", height=420)

        # ========== Laporan (PDF) ==========
        st.subheader("📄 Laporan (PDF)")
        st.caption("Butuh paket `reportlab` (install: `pip install reportlab`).")
        def make_report_bytes(d: pd.DataFrame) -> bytes:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm

            buff = io.BytesIO()
            c = canvas.Canvas(buff, pagesize=A4)
            W, H = A4

            def line(y): c.line(1.5*cm, y, W-1.5*cm, y)

            # Header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(2*cm, H-2*cm, "Laporan Deteksi Ombak + Tsunami Alert")
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, H-2.6*cm, f"Dibuat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            line(H-2.8*cm)

            # Ringkasan
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, H-3.6*cm, "Ringkasan")
            c.setFont("Helvetica", 10)

            waktu_min = str(d['waktu'].min()) if 'waktu' in d.columns else "-"
            waktu_max = str(d['waktu'].max()) if 'waktu' in d.columns else "-"
            total = len(d)

            y = H-4.2*cm
            c.drawString(2*cm, y, f"Rentang data : {waktu_min}  s/d  {waktu_max}"); y -= 0.6*cm
            c.drawString(2*cm, y, f"Jumlah entri : {total}"); y -= 0.6*cm

            if 'puncak_ombak_y' in d.columns and len(d)>0:
                c.drawString(2*cm, y, f"Peak Y  (min/mean/max) : {int(d['puncak_ombak_y'].min())} / {round(d['puncak_ombak_y'].mean(),1)} / {int(d['puncak_ombak_y'].max())}")
                y -= 0.6*cm

            if 'extreme_count' in d.columns and len(d)>0:
                max_extreme = int(d['extreme_count'].max())
                c.drawString(2*cm, y, f"Maximum Extreme Count : {max_extreme}")
                y -= 0.6*cm

            if 'alert_sent' in d.columns and len(d)>0:
                alert_count = len(d[d['alert_sent'] == True])
                c.drawString(2*cm, y, f"Jumlah Alert Tsunami : {alert_count}")
                y -= 0.6*cm

            if 'status_ombak' in d.columns and len(d)>0:
                c.drawString(2*cm, y, "Distribusi status:"); y -= 0.5*cm
                counts = d['status_ombak'].value_counts()
                for s, n in counts.items():
                    c.drawString(2.5*cm, y, f"- {s}: {n}")
                    y -= 0.5*cm

            # Footer
            line(2*cm)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(2*cm, 1.5*cm, "Generated by Ombak Dashboard + Tsunami Alert")

            c.showPage(); c.save()
            return buff.getvalue()

        if st.button("📄 Unduh Laporan (PDF)", key="btn_download_pdf"):
            try:
                pdf_bytes = make_report_bytes(dff)
                st.download_button("Download sekarang", data=pdf_bytes, file_name="laporan_ombak_tsunami_alert.pdf", mime="application/pdf", key="btn_download_pdf_file")
            except Exception as e:
                st.error(f"Gagal membuat PDF. Pastikan reportlab terpasang. Error: {e}")
    else:
        st.info("Tidak ada data untuk grafik/laporan.")
