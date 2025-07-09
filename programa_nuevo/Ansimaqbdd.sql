
-- Crear tabla equipos
CREATE TABLE equipos (
    numero_vigente VARCHAR(100) PRIMARY KEY, -- Número de serie o identificación del equipo
    nombre_modelo VARCHAR(100), -- Nombre del modelo del equipo
    estado INTEGER -- 1=disponible; 2=en arriendo; 3=en reparación; 4=averiado
);

-- Crear tabla Clientes
CREATE TABLE clientes (
    rut_empresa INTEGER PRIMARY KEY, -- RUT de la empresa
    nombre_empresa VARCHAR(100), -- Nombre de la empresa
    obra VARCHAR(100), -- Nombre de la obra o proyecto
    nombre_representante VARCHAR(100), -- Nombre del representante de la empresa
    rut_representante INTEGER, -- RUT del representante
    correo VARCHAR(100), -- Correo electrónico de contacto
    telefono INTEGER -- Teléfono de contacto
);

-- Crear tabla Contrato
CREATE TABLE contrato (
    folio INTEGER PRIMARY KEY, -- Folio del contrato
    rut_empresa INTEGER REFERENCES clientes(rut_empresa) ON DELETE CASCADE, -- RUT de la empresa contratante
    precio_mensual INTEGER, -- Precio mensual del arriendo
    horas_contrtadas INTEGER, -- Horas contratadas del equipo
    fecha_inicio_contrato DATE, -- Fecha de inicio del contrato
    fecha_termino_contrato DATE, -- Fecha de término del contrato
    egreso_arriendo INTEGER, -- costo de sumatoria(mantencion + reparacion + cambio de equipo)
    precio_envio INTEGER -- Precio del envío del equipo
);

-- Crear tabla historial de contrato
CREATE TABLE historial_contrato (
    id_historial SERIAL PRIMARY KEY, -- Identificador único del historial
    folio INTEGER REFERENCES contrato(folio) ON DELETE CASCADE, -- Referencia al contrato asociado
    numero_vigente VARCHAR(100) REFERENCES equipos(numero_vigente) ON DELETE CASCADE, -- Referencia al equipo arrendado
    tipo_servicio VARCHAR(100), -- mantención, reparación, cambio de equipo, despacho, etc.
    fecha_servicio DATE, -- Fecha del servicio realizado
    horometro INTEGER -- Horas de uso del equipo
); 

-- Crear tabla de cobros
CREATE TABLE cobros (
    id_cobros SERIAL PRIMARY KEY, -- Identificador único del cobro
    id_historial SERIAL REFERENCES historial_contrato(id_historial) ON DELETE CASCADE, -- Referencia al historial de contrato
    numero_vigente VARCHAR(100) REFERENCES equipos(numero_vigente) ON DELETE CASCADE, -- Referencia al equipo arrendado
    folio INTEGER REFERENCES contrato(folio) ON DELETE CASCADE, -- Referencia al contrato asociado
	fecha_pago DATE, -- Fecha del pago del cobro
    cobro INTEGER, -- Monto del cobro (precio_mensual + if es primer mes(precio_envio) + (horas_extra * costo_hora_extra)-egreso_arriendo)
    horas_extra INTEGER, -- Horas extra de uso del equipo 
    costo_hora_extra INTEGER, -- Costo por hora extra
    rentabilidad INTEGER, -- Rentabilidad del generador en el mes (cobro - egreso_equipo)
    egreso_equipo INTEGER, -- Egreso del equipo (costo de mantención, reparación, etc.)
    estado INTEGER, -- 1=pendiente; 2=pagado; 
    mes INTEGER, -- Mes del cobro
    anio INTEGER -- Año del cobro
);

