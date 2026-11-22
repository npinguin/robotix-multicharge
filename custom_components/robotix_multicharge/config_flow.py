"""Native Home Assistant onboarding for the inert bootstrap."""

from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN, NAME


class RobotixMultiChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One installation entry; no physical charging source is bound."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Create only the integration entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title=NAME, data={})
