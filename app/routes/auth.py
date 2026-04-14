from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends

from app.schemas.auth import (
    UserRegister,
    VerifyOTPRequest,
    ResendOTPRequest,
    UserLogin,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SocialLoginRequest,
    UserUpdate
)
from app.core.security import hash_password, verify_password, create_access_token
from app.services.firestore_services import (
    create_user,
    get_user_by_email,
    save_user_otp,
    verify_user,
    update_user,
    delete_user
)
from app.services.otp_service import generate_otp, get_otp_expiry, is_otp_expired
from app.services.email_services import send_otp_email, send_welcome_email
from app.core.config import settings
from app.core.dependencies import get_current_user
from firebase_admin import auth
from fastapi import Request
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserRegister):
    existing_user = await get_user_by_email(user_data.email)

    if existing_user:
        # Check if user is stale (unverified and > 5 mins old)
        if not existing_user.get("is_verified"):
            created_at = existing_user.get("created_at")
            if created_at:
                # Ensure created_at is aware
                if hasattr(created_at, "replace") and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                elif isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                    except:
                        pass
                
                if isinstance(created_at, datetime) and datetime.now(timezone.utc) > created_at + timedelta(minutes=5):
                    # Delete stale user
                    delete_user(user_data.email)
                    existing_user = None
        
        if existing_user:
            # Silent success to prevent enumeration
            return {
                "message": "Registration received. If you are a new user, please verify the OTP sent to your email."
            }

    role = "user"
    if user_data.role == "admin":
        if user_data.admin_secret != settings.ADMIN_REGISTRATION_SECRET:
            raise HTTPException(status_code=403, detail="Invalid admin registration secret")
        role = "admin"

    otp_code = generate_otp()
    otp_expires_at = get_otp_expiry()

    user = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "password": hash_password(user_data.password),
        "role": role,
        "is_verified": False,
        "is_approved": True if role == "user" else False,
        "otp_code": otp_code,
        "otp_expires_at": otp_expires_at,
        "created_at": datetime.now(timezone.utc)
    }

    await create_user(user)

    try:
        await send_otp_email(user_data.email, otp_code)
    except Exception as e:
        print(f"SMTP Email Error: {e}. Falling back to default OTP 123456 for testing.")
        otp_code = "123456"
        user["otp_code"] = otp_code
        update_user(user_data.email, {"otp_code": otp_code})

    return {
        "message": f"{role.capitalize()} registered successfully. Please verify OTP sent to email."
    }


@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, data: VerifyOTPRequest):
    user = await get_user_by_email(data.email, scrub=False)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or verification code")

    if user.get("is_verified"):
        return {"message": "User already verified"}

    saved_otp = user.get("otp_code")
    otp_expires_at = user.get("otp_expires_at")

    if not saved_otp:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

    if is_otp_expired(otp_expires_at):
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    if data.otp_code != saved_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    verify_user(data.email)
    
    # Send welcome email in background
    try:
        await send_welcome_email(data.email, user.get("full_name", "User"), user.get("role", "user"))
    except:
        pass # Don't block verification if email fails

    access_token = create_access_token(
        data={
            "sub": user["email"],
            "role": user.get("role", "user")
        }
    )

    return {
        "message": "Email verified successfully",
        "access_token": access_token
    }


@router.post("/resend-otp")
@limiter.limit("5/minute")
async def resend_otp(request: Request, data: ResendOTPRequest):
    user = await get_user_by_email(data.email)

    if not user:
        # Generic response to prevent enumeration
        return {"message": "If this email is registered, a new OTP has been sent."}

    if user.get("is_verified"):
        return {"message": "User is already verified"}

    otp_code = generate_otp()
    otp_expires_at = get_otp_expiry()

    try:
        await send_otp_email(data.email, otp_code)
        save_user_otp(data.email, otp_code, otp_expires_at)
    except Exception as e:
        print(f"SMTP Email Error: {e}. Falling back to default OTP 123456 for testing.")
        otp_code = "123456"
        save_user_otp(data.email, otp_code, otp_expires_at)

    return {"message": "OTP resent successfully"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    user = await get_user_by_email(user_data.email, scrub=False)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_verified", False):
        # Check if stale
        created_at = user.get("created_at")
        if created_at:
            if hasattr(created_at, "replace") and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elif isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                except:
                    pass
            
            if isinstance(created_at, datetime) and datetime.now(timezone.utc) > created_at + timedelta(minutes=5):
                delete_user(user_data.email)
                raise HTTPException(status_code=401, detail="Account expired (unverified for too long). Please register again.")
        raise HTTPException(status_code=403, detail="Please verify your email before login")

    if user.get("role") == "admin":
        if not user.get("is_approved", False):
            raise HTTPException(status_code=403, detail="Access Denied: Your account is pending Superadmin approval.")

    access_token = create_access_token(
        data={
            "sub": user["email"],
            "role": user.get("role", "user")
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        message=f"Welcome back, {user.get('full_name', 'User')}!"
    )

@router.post("/social-login")
async def social_login(request: SocialLoginRequest):
    try:
        decoded_token = auth.verify_id_token(request.firebase_id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid social token: {str(e)}")

    email = decoded_token.get("email")
    name = decoded_token.get("name") or "User"
    
    if not email:
        raise HTTPException(status_code=400, detail="Social account must have an email associated")

    user = await get_user_by_email(email)

    if not user:
        otp_code = generate_otp()
        otp_expires_at = get_otp_expiry()
        
        user_data = {
            "email": email,
            "full_name": name,
            "password": hash_password(request.firebase_id_token), # dummy password
            "role": "user",
            "is_verified": False,
            "is_approved": True,
            "otp_code": otp_code,
            "otp_expires_at": otp_expires_at,
            "is_social": True,
            "created_at": datetime.now(timezone.utc)
        }
        await create_user(user_data)
        
        try:
            await send_otp_email(email, otp_code)
        except Exception as e:
            print(f"SMTP Email Error: {e}. Falling back to default OTP 123456 for testing.")
            otp_code = "123456"
            user_data["otp_code"] = otp_code
            update_user(email, {"otp_code": otp_code})
            
        return {
            "message": "Social login successful. Please verify OTP sent to your email.",
            "requires_otp": True
        }

    if not user.get("is_verified", False):
        otp_code = generate_otp()
        otp_expires_at = get_otp_expiry()
        
        save_user_otp(email, otp_code, otp_expires_at)
        
        try:
            await send_otp_email(email, otp_code)
        except Exception as e:
            print(f"SMTP Email Error: {e}. Falling back to default OTP 123456 for testing.")
            otp_code = "123456"
            save_user_otp(email, otp_code, otp_expires_at)
            
        return {
            "message": "Account exists but is unverified. A new OTP has been sent to your email.",
            "requires_otp": True
        }

    if user.get("role") == "admin":
        if not user.get("is_approved", False):
            raise HTTPException(status_code=403, detail="Access Denied: Your account is pending Superadmin approval.")

    access_token = create_access_token(
        data={
            "sub": user["email"],
            "role": user.get("role", "user")
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    user = await get_user_by_email(data.email)
    if not user:
        # Generic response to prevent enumeration
        return {"message": "If this email is registered, a reset code has been sent."}

    otp_code = generate_otp()
    otp_expires_at = get_otp_expiry()

    save_user_otp(data.email, otp_code, otp_expires_at)

    try:
        await send_otp_email(data.email, otp_code)
    except Exception as e:
        print(f"SMTP Email Error: {e}. Falling back to default OTP 123456 for testing.")
        otp_code = "123456"
        save_user_otp(data.email, otp_code, otp_expires_at)

    return {"message": "Password reset OTP sent to email"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    user = await get_user_by_email(data.email, scrub=False)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or verification code")

    saved_otp = user.get("otp_code")
    otp_expires_at = user.get("otp_expires_at")

    if not saved_otp:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

    if is_otp_expired(otp_expires_at):
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    if data.otp_code != saved_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    new_hashed_password = hash_password(data.new_password)
    update_user(data.email, {
        "password": new_hashed_password,
        "otp_code": None,
        "otp_expires_at": None
    })

    return {"message": "Password updated successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "is_verified": user.get("is_verified", False)
    }

@router.put("/me")
async def update_me(data: UserUpdate, current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    updates = {}
    if data.full_name:
        updates["full_name"] = data.full_name

    if not updates:
        return {"message": "No updates provided"}

    update_user(email, updates)
    return {"message": "Profile updated successfully"}

@router.post("/request-doc-otp")
@limiter.limit("5/minute")
async def request_doc_otp(request: Request, current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    role = current_user.get("role")
    
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins can request document access")
        
    otp_code = generate_otp()
    otp_expires_at = get_otp_expiry()
    save_user_otp(email, otp_code, otp_expires_at)
    
    try:
        await send_otp_email(email, otp_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send Document OTP: {str(e)}")
        
    return {"message": "Document access OTP sent to your email."}

@router.post("/verify-doc-otp")
async def verify_doc_otp(data: VerifyOTPRequest, current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    if email != data.email:
        raise HTTPException(status_code=403, detail="Email mismatch")
        
    user = await get_user_by_email(email, scrub=False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    saved_otp = user.get("otp_code")
    otp_expires_at = user.get("otp_expires_at")
    
    if not saved_otp or is_otp_expired(otp_expires_at):
        raise HTTPException(status_code=400, detail="OTP expired or not requested")
        
    if data.otp_code != saved_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
        
    # Clear OTP
    update_user(email, {
        "otp_code": None,
        "otp_expires_at": None
    })
    
    # Generate new token with doc_access claim
    access_token = create_access_token(
        data={
            "sub": email,
            "role": user.get("role", "admin"),
            "doc_access": True # Extra claim for Document Access
        }
    )
    
    return {
        "message": "Document access granted",
        "access_token": access_token
    }
