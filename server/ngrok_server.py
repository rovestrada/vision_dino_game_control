#!/usr/bin/env python3
"""
🎮 Servidor del Dinosaurio con ngrok
Versión simplificada y rápida de configurar
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pyautogui
import time
import subprocess
import requests
from datetime import datetime
import os
import sys

app = Flask(__name__)
CORS(app)

# Configuración
pyautogui.FAILSAFE = True
last_action_time = 0
min_action_interval = 0.15  # 150ms entre acciones para gaming

@app.route('/comando', methods=['POST'])
def ejecutar_comando():
    global last_action_time
    
    try:
        data = request.json
        comando = data.get('comando')
        current_time = time.time()
        
        # Control de velocidad
        if current_time - last_action_time < min_action_interval:
            return jsonify({'status': 'throttled'})
        
        if comando == 'saltar':
            print(f"🦘 [{datetime.now().strftime('%H:%M:%S')}] SALTANDO!")
            pyautogui.press('space')
            last_action_time = current_time
            return jsonify({'status': 'ok', 'accion': 'saltar'})
            
        elif comando == 'agachar':
            print(f"🐴 [{datetime.now().strftime('%H:%M:%S')}] AGACHANDO!")
            pyautogui.press('down')
            last_action_time = current_time
            return jsonify({'status': 'ok', 'accion': 'agachar'})
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'status': 'error', 'mensaje': str(e)})
    
    return jsonify({'status': 'comando_no_reconocido'})

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'servidor_activo', 'tiempo': time.time()})

def verificar_ngrok():
    """Verifica si ngrok está instalado"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        print(f"✅ ngrok encontrado: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        return False

def obtener_url_publica():
    """Obtiene la URL pública de ngrok"""
    try:
        time.sleep(2)  # Esperar que ngrok se inicie
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        tunnels = response.json()
        
        for tunnel in tunnels['tunnels']:
            if tunnel['config']['addr'] == 'http://localhost:5000':
                url = tunnel['public_url']
                print(f"\n🌐 TU URL PÚBLICA ES:")
                print(f"🔗 {url}")
                print(f"\n📋 COPIA ESTA URL EXACTA PARA COLAB:")
                print(f"SERVER_URL = \"{url}\"")
                return url
                
    except Exception as e:
        print(f"⚠️ No se pudo obtener URL automáticamente")
        print(f"💡 Ve a http://localhost:4040 para ver tus túneles")
        return None

def iniciar_ngrok():
    """Inicia ngrok en background"""
    try:
        print("🌐 Iniciando túnel ngrok...")
        process = subprocess.Popen([
            'ngrok', 'http', '5000', '--log', 'stdout'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return process
    except Exception as e:
        print(f"❌ Error iniciando ngrok: {e}")
        return None

def main():
    print("🎮 SERVIDOR DEL DINOSAURIO DE CHROME")
    print("=" * 50)
    
    # Verificar ngrok
    if not verificar_ngrok():
        print("❌ ngrok no está instalado")
        print("📥 Descarga desde: https://ngrok.com/download")
        print("💡 O usa la Opción 2 (sin ngrok)")
        return
    
    # Iniciar ngrok
    ngrok_process = iniciar_ngrok()
    if not ngrok_process:
        print("❌ No se pudo iniciar ngrok")
        return
    
    print("⚡ Servidor Flask iniciándose...")
    print("🎯 Abre chrome://dino/ en tu navegador")
    print("⚠️ FAILSAFE: Mueve ratón a esquina superior izquierda para parar")
    
    # Obtener URL pública después de un momento
    import threading
    def obtener_url_delayed():
        url = obtener_url_publica()
        if url:
            print(f"\n🚀 ¡LISTO! Ahora ejecuta tu código de Colab")
        else:
            print(f"\n💡 Revisa http://localhost:4040 para ver la URL")
    
    timer = threading.Timer(3.0, obtener_url_delayed)
    timer.start()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
        if ngrok_process:
            ngrok_process.terminate()
    finally:
        print("👋 ¡Hasta luego!")

if __name__ == '__main__':
    main()