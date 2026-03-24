from django.core import signing

def generate_verification_token(email):
    return signing.dumps(email, salt="email-verification")

def verify_token(token, max_age=86400):  # expires after 24 hrs
    try:
        return signing.loads(token, salt="email-verification", max_age=max_age)
    except (signing.SignatureExpired, signing.BadSignature):
        return None