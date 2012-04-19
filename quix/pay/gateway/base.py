from exceptions import NotImplementedError
import urllib2

from quix.pay.transaction import CreditCard

class AbstractGateway(object):
    """
    Abstract class for interfacing with payment gateways. 
    """
    test_mode = False
    request_timeout = 30
    use_test_url = False
    use_test_mode = False
    
    @property
    def live_url(self):
        """ The gateway API URL used for test requests. """
        raise NotImplementedError("Property not implemented in gateway class: 'live_url'")
        
    @property
    def test_url(self):
        """ The gateway API URL used for production requests. """
        raise NotImplementedError("Property not implemented in gateway class: 'test_url'.")

    def authentication(self, login, password):
        """
        Specify payment gateway authentication.
        
        Args
            login - A string used by the gateway to identify a user of the API.
            password - A string used by the gateway to authenticate the user.
        """
        self.login = login
        self.password = password
        
    def authorize(self, amount, card, order=None, customer=None):
        """ 
        Send a credit card authorization request to the gateway.
        
        Args
            amount - The amount of the order.
            card - A CreditCard object containing valid credit card info.

        Returns:
            A GatewayResponse object.
        """
        raise NotImplementedError("Method not implemented in gateway class: 'authorize'.")

    def capture(self, trans_id):
        """ 
        Send a credit card capture request to the gateway.
        
        Args
            card - A CreditCard object containing valid credit card info.
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() method.

        Returns:
            A GatewayResponse object.
        """
        raise NotImplementedError("Method not implemented in gateway class: 'capture'.")
    
    def credit(self, trans_id, amount, card=None, order=None, customer=None):
        """ 
        Send a credit card refund request to the gateway.
        
        Args
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() or sale() 
                methods.
            amount - The amount to refund. Should be less than or equal to the 
                amount of the original transaction.
            card - A CreditCard number or the last 4 digits of a credit card
                number may be required by some gateways.

        Returns:
            A GatewayResponse object.
        """
        raise NotImplementedError("Method not implemented in gateway class: 'credit'.")
        
    def get_last_request(self):
        """
        Gets the GatewayRequest instance from the last call to the request()
        method.
        
        Returns
            An existing GatewayRequest instance.
        """
        return self._last_request
    
    def __init__(self, login=None, password=None):
        """
        Optionally provide arguments to the authentication() method as a 
        convenience.
        """
        self.authentication(login, password)
        self._last_request = None
        
    def request(self, url, data):
        """
        Submits an http(s) request to the provided gateway url. This response is
        saved internally and accessible using the get_last_request() method.
        
        Args
            url - The gateway url
            data - The data to post to the gateway url
            
        Returns
            A new GatewayResponse instance
        """
        self._last_request = GatewayRequest(url, data, self.request_timeout)
        response = self._last_request.send()
        
        return response
    
    def sale(self, amount, card, order=None, customer=None):
        """ 
        Send a credit card authorization and capture request to the gateway.
        
        Args
            amount - The amount of the order.
            card - A CreditCard object containing valid credit card info.
            order - An optional Order object specifying order details.
            customer - An optional Customer object specifying customer info.

        Returns
            A GatewayResponse object.
        """
        raise NotImplementedError("Method not implemented in gateway class: 'sale'.")
 
    def void(self, trans_id, card=None, order=None, customer=None):
        """ 
        Send a credit card void request to the gateway.
        
        Args
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() or sale() 
                methods.
            amount - The amount to refund. Should be less than or equal to the 
                amount of the original transaction.

        Returns:
            A GatewayResponse object.
        """
        raise NotImplementedError("Method not implemented in gateway class: 'void'.")
        
class GatewayRequest(object):
    """
    An http(s) request to the payment gateway.
    
    An instance of a GatewayRequest object provides url and POST data from the 
    request so that client applications may choose to further process or log
    the request details.
    """
    
    def __init__(self, url, data, timeout=30):
        """
        Initialize an http(s) request.
        
        Args
            url - The full URL for the request.
            data - The raw text data to post to the request url.
            timeout - Time in seconds to timeout the request.
        """
        self.url = url
        self.data = data
        self.timeout = timeout
    
    def send(self):
        """
        Send an http(s) request.
        
        Returns
            A new instance of a GatewayResponse object.
        """
        r = urllib2.urlopen(self.url, self.data) #, self.timeout)
        response = GatewayResponse(r.read(), r.info())
        return response
    
class GatewayResponse(object):
    """
    An http(s) response from the payment gateway.
    
    An instance of the GatewayResponse provides details of the response from 
    the payment gateway.
    """
    # constants for the status of the transaction
    status_strings = ('Unknown', 'Approved', 'Declined', 'Error')
    UNKNOWN = 0
    APPROVED = 1
    DECLINED = 2
    ERROR = 3
    
    # must be set by a gateway class instance    
    status = 0
    message = ''
    trans_id = None
    avs_result = None
    gateway_data = None
    
    def __init__(self, body, headers=None):
        """
        Initializes the GatewayResponse instance with the full contents of the 
        http response.
        
        Args
            body - The raw, un-parsed http body from the response.
            headers - The http headers from the response.
        """
        self.body = body
        self.headers = headers

