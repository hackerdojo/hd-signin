from base import AbstractGateway
from authorizenet import AimGateway
from quix.pay.transaction import CreditCard

class AimEmulationGateway(AimGateway):
    """ 
    Interface to the QuantamGateway using Authorize.Net Emulation.
    
    The QuantamGateway provides a basic emulation mode of the Authorize.Net
    payment gateway. This class simply extends the AimGatewy class to utilize
    the QuantamGateway URL instead. Since this is only a basic emulation, you
    should refer to the QuantamGateway documentation at    
    https://www.quantumgateway.com/view_developer.php?Cat1=6 to understand
    it's limitations.
    """
    live_url = 'https://secure.quantumgateway.com/cgi/authnet_aim.php'
    test_url = live_url
        
    def __str__(self):
        return "QuantamGateway Authorize.Net AIM Emulation"

class TransparentDbEngine(AbstractGateway):
    pass

