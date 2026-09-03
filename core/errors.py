from __future__ import annotations


class CampaignLabError(Exception):
    """Base error safe to surface through CampaignLab's UI boundary."""


class CampaignLabAPIError(CampaignLabError):
    pass


class CampaignLabDataError(CampaignLabError):
    pass


class CampaignLabToolError(CampaignLabError):
    pass


class CampaignLabValidationError(CampaignLabError):
    pass
