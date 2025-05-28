# hsecurities_engagement_booster/licensing/__init__.py
"""
The 'licensing' package handles the validation of Pro licenses
for the hSECURITIES Engagement Booster.
"""
from .license_validator import LicenseValidator

__all__ = ['LicenseValidator'] # Controls 'from licensing import *'
