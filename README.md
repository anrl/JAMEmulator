# JAMEmulator (WiFi Version)

This is based on Mininet-WiFi. It is useful for emulating
configurations with node disconnections. 

To get started, get Mininet-WiFi. Install it following the instructions
at: https://github.com/intrig-unicamp/mininet-wifi

Now, install this repo. Use the following command:

    git clone -b console https://github.com/anrl/JAMEmulator.git

You may want to install Python-Yaml parser

sudo apt install python-yaml should do. Otherwise,
do aptitude search yaml and it should show the package to install for
your Ubuntu version.

Issue the following command to run the emulator with two fogs.

    sudo python emulator.py cot-f2.yaml


With three fogs

    sudo python emulator.py cot-f2.yaml







Below are some useful to Mininet-Wifi commands that can be run in the command line. 

Get all hosts in the topology

    mininet-wifi> nodes

Get all etherent links in the topology

    mininet-wifi> links

Open an xterm window on host h1

    mininet-wifi> xterm h1


In the following examples "sta1" is the name of a wireless node, and "ap1" is a wireless access point (AP).    

Get info: 

    mininet-wifi> info sta1

Get the position: 

    mininet-wifi> py sta1.params[’position’]

Get which AP it is associated to: 

    mininet-wifi> py sta1.params[’associatedTo’]

Get all APs in range: 

    mininet-wifi> py sta1.params[’apsInRange’]

Get the channel: 

    mininet-wifi> py sta1.params[’channel’]

Get the frequency: 

    mininet-wifi> py sta1.params[’frequency’]

Get the mode: 

    mininet-wifi> py sta1.params[’mode’]

Get the rssi: 

    mininet-wifi> py sta1.params[’rssi’]

Getting the Tx power: 

    mininet-wifi> sta1.params[’txpower’]

Change the signal range: 

    mininet-wifi> py sta1.ssid

Get the stations associated to AP1:

    mininet-wifi> py ap1.associatedStations

Change the position:
    
    mininet-wifi> py sta1.moveStationTo(’40,20,40’)
    
Set up the antenna gain: 

    mininet-wifi> py sta1.setAntennaGain(’sta1-wlan0’, 5)
    
Change the signal range:

    mininet-wifi> py sta.setRange(100)
    
Move association to a specific AP:

    mininet-wifi> py sta1.moveAssociationTo(’sta1-wlan0’, ’ap1’)
