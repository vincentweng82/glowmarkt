### Manual installation

Copy the `custom_components/glowmarkt/` directory and all of its files to your `config/custom_components/` directory.

## Configuration

Once installed, restart Home Assistant:

[![Open your Home Assistant instance and show the system dashboard.](https://my.home-assistant.io/badges/system_dashboard.svg)](https://my.home-assistant.io/redirect/system_dashboard/)

Then, add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=glowmarkt)


<details>
  <summary>Manually add the Integration</summary>
  Visit the <i>Integrations</i> section in Home Assistant and click the <i>Add</i> button in the bottom right corner. Search for <code>Glowmarkt</code> and input your brigh app credentials. <b>You may need to clear your browser cache before the integration appears in the list.</b>
</details>

## Sensors

Once you've authenticated, the integration will automatically set up the following sensors for each of the smart meters on your account:

- 30 Minute Usage   -- 30 minute time reading
- Cumulative Usage(today)  --Consumption today (kWh)
- Electricity Cost(today)  --Total cost of today's consumption (GBP)
- Electricity Rate   --Current tariff (GBP/kWh)
- Electricity Standing Charge  --Current standing charge (GBP)

The usage and cost sensors will still show the previous day's data until shortly after 01:30 to ensure that all of the previous day's data is collected.

The standing charge and rate sensors are disabled by default as they are less commonly used. Before enabling them, ensure the data is visible in the Bright app.

If the data being shown is wrong, check the Bright app first. If it is also wrong there, you will need to contact your supplier and tell them to fix the data being provided to DCC Other Users, as Bright is one of these.

## Energy Management

The sensors created integrate directly into Home Assistant's [Home Energy Management](https://www.home-assistant.io/docs/energy/).
It is recommended you use the daily usage and cost sensors in the Energy integration.

[![Open your Home Assistant instance and show your Energy configuration panel.](https://my.home-assistant.io/badges/config_energy.svg)](https://my.home-assistant.io/redirect/config_energy/)

## Debugging

To debug the integration, add the following to your `configuration.yaml`

```yaml
logger:
  default: warning
  logs:
    custom_components.glowmarkt: debug
```


### Code Style

This project makes use of black, isort and pylint to enforce a consistent code style across the codebase.

## Credits

Thanks go to:

- The Hildebrand API [documentation](https://docs.glowmarkt.com/GlowmarktAPIDataRetrievalDocumentationIndividualUserForBright.pdf) and [Swagger UI](https://api.glowmarkt.com/api-docs/v0-1/resourcesys/).

- The [Hildebrand-Glow-Python-Library](https://github.com/ghostseven/Hildebrand-Glow-Python-Library), used for understanding the API.

- All of the contributors and users, without whom this integration wouldn't be where it is today.
