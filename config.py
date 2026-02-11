"""
StormOps Configuration
"""

import os

# Database
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'stormops')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')

# CRM
CRM_TYPE = os.environ.get('CRM_TYPE', 'servicetitan')
CRM_API_KEY = os.environ.get('CRM_API_KEY', '')
CRM_API_URL = os.environ.get('CRM_API_URL', 'https://api.servicetitan.com')

# Earth-2
EARTH2_API_KEY = os.environ.get('EARTH2_API_KEY', '')
EARTH2_API_URL = os.environ.get('EARTH2_API_URL', 'https://api.earth2.nvidia.com')

# Operational
DEFAULT_ZIP = '75034'
DEFAULT_SII_MIN_LEAD_GEN = 60
DEFAULT_SII_MIN_ROUTE = 70
DEFAULT_SII_MIN_REPORTS = 75
DEFAULT_NUM_CANVASSERS = 4
DEFAULT_SLA_MINUTES = 15

# Thresholds
HAIL_DAMAGE_THRESHOLD_MM = 20
FORECAST_SEVERE_THRESHOLD = 0.15
FORECAST_HAIL_THRESHOLD = 0.20

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
