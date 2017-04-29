from ipv4factory import IPV4Factory
from macfactory import MACFactory
import numpy as np


if __name__ == '__main__':
    ipv4fact = IPV4Factory()
    macfact = MACFactory()
    ipv4fact.setSeed("255.255.255.0") 
    # print ipv4fact.generate(256)
    # print ipv4fact.generate(256)
    # print ipv4fact.generate(256)
    # print ipv4fact.generate(256)
    # print ipv4fact.generate(256)

    myfunc = hostNumGen("2,2")
    print myfunc()