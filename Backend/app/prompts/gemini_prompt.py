MERMAID_PROMPT_GEMINI = """
═══════════════════════════════════════════════════════════════════════════════
🚀 PROMPT ULTRA-MEJORADO PARA GEMINI FLASH - ANÁLISIS SP CON SUBGRAFOS Y FUENTES
═══════════════════════════════════════════════════════════════════════════════
 
GEMINI: Este prompt está diseñado específicamente para que generes diagramas Mermaid
con SUBGRAFOS OBLIGATORIOS y REFERENCIAS EXPLÍCITAS A TABLAS/FUENTES. NO generes
diagramas lineales verticales ni ocultes de dónde provienen los datos.
 
═══════════════════════════════════════════════════════════════════════════════
⚡ REGLA ABSOLUTA #1: SIEMPRE USA SUBGRAFOS
═══════════════════════════════════════════════════════════════════════════════
 
❌ PROHIBIDO hacer esto:
START --> PASO1 --> PASO2 --> PASO3 --> FIN
(Todo en línea recta vertical = INCORRECTO)
 
✅ OBLIGATORIO hacer esto:
 
flowchart TB
    START(["⚙️ INICIO"]):::mainControl
   
    subgraph FASE1 ["📋 NOMBRE FASE 1"]
        direction TB
        PASO1["..."]:::clase
        PASO2["..."]:::clase
        PASO1 --> PASO2
    end
   
    START --> FASE1
    PASO2 --> FIN
    FIN(["✅ FIN"]):::mainControl
 
═══════════════════════════════════════════════════════════════════════════════
📋 ANÁLISIS OBLIGATORIO PREVIO (PASO A PASO)
═══════════════════════════════════════════════════════════════════════════════
 
GEMINI: Antes de generar el diagrama, DEBES realizar este análisis:
 
PASO 1: Lee el Stored Procedure COMPLETO
PASO 2: Identifica las FASES LÓGICAS principales (mínimo 3, máximo 7)
PASO 3: Identifica explícitamente TODAS las tablas origen (fuentes) y tablas destino.
PASO 4: Agrupa las operaciones dentro de cada fase asegurando nombrar las tablas.
PASO 5: Genera el diagrama con subgrafos.
 
═══════════════════════════════════════════════════════════════════════════════
💡 EJEMPLO DE FASES TÍPICAS EN UN SP:
═══════════════════════════════════════════════════════════════════════════════
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: INICIALIZACIÓN Y VALIDACIONES                       │
│ • Declarar variables                                        │
│ • Insertar logs de inicio                                   │
│ • Obtener periodos/fechas                                   │
│ • Contar registros de fuentes                               │
│ • Validar conteos (decisión principal)                      │
│ • Manejar errores si validación falla                       │
└─────────────────────────────────────────────────────────────┘
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: CONSTRUCCIÓN DE TABLA TEMPORAL                      │
│ • Crear tablas temporales auxiliares (#AH_META, etc.)       │
│ • DROP tabla tmp_new si existe                              │
│ • SELECT INTO tmp_new con JOINs masivos                     │
│ • UPDATEs iniciales (seguros, nómina, multicash)            │
└─────────────────────────────────────────────────────────────┘
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: APLICACIÓN DE REGLAS DE NEGOCIO                     │
│ (Esta fase puede tener SUB-FASES en subgrafos anidados)     │
│                                                             │
│ SUBFASE 3A: Lógica Comisiones TC                            │
│ • Obtener periodo IVC                                       │
│ • Crear TRB_AB_COMISIONES_TC                                │
│ • Aplicar reglas TN/RB con fechas                           │
│ • Limpiar registros que no cumplen                          │
│                                                             │
│ SUBFASE 3B: Lógica Comisiones MUC                           │
│ • Crear TMP_CODOPE_CLTE                                     │
│ • Crear múltiples TRB_AB_COMISIONES_MUC                     │
│ • Aplicar reglas de negocio específicas                     │
│ • Actualizar tmp_new con resultados                         │
└─────────────────────────────────────────────────────────────┘
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: CÁLCULO DE INDICADORES (IVC)                        │
│ • UPDATE IVC para Banca Personas                            │
│ • UPDATE IVC para Micro                                     │
│ • UPDATE IVC para Banca Empresas                            │
│ • UPDATE COD_ESTADO_DOMINIO                                 │
└─────────────────────────────────────────────────────────────┘
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 5: VALIDACIÓN FINAL Y CARGA                            │
│ • Contar registros tmp_new                                  │
│ • Validar conteo vs cltefil (decisión)                      │
│ • TRUNCATE tabla destino                                    │
│ • INSERT datos finales                                      │
│ • DROP tablas temporales                                    │
│ • UPDATE log de éxito                                       │
│ • Insertar notificación de éxito                            │
└─────────────────────────────────────────────────────────────┘
 
┌─────────────────────────────────────────────────────────────┐
│ FASE 6: MANEJO DE ERRORES (TRY-CATCH)                       │
│ • BEGIN CATCH                                               │
│ • Capturar ERROR_MESSAGE                                    │
│ • UPDATE/INSERT log de error                                │
│ • PRINT error                                               │
│ • END CATCH                                                 │
└─────────────────────────────────────────────────────────────┘
 
═══════════════════════════════════════════════════════════════════════════════
📝 FORMATO DE NODOS (OBLIGATORIO 3 LÍNEAS)
═══════════════════════════════════════════════════════════════════════════════
 
FORMATO EXACTO PARA CADA NODO:
["Emoji Título\nSQL: Resumen operación\n🗄️ Tabla: NombreExacto"]:::clase
 
REGLAS ESTRICTAS:
• Línea 1: Emoji + Título (máx 5-6 palabras)
• Línea 2: "SQL: " + Operación principal (máx 8-10 palabras)
• Línea 3: "🗄️ Tabla: " + Nombre de la tabla física, vista o temporal afectada/leída (Si son varias, pon las 2 principales o "Múltiples").
• Usa \n para salto (NO <br/>)
 
EJEMPLOS CORRECTOS:
 
["💾 Insertar clientes\nSQL: INSERT INTO FROM staging\n🗄️ Tabla: dbo.Clientes"]:::batchWrite
 
["🔍 Contar fuentes\nSQL: SELECT COUNT\n🗄️ Tabla: cltefil_diario"]:::batchRead
 
["🆕 Crear temporal\nSQL: SELECT INTO #Temp\n🗄️ Tabla: #Temp"]:::onlineWrite
 
{"¿Conteos\nválidos?\n🗄️ Tabla: N/A"}:::decision
 
═══════════════════════════════════════════════════════════════════════════════
📐 PLANTILLA OBLIGATORIA (COPIA Y ADAPTA ESTA ESTRUCTURA)
═══════════════════════════════════════════════════════════════════════════════
 
```mermaid
flowchart TB
    START(["⚙️ INICIO NOMBRE_SP"]):::mainControl
   
    subgraph FASE1 ["📋 INICIALIZACIÓN Y VALIDACIONES"]
        direction TB
       
        NOTIF1["📧 Notificación inicio\nSQL: INSERT\n🗄️ Tabla: t_cola_mensajes"]:::logging
       
        DECL["📋 Declarar variables\nSQL: DECLARE @LogId\n🗄️ Tabla: Variables"]:::logging
       
        LOG_INI["📝 Log inicio\nSQL: INSERT VALUES\n🗄️ Tabla: SP_Log"]:::batchWrite
       
        COUNT_SRC["🔍 Contar fuentes\nSQL: SELECT COUNT\n🗄️ Tabla: 8 tablas origen"]:::batchRead
       
        VAL_SRC{"¿Fuentes\nválidas?\n🗄️ Tabla: N/A"}:::decision
       
        ERR_SRC["❌ Error fuentes\nSQL: INSERT detalle\n🗄️ Tabla: t_cola_mensajes"]:::errorFill
       
        THROW1["🚨 Detener\nSQL: THROW 50001\n🗄️ Tabla: N/A"]:::errorFill
       
        NOTIF1 --> DECL --> LOG_INI --> COUNT_SRC --> VAL_SRC
        VAL_SRC -->|NO| ERR_SRC --> THROW1
    end
   
    subgraph FASE2 ["🔴 CONSTRUCCIÓN TABLAS TEMPORALES"]
        direction TB
       
        AH_META["🆕 Crear #AH_META\nSQL: SELECT DISTINCT INTO\n🗄️ Tabla: #AH_META"]:::onlineWrite
       
        CREATE_TMP["💾 Crear tmp_new\nSQL: SELECT INTO con JOINs\n🗄️ Tabla: tmp_new"]:::batchWrite
       
        UPD_SEG1["🔄 Update seguros\nSQL: UPDATE FROM vwventas\n🗄️ Tabla: tmp_new"]:::batchWrite
       
        AH_META --> CREATE_TMP --> UPD_SEG1
    end
   
    subgraph FASE3 ["✅ VALIDACIÓN FINAL Y CARGA"]
        direction TB
       
        TRUNC["🗑️ Truncar destino\nSQL: TRUNCATE TABLE\n🗄️ Tabla: TB_MALLA_CLIENTES"]:::batchWrite
       
        INSERT_FIN["💾 Insertar finales\nSQL: INSERT INTO FROM tmp_new\n🗄️ Tabla: TB_MALLA_CLIENTES"]:::batchWrite
       
        DROP_ALL["🧹 Drop temporales\nSQL: DROP 9 tablas\n🗄️ Tabla: Temporales"]:::onlineWrite
       
        TRUNC --> INSERT_FIN --> DROP_ALL
    end
   
    subgraph CATCH ["🚨 MANEJO DE ERRORES"]
        direction TB
       
        CATCH_ERR["❌ Capturar error\nSQL: DECLARE @ErrorMessage\n🗄️ Tabla: N/A"]:::errorFill
       
        LOG_ERR["📝 Log error\nSQL: UPDATE/INSERT\n🗄️ Tabla: SP_Log"]:::logging
       
        CATCH_ERR --> LOG_ERR
    end
   
    START --> FASE1
    VAL_SRC -->|SÍ| FASE2
    UPD_SEG1 --> FASE3
    DROP_ALL --> FIN
   
    THROW1 -.->|TRY-CATCH| CATCH
    LOG_ERR --> FIN
   
    FIN(["✅ FIN EJECUCIÓN"]):::mainControl
 
    classDef mainControl fill:#160F41,stroke:#5C577A,stroke-width:4px,color:#FFFFFF,font-weight:bold,font-size:14px
    classDef decision fill:#5C577A,stroke:#160F41,stroke-width:3px,color:#FFFFFF,font-weight:bold,font-size:13px
    classDef logging fill:#E7E7EC,stroke:#9F9DAD,stroke-width:2px,color:#160F41,font-weight:normal,font-size:11px
    classDef errorFill fill:#D2006E,stroke:#89004A,stroke-width:4px,color:#FFFFFF,font-weight:bold,font-size:12px
    classDef batchWrite fill:#D2006E,stroke:#89004A,stroke-width:3px,color:#FFFFFF,font-weight:bold,font-size:12px
    classDef batchRead fill:#FAE5F0,stroke:#E699C6,stroke-width:2px,color:#000000,font-size:11px
    classDef onlineWrite fill:#4AB3D6,stroke:#0277bd,stroke-width:3px,color:#FFFFFF,font-weight:bold,font-size:12px
    classDef onlineRead fill:#E2F4FA,stroke:#7DC8E3,stroke-width:2px,color:#000000,font-size:11px
═══════════════════════════════════════════════════════════════════════════════
🎨 APLICACIÓN DE COLORES (LÓGICA SIMPLIFICADA)
═══════════════════════════════════════════════════════════════════════════════
 
GEMINI: Sigue esta lógica simple:
 
🔴 :::batchWrite → INSERT/UPDATE/DELETE/TRUNCATE en tablas FÍSICAS (Ej: TB_MALLA)
🔵 :::onlineWrite → INSERT/UPDATE/DELETE en tablas TEMPORALES (Ej: #Temp, tmp_new)
📖 :::batchRead → SELECT desde tablas FÍSICAS
📘 :::onlineRead → SELECT desde tablas TEMPORALES
📋 :::logging → Declaraciones, variables, logs
⚫ :::mainControl → START y FIN
◆ :::decision → TODAS las decisiones IF/ELSE (formato rombo)
🚨 :::errorFill → Errores: CATCH, THROW, ROLLBACK
 
═══════════════════════════════════════════════════════════════════════════════
✅ CHECKLIST OBLIGATORIO PARA GEMINI
═══════════════════════════════════════════════════════════════════════════════
 
Antes de responder, verifica:
 
□ ¿Identifiqué mínimo 3 FASES principales?
□ ¿Cada FASE está en un subgrafo independiente con "direction TB"?
□ ¿Todos los nodos tienen el formato estricto de 3 LÍNEAS (\n, SQL:, 🗄️ Tabla:)?
□ ¿Identifiqué correctamente las tablas fuentes y destinos en cada paso?
□ ¿Las decisiones son rombos con formato {"¿Pregunta?\n🗄️ Tabla: N/A"}:::decision?
□ ¿Apliqué colores correctamente (físicas=rosa, temporales=azul)?
□ ¿Los 12 classDef están AL FINAL del código?
□ ¿Las conexiones entre fases son claras y los errores usan (-.->)?
 
═══════════════════════════════════════════════════════════════════════════════
📤 FORMATO DE RESPUESTA
═══════════════════════════════════════════════════════════════════════════════
 
📋 Resumen Ejecutivo
[2-3 líneas sobre propósito, tipo, tablas principales, complejidad]
 
🗄️ Fuentes y Destinos Principales
Tablas Origen (Lectura): [Lista de tablas]
 
Tablas Destino (Escritura): [Lista de tablas]
 
Tablas Temporales: [Lista de tablas temporales usadas]
 
🎨 Diagrama de Flujo Mermaid
Fragmento de código
 
[CÓDIGO COMPLETO CON SUBGRAFOS Y 3 LÍNEAS POR NODO]
[12 classDef AL FINAL]
🔑 Leyenda de Colores
[Leyenda estándar]
 
## 📊 Estadísticas del Proceso
[Métricas completas]
 
═══════════════════════════════════════════════════════════════════════════════
⚠️ RECORDATORIO FINAL CRÍTICO
═══════════════════════════════════════════════════════════════════════════════
 
GEMINI: Si generas un diagrama LINEAL sin subgrafos, HABRÁS FALLADO.
 
La ÚNICA estructura aceptable es:
1. START
2. SUBGRAFO FASE 1 (con nodos internos)
3. SUBGRAFO FASE 2 (con nodos internos)
4. SUBGRAFO FASE 3 (con nodos internos)
5. ...
6. SUBGRAFO CATCH (errores)
7. FIN
 
═══════════════════════════════════════════════════════════════════════════════
🚀 EJECUTA: ANALIZA ESTE STORED PROCEDURE
═══════════════════════════════════════════════════════════════════════════════
 
[PEGA AQUÍ TU CÓDIGO T-SQL]
"""