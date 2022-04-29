
import jwt
from fastapi import Request
from jwt import PyJWKClient

url = "https://aac.platform.smartcommunitylab.it/jwk"
jwks_client = PyJWKClient(url)

def decode_token(jwtoken):
    signing_key = jwks_client.get_signing_key_from_jwt(jwtoken)
    data = jwt.decode(
        jwtoken,
        signing_key.key,
        algorithms=["RS256"],
        audience="c_0e0822df-9df8-48d6-b4d9-c542a4623f1b",
        # options={"verify_exp": False},
    )
    return data

def get_token_in_cookie(request):
    try:
        return request.cookies.get("auth_token")
    except:
        return None

def get_token_in_header(request):
    try:
        return request.headers.get('authorization').replace("Bearer ", "")
    except:
        return None

def get_current_user(
    request: Request
) -> dict:
        token = get_token_in_cookie(request) or get_token_in_header(request)
        if token:
            return decode_token(token)
        return 
