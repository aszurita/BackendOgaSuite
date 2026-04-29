from pydantic import BaseModel


class UserInfo(BaseModel):
    email: str
    display_name: str
    username: str
    codigo_empleado: str | None = None
    centro_costo: str | None = None
    departamento: str | None = None
    cargo: str | None = None
    localidad: str | None = None


class GlosarioPermisos(BaseModel):
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False


class MetadatosPermisos(BaseModel):
    can_edit_direct: bool = False
    requires_approval: bool = True


class AprobacionesPermisos(BaseModel):
    can_approve: bool = False
    can_reject: bool = False


class DominiosPermisos(BaseModel):
    can_create: bool = False
    can_edit: bool = False


class CampaniasPermisos(BaseModel):
    can_manage: bool = False


class PermissionsMap(BaseModel):
    glosario: GlosarioPermisos
    metadatos: MetadatosPermisos
    aprobaciones: AprobacionesPermisos
    dominios: DominiosPermisos
    campanias: CampaniasPermisos


class MeResponse(BaseModel):
    user: UserInfo
    is_oga: bool
    permissions: PermissionsMap


class CurrentUser(BaseModel):
    """Objeto de usuario inyectado por Depends en los endpoints."""
    email: str
    display_name: str
    username: str
    codigo_empleado: str | None = None
    centro_costo: str | None = None
    departamento: str | None = None
    cargo: str | None = None
    localidad: str | None = None
    is_oga: bool = False
    permissions: PermissionsMap | None = None

    model_config = {"arbitrary_types_allowed": True}
