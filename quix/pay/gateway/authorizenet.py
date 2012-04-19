from base import AbstractGateway, GatewayRequest, GatewayResponse
import urllib

from quix.pay.transaction import CreditCard

class AimGateway(AbstractGateway):
    """ 
    Interface to the Authorize.Net Advanced Integration Method (AIM) payment
    gateway.
    
    The authentication login and password corresponds to the AIM API Login ID 
    and Transaction Key respectively. For example:
    
        gateway = AimGateway('<Your API Login ID>', '<Your Transaction Key>')
    
    This API is based on the "Advanced Integration Method (AIM) Developer Guide"
    version 2.0 published in June, 2010. Full documentation and examples
    are available at http:://www.quixotix.com/projects/quix.pay/
    
    Supported:
        - Authorization and Capture transactions using the sale() method.
        - Authorization Only transactions using the authorize() method.
        - Prior Authorization and Capture transactions using the capture() method.
        - Credit transactions using credit() method.
        - Void transactions using the void() method.
        - Customer details
        - Itemized order details
        
    Not Supported:
        - Capture Only transactions
        - Unlinked Credit transactions
        - Partial Authorization transactions
        - eCheck (use the eCheckGateway)
        - Automatic Recurring Payments (use the ArbGateway)
    
    """
    test_url = 'https://test.authorize.net/gateway/transact.dll'
    live_url = 'https://secure.authorize.net/gateway/transact.dll'

    API_VERSION = '3.1'
    DELIM_CHAR = ','
    
    def authorize(self, amount, card, order=None, customer=None):
        """ 
        Send a credit card AUTH_ONLY request to the Authorize.Net gateway.
        
        Args
            amount - The amount of the order.
            card - A CreditCard object containing valid credit card info.
            order - An optional Order object specifying order details.
            customer - An optional Customer object specifying customer info.

        Returns:
            A GatewayResponse object.
        """
        fields = self._create_common_fields(card, order, customer)
        fields.update({
            'x_type': 'AUTH_ONLY',
            'x_amount': str(amount),
        })

        # send request
        response = self.request(self.get_request_url(), 
                                self._prepare_fields(fields))

        return self.parse_response(response)
    
    def capture(self, trans_id):
        """ 
        Send a credit card PRIOR_AUTH_CAPTURE request to the Authorize.Net 
        gateway.
        
        Args
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() method.

        Returns:
            A GatewayResponse object.
        """
        fields = self._create_common_fields()
        fields.update({
            'x_type': 'PRIOR_AUTH_CAPTURE',
            'x_trans_id': trans_id,
        })

        # send request
        response = self.request(self.get_request_url(), 
                                self._prepare_fields(fields))

        return self.parse_response(response)

    def _create_address_fields(self, a, prefix=''):
        """ Creates a dictionary of the address fields """
        fields = {}
        
        if a.first_name is not None:
            fields['x_'+prefix+'first_name'] = a.first_name
        if a.last_name is not None:
            fields['x_'+prefix+'last_name'] = a.last_name
        if a.company is not None:
            fields['x_'+prefix+'company'] = a.company
        if a.address1 is not None or a.address2 is not None:
            fields['x_'+prefix+'address'] = "%s, %s" % (a.address1 or '', 
                                                        a.address2 or '')
        if a.city is not None:
            fields['x_'+prefix+'city'] = a.city
        if a.state_province is not None:
            fields['x_'+prefix+'state'] = a.state_province
        if a.postal_code is not None:
            fields['x_'+prefix+'zip'] = a.postal_code
        if a.country is not None:
            fields['x_'+prefix+'country'] = a.country
        
        return fields
        
    def _create_common_fields(self, card=None, order=None, customer=None):
        """ Creates a dictionary of fields common in most requests. """
        fields = {
            'x_login': self.login,
            'x_tran_key': self.password,
            'x_version': self.API_VERSION,
            'x_relay_response': 'FALSE',    # not used with AIM
            'x_delim_data': 'TRUE',         # "best practices" in all requests
            'x_delim_char': self.DELIM_CHAR
        }
        
        if self.use_test_mode:
            fields['x_test_request'] = 'TRUE'
        
        if card is not None:
            fields.update({
                'x_card_num': card.number,
                'x_exp_date': "%s%s" % (card.month, card.year) #MMYYYY
            })
            if card.code is not None:
                fields['x_card_code'] = card.code

        if customer is not None:
            if customer.ip is not None:
                fields['x_customer_ip'] = customer.ip
            if customer.email is not None:
                fields['x_email'] = customer.email
            if customer.cust_id is not None:
                fields['x_cust_id'] = customer.cust_id
            if customer.billing_address is not None:
                b = customer.billing_address
                fields.update(self._create_address_fields(b))
                if b.phone is not None:
                    fields['x_phone'] = b.phone 
                if b.fax is not None:
                    fields['x_fax'] = b.fax     
            if customer.shipping_address is not None:
                s = customer.shipping_address
                fields.update(self._create_address_fields(s, 'ship_to_'))
        
        if order is not None:
            # limit 30 items
            if order.order_id is not None:
                fields['x_invoice_num'] = order.order_id
            if order.description is not None:
                fields['x_description'] = order.description
            if order.items is not None:
                for item in order.items:
                    fields['x_line_item'] = "%s<|>%s<|>%s<|>%s<|>%s<|>" % (
                                                item.item_id or '',
                                                item.name or '',
                                                item.description or '',
                                                item.price or '',
                                                item.qty or ''
                                            )
        
        return fields
    
    def credit(self, trans_id, amount, card, order=None, customer=None):
        """ 
        Send a credit card CREDIT request to the Authorize.Net gateway.
        
        Args
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() or sale() 
                methods.
            amount - The amount to refund. Should be less than or equal to the 
                amount of the original transaction.
            card - A CreditCard object containing the original credit card 
                number or at least the last 4 digits of the credit card number.

        Returns:
            A GatewayResponse object.
        """
        fields = self._create_common_fields(card, order, customer)
        fields.update({
            'x_type': 'CREDIT',
            'x_trans_id': trans_id,
            'x_amount': str(amount)
        })

        # send request
        response = self.request(self.get_request_url(), 
                                self._prepare_fields(fields))

        return self.parse_response(response)
        
    def get_request_url(self):
        """
        Get the gateway request URL.
        
        Returns
            The Authorize.Net test gateway URL if in test mode, the production
            gateway URL otherwise.
        """
        if self.use_test_url:
            return self.test_url
        else:
            return self.live_url
         
    def parse_response(self, response):
        """ 
        Parses the response body into properties for convenience and abstraction
        in the client code. This should be called internally on every created
        GatewayResponse instance.
        
        response.status is set based on the "Response Code".
        response.message is set to the "Response Reason Text"
        response.trans_id is set to the "Transaction ID"
        
        The entire fields returned from Authorize.NET are stored as a dictionary
        in the response.gateway_data property. The keys correspond to the
        "field name" as defined in version 2.0 the AIM developer guide at 
        http://developer.authorize.net
        
        Args
            response - A GatewayResponse object
        
        Returns
            The udpated GatewayResponse object
        """
        response_offsets =  (
            'Response Code',
            'Response Subcode',
            'Response Reason Code',
            'Response Reason Text',
            'Authorization Code',
            'AVS Response',
            'Transaction ID',
            'Invoice Number',
            'Description',
            'Amount',
            'Method',
            'Transaction Type',
            'Customer ID',
            'First Name',
            'Last Name',
            'Company',
            'Address',
            'City',
            'State',
            'ZIP Code',
            'Country',
            'Phone',
            'Fax',
            'Email Address',
            'Ship To First Name',
            'Ship To Last Name',
            'Ship To Company',
            'Ship To Address',
            'Ship To City',
            'Ship To State',
            'Ship To ZIP Code',
            'Ship To Country',
            'Tax',
            'Duty',
            'Freight',
            'Tax Exempt',
            'Purchase Order Number',
            'MD5 Hash',
            'Card Code Response',
            'Cardholder Authentication Verification Response',
            'Account Number',
            'Card Type',
            'Split Tender ID',
            'Requested Amount',
            'Balance On Card'
        )
        
        fields = response.body.split(self.DELIM_CHAR)    
        response.gateway_data = {}
        
        # TODO: comprehension?
        for i, field in enumerate(fields):
            if i >= len(response_offsets):
                break;
            response.gateway_data[response_offsets[i]] = field
        
        if fields[0] == '1':
            response.status = GatewayResponse.APPROVED
        elif fields[0] == '2':
            response.status = GatewayResponse.DECLINED
        elif fields[0] == '3':
            response.status = GatewayResponse.ERROR
        else:
            response.status = GatewayResponse.UNKNOWN
        
        response.message = fields[3]
        response.avs_result = fields[5]
        response.trans_id = fields[6]
        
        return response
    
    def _prepare_fields(self, fields):
        """ Prepare fields for sending to Authorize.net """
        # a comma would break the CSV response
        fields = dict([k,str(v).replace(',', '')] for (k,v) in fields.iteritems())
        fields['x_delim_char'] = self.DELIM_CHAR # in-case it's a comma
        
        return urllib.urlencode(fields)
    
    def sale(self, amount, card, order=None, customer=None):
        """ 
        Send a credit card AUTH_CAPTURE request to the Authorize.Net gateway.
        
        Args
            amount - The amount of the order.
            card - A CreditCard object containing valid credit card info.
            order - An optional Order object specifying order details.
            customer - An optional Customer object specifying customer info.

        Returns:
            A GatewayResponse object.
        """
        fields = self._create_common_fields(card, order, customer)
        fields.update({
            'x_type': 'AUTH_CAPTURE',
            'x_amount': str(amount),
        })

        # send request
        response = self.request(self.get_request_url(), 
                                self._prepare_fields(fields))

        return self.parse_response(response)
        
    def __str__(self):
        return "Authorize.Net Advanced Integration Method (AIM)"
    
    def test_response(self, response_code):
        """
        Test a response code.
        
        The Authorize.Net API provides a means of testing each response reason
        code using a special credit card number and specifying the response
        code you want the server to return as the dollar amount of the sale. 
        This method does just that.
        
        Args
            response_code - The response code you want to test
        
        Returns
            The GatewayResponse object from a call to the sale() method.
        """
        mode = self.use_test_mode
        url = self.use_test_url
        
        self.use_test_mode = self.use_test_url = True
        
        card = CreditCard(
            number = '4222222222222',
            month = '10',
            year = '2020',
            first_name = 'John',
            last_name = 'Doe',
            code = '123'    
        )
        
        response = self.sale(response_code, card)
        
        self.use_test_mode = mode
        self.use_test_url = url
        
        return response
    
    def void(self, trans_id, card=None, order=None, customer=None):
        """ 
        Send a credit card VOID request to the Authorize.Net gateway.
        
        Args
            trans_id - The transaction ID found in the GatewayResponse object
                returned from a previous call to the authorize() or sale() 
                methods.

        Returns:
            A GatewayResponse object.
        """
        fields = self._create_common_fields(card, order, customer)
        fields.update({
            'x_type': 'VOID',
            'x_trans_id': trans_id
        })

        # send request
        response = self.request(self.get_request_url(), 
                                self._prepare_fields(fields))

        return self.parse_response(response)
