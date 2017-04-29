
class IPV4Factory:

    _current = 0

    """ Takes an decimal number and encodes it as an IPV4 address """
    def _toIPV4(self, decimal):
        if (decimal > 4294967295):
            raise ValueError("Cannot encode values larger than 4294967295")
        if (decimal < 0):
            raise ValueError("Cannot encode negative values")

        encoding = str(hex(decimal))
        encoding = encoding[2:]
        padding = '0' * (8 - len(encoding))
        encoding = padding + encoding
        encoding = [a + b for a,b in zip(encoding[::2], encoding[1::2])]
        ipv4 = ".".join(str(int(a,16)) for a in encoding)
        return ipv4

    """ Takes an IPV4 address and encodes it as a decimal number """
    def _toDecimal(self, ipv4):
        encoding = ipv4.split(".")
        encoding = [hex(int(a))[2:] for a in encoding]
        for i in range(0, 4):
            if (len(encoding[i]) == 1):
                encoding[i] = '0' + encoding[i]
        return int("".join(encoding), 16)

        """ Returns a new IPV4 address with the specfied offset"""
    def generate(self, offset=1):
        dec = self._toDecimal(self._current) + offset
        self._current = self._toIPV4(dec)
        return self._current


    """ Sets a new seed for generatng IPV4 addresses """
    def setSeed(self, seed):
        if (isinstance(seed, int)):
            seed = self._toIPV4(seed)
        self._current = seed
