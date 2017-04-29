
class MACFactory:

    _current = 0

    """ Takes an decimal number and encodes it as a MAC address """
    def _toMAC(self, decimal):
        if (decimal > 281474976710655):
            raise ValueError("Cannot encode values larger than 281474976710655")
        if (decimal < 0):
            raise ValueError("Cannot encode negative values")

        encoding = str(hex(decimal))
        encoding = encoding[2:]
        padding = '0' * (12 - len(encoding))
        encoding = padding + encoding
        mac = ':'.join(a + b for a,b in zip(encoding[::2], encoding[1::2])) 
        return mac


    """ Takes a MAC address and encodes it as a decimal number """
    def _toDecimal(self, mac):
        encoding = mac.split(":")
        return int("".join(encoding), 16)


    """ Returns a new MAC address with the specified offset"""
    def generate(self, offset=1):
        dec = self._toDecimal(self._current) + offset
        self._current = self._toMAC(dec)
        return self._current


    """ Sets a new seed for generatng MAC addresses """
    def setSeed(self, seed):
        if (isinstance(seed, int)):
            seed = self._toMAC(seed)
        self._current = seed