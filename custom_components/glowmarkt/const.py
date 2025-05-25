from datetime import timedelta

DOMAIN = "glowmarkt"
DEFAULT_NAME = "Glowmarkt"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)

# 固定参数（来自Bright App）
BRIGHT_APP_ID = "b0f1b774-a586-4f72-9edd-27ead8aa7a8d"
API_URL = "https://api.glowmarkt.com/api/v0-1"
AUTH_URL = "https://api.glowmarkt.com/api/v0-1/auth"

# 配置项（用户只需输入这些）
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_RESOURCE_ID = "resource_id"
CONF_RESOURCE_TYPE = "resource_type"  # 新增

# 属性字段
ATTR_CURRENT_USAGE = "current_usage"
ATTR_CUMULATIVE_USAGE = "cumulative_usage"
ATTR_UNITS = "units"
ATTR_TIMESTAMP = "timestamp"