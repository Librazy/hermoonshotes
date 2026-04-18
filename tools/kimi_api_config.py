"""Kimi/Moonshot API configuration resolver.

This module handles the resolution of API keys and base URLs for Kimi/Moonshot API,
following the priority logic defined in the requirements.
"""

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Default endpoints
DEFAULT_MOONSHOT_CN_URL = "https://api.moonshot.cn/v1"
DEFAULT_MOONSHOT_AI_URL = "https://api.moonshot.ai/v1"

# Kimi Code API prefix
KIMI_CODE_API_PREFIX = "sk-kimi-"
KIMI_CODE_API_BASE_URL_PREFIX = "https://api.kimi.com/coding/"


def resolve_api_config() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve API key and base URL for Moonshot/Kimi API.

    Resolution logic:
    0. If both MOONSHOT_API_KEY and MOONSHOT_BASE_URL are set, use them.
    1. Resolve the key first:
       a. If KIMI_CN_API_KEY is set, use it and set default endpoint to https://api.moonshot.cn/v1
       b. If KIMI_API_KEY is set, and it does not start with 'sk-kimi-', use it and set default endpoint to https://api.moonshot.ai/v1
       c. If KIMI_API_KEY is set and starts with 'sk-kimi-', return warning to set MOONSHOT_API_KEY and MOONSHOT_BASE_URL
    2. Resolve the endpoint:
       a. Inherit the default endpoint from the key resolution
       b. If MOONSHOT_BASE_URL is set, use it
       c. If KIMI_BASE_URL is set and does not start with 'https://api.kimi.com/coding/', use it

    Returns:
        Tuple of (api_key, base_url, warning_message)
        - api_key: The resolved API key or None if not found
        - base_url: The resolved base URL or None if not found
        - warning_message: Warning message if plugin should be disabled, None otherwise
    """
    # Step 0: If both MOONSHOT_API_KEY and MOONSHOT_BASE_URL are set, use them
    moonshot_api_key = os.getenv("MOONSHOT_API_KEY")
    moonshot_base_url = os.getenv("MOONSHOT_BASE_URL")

    if moonshot_api_key and moonshot_base_url:
        logger.debug("Using MOONSHOT_API_KEY and MOONSHOT_BASE_URL")
        return moonshot_api_key, moonshot_base_url, None

    # Step 1: Resolve the key
    api_key = None
    default_endpoint = None
    warning_message = None

    # 1a. Check KIMI_CN_API_KEY
    kimi_cn_api_key = os.getenv("KIMI_CN_API_KEY")
    if kimi_cn_api_key:
        logger.debug("Using KIMI_CN_API_KEY")
        api_key = kimi_cn_api_key
        default_endpoint = DEFAULT_MOONSHOT_CN_URL

    # 1b. Check KIMI_API_KEY (if not already resolved and not Kimi Code API key)
    if api_key is None:
        kimi_api_key = os.getenv("KIMI_API_KEY")
        if kimi_api_key:
            if not kimi_api_key.startswith(KIMI_CODE_API_PREFIX):
                logger.debug("Using KIMI_API_KEY (Moonshot)")
                api_key = kimi_api_key
                default_endpoint = DEFAULT_MOONSHOT_AI_URL
            else:
                # 1c. KIMI_API_KEY is a Kimi Code API key
                logger.warning(
                    "KIMI_API_KEY starts with 'sk-kimi-' which indicates Kimi Code API. "
                    "Please set MOONSHOT_API_KEY and MOONSHOT_BASE_URL explicitly for Moonshot API."
                )
                warning_message = (
                    "KIMI_API_KEY is a Kimi Code API key (starts with 'sk-kimi-'). "
                    "Please set MOONSHOT_API_KEY and MOONSHOT_BASE_URL explicitly."
                )
                return None, None, warning_message

    # If no API key found at all
    if api_key is None:
        # Check if only MOONSHOT_API_KEY is set without MOONSHOT_BASE_URL
        if moonshot_api_key and not moonshot_base_url:
            logger.warning(
                "MOONSHOT_API_KEY is set but MOONSHOT_BASE_URL is not set. "
                "Please set MOONSHOT_BASE_URL to specify which Moonshot endpoint to use."
            )
            warning_message = (
                "MOONSHOT_API_KEY is set but MOONSHOT_BASE_URL is not set. "
                "Please set MOONSHOT_BASE_URL to specify which Moonshot endpoint to use."
            )
            return None, None, warning_message
        return None, None, None

    # Step 2: Resolve the endpoint

    # 2b. If MOONSHOT_BASE_URL is set, use it directly
    if moonshot_base_url:
        logger.debug("Using MOONSHOT_BASE_URL")
        return api_key, moonshot_base_url, None

    # 2a & 2c. Otherwise, use default endpoint or KIMI_BASE_URL
    base_url = default_endpoint

    # 2c. If KIMI_BASE_URL is set and does not start with Kimi Code API prefix, use it
    kimi_base_url = os.getenv("KIMI_BASE_URL")
    if kimi_base_url and not kimi_base_url.startswith(KIMI_CODE_API_BASE_URL_PREFIX):
        logger.debug("Using KIMI_BASE_URL")
        base_url = kimi_base_url

    return api_key, base_url, None


def check_moonshot_available() -> bool:
    """
    Check if Moonshot API is available (has valid configuration).

    Returns:
        True if API key and base URL are properly configured
    """
    api_key, base_url, warning = resolve_api_config()
    return api_key is not None and base_url is not None and warning is None


def get_api_key() -> Optional[str]:
    """
    Get resolved API key.

    Returns:
        Resolved API key or None
    """
    api_key, _, _ = resolve_api_config()
    return api_key


def get_base_url() -> Optional[str]:
    """
    Get resolved base URL.

    Returns:
        Resolved base URL or None
    """
    _, base_url, _ = resolve_api_config()
    return base_url
