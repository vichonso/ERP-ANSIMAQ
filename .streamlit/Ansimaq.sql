
-- Crear tabla Generadores
CREATE TABLE generadores (
    id_generador SERIAL PRIMARY KEY,
    nombre_modelo VARCHAR(100),
    marca VARCHAR(100),
    voltamperio INTEGER,
    estado INTEGER -- 1=disponible; 2=en arriendo; 3=en reparación; 4=averiado
);

-- Crear tabla Clientes
CREATE TABLE clientes (
    id_cliente SERIAL PRIMARY KEY,
    rut_empresa BIGINT,
    nombre_empresa VARCHAR(100),
    nombre_representante VARCHAR(100),
    rut_representante BIGINT,
    correo VARCHAR(100),
    telefono BIGINT
);

-- Crear tabla Contrato
CREATE TABLE contrato (
    id_contrato SERIAL PRIMARY KEY,
    id_cliente INTEGER REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    fecha_inicio_contrato DATE,
    fecha_termino_contrato DATE,
    costo_arriendo INTEGER,
    costo_envio INTEGER,
    costo_arreglo INTEGER,
    costo_mantencion INTEGER
);

-- Crear tabla Generador en Contrato
CREATE TABLE generador_en_contrato (
    id_arriendogenerador SERIAL PRIMARY KEY,
    id_contrato INTEGER REFERENCES contrato(id_contrato) ON DELETE CASCADE,
    id_generador INTEGER REFERENCES generadores(id_generador) ON DELETE CASCADE,
	fecha_inicio_arriendo DATE,
	fecha_termino_arriendo DATE
);

-- Crear tabla Arreglos y Mantenciones
CREATE TABLE arreglos_y_mantenciones (
    id_arreglos SERIAL PRIMARY KEY,
    id_generador INTEGER REFERENCES generadores(id_generador) ON DELETE CASCADE,
    fecha_inicio_arreglo DATE,
    fecha_termino_arreglo DATE,
    costo INTEGER,
    tipo INTEGER -- 1=arreglo; 2=mantención
); 