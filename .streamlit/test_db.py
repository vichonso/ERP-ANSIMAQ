from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://postgres:pc-database@localhost:5432/ansimaq')

with engine.begin() as conn:
    conn.execute(
        text("INSERT INTO generadores (codigo_interno, nombre_modelo, marca, voltamperio, estado) VALUES (:ci, :nm, :ma, :va, :es)"),
        {"ci": "TEST", "nm": "TEST", "ma": "TEST", "va": 1, "es": 1}
    )
print("Insert OK")
