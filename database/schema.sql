-- LABOREA IA - Esquema de base de datos (PostgreSQL)
-- Generado a partir de backend/models.py. La app crea las tablas sola al iniciar (create_all);
-- este archivo sirve para crearlas a mano o documentarlas.

CREATE TABLE sesion_chat (
	id_sesion VARCHAR(32) NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	paso_perfil INTEGER NOT NULL, 
	activa BOOLEAN NOT NULL, 
	creada TIMESTAMP WITH TIME ZONE NOT NULL, 
	ultima_actividad TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_sesion)
);

CREATE TABLE documento_cv (
	id_cv SERIAL NOT NULL, 
	id_sesion VARCHAR(32) NOT NULL, 
	nombre_archivo VARCHAR(255) NOT NULL, 
	formato VARCHAR(10) NOT NULL, 
	tamano_bytes INTEGER NOT NULL, 
	texto_extraido TEXT NOT NULL, 
	metadatos JSON, 
	creado TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_cv), 
	FOREIGN KEY(id_sesion) REFERENCES sesion_chat (id_sesion) ON DELETE CASCADE
);

CREATE INDEX ix_documento_cv_id_sesion ON documento_cv (id_sesion);

CREATE TABLE mensaje_chat (
	id_mensaje SERIAL NOT NULL, 
	id_sesion VARCHAR(32) NOT NULL, 
	rol VARCHAR(10) NOT NULL, 
	contenido TEXT NOT NULL, 
	creado TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_mensaje), 
	FOREIGN KEY(id_sesion) REFERENCES sesion_chat (id_sesion) ON DELETE CASCADE
);

CREATE INDEX ix_mensaje_chat_id_sesion ON mensaje_chat (id_sesion);

CREATE TABLE perfil_objetivo (
	id_perfil SERIAL NOT NULL, 
	id_sesion VARCHAR(32) NOT NULL, 
	puesto_deseado VARCHAR(200), 
	meta_profesional TEXT, 
	proyectos_destacar TEXT, 
	id_puesto_base VARCHAR(60), 
	creado TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_perfil), 
	UNIQUE (id_sesion), 
	FOREIGN KEY(id_sesion) REFERENCES sesion_chat (id_sesion) ON DELETE CASCADE
);

CREATE TABLE analisis_ia (
	id_analisis SERIAL NOT NULL, 
	id_sesion VARCHAR(32) NOT NULL, 
	id_cv INTEGER NOT NULL, 
	id_puesto_base VARCHAR(60) NOT NULL, 
	match_score FLOAT NOT NULL, 
	skills_gap JSON NOT NULL, 
	plan_estudio_json JSON NOT NULL, 
	resultado_json JSON NOT NULL, 
	modo VARCHAR(10) NOT NULL, 
	modelo VARCHAR(60), 
	creado TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id_analisis), 
	FOREIGN KEY(id_sesion) REFERENCES sesion_chat (id_sesion) ON DELETE CASCADE, 
	FOREIGN KEY(id_cv) REFERENCES documento_cv (id_cv) ON DELETE CASCADE
);

CREATE INDEX ix_analisis_ia_id_sesion ON analisis_ia (id_sesion);
