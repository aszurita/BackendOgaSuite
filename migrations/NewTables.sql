-- ============================================================
-- OGA Suite Backend - Migration 001
-- Nuevas tablas requeridas para el backend profesional
-- Ejecutar en: BG_OGASUITE
-- ============================================================

-- ============================================================
-- TABLA 1: t_oga_usuarios
-- Reemplaza la lista hardcodeada de emails OGA en el frontend.
-- Permite gestionar miembros OGA desde BD sin redeploy.
-- ============================================================
USE BG_OGASUITE;
CREATE TABLE IF NOT EXISTS t_oga_usuarios (
    id              INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255)  NOT NULL,
    nombre_completo VARCHAR(255)  NULL,
    username        VARCHAR(100)  NULL,
    rol             VARCHAR(50)   NOT NULL DEFAULT 'OGA_MEMBER',
    sn_activo       TINYINT(1)    NOT NULL DEFAULT 1,
    fecha_alta      DATETIME      NOT NULL DEFAULT NOW(),
    fecha_baja      DATETIME      NULL,
    agregado_por    VARCHAR(255)  NULL,
    CONSTRAINT UQ_oga_usuarios_email UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO t_oga_usuarios (email, username, rol) VALUES
('jgutierrez@bancoguayaquil.com', 'jgutierrez', 'OGA_ADMIN'),
('hangulo@bancoguayaquil.com',    'hangulo',    'OGA_MEMBER'),
('kmejia@bancoguayaquil.com',     'kmejia',     'OGA_MEMBER'),
('klamilla@bancoguayaquil.com',   'klamilla',   'OGA_MEMBER'),
('pramos@bancoguayaquil.com',     'pramos',     'OGA_MEMBER'),
('dramirez1@bancoguayaquil.com',  'dramirez1',  'OGA_MEMBER'),
('mmata@bancoguayaquil.com',      'mmata',      'OGA_MEMBER');

-- ============================================================
-- TABLA 2: t_auditoria_cambios
-- Log inmutable de todos los cambios realizados a traves del backend.
-- Requerido por compliance regulatorio del banco.
-- ============================================================
CREATE TABLE IF NOT EXISTS t_auditoria_cambios (
    id               BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tabla_afectada   VARCHAR(200)  NOT NULL,
    operacion        VARCHAR(10)   NOT NULL,
    registro_id      VARCHAR(100)  NULL,
    campo_modificado VARCHAR(200)  NULL,
    valor_anterior   TEXT          NULL,
    valor_nuevo      TEXT          NULL,
    usuario_email    VARCHAR(255)  NULL,
    usuario_codigo   VARCHAR(50)   NULL,
    fecha_cambio     DATETIME      NOT NULL DEFAULT NOW(),
    modulo           VARCHAR(100)  NULL,
    id_aprobacion    INT           NULL,
    detalle_json     TEXT          NULL,
    INDEX IX_auditoria_tabla_fecha (tabla_afectada, fecha_cambio),
    INDEX IX_auditoria_usuario     (usuario_email,  fecha_cambio),
    INDEX IX_auditoria_modulo      (modulo,         fecha_cambio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA 3: t_configuracion_app
-- Parametros de configuracion de la aplicacion gestionables
-- en caliente sin necesidad de redeploy del backend.
-- ============================================================
CREATE TABLE IF NOT EXISTS t_configuracion_app (
    clave              VARCHAR(100)  NOT NULL PRIMARY KEY,
    valor              TEXT          NOT NULL,
    descripcion        VARCHAR(500)  NULL,
    tipo_dato          VARCHAR(20)   NOT NULL DEFAULT 'string',
    modulo             VARCHAR(100)  NULL,
    fecha_modificacion DATETIME      NOT NULL DEFAULT NOW(),
    modificado_por     VARCHAR(255)  NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO t_configuracion_app (clave, valor, descripcion, tipo_dato, modulo) VALUES
('cache_arbol_ttl_minutos',    '15',    'TTL en minutos del arbol de metadatos en cache servidor',  'int',    'metadatos'),
('cache_terminos_ttl_minutos', '10',    'TTL en minutos del glosario en cache servidor',             'int',    'glosario'),
('cache_permisos_ttl_minutos', '5',     'TTL en minutos del cache de permisos por usuario',          'int',    'auth'),
('registrar_visitas_activo',   '1',     'Activar (1) o desactivar (0) el registro de visitas',       'bool',   'analytics'),
('version_api',                '1.0.0', 'Version actual del backend OGA Suite',                      'string', 'sistema');

-- ============================================================
-- TABLA 4: T_VISITAS_OGA_NEW
-- Registro de navegacion de usuarios en OGA Suite.
-- Sustituye el hook useRegistrarVisita.js del frontend.
-- ============================================================
CREATE TABLE IF NOT EXISTS T_VISITAS_OGA_NEW (
    id               INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    USUARIO          VARCHAR(100)  NULL,
    CODIGO_EMPLEADO  VARCHAR(20)   NULL,
    DESC_PAGINA      VARCHAR(500)  NULL,
    SUB_PAGINA       VARCHAR(500)  NULL,
    CENTRO_COSTO     VARCHAR(200)  NULL,
    DEPARTAMENTO     VARCHAR(200)  NULL,
    FECHA            DATETIME(3)   NOT NULL DEFAULT NOW(3),
    INDEX IX_visitas_usuario   (USUARIO,    FECHA),
    INDEX IX_visitas_pagina    (DESC_PAGINA, FECHA)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- FIN Migration 001
-- ============================================================
