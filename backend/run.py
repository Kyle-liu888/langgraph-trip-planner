"""启动脚本"""

import uvicorn
import sys
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        loop="app.event_loop:selector_factory" if sys.platform == "win32" else "auto",
        log_level=settings.log_level.lower()
    )
