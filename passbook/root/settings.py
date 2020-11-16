"""
Django settings for passbook project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import importlib
import os
import sys
from json import dumps
from time import time

import structlog
from celery.schedules import crontab
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from passbook import __version__
from passbook.core.middleware import structlog_add_request_id
from passbook.lib.config import CONFIG
from passbook.lib.logging import add_common_fields, add_process_id
from passbook.lib.sentry import before_send


def j_print(event: str, log_level: str = "info", **kwargs):
    """Print event in the same format as structlog with JSON.
    Used before structlog is configured."""
    data = {
        "event": event,
        "level": log_level,
        "logger": __name__,
        "timestamp": time(),
    }
    data.update(**kwargs)
    print(dumps(data), file=sys.stderr)


LOGGER = structlog.get_logger()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_ROOT = BASE_DIR + "/static"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = CONFIG.y(
    "secret_key", "9$@r!d^1^jrn#fk#1#@ks#9&i$^s#1)_13%$rwjrhd=e8jfi_s"
)  # noqa Debug

DEBUG = CONFIG.y_bool("debug")
INTERNAL_IPS = ["127.0.0.1"]
ALLOWED_HOSTS = ["*"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_URL = "passbook_flows:default-authentication"

# Custom user model
AUTH_USER_MODEL = "passbook_core.User"

_cookie_suffix = "_debug" if DEBUG else ""
CSRF_COOKIE_NAME = "passbook_csrf"
LANGUAGE_COOKIE_NAME = f"passbook_language{_cookie_suffix}"
SESSION_COOKIE_NAME = f"passbook_session{_cookie_suffix}"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "passbook.admin.apps.PassbookAdminConfig",
    "passbook.api.apps.PassbookAPIConfig",
    "passbook.audit.apps.PassbookAuditConfig",
    "passbook.crypto.apps.PassbookCryptoConfig",
    "passbook.flows.apps.PassbookFlowsConfig",
    "passbook.outposts.apps.PassbookOutpostConfig",
    "passbook.lib.apps.PassbookLibConfig",
    "passbook.policies.apps.PassbookPoliciesConfig",
    "passbook.policies.dummy.apps.PassbookPolicyDummyConfig",
    "passbook.policies.expiry.apps.PassbookPolicyExpiryConfig",
    "passbook.policies.expression.apps.PassbookPolicyExpressionConfig",
    "passbook.policies.hibp.apps.PassbookPolicyHIBPConfig",
    "passbook.policies.password.apps.PassbookPoliciesPasswordConfig",
    "passbook.policies.group_membership.apps.PassbookPoliciesGroupMembershipConfig",
    "passbook.policies.reputation.apps.PassbookPolicyReputationConfig",
    "passbook.providers.proxy.apps.PassbookProviderProxyConfig",
    "passbook.providers.oauth2.apps.PassbookProviderOAuth2Config",
    "passbook.providers.saml.apps.PassbookProviderSAMLConfig",
    "passbook.recovery.apps.PassbookRecoveryConfig",
    "passbook.sources.ldap.apps.PassbookSourceLDAPConfig",
    "passbook.sources.oauth.apps.PassbookSourceOAuthConfig",
    "passbook.sources.saml.apps.PassbookSourceSAMLConfig",
    "passbook.stages.captcha.apps.PassbookStageCaptchaConfig",
    "passbook.stages.consent.apps.PassbookStageConsentConfig",
    "passbook.stages.dummy.apps.PassbookStageDummyConfig",
    "passbook.stages.email.apps.PassbookStageEmailConfig",
    "passbook.stages.prompt.apps.PassbookStagPromptConfig",
    "passbook.stages.identification.apps.PassbookStageIdentificationConfig",
    "passbook.stages.invitation.apps.PassbookStageUserInvitationConfig",
    "passbook.stages.user_delete.apps.PassbookStageUserDeleteConfig",
    "passbook.stages.user_login.apps.PassbookStageUserLoginConfig",
    "passbook.stages.user_logout.apps.PassbookStageUserLogoutConfig",
    "passbook.stages.user_write.apps.PassbookStageUserWriteConfig",
    "passbook.stages.otp_static.apps.PassbookStageOTPStaticConfig",
    "passbook.stages.otp_time.apps.PassbookStageOTPTimeConfig",
    "passbook.stages.otp_validate.apps.PassbookStageOTPValidateConfig",
    "passbook.stages.password.apps.PassbookStagePasswordConfig",
    "passbook.static.apps.PassbookStaticConfig",
    "rest_framework",
    "django_filters",
    "drf_yasg2",
    "guardian",
    "django_prometheus",
    "channels",
    "dbbackup",
]

GUARDIAN_MONKEY_PATCH = False

SWAGGER_SETTINGS = {
    "DEFAULT_INFO": "passbook.api.v2.urls.info",
    "SECURITY_DEFINITIONS": {
        "token": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework_guardian.filters.ObjectPermissionsFilter",
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.DjangoObjectPermissions",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "passbook.api.auth.PassbookTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": (
            f"redis://:{CONFIG.y('redis.password')}@{CONFIG.y('redis.host')}:6379"
            f"/{CONFIG.y('redis.cache_db')}"
        ),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_SAMESITE = "lax"

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "passbook.core.middleware.RequestIDMiddleware",
    "passbook.audit.middleware.AuditMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "passbook.core.middleware.ImpersonateMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "passbook.root.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "passbook.lib.config.context_processor",
            ],
        },
    },
]

ASGI_APPLICATION = "passbook.root.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                f"redis://:{CONFIG.y('redis.password')}@{CONFIG.y('redis.host')}:6379"
                f"/{CONFIG.y('redis.ws_db')}"
            ],
        },
    },
}


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": CONFIG.y("postgresql.host"),
        "NAME": CONFIG.y("postgresql.name"),
        "USER": CONFIG.y("postgresql.user"),
        "PASSWORD": CONFIG.y("postgresql.password"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Celery settings
# Add a 10 minute timeout to all Celery tasks.
CELERY_TASK_SOFT_TIME_LIMIT = 600
CELERY_BEAT_SCHEDULE = {
    "clean_expired_models": {
        "task": "passbook.core.tasks.clean_expired_models",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "passbook_scheduled"},
    },
    "db_backup": {
        "task": "passbook.core.tasks.backup_database",
        "schedule": crontab(minute=0, hour=0),
        "options": {"queue": "passbook_scheduled"},
    },
}
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_DEFAULT_QUEUE = "passbook"
CELERY_BROKER_URL = (
    f"redis://:{CONFIG.y('redis.password')}@{CONFIG.y('redis.host')}"
    f":6379/{CONFIG.y('redis.message_queue_db')}"
)
CELERY_RESULT_BACKEND = (
    f"redis://:{CONFIG.y('redis.password')}@{CONFIG.y('redis.host')}"
    f":6379/{CONFIG.y('redis.message_queue_db')}"
)

# Database backup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": "./backups" if DEBUG else "/backups"}
DBBACKUP_CONNECTOR_MAPPING = {
    "django_prometheus.db.backends.postgresql": "dbbackup.db.postgresql.PgDumpConnector"
}
if CONFIG.y("postgresql.s3_backup"):
    DBBACKUP_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    DBBACKUP_STORAGE_OPTIONS = {
        "access_key": CONFIG.y("postgresql.s3_backup.access_key"),
        "secret_key": CONFIG.y("postgresql.s3_backup.secret_key"),
        "bucket_name": CONFIG.y("postgresql.s3_backup.bucket"),
        "region_name": CONFIG.y("postgresql.s3_backup.region", "eu-central-1"),
        "default_acl": "private",
        "endpoint_url": CONFIG.y("postgresql.s3_backup.host"),
    }
    j_print(
        "Database backup to S3 is configured.",
        host=CONFIG.y("postgresql.s3_backup.host"),
    )

# Sentry integration
_ERROR_REPORTING = CONFIG.y_bool("error_reporting.enabled", False)
if not DEBUG and _ERROR_REPORTING:
    sentry_init(
        dsn="https://33cdbcb23f8b436dbe0ee06847410b67@sentry.beryju.org/3",
        integrations=[
            DjangoIntegration(transaction_style="function_name"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        before_send=before_send,
        release="passbook@%s" % __version__,
        traces_sample_rate=0.6,
        environment=CONFIG.y("error_reporting.environment", "customer"),
        send_default_pii=CONFIG.y_bool("error_reporting.send_pii", False),
    )
    j_print(
        "Error reporting is enabled.",
        env=CONFIG.y("error_reporting.environment", "customer"),
    )


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"


structlog.configure_once(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_process_id,
        add_common_fields(CONFIG.y("error_reporting.environment", "customer")),
        structlog_add_request_id,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOG_PRE_CHAIN = [
    # Add the log level and a timestamp to the event_dict if the log entry
    # is not from structlog.
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(sort_keys=True),
            "foreign_pre_chain": LOG_PRE_CHAIN,
        },
        "colored": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(colors=DEBUG),
            "foreign_pre_chain": LOG_PRE_CHAIN,
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "colored" if DEBUG else "plain",
        },
    },
    "loggers": {},
}

TEST = False
TEST_RUNNER = "passbook.root.test_runner.PytestTestRunner"
LOG_LEVEL = CONFIG.y("log_level").upper()


_LOGGING_HANDLER_MAP = {
    "": LOG_LEVEL,
    "passbook": LOG_LEVEL,
    "django": "WARNING",
    "celery": "WARNING",
    "selenium": "WARNING",
    "grpc": LOG_LEVEL,
    "docker": "WARNING",
    "urllib3": "WARNING",
    "websockets": "WARNING",
    "daphne": "WARNING",
    "dbbackup": "ERROR",
    "kubernetes": "INFO",
}
for handler_name, level in _LOGGING_HANDLER_MAP.items():
    # pyright: reportGeneralTypeIssues=false
    LOGGING["loggers"][handler_name] = {
        "handlers": ["console"],
        "level": level,
        "propagate": False,
    }


_DISALLOWED_ITEMS = [
    "INSTALLED_APPS",
    "MIDDLEWARE",
    "AUTHENTICATION_BACKENDS",
    "CELERY_BEAT_SCHEDULE",
]
# Load subapps's INSTALLED_APPS
for _app in INSTALLED_APPS:
    if _app.startswith("passbook"):
        if "apps" in _app:
            _app = ".".join(_app.split(".")[:-2])
        try:
            app_settings = importlib.import_module("%s.settings" % _app)
            INSTALLED_APPS.extend(getattr(app_settings, "INSTALLED_APPS", []))
            MIDDLEWARE.extend(getattr(app_settings, "MIDDLEWARE", []))
            AUTHENTICATION_BACKENDS.extend(
                getattr(app_settings, "AUTHENTICATION_BACKENDS", [])
            )
            CELERY_BEAT_SCHEDULE.update(
                getattr(app_settings, "CELERY_BEAT_SCHEDULE", {})
            )
            for _attr in dir(app_settings):
                if not _attr.startswith("__") and _attr not in _DISALLOWED_ITEMS:
                    globals()[_attr] = getattr(app_settings, _attr)
        except ImportError:
            pass

if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    CELERY_TASK_ALWAYS_EAGER = True

INSTALLED_APPS.append("passbook.core.apps.PassbookCoreConfig")

j_print("Booting passbook", version=__version__)
