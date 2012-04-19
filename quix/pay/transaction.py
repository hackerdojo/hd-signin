class Address(object):
    """
    Address used in a payment gateway transaction.
    """
    def __init__(self, first_name=None, last_name=None, company=None, 
                 address1=None, address2=None, city=None, state_province=None,
                 postal_code=None, country=None, phone=None, fax=None):
        """
        Initializes a new mailing address. All arguments should be strings or 
        None.
        
        Args
            first_name - First name
            last_name - Last name
            company - A company/organization name or None.
            address1 - First line of the street address.
            address2 - Second line of street address (such as APT or SUITE) or
                None.
            city - Name of the city.
            state_province - State or province in ISO 3166-2 or FIPS 10-4 
                string e.g., 'CA' for California, 'ON' for Ontario, etc.
                http://www.iso.org/iso/country_codes/background_on_iso_3166/iso_3166-2.htm
                http://www.itl.nist.gov/fipspubs/fip10-4.htm
            postal_code - 5-digit US Zip Code or a postal code as a string e.g., 
                'L5NV2', '97217', etc.
            country - ISO 3166 Country Code as a string e.g., 'US', 'GB', etc.
                http://www.iso.org/iso/english_country_names_and_code_elements
            phone - A phone number as a string e.g., '(555) 555-5555'.
            fax - A fax number as a string. e.g., '(555) 555-5555'.

        """
        self.first_name = first_name
        self.last_name = last_name
        self.company = company
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state_province = state_province.upper()
        self.postal_code = postal_code
        self.country = country.upper()
        self.phone = phone 
        self.fax = fax 
        
    def __str__(self):
        sections = [
            "%s %s" % (self.first_name or '', self.last_name or ''),
            self.company or '',
            self.address1 or '',
            self.address2 or '',
            self.city or '',
            "%s %s %s" % (self.state_province or '', self.postal_code or '', 
                          self.country or '')
        ]
        return ', '.join(sections)
    
class Check(object):
    """
    Electronic check information used in a payment gateway transaction.
    """
    pass
    
class CreditCard(object):
    """
    Credit card information used in a payment gateway transaction.
    """
    TYPES = (
        'Visa',
        'MasterCard',
        'American Express',
        'Discover',
        'Diners Club',
        'JCB'
    )
    
    def __init__(self, number, first_name, last_name, month, year, code=None):
        self.number = number
        self.first_name = first_name
        self.last_name = last_name
        self.month = month
        self.year = year
        self.code = code
        self.type = None
    
    def is_valid(self):
        """ 
        Checks if the credit card number is valid.
        """

        return True

class Customer(object):
    """
    Customer information used in a payment gateway transaction.
    """
    def __init__(self, cust_id=None, email=None, ip=None, billing_address=None, 
                 shipping_address=None):
        """
        Initializes a Customer instance.
        
        Args
            cust_id - A merchant assigned ID for the customer
            email - A valid email address string or None.
            ip - An IP address e.g. '255.255.255.255' or None.
            billing_address - An Address object instance or None.
            shipping_address - An Address object instance or None.
        """
        self.cust_id = cust_id
        self.email = email
        self.ip = ip
        self.billing_address = billing_address
        self.shipping_address = shipping_address

class Item(object):
    """
    Item information used in an Order passed to a payment gateway transaction.
    """
    def __init__(self, item_id=None, name=None, description=None, qty=None, 
                 price=None):
        """
        Initializes an Item instance.
        
        Args
            item_id - The ID of SKU of the item or None
            name - The name of the item or None
            description - A short description of the item or None
            qty - The quantity of the item purchased or None
            price - The price per unit of the item or None
        """
        self.item_id = item_id
        self.name = name
        self.description = description
        self.qty = qty
        self.price = price
        
    
class Order(object):
    """
    Order information used in a payment gateway transaction.
    """
    def __init__(self, order_id=None, description=None, items=None):
        """
        Initializes an Order instance.
        
        Args
            order_id - The unique order ID or None
            description - A short description of the order or None
            items - A list of Item objects or None
        """
        self.order_id = order_id
        self.description = description
        self.items = items

       
