"""Config flow for RTS Smart Covers."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

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


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the config/options form schema."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_COVER,
                default=defaults.get(CONF_SOURCE_COVER),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="cover")
            ),
            vol.Required(
                CONF_NAME,
                default=defaults.get(CONF_NAME, DEFAULT_NAME),
            ): selector.TextSelector(),
            vol.Required(
                CONF_TRAVEL_TIME,
                default=defaults.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_TRAVEL_TIME,
                    max=MAX_TRAVEL_TIME,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_INITIAL_POSITION,
                default=defaults.get(CONF_INITIAL_POSITION, DEFAULT_INITIAL_POSITION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    )


class RtsSmartCoversConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTS Smart Covers."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            source_cover = user_input[CONF_SOURCE_COVER]

            await self.async_set_unique_id(source_cover)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RtsSmartCoversOptionsFlow:
        """Create the options flow."""
        return RtsSmartCoversOptionsFlow(config_entry)


class RtsSmartCoversOptionsFlow(config_entries.OptionsFlow):
    """Handle options for RTS Smart Covers."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
            errors={},
        )
