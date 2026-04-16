from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity


from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Mapping der Unit-Codes aus deinem JSON
UNIT_MAP = {
    30: UnitOfEnergy.KILO_WATT_HOUR,       # kWh
    35: UnitOfElectricPotential.VOLT,      # V
    33: UnitOfElectricCurrent.AMPERE,      # A
    27: UnitOfPower.WATT,                  # W
    44: UnitOfFrequency.HERTZ,             # Hz
    8: "°",                                # Grad (Phasenwinkel)
}


def obis_to_name(obis: str) -> str:
    """Wandelt eine OBIS-Kennung in einen sprechenden Namen um."""

    mapping = {
        "0100010800ff": "energy_import_total",
        "0100020800ff": "energy_export_total",
        "01000e0700ff": "grid_frequency",
        "0100100700ff": "power_total",
        "01001f0700ff": "current_l1",
        "0100200700ff": "voltage_l1",
        "0100240700ff": "power_l1",
        "0100330700ff": "current_l2",
        "0100340700ff": "voltage_l2",
        "0100380700ff": "power_l2",
        "0100470700ff": "current_l3",
        "0100480700ff": "voltage_l3",
        "01004c0700ff": "power_l3",
        "0100510701ff": "phase_angle_l1",
        "0100510702ff": "phase_angle_l2",
        "0100510704ff": "phase_angle_l3",
        "010051070fff": "phase_angle_total",
        "010051071aff": "phase_angle_extra",
    }

    return mapping.get(obis, obis)


async def async_setup_entry(hass, entry, async_add_entities):
    """Sensoren aus dem Coordinator erzeugen."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []

    # Alle Werte aus dem JSON durchgehen
    for item in coordinator.data.get("values", []):
        logical_name = item.get("logical_name", "")
        obis = logical_name.split(".")[0]

        sensors.append(
            SmartmeterOriginSensor(
                coordinator=coordinator,
                obis=obis,
                name=obis_to_name(obis),
                unit_code=item.get("unit"),
                scaler=item.get("scaler"),
            )
        )

    async_add_entities(sensors)


class SmartmeterOriginSensor(CoordinatorEntity, SensorEntity):
    """Ein Sensor für einen einzelnen OBIS-Wert."""

    def __init__(self, coordinator, obis, name, unit_code, scaler):
        super().__init__(coordinator)

        self._attr_name = f"Smartmeter {name}"
        self._attr_unique_id = f"emh_gateway_{obis}"
        self._attr_suggested_object_id = f"emh_gateway_{name}"
        self.obis = obis
        self.unit_code = unit_code
        self.scaler = scaler

        # Einheit bestimmen
        self._attr_native_unit_of_measurement = UNIT_MAP.get(unit_code)

        # Energy Dashboard Kompatibilität
        if obis == "0100010800ff":
            self._attr_device_class = "energy"
            self._attr_state_class = "total_increasing"

        elif obis == "0100020800ff":
            self._attr_device_class = "energy"
            self._attr_state_class = "total_increasing"

        elif unit_code == 27:
            self._attr_device_class = "power"

        elif unit_code == 33:
            self._attr_device_class = "current"

        elif unit_code == 35:
            self._attr_device_class = "voltage"

        elif unit_code == 44:
            self._attr_device_class = "frequency"

        # Geräte-Info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "emh_gateway")},
            "name": "EMH Gateway",
            "manufacturer": "Unknown",
            "model": "Origin Meter",
        }

    @property
    def native_value(self):
        """Berechnet den skalierten Wert."""

        try:
            # Wert aus dem Coordinator holen
            for item in self.coordinator.data.get("values", []):
                if item["logical_name"].startswith(self.obis):
                    raw = float(item["value"])

                    # Energie-Register: Wert ist in Wh → in kWh umrechnen
                    if self.obis in ["0100010800ff", "0100020800ff"]:
                        return raw / 10000

                    # Alle anderen Register: Scaler normal anwenden
                    return raw * (10 ** self.scaler)

        except Exception as err:
            _LOGGER.error("Fehler beim Skalieren: %s", err)

        return None
