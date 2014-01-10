pynest
======
for command line mode create pynest.json:

    {
        "username": "nest@adam.gs",
        "password": "somepassword"
    }

Usage: pynest.py [options]

    Options:
      -h, --help            show this help message and exit
      -s STRUCTURES, --structure=STRUCTURES
      -t THERMOSTATS, --thermostat=THERMOSTATS
      -u, --all-thermostats
      -w, --all-structures  
      -d, --debug           
      -l, --list            

usage:
set fan mode on all thermostats in structure (name=Home) to duty-cycle

    pynest -s name=Home -u fan-mode duty-cycle

set temperature on the basement thermostat to 25:

    pynest -s name=Home -t name=Basement temperature 25

to create rrds with temperature data:

    mkdir rrds
    pynest -r rrds

this will create an rrd file per thermostat with various data about the thermostat

    hvac_ac_state
    hvac_heater_state
    hvac_fan_state
    hvac_alt_heat_x2_state
    compressor_lockout_enabled
    can_heat
    hvac_aux_heater_state
    target_change_pending
    hvac_heat_x2_state
    hvac_heat_x3_state
    hvac_cool_x2_state
    hvac_emer_heat_state
    can_cool
    hvac_alt_heat_state
    current_temp
    target_temp_low
    target_temp_high

You can use this (code not included here) to make graphs like this:
![sample graph](http://adam.gs/x/screenshot-1389325556.13339.png)
