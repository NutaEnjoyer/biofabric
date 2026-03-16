from datetime import datetime, timedelta
from jose import jwt

def sign_jwt(payload, secret, ttl_minutes):
    to_encode = payload.copy()
    to_encode['exp'] = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    return jwt.encode(to_encode, secret, algorithm='HS256')
