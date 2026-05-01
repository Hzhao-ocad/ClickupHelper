import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import uvicorn
from app.config import Settings


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=[str(backend_dir)],
        log_level=settings.log_level,
    )
