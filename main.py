import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from supabase import create_client, Client

app = FastAPI()

# Configurar CORS para que cualquier página web pueda enviarle pedidos de forma segura
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción puede cambiar esto por el dominio real de su web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credenciales seguras (Usaremos Variables de Entorno en Render/Railway)
SUPABASE_URL = os.getenv("https://bzababetnhqkkemvbpze.supabase.co", "https://bzababetnhqkkemvbpze.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ6YWJhYmV0bmhxa2tlbXZicHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NjUxOTQsImV4cCI6MjA5ODI0MTE5NH0.eRT8HgoLmybKz1McDeeVeOdGYil32T0-yx3AR8a-veA
", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ6YWJhYmV0bmhxa2tlbXZicHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NjUxOTQsImV4cCI6MjA5ODI0MTE5NH0.eRT8HgoLmybKz1McDeeVeOdGYil32T0-yx3AR8a-veA
")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Reglas del Negocio (Santa Cruz)
MONTO_MINIMO_DELIVERY = 8000
COSTO_DESPACHO = 1500

class ItemCarrito(BaseModel):
    producto_id: int
    nombre: str
    precio: int
    cantidad: int

class PedidoRequest(BaseModel):
    cliente_nombre: str
    cliente_telefono: str
    modalidad: str  # 'retiro' o 'delivery'
    direccion: Optional[str] = None
    items: List[ItemCarrito]

@app.post("/procesar-pedido")
def procesar_pedido(pedido: PedidoRequest):
    subtotal = sum(item.precio * item.cantidad for item in pedido.items)
    costo_envio = 0
    
    # CONTROL DE COMPRAS MENORES (Filtro Anti-Quiebre)
    if pedido.modalidad == "delivery":
        if subtotal < MONTO_MINIMO_DELIVERY:
            raise HTTPException(
                status_code=400, 
                detail=f"La compra mínima para despacho a domicilio es de ${MONTO_MINIMO_DELIVERY}. Tu subtotal actual es de ${subtotal}."
            )
        costo_envio = COSTO_DESPACHO

    total = subtotal + costo_envio

    # Guardar Cabecera en Supabase
    pedido_db = {
        "cliente_nombre": pedido.cliente_nombre,
        "cliente_telefono": pedido.cliente_telefono,
        "modalidad": pedido.modalidad,
        "direccion": pedido.direccion,
        "subtotal": subtotal,
        "costo_envio": costo_envio,
        "total": total,
        "estado": "Pendiente"
    }
    
    res_pedido = supabase.table("pedidos").insert(pedido_db).execute()
    pedido_id = res_pedido.data[0]['id']

    # Guardar Detalles en Supabase
    for item in pedido.items:
        detalle_db = {
            "pedido_id": pedido_id,
            "producto_id": item.producto_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio
        }
        supabase.table("pedido_detalle").insert(detalle_db).execute()

    # Retornar datos limpios para que el Frontend arme el WhatsApp sin esfuerzo
    return {
        "status": "success",
        "pedido_id": pedido_id,
        "total": total,
        "cliente_nombre": pedido.cliente_nombre,
        "modalidad": pedido.modalidad
    }
