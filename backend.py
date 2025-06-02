from flask import Flask, request, jsonify, render_template
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Circle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.path import Path
import math
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

def calcular_tiempo_llegada(pos_balon, velocidad_balon, pos_jugador):
    """Calcula el tiempo que tarda el balón en llegar a la posición del jugador"""
    distancia = math.sqrt((pos_balon[0] - pos_jugador[0])**2 + (pos_balon[1] - pos_jugador[1])**2)
    tiempo = distancia / (velocidad_balon * 1000 / 3600)  # Convertir km/h a m/s
    return tiempo

def calcular_radio_efectivo(tiempo_llegada, radio_base, tiempo_reaccion):
    """Ajusta el radio en función del tiempo de llegada vs tiempo de reacción"""
    factor = tiempo_llegada / tiempo_reaccion
    return radio_base * factor

def calcular_xsit(pos_balon, portero, jugadores, velocidad_balon):
    """Calcula una métrica xSIT basada en la proporción de interferencia en el triángulo de disparo"""

    # Definir la portería en función de la posición del balón
    porteria = [(120, 32), (120, 43)] if pos_balon[0] >= 60 else [(0, 32), (0, 43)]

    # Área del triángulo formado por balón y portería
    def area_triangulo(a, b, c):
        return abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])) / 2.0)

    area_total = area_triangulo(pos_balon, porteria[0], porteria[1])

    # Calcular cuánta parte del triángulo está cubierta por jugadores
    def jugador_interfiere(jugador):
        tiempo = calcular_tiempo_llegada(pos_balon, velocidad_balon, jugador)
        radio = calcular_radio_efectivo(tiempo, radio_base=1.5, tiempo_reaccion=0.25)
        # Si el jugador está dentro del triángulo, lo consideramos como que interfiere
        area1 = area_triangulo(jugador, porteria[0], porteria[1])
        area2 = area_triangulo(pos_balon, jugador, porteria[1])
        area3 = area_triangulo(pos_balon, porteria[0], jugador)
        return abs(area1 + area2 + area3 - area_total) < 1e-2

    jugadores_interfieren = sum(jugador_interfiere(j) for j in jugadores)

    # Portero también interfiere, con más peso
    interfiere_portero = jugador_interfiere(portero)
    peso_portero = 2

    total_interferencia = jugadores_interfieren + (peso_portero if interfiere_portero else 0)

    # Normalizar entre 0 y 1
    max_valor = len(jugadores) + peso_portero
    xsit = total_interferencia / max_valor if max_valor > 0 else 0

    return round(xsit, 4)

@app.route('/calculate_xsit', methods=['POST'])
def calculate_xsit_route():
    data = request.json
    print("Datos recibidos:", data) 
    pos_balon = data.get("pos_balon")  # [x, y]
    velocidad_balon = data.get("velocidad_balon")  # en km/h
    portero = data.get("portero")  # [x, y]
    jugadores = data.get("jugadores")  # lista de [x, y]

    if not pos_balon or not velocidad_balon or not portero or not jugadores:
        return jsonify({"error": "Faltan datos"}), 400

    xsit_value = calcular_xsit(pos_balon, portero, jugadores, velocidad_balon)
    return jsonify({"xsit": xsit_value})

@app.route("/")
def index():
    return render_template("xSIT.html") 

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
