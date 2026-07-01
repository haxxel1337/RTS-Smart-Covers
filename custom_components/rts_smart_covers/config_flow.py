"""Config flow for RTS Smart Covers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_INITIAL_POSITION,
    CONF_SOURCE_COVER,
    CONF_TRAVEL_TIME,
    DEFAULT_INITIAL_POSITION,
    DEFAULT_NAME,
    DEFAULT_TRAVEL_TIME,
    DOMAIN,
    MAX_TRAVEL_TIME,
    MIN_TRAVEL_TIME,
)


def _data_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_COVER, default=defaults.get(CONF_SOURCE_COVER)): EntitySelector(
                EntitySelectorConfig(domain="cover")
            ),
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
            vol.Required(CONF_TRAVEL_TIME, default=defaults.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME)): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_TRAVEL_TIME,
                    max=MAX_TRAVEL_TIME,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_INITIAL_POSITION,
                default=defaults.get(CONF_INITIAL_POSITION, DEFAULT_INITIAL_POSITION),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    )


class RtsSmartCoversConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTS Smart Covers."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOURCE_COVER])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_data_schema(), errors={})

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        config_entry = self._get_reconfigure_entry()

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOURCE_COVER])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(config_entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_data_schema(dict(config_entry.data)),
            errors={},
        )
