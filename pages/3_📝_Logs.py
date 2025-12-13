"""
Logs Page
Shows system logs and activity
"""
import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

st.title("📝 System Logs")

# Log file options
log_files = {
    "Daily Trading": "logs/tradenova_daily.log",
    "Main Log": "tradenova.log",
    "Dashboard": "logs/dashboard.log",
    "Service": "logs/tradenova_service.log",
    "Error": "logs/tradenova_service_error.log"
}

# Select log file
selected_log = st.selectbox("Select Log File", list(log_files.keys()))
log_path = Path(log_files[selected_log])

# Number of lines to show
num_lines = st.slider("Number of lines to show", 50, 1000, 200)

# Auto-refresh
auto_refresh = st.checkbox("Auto-refresh (every 5 seconds)", value=False)

if log_path.exists():
    try:
        # Read last N lines
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            last_lines = lines[-num_lines:] if len(lines) > num_lines else lines
        
        # Display logs
        log_text = ''.join(last_lines)
        
        # Search filter
        search_term = st.text_input("🔍 Search in logs", "")
        if search_term:
            filtered_lines = [line for line in last_lines if search_term.lower() in line.lower()]
            log_text = ''.join(filtered_lines)
            st.info(f"Found {len(filtered_lines)} lines matching '{search_term}'")
        
        # Display in code block
        st.code(log_text, language=None)
        
        # Download button
        st.download_button(
            label="📥 Download Full Log",
            data=''.join(lines),
            file_name=f"{selected_log.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.log",
            mime="text/plain"
        )
        
        # Auto-refresh
        if auto_refresh:
            import time
            time.sleep(5)
            st.rerun()
            
    except Exception as e:
        st.error(f"Error reading log file: {e}")
else:
    st.warning(f"Log file not found: {log_path}")
    st.info("Logs will appear here once the trading system starts generating logs.")

# Log statistics
st.markdown("---")
st.subheader("Log Statistics")

log_stats = {}
for name, path in log_files.items():
    log_file = Path(path)
    if log_file.exists():
        try:
            size = log_file.stat().st_size
            size_mb = size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # Count lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            
            log_stats[name] = {
                'size_mb': size_mb,
                'lines': line_count,
                'modified': mod_time
            }
        except:
            pass

if log_stats:
    import pandas as pd
    stats_df = pd.DataFrame(log_stats).T
    stats_df.columns = ['Size (MB)', 'Lines', 'Last Modified']
    st.dataframe(stats_df, use_container_width=True)
else:
    st.info("No log statistics available")

