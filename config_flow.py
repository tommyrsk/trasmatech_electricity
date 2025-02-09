import json
import os
import aiofiles
from homeassistant import config_entries
import voluptuous as vol

DOMAIN = "trasmatech_electricity"

CONF_PROVIDER = "provider"
CONF_API_URL = "api_url"
CONF_TOKEN = "token"
CONF_METER_ID = "meter_id"

async def load_providers():
    """Load provider data asynchronously from the translation file."""
    lang_path = os.path.join(os.path.dirname(__file__), "translations/en.json")

    try:
        async with aiofiles.open(lang_path, encoding="utf-8") as f:
            content = await f.read()
            translations = json.loads(content)
        return translations.get("config", {}).get("providers", {}), translations.get("common", {})
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}, {}

class TrasMaTechElectricityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles the configuration flow for the TrasMaTech Electricity integration."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user selects a provider and enters credentials."""
        errors = {}

        # 🔹 Load provider and common translation data from JSON file
        providers_data, common_translations = await load_providers()

        if not providers_data:
            errors["base"] = "no_providers"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors=errors
            )

        PROVIDERS = {key: value["api_url"] for key, value in providers_data.items()}
        PROVIDER_NAMES = {key: value["name"] for key, value in providers_data.items()}

        if not PROVIDERS:
            errors["base"] = "no_providers"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors=errors
            )

        default_provider = list(PROVIDERS.keys())[0]

        DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_PROVIDER, default=default_provider): vol.In(PROVIDER_NAMES),
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_METER_ID): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        )

        if user_input is not None:
            provider_key = user_input[CONF_PROVIDER]
            api_url = PROVIDERS.get(provider_key, "")

            return self.async_create_entry(
                title=f"TrasMaTech Electricity ({PROVIDER_NAMES.get(provider_key, 'Unknown')})",
                data={
                    CONF_API_URL: api_url,
                    CONF_PROVIDER: provider_key,
                    CONF_TOKEN: user_input[CONF_TOKEN],
                    CONF_METER_ID: user_input[CONF_METER_ID]
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            description_placeholders={
                "provider": common_translations.get("provider", "Provider"),
                "token": common_translations.get("token", "API Token"),
                "meter_id": common_translations.get("meter_id", "Meter ID")
            },
            errors=errors,
        )
