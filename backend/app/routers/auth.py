import random
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse

from app.core.database import SessionLocal
from app.models.db_models import User
from app.models.schemas import UserRegister, UserLogin, VerifyOTP, TokenResponse, UserOut
from app.services.security_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_google_auth_url,
    exchange_google_code,
)
from app.services.email_service import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


@router.post("/register", response_model=dict)
async def register(req: UserRegister):
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
        if existing:
            if existing.is_verified:
                raise HTTPException(status_code=400, detail="Email sudah terdaftar. Silakan login.")

            # Resend OTP for unverified user
            otp_code = generate_otp()
            existing.otp_code = otp_code
            existing.otp_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            if req.name:
                existing.name = req.name
            existing.hashed_password = hash_password(req.password)
            db.commit()

            asyncio.create_task(send_otp_email(existing.email, otp_code))
            return {"message": "Kode OTP verifikasi telah dikirim ulang ke email Anda.", "email": existing.email}

        otp_code = generate_otp()
        now_iso = datetime.now(timezone.utc).isoformat()
        otp_expire = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        new_user = User(
            name=req.name or req.email.split("@")[0],
            email=req.email.lower().strip(),
            hashed_password=hash_password(req.password),
            is_verified=False,
            auth_provider="email",
            otp_code=otp_code,
            otp_expires_at=otp_expire,
            created_at=now_iso,
        )
        db.add(new_user)
        db.commit()

        asyncio.create_task(send_otp_email(new_user.email, otp_code))
        return {"message": "Pendaftaran berhasil! Kode OTP verifikasi telah dikirim ke email Anda.", "email": new_user.email}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(req: VerifyOTP):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == req.email.lower().strip()).first()
        if not user:
            raise HTTPException(status_code=404, detail="Email pengguna tidak ditemukan.")

        if not user.otp_code or user.otp_code != req.otp_code.strip():
            raise HTTPException(status_code=400, detail="Kode OTP tidak valid.")

        if user.otp_expires_at:
            expire_dt = datetime.fromisoformat(user.otp_expires_at)
            if datetime.now(timezone.utc) > expire_dt:
                raise HTTPException(status_code=400, detail="Kode OTP sudah kadaluarsa. Silakan minta kode baru.")

        user.is_verified = True
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()
        db.refresh(user)

        token = create_access_token({"sub": str(user.id), "email": user.email})
        user_out = UserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        )
        return TokenResponse(access_token=token, token_type="bearer", user=user_out)


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == req.email.lower().strip()).first()
        if not user:
            raise HTTPException(status_code=400, detail="Email atau password salah.")

        if not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Email atau password salah.")

        if not user.is_verified:
            otp_code = generate_otp()
            user.otp_code = otp_code
            user.otp_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.commit()
            asyncio.create_task(send_otp_email(user.email, otp_code))
            raise HTTPException(
                status_code=403,
                detail="Akun belum diverifikasi. Kode OTP baru telah dikirim ke email Anda.",
            )

        token = create_access_token({"sub": str(user.id), "email": user.email})
        user_out = UserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        )
        return TokenResponse(access_token=token, token_type="bearer", user=user_out)


@router.get("/google/login")
async def google_login():
    url = get_google_auth_url()
    return {"url": url}


@router.get("/google/callback")
async def google_callback(code: str):
    try:
        google_profile = await exchange_google_code(code)
        email = google_profile.get("email", "").lower().strip()
        name = google_profile.get("name", email.split("@")[0])

        if not email:
            raise HTTPException(status_code=400, detail="Email tidak ditemukan dari profil Google.")

        with SessionLocal() as db:
            user = db.query(User).filter(User.email == email).first()
            now_iso = datetime.now(timezone.utc).isoformat()
            if not user:
                user = User(
                    name=name,
                    email=email,
                    is_verified=True,
                    auth_provider="google",
                    created_at=now_iso,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            elif not user.is_verified:
                user.is_verified = True
                user.auth_provider = "google"
                db.commit()
                db.refresh(user)

            token = create_access_token({"sub": str(user.id), "email": user.email})
            # Redirect to frontend with token parameter
            redirect_url = f"http://localhost:3000/?token={token}"
            return RedirectResponse(url=redirect_url)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal memproses OAuth Google: {exc}")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        is_verified=current_user.is_verified,
        auth_provider=current_user.auth_provider,
        created_at=current_user.created_at,
    )
