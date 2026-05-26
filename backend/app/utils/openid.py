import re
import httpx
from urllib.parse import urlencode

class SteamOpenID:
    
    STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
    
    @classmethod
    def get_login_url(cls, return_to: str) -> str:
        params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': return_to,
            'openid.realm': return_to.split('/callback')[0],  # Base URL
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
        }
        return f"{cls.STEAM_OPENID_URL}?{urlencode(params)}"
    
    @classmethod
    async def verify_response(cls, params: dict) -> str:

        required_params = [
            'openid.mode', 'openid.op_endpoint', 'openid.claimed_id',
            'openid.identity', 'openid.return_to', 'openid.response_nonce',
            'openid.assoc_handle', 'openid.signed', 'openid.sig'
        ]
        
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        verification_params = dict(params)
        verification_params['openid.mode'] = 'check_authentication'
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                cls.STEAM_OPENID_URL,
                data=verification_params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise ValueError("Steam verification request failed")
            
            verification_response = response.text
            if 'is_valid:true' not in verification_response:
                raise ValueError("Steam authentication verification failed")
        
        claimed_id = params.get('openid.claimed_id', '')
        steam_id_match = re.search(r'steamcommunity\.com/openid/id/(\d+)', claimed_id)
        
        if not steam_id_match:
            raise ValueError("Could not extract Steam ID from response")
        
        return steam_id_match.group(1)