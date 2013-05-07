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
