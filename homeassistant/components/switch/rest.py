"""
Support for RESTful switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rest/
"""
import logging

import requests
import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_NAME, CONF_RESOURCE, CONF_VALUE_TEMPLATE, CONF_TIMEOUT)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import template

CONF_BODY_OFF = 'body_off'
CONF_BODY_ON = 'body_on'
DEFAULT_BODY_OFF = 'OFF'
DEFAULT_BODY_ON = 'ON'
DEFAULT_NAME = 'REST Switch'
DEFAULT_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Optional(CONF_BODY_OFF, default=DEFAULT_BODY_OFF): cv.string,
    vol.Optional(CONF_BODY_ON, default=DEFAULT_BODY_ON): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument,
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the RESTful switch."""
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    body_on = config.get(CONF_BODY_ON)
    body_off = config.get(CONF_BODY_OFF)
    value_template = config.get(CONF_VALUE_TEMPLATE)
    timeout = config.get(CONF_TIMEOUT)

    try:
        requests.get(resource, timeout=10)
    except requests.exceptions.MissingSchema:
        _LOGGER.error("Missing resource or schema in configuration. "
                      "Add http:// or https:// to your URL")
        return False
    except requests.exceptions.ConnectionError:
        _LOGGER.error("No route to resource/endpoint: %s", resource)
        return False

    add_devices_callback(
        [RestSwitch(hass, name, resource,
                    body_on, body_off, value_template, timeout)])


# pylint: disable=too-many-arguments
class RestSwitch(SwitchDevice):
    """Representation of a switch that can be toggled using REST."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, hass, name, resource, body_on, body_off,
                 value_template, timeout):
        """Initialize the REST switch."""
        self._state = None
        self._hass = hass
        self._name = name
        self._resource = resource
        self._body_on = body_on
        self._body_off = body_off
        self._value_template = value_template
        self._timeout = timeout

    @property
    def name(self):
        """The name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        body_on_t = template.render(self._hass, self._body_on)
        request = requests.post(self._resource,
                                data=body_on_t,
                                timeout=self._timeout)
        if request.status_code == 200:
            self._state = True
        else:
            _LOGGER.error("Can't turn on %s. Is resource/endpoint offline?",
                          self._resource)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        body_off_t = template.render(self._hass, self._body_off)
        request = requests.post(self._resource,
                                data=body_off_t,
                                timeout=self._timeout)
        if request.status_code == 200:
            self._state = False
        else:
            _LOGGER.error("Can't turn off %s. Is resource/endpoint offline?",
                          self._resource)

    def update(self):
        """Get the latest data from REST API and update the state."""
        request = requests.get(self._resource, timeout=self._timeout)

        if self._value_template is not None:
            response = template.render_with_possible_json_value(
                self._hass, self._value_template, request.text, 'None')
            if response == 'True':
                self._state = True
            elif response == 'False':
                self._state = False
            else:
                self._state = None
        else:
            if request.text == self._body_on:
                self._state = True
            elif request.text == self._body_off:
                self._state = False
            else:
                self._state = None
