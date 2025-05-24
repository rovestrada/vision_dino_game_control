#!/usr/bin/env python3
"""
🎮 Servidor del Dinosaurio
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pyautogui
import time
import subprocess
import requests
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
import sys
from collections import deque

app = Flask(__name__)
CORS(app)

# Configuración anti-congelamiento
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01  # Pausa mínima entre comandos pyautogui

# Sistema de rate limiting ajustado para gaming
last_action_time = 0
min_action_interval = 0.02  # 20ms mínimo (mucho más rápido)
request_queue = queue.Queue(maxsize=20)  # Cola más grande
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="keypress")  # Más workers

# Estadísticas y debugging
stats = {
    'total_requests': 0,
    'successful_actions': 0,
    'throttled_requests': 0,
    'errors': 0,
    'queue_full': 0
}

# Rate limiting menos agresivo para gaming
request_times = deque(maxlen=50)  # Más requests permitidos
MAX_REQUESTS_PER_SECOND = 40  # Máximo 40 req/s (más permisivo)

def is_rate_limited():
    """Verifica si estamos siendo spammeados"""
    current_time = time.time()
    request_times.append(current_time)
    
    # Limpiar requests antiguos (más de 1 segundo)
    while request_times and current_time - request_times[0] > 1.0:
        request_times.popleft()
    
    return len(request_times) > MAX_REQUESTS_PER_SECOND

def execute_keypress(comando):
    """Ejecuta el comando de teclado de forma segura"""
    try:
        if comando == 'saltar':
            pyautogui.press('space')
            return True, 'saltar'
        elif comando == 'agachar':
            pyautogui.press('down')
            return True, 'agachar'
        else:
            return False, 'comando_desconocido'
    except Exception as e:
        print(f"⚠️ Error en pyautogui: {e}")
        return False, f'error_pyautogui: {e}'

def process_command_async(comando):
    """Procesa comando en thread separado"""
    try:
        success, result = execute_keypress(comando)
        if success:
            stats['successful_actions'] += 1
            print(f"🎮 [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {result.upper()}! (Total: {stats['successful_actions']})")
        else:
            stats['errors'] += 1
            print(f"❌ Error ejecutando {comando}: {result}")
    except Exception as e:
        stats['errors'] += 1
        print(f"❌ Error en thread: {e}")

@app.route('/comando', methods=['POST'])
def ejecutar_comando():
    global last_action_time
    
    stats['total_requests'] += 1
    
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
            
        comando = data.get('comando')
        if not comando:
            return jsonify({'status': 'error', 'message': 'No comando'}), 400
        
        current_time = time.time()
        
        # Rate limiting más permisivo - solo verificar tiempo básico
        if current_time - last_action_time < min_action_interval:
            stats['throttled_requests'] += 1
            return jsonify({'status': 'throttled'})  # Sin 429, más simple
        
        # Validar comando
        if comando not in ['saltar', 'agachar']:
            return jsonify({'status': 'error', 'message': 'Comando no válido'}), 400
        
        # Rate limiting menos agresivo - solo revisar spam extremo
        if is_rate_limited() and len(request_times) > 35:  # Solo bloquear spam extremo
            stats['throttled_requests'] += 1
            return jsonify({'status': 'rate_limited'})
        
        # Procesar comando DIRECTAMENTE sin cola si es posible
        try:
            # Intentar ejecución directa primero
            success, result = execute_keypress(comando)
            if success:
                stats['successful_actions'] += 1
                last_action_time = current_time
                print(f"🎮 [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {result.upper()}! (Total: {stats['successful_actions']})")
                
                return jsonify({
                    'status': 'ok', 
                    'accion': comando,
                    'timestamp': current_time,
                    'method': 'direct'  # Ejecución directa
                })
            else:
                stats['errors'] += 1
                return jsonify({'status': 'error', 'message': result})
                
        except Exception as e:
            # Si falla la ejecución directa, usar cola como backup
            try:
                request_queue.put_nowait(comando)
                executor.submit(process_command_async, comando)
                last_action_time = current_time
                
                return jsonify({
                    'status': 'ok', 
                    'accion': comando,
                    'timestamp': current_time,
                    'method': 'queued'  # En cola
                })
            except queue.Full:
                stats['queue_full'] += 1
                return jsonify({'status': 'busy'})  # Sin 503, más simple
        
    except Exception as e:
        stats['errors'] += 1
        print(f"❌ Error en ruta: {e}")
        return jsonify({'status': 'error', 'mensaje': str(e)})

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        'status': 'servidor_activo', 
        'tiempo': time.time(),
        'stats': stats,
        'queue_size': request_queue.qsize(),
        'thread_count': threading.active_count()
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Endpoint para ver estadísticas del servidor"""
    uptime = time.time() - server_start_time if 'server_start_time' in globals() else 0
    
    return jsonify({
        'uptime_seconds': uptime,
        'stats': stats,
        'current_queue_size': request_queue.qsize(),
        'active_threads': threading.active_count(),
        'requests_per_second': stats['total_requests'] / uptime if uptime > 0 else 0,
        'success_rate': stats['successful_actions'] / stats['total_requests'] if stats['total_requests'] > 0 else 0
    })

@app.route('/reset', methods=['POST'])
def reset_stats():
    """Resetea las estadísticas"""
    global stats
    stats = {
        'total_requests': 0,
        'successful_actions': 0,
        'throttled_requests': 0,
        'errors': 0,
        'queue_full': 0
    }
    return jsonify({'status': 'stats_reset'})

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
        time.sleep(3)  # Más tiempo para que ngrok se estabilice
        response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
        tunnels = response.json()
        
        for tunnel in tunnels['tunnels']:
            if tunnel['config']['addr'] == 'http://localhost:5000':
                url = tunnel['public_url']
                print(f"\n🌐 TU URL PÚBLICA ES:")
                print(f"🔗 {url}")
                print(f"\n📋 COPIA ESTA URL EXACTA PARA COLAB:")
                print(f"SERVER_URL = \"{url}\"")
                print(f"\n📊 Ver estadísticas en: {url}/stats")
                return url
                
    except Exception as e:
        print(f"⚠️ No se pudo obtener URL automáticamente: {e}")
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

def monitor_server():
    """Monitorea el servidor y muestra estadísticas"""
    while True:
        time.sleep(30)  # Cada 30 segundos
        uptime = time.time() - server_start_time
        rps = stats['total_requests'] / uptime if uptime > 0 else 0
        
        print(f"\n📊 ESTADÍSTICAS DEL SERVIDOR ({uptime:.0f}s uptime):")
        print(f"   📡 Requests totales: {stats['total_requests']}")
        print(f"   ✅ Acciones exitosas: {stats['successful_actions']}")
        print(f"   🚫 Throttled: {stats['throttled_requests']}")
        print(f"   ❌ Errores: {stats['errors']}")
        print(f"   📈 Req/s promedio: {rps:.2f}")
        print(f"   🔄 Threads activos: {threading.active_count()}")
        print(f"   📋 Cola actual: {request_queue.qsize()}")

def main():
    global server_start_time
    
    print("🎮 SERVIDOR ROBUSTO DEL DINOSAURIO")
    print("=" * 50)
    print("🛡️ CARACTERÍSTICAS ANTI-CONGELAMIENTO:")
    print("   ⚡ Threading para pyautogui")
    print("   🔄 Cola de comandos limitada")
    print("   🚫 Rate limiting agresivo")
    print("   📊 Monitoreo en tiempo real")
    print("   🛠️ Manejo robusto de errores")
    print("=" * 50)
    
    # Verificar ngrok
    if not verificar_ngrok():
        print("❌ ngrok no está instalado")
        print("📥 Descarga desde: https://ngrok.com/download")
        return
    
    # Iniciar ngrok
    ngrok_process = iniciar_ngrok()
    if not ngrok_process:
        print("❌ No se pudo iniciar ngrok")
        return
    
    print("⚡ Servidor Flask iniciándose...")
    print("🎯 Abre chrome://dino/ en tu navegador")
    print("⚠️ FAILSAFE: Mueve ratón a esquina superior izquierda para parar")
    
    server_start_time = time.time()
    
    # Iniciar monitor en thread separado
    monitor_thread = threading.Thread(target=monitor_server, daemon=True)
    monitor_thread.start()
    
    # Obtener URL pública después de un momento
    def obtener_url_delayed():
        url = obtener_url_publica()
        if url:
            print(f"\n🚀 ¡SERVIDOR ROBUSTO LISTO!")
            print(f"🎮 Ejecuta tu código de Colab")
            print(f"📊 Estadísticas: {url}/stats")
        else:
            print(f"\n💡 Revisa http://localhost:4040 para ver la URL")
    
    timer = threading.Timer(5.0, obtener_url_delayed)
    timer.start()
    
    try:
        # Usar servidor multithreaded para manejar concurrencia
        app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=False,
            threaded=True,  # Importante: permite múltiples requests concurrentes
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
        if ngrok_process:
            ngrok_process.terminate()
    finally:
        print("👋 ¡Hasta luego!")
        # Cerrar executor
        executor.shutdown(wait=False)

if __name__ == '__main__':
    main()