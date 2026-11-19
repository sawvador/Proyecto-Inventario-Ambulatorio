import os
import sys
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection, init_db


def get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(get_base_path(), "templates"))
init_db()

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def home(request: Request):
    conn = get_db_connection()
    insumos = conn.execute("SELECT * FROM insumos ORDER BY nombre ASC").fetchall()
    movimientos = conn.execute("""
        SELECT m.id, m.tipo, m.cantidad, m.motivo, m.fecha, i.nombre AS insumo_nombre, i.unidad
        FROM movimientos m
        JOIN insumos i ON m.insumo_id = i.id
        ORDER BY m.id DESC
        LIMIT 30
    """).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"insumos": insumos, "movimientos": movimientos}
    )

@app.post("/insumos/nuevo")
def crear_insumo(
    nombre: str = Form(...),
    categoria: str = Form(...),
    unidad: str = Form(...),
    stock_actual: int = Form(0),
    stock_minimo: int = Form(5)
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO insumos (nombre, categoria, unidad, stock_actual, stock_minimo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombre.strip(), categoria.strip(), unidad.strip(), max(0, stock_actual), max(0, stock_minimo))
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/", status_code=303)
        
@app.post("/movimientos/registrar")
def registrar_movimiento(
    insumo_id: int = Form(...),
    tipo: str = Form(...),
    cantidad: int = Form(...),
    motivo: str = Form("")
):
    if cantidad <= 0:
        return RedirectResponse(url="/", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor()
    insumo = cursor.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()

    if insumo:
        stock_actual = insumo["stock_actual"]
        if tipo == "ENTRADA":
            nuevo_stock = stock_actual + cantidad
        elif tipo == "SALIDA":
            if cantidad > stock_actual:
                conn.close()
                return RedirectResponse(url="/", status_code=303)
            nuevo_stock = stock_actual - cantidad
        else:
            conn.close()
            return RedirectResponse(url="/", status_code=303)

        cursor.execute(
            "UPDATE insumos SET stock_actual = ? WHERE id = ?",
            (nuevo_stock, insumo_id)
        )
        cursor.execute(
            "INSERT INTO movimientos (insumo_id, tipo, cantidad, motivo) VALUES (?, ?, ?, ?)",
            (insumo_id, tipo, cantidad, motivo.strip() or ("Entrada de insumo" if tipo == "ENTRADA" else "Salida de insumo"))
        )
        conn.commit()

    
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)