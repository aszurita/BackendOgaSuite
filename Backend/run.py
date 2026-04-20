"""
Punto de entrada del servidor.
Ejecutar: python run.py
"""
import uvicorn
from app.config import APP_HOST, APP_PORT

if __name__ == "__main__":
    print(f"Iniciando OGA Gestion API en http://{APP_HOST}:{APP_PORT}")
    print(f"  Swagger UI : http://localhost:{APP_PORT}/docs")
    print(f"  Scalar     : http://localhost:{APP_PORT}/scalar")
    print(f"  Health     : http://localhost:{APP_PORT}/health")
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True,
    )
