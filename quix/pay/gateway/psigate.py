import base
from xml.etree import ElementTree

class XmlMessengerGateway(base.Gateway):
    test_url = 'https://dev.psigate.com:7989/Messenger/XMLMessenger'
    live_url = 'https://secure.psigate.com:7934/Messenger/XMLMessenger'

    def authorize(self, card, amount, order_num=None, description=None):
        """ Submit a card authorization request. """
        xml = self._head_xml()
        xml += "\t<CardAction>1</CardAction>\n"
        xml += "\t<Subtotal>%s</Subtotal>\n" % str(amount)
        xml += self._card_xml(card)
        
        if order_num:
            xml += "\t<OrderID>%s</OrderID>\n" % order_num
       
        if description:
            xml += "\t<Comments>%s</Comments>\n" % description
            
        if self.test_mode:
            post_url = self.test_url
        else:
            post_url = self.live_url
        
        xml += self._foot_xml()
        
        request = gateway.Request(post_url, xml, self.request_timeout)
        response = request.send()
        self.parse_response(response)
        
        return (request, response)
    
    def _card_xml(self, card):
        xml = "<CardNumber>%s</CardNumber>" % card.number
        xml += "<CardExpMonth>%s</CardExpMonth>" % card.month
        xml += "<CardExpYear>%s</CardExpYear>" % card.year[2:]
        
        return xml
        
    def _foot_xml(self):
        xml = "</Order>";
        return xml
        
    def _head_xml(self):
        xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        xml += "<Order>"
        xml += "<StoreId>%s</StoreId>" % self.login
        xml += "<Passphrase>%s</Passphrase>" % self.password
        xml += "<PaymentType>CC</PaymentType>"
        
        return xml
    
    def parse_response(self, response):
        element = ElementTree.XML(response.body)
        approved = element.find('Approved')
        errmsg = element.find('ErrMsg')
       
        if approved is None or errmsg is None:
            response.status = gateway.Response.UNKNOWN
            response.status_text = "Failed parsing response XML."
            return response

        response.status_text = approved.text
        
        if response.status_text == 'APPROVED':
            response.status = gateway.Response.APPROVED
        elif response.status_text == 'DECLINED':
            response.status = gateway.Response.DECLINED
        elif response.status_text == 'ERROR':
            response.status = gateway.Response.ERROR
            response.status_text = errmsg.text
        else:
            approved.status = gateway.Response.UNKNOWN
        
        trans = element.find('TransRefNumber')
        if trans is not None:
            response.trans_id = trans.text

        return response
        
    def __str__(self):
        return "PSiGate XML Messenger Interface"
