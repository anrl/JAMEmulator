# JAMEmulator

JAM Emulator requires MiniNeXT and MiniNet 2.1.0 to run.

MiniNeXT can be downloaded from: 

https://github.com/USC-NSL/miniNExT

The VM image for MiniNet 2.1.0 can be downloaded from: 

https://github.com/mininet/mininet/wiki/Mininet-VM-Images

The JAM Emulator requires a topology configuration in the form of a YAML file in order to run. For an example YAML configuration see "ethernet.yaml". The emulator can be run as follows:

    sudo python jamemulator.py config

JAM Builder can be used to convert large scale GML topologies into YAML configurations that can then be run by the JAM Emulator. Available topologies in GML format can be found at "www.topology-zoo.org". The JAM Builder can be run as follows:

    sudo python jambuilder.py input output