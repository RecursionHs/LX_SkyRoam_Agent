from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import urlparse

router = APIRouter()

_ALLOWED_HOSTS = {
    "sns-img-hw.xhscdn.com",
    "sns-img-qc.xhscdn.com",
    "sns-img-bd.xhscdn.com",
    "img.xiaohongshu.com",
    "ci.xiaohongshu.com",
}

def _is_allowed_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if host in _ALLOWED_HOSTS:
            return True
        # 允许子域的通配
        return host.endswith(".xhscdn.com") or host.endswith(".xiaohongshu.com")
    except Exception:
        return False

@router.get("/image")
async def proxy_image(url: str = Query(..., description="图片源URL")):
    if not _is_allowed_host(url):
        raise HTTPException(status_code=400, detail="不支持的图片来源")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.xiaohongshu.com/",
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"源站请求失败: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="源站返回非200")

    content_type = resp.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="非图片内容")

    return StreamingResponse(resp.aiter_bytes(), media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})

