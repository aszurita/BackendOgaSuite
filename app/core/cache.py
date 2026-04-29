from cachetools import TTLCache
from threading import Lock
from app.core.config import settings

# Cache del arbol de metadatos (servidor->base->esquema->tablas)
_arbol_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.CACHE_TTL_ARBOL_SEGUNDOS)
_arbol_lock = Lock()

# Cache de permisos por usuario (email -> permisos)
_permisos_cache: TTLCache = TTLCache(maxsize=500, ttl=settings.CACHE_TTL_PERMISOS_SEGUNDOS)
_permisos_lock = Lock()

# Cache de terminos/glosario
_terminos_cache: TTLCache = TTLCache(maxsize=2, ttl=settings.CACHE_TTL_TERMINOS_SEGUNDOS)
_terminos_lock = Lock()

# Cache del JWKS de Azure AD (24 horas)
_jwks_cache: TTLCache = TTLCache(maxsize=1, ttl=86400)
_jwks_lock = Lock()


def get_arbol_cache() -> TTLCache:
    return _arbol_cache

def get_arbol_lock() -> Lock:
    return _arbol_lock

def get_permisos_cache() -> TTLCache:
    return _permisos_cache

def get_permisos_lock() -> Lock:
    return _permisos_lock

def get_terminos_cache() -> TTLCache:
    return _terminos_cache

def get_terminos_lock() -> Lock:
    return _terminos_lock

def get_jwks_cache() -> TTLCache:
    return _jwks_cache

def get_jwks_lock() -> Lock:
    return _jwks_lock


def invalidar_arbol_cache() -> None:
    with _arbol_lock:
        _arbol_cache.clear()

def invalidar_terminos_cache() -> None:
    with _terminos_lock:
        _terminos_cache.clear()

def invalidar_permisos_usuario(email: str) -> None:
    with _permisos_lock:
        _permisos_cache.pop(email, None)
