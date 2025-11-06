# src/services/cookie_validation.py
from src.test_cookies import validate_cookies_for_account

def validate_account_cookies(account_name: str, visible: bool = False, test_mode: bool = False):
    result = validate_cookies_for_account(account_name, visible, test_mode)
    return result
