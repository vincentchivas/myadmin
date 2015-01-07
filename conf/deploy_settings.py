PROJECT_NAME = 'dolphin-operation'

VERSION_CONTROL = "dolphindeploy.git"

# The Project Role Alias table.
ROLE_ALIAS = {
    'provision-service-role' : 'Dolphin Provision Service',
    'provider-service-role' : 'Dolphin Provider Service',
    'provisionadmin-service-role' : 'Dolphin Provision Admin Service',
}

# The project app table
ROLE_APPS_TABLE = {
    'Dolphin Provision Service' : ['provision-service'],
    'Dolphin Provider Service' : ['provider-service'],
    'Dolphin Provision Admin Service' : ['provisionadmin-service'],
}

# Extra extension to search
EXTRA_EXT_PATTERN = (
        '.conf',
        '.cfg',
        '.xml',
        '.csv',
        '.nginx'
        )

# Extra file name to search
EXTRA_CONF_NAME_PATTERN = (
        'settings2.py',
        'version'
        )

# Disuse compressor
BUILD_HANDLER_CONFIG =(
        'dolphindeploy.handlers.ConfigurationFileHandler',
        )
