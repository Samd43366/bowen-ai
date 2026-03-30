from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.core.security import decode_access_token
from app.services.firestore_services import get_user_by_id

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Inject doc_access claim if present in token
        user["doc_access"] = payload.get("doc_access", False)

        # Log daily activity
        try:
            from app.services.analytics_services import log_user_activity
            log_user_activity(user["email"])
        except Exception:
            pass

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    if not credentials:
        return None

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            return None

        user = await get_user_by_id(user_id)
        return user

    except Exception:
        return None

async def admin_required(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def superadmin_required(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user

async def document_admin_required(current_user: dict = Depends(admin_required)):
    if not current_user.get("doc_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document OTP authorization required"
        )
    return current_user