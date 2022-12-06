from base64 import decode
from grab import Grab
import json 
import logging

# done

LOGR = logging.getLogger(__name__)

class AuthenticateDevice:
    """
    This class is used to authenticate with the Microsoft Graph API and Outlook 

    Attributes
    ----------
    url : str
        url of the current url
    code : str
        The code given by the device code 
    response : str
        The current response of the grab object go command
    tenant_id : str
        The Directory (tenant) ID that is shown on the Microsoft Azure Project Page 
    
    Methods
    -------
    find_value_to_key
        Given a target, find the value that is associated to it in the g.doc response
    decode_response
        Returns the utf-8 of the g.doc.body response 
    connect
        Goes through authentication proccess
    """

    def __init__(self, url, code, credential, tenant_id) -> None:
        self.url = 'https://microsoft.com/devicelogin'
        self.code = code
        self.response = ""
        self.credential = credential
        self.tenant_id = tenant_id
        self.connect()

    def debug_print_code(self, g):
        print("status code: " + str(g.doc.code))
        

    def debug_print_response(self, g):
        body = g.doc.body
        body_as_string = body.decode("utf-8")
        print(body_as_string)

    def debug_print_url(self, g):
        print("URL destination: " + g.doc.url)

    def g_doc_to_json(self, g):
        body_as_string = (g.doc.body).decode("utf-8")
        j = json.loads(body_as_string)
        return j

    def find_value_to_key(self, g, target):
        """
        Given a target, find the value that is associated to it in the g.doc response

        Parameters 
        ----------
        g : Grab Object
        target : str
            The name of the keyword 
        """

        response = (g.doc.body).decode("utf-8")
        is_ctx = False
        if target == 'ctx':
            is_ctx = True
            findNext = True
        displacer  = 0
        index = 0
        while True:
            index = (response).find(target, index + displacer)

            if (index == -1):
                #LOGR.exception('%s does not exist in the response from %s', target, g.doc.url)
                raise Exception(target + " does not exist in the response from " + g.doc.url)

            value_type = (response)[index + len(target)]
            
            if (value_type == '\"'):
                if ((response)[index + len(target) + 2: index + len(target) + 7] == "value"):
                    target = "value"
                    continue

                start_index = index + len(target) + 3
                break
            elif (value_type == '='):

                if (is_ctx == True and findNext == True):
                    findNext = False
                    continue
                if ((response)[index + len(target) + 1] == "\""):
                    start_index = index + len(target) + 2
                    break
                else:
                    start_index = index + len(target) + 1
                    break
            
            if (displacer != 1):
                displacer = displacer + 1

            
        end_index = (response).find('\"', start_index)

        return (response)[start_index:end_index]

    def decode_response(self, g):
        """
        Returns the utf-8 of the g.doc.body response 

        Parameters
        ----------
        g : Grab Object
        
        """

        return (g.doc.body).decode("utf-8")

    def connect(self):
        """
        Goes through authentication proccess
        """

        g = Grab()
        g.go(self.url)
        self.response = self.decode_response(g)

        canary = self.find_value_to_key(g, 'canary')
        sessionId = self.find_value_to_key(g, 'sessionId')
        
        #####################################################

        url = "https://login.microsoftonline.com/common/oauth2/deviceauth?code=" + self.code
        g.go(url)
        self.response = self.decode_response(g)
        
        #####################################################

        url = '	https://login.microsoftonline.com/common/oauth2/deviceauth'
        
        payload = {
            'otc': self.code,
            'canary': canary,
            'flowToken': '',
            'hpgrequestid': sessionId
        }

        g.go(url, post=payload)
        self.response = self.decode_response(g)

        sFT = self.find_value_to_key(g, 'sFT') # this is the flowToken
        ctx = self.find_value_to_key(g, 'ctx')
        
        #####################################################

        url = 'https://login.microsoftonline.com/common/GetCredentialType?mkt=en-US'
        payload = {
            'country': 'US',
            'flowToken': sFT,
            'username': self.credential[0]
        }
        payload_as_json = json.dumps(payload)

        g.go(url, post=payload_as_json)
        self.response = self.decode_response(g)

        #####################################################

        # login
        url = 'https://login.microsoftonline.com/' + self.tenant_id + '/login'
  
        header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': 1,
            'Host': 'login.microsoftonline.com',
            'Origin': 'https://login.microsoftonline.com', 
            'Referer': 'https://login.microsoftonline.com/common/oauth2/deviceauth',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0'
        }

        payload = {
            'i13': '0',
            'login': self.credential[0],
            'loginfmt': self.credential[0],
            'type': '11',
            'LoginOptions': '3',
            'passwd': self.credential[1],
            'ps': '2',
            'canary': canary,
            'ctx': ctx,
            'hpgrequestid': sessionId,
            'flowToken': sFT,
        }

        g.setup(headers=header)
        
        g.go(url, post=payload)
        self.response = self.decode_response(g)
        
        #####################################################
        
        g2 = Grab()
        #self.debug_print_response(g)

        scope = self.find_value_to_key(g, 'scope')
        response_mode = self.find_value_to_key(g, 'response_mode')
        id_token_hint = self.find_value_to_key(g, 'id_token_hint')
        response_type = self.find_value_to_key(g, 'response_type')
        client_id = self.find_value_to_key(g, 'client_id')
        redirect_uri = self.find_value_to_key(g, 'redirect_uri')
        claims = self.find_value_to_key(g, 'claims')
        client_request_id = self.find_value_to_key(g, 'client-request-id')
        nonce = self.find_value_to_key(g, 'nonce')
        ExternalClaimsProviderAuthorizeEndpointUri = self.find_value_to_key(g, 'ExternalClaimsProviderAuthorizeEndpointUri')
        state = self.find_value_to_key(g, 'state')
        flowToken = self.find_value_to_key(g, 'flowtoken')
        canary = self.find_value_to_key(g, 'canary')
        

        payload = [
            ('scope', scope),
            ('response_mode', response_mode),
            ('id_token_hint', id_token_hint),
            ('response_type', response_type),
            ('client_id', client_id),
            ('redirect_uri', redirect_uri),
            ('claims', claims),
            ('client-request-id', client_request_id),
            ('nonce', nonce),
            ('ExternalClaimsProviderAuthorizeEndpointUri', ExternalClaimsProviderAuthorizeEndpointUri),
            ('state', state),
            ('flowtoken', flowToken),
            ('canary', canary),
        ]

        header = {
            'Host': 'login.microsoftonline.com',
            'Origin': 'https://login.microsoftonline.com',
            'Referer': 'https://login.microsoftonline.com/common/login',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0'
        }

        g2.setup(headers=header)
        g2.go('https://login.microsoftonline.com/federation/redirecttoexternalprovider', multipart_post=payload)
        

        #####################################################

        g2.submit()

        #####################################################
        g2.submit()
        
        #####################################################
        g2.submit()
        # the response has _xsrf token 
        xsrf = self.find_value_to_key(g2, '_xsrf')
    
        # The sid is created through a 302 redirect
        start_index = (g2.doc.url).find('sid=')
        sid = (g2.doc.url)[start_index + 4:]
        exit_request_referrer = g2.doc.url
        
        #####################################################
        g2.submit()

        prompt_response_as_json = self.g_doc_to_json(g2)
        txid = prompt_response_as_json['response']['txid']

        #####################################################
        url = 'https://api-cd3ecedb.duosecurity.com/frame/v4/status'

        header = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Host': 'api-cd3ecedb.duosecurity.com',
            'Origin': 'https://api-cd3ecedb.duosecurity.com',
            'Referer': exit_request_referrer,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0'
        }

        payload = {
            'txid': txid,
            'sid': sid
        }
       
        g2.go(url, post=payload)

        #####################################################
     
        g2.go(url, post=payload)
      
        #####################################################
        #exit
        url = 'https://api-cd3ecedb.duosecurity.com/frame/v4/oidc/exit'
        payload = [
            ('sid', sid),
            ('txid', txid),
            ('factor', 'Duo+Push'), 
            #('device_key', 'device_key'), # need to find device key instead of hardcode 
            ('_xsrf', xsrf),
            ('dampen_choice', 'true')
        ]
        
        g2.go(url, multipart_post=payload)
        
        #####################################################

        g2.submit()

        #####################################################

        ctx = self.find_value_to_key(g2, 'sCtx')
        hpgrequestid = self.find_value_to_key(g2, 'sessionId')
        flowToken = self.find_value_to_key(g2, 'sFT')

        start_index = (self.decode_response(g2)).find('canary":"')
        end_index = (self.decode_response(g2)).find('\"', start_index + 10)
        canary = (self.decode_response(g2))[start_index + 9: end_index]
    
        url = 'https://login.microsoftonline.com/appverify'

        payload = [
            ('ContinueAuth', 'true'),
            ('ctx', ctx),
            ('hpgrequestid', hpgrequestid),
            ('flowToken', flowToken),
            ('canary', canary),
        ]

        g2.go(url, multipart_post=payload)