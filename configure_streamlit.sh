#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# 1. Install dependencies using dnf (the package manager for AL2023)
dnf install -y git python3-pip
PYTHON_EXECUTABLE="/usr/bin/python3"

# 2. Get Application Code
git clone https://github.com/katienkim/Training-GenAI-Prototype.git /app
cd /app/streamlit_ui

# 3. Create a virtual environment in a standard location
$PYTHON_EXECUTABLE -m venv /opt/streamlit_venv

# 4. Install Python Libraries into the virtual environment
# Note: We activate the venv first
source /opt/streamlit_venv/bin/activate
pip3 install -r requirements.txt

# 5. Set Environment Variable for the API URL
echo "API_ENDPOINT_URL=##API_ENDPOINT_URL##" > .env

# 6. Create and run the systemd service
cat <<EOF > /etc/systemd/system/streamlit.service
[Unit]
Description=Streamlit AI Auditor App
After=network.target

[Service]
User=ec2-user
EnvironmentFile=/app/streamlit_ui/.env
WorkingDirectory=/app/streamlit_ui/
# IMPORTANT: ExecStart now points to the python inside the venv
ExecStart=/opt/streamlit_venv/bin/python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 7. Start the service
systemctl daemon-reload
systemctl enable streamlit.service
systemctl start streamlit.service