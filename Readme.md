
# Provisioner python tools

This repository contains the tools and libraries for the hexpansion provisioner and provisioning the quest markers.


## Running

CUrrent initial tests can be run by running main.py

## Instalation

'''pip install -r requirements.txt'''

### FTDI setup

This program uses the pyftdi setup which requires additional setup to configure the FTDI cable for use. see https://eblot.github.io/pyftdi/installation.html for details on how to set this up.

#### Windows notes

If using a venv the windows libusb dll can be placed in the venv/scripts folder rather than placing in a global location. 