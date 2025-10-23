from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    return {"message": "Logs router funcionando"}

@router.get("/audit")
async def get_audit_logs():
    return {"message": "Audit logs endpoint funcionando"}
