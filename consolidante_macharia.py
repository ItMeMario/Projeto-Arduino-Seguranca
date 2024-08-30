import os
import json
import traceback
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from eyeflow_sdk.log_obj import log
import threading
from enum import Enum

# Constantes
MAX_FRAME_EMPILHADEIRA = 10  # Número máximo de frames para confirmar a presença de uma empilhadeira
TIMEOUT = 6  # Tempo limite para desligar a luz após a última detecção
DESLIGAR_DELAY = 3  # Tempo de atraso antes de desligar a luz após a ausência de empilhadeira

class Component:
    """Classe para execução de scripts de check-list, controlando o estado de uma luz baseado na detecção de empilhadeiras."""

    def __init__(self, parms):
        """
        Inicializa o componente.
        Args:
            parms (dict): Dicionário de parâmetros de configuração.
        """
        self._component_id = parms["_id"]  # ID do componente
        self._flow_component_id = parms["component_id"]  # ID do fluxo do componente
        self._flow_component_name = os.path.basename(__file__)[:-3]  # Nome do fluxo do componente (baseado no nome do arquivo)
        self._component_type = parms["options"]["component"]  # Tipo do componente
        self._component_name = "consolidate_macharia"  # Nome do componente
        self.timeout = TIMEOUT  # Define o tempo limite
        self.desligar_timer = None  # Timer para o atraso ao desligar a luz
        self.timer = None  # Timer para controlar o desligamento da luz
        self.lock = threading.Lock()  # Lock para controle de concorrência
        self.lock_state = threading.Lock()  # Lock para controlar o estado da luz
        self.control_lamp(1, 0)  # Inicialmente, desliga a luz

        # Inicializa contadores
        self.tentativa_detectar = 0  # Contador de tentativas falhas
        self.count_empilhadeira = 0  # Contador de frames confirmando a presença de uma empilhadeira

    def start_event(self):
        """Inicia ou reinicia o timer de timeout."""
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()  # Cancela o timer existente, se houver
            self.timer = threading.Timer(self.timeout, self.close_event)  # Configura um novo timer
            self.timer.start()  # Inicia o timer

    def close_event(self):
        """Função chamada quando o timer expira (timeout), apagando a luz se estiver acesa."""
        # log.info("Evento de fechamento acionado após o timeout!")

        with self.lock_state:
            if self.relay_status() == 1:  # Se a luz estiver acesa
                self.control_lamp(1, 0)  # Desliga a luz
               # log.info("Luz apagada após timeout.")
                self.count_empilhadeira = 0  # Reseta o contador de empilhadeiras detectadas

    def stop(self):
        """Para o timer, se estiver ativo."""
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()  # Cancela o timer
                self.timer = None  # Reseta o timer

    def process_outputs(self, outputs):
        """Processa a saída de dados (outputs) para verificar a detecção de empilhadeiras."""
        for idx, val in outputs.items():
            for idx, output in enumerate(val):
                self.process_output(output)  # Processa cada detecção

    def relay_status(self):
        """Verifica o status atual do relé (luz ligada ou desligada)."""
        url = "http://192.168.7.145/get_output_status?format=1"
        try:
            response = requests.get(url)
            if response.status_code in [200, 201]:  # Se a resposta for bem-sucedida
                data = response.json()  # Converte a resposta para JSON
                state_relay = data['data']['outputs']['state']  # Obtém o estado do relé
                return state_relay  # Retorna o estado do relé
            else:
                log.error(f"Erro na solicitação: {response.status_code}")
                return None
        except Exception as e:
            log.error(f"Erro ao obter o status do relé: {str(e)}")
            return None

    def control_lamp(self, relay=1, state=0):
        """
        Controla o relé da lâmpada.
        Args:
            relay (int): Endereço do relé.
            state (int): Estado desejado (1 para ligar, 0 para desligar).
        """
        url = f"http://192.168.7.145/set_output?address={relay}&state={state}"
        response = requests.get(url)

        if response.status_code in [200, 201]:  # Verifica se a solicitação foi bem-sucedida
            log.info("Solicitação enviada com sucesso!")
        else:
            log.error(f"Erro na solicitação: {response.status_code}")
            log.error("Resposta:", response.text)

    def delay_lamp_off(self):
        """Aguarda um tempo (DESLIGAR_DELAY) antes de desligar a luz após a ausência de empilhadeira."""
        # log.info("Aguardando antes de desligar a luz pela ausência de empilhadeira...")
        with self.lock_state:
            if self.relay_status() == 1:  # Se a luz ainda estiver acesa
                self.control_lamp(1, 0)  # Desliga a luz
               # log.info("Luz desligada após atraso.")

    def process_output(self, output):
        """Processa uma detecção individual de empilhadeira."""
        with self.lock_state:
            if output['label'] == 'Empilhadeira':  # Se uma empilhadeira for detectada
                self.count_empilhadeira += 1  # Incrementa o contador de frames com empilhadeira
                if self.count_empilhadeira >= MAX_FRAME_EMPILHADEIRA:  # Se o limite for atingido
                   # log.info("Empilhadeira válida detectada com sucesso.")
                    self.count_empilhadeira = 0  # Reseta o contador

                    if self.relay_status() == 0:  # Se a luz estiver apagada
                        self.control_lamp(1, 1)  # Liga a luz
                       # log.info("Luz acesa.")
                        self.start_event()  # Inicia o timer
                    else:
                      #  log.info("A luz já está acesa.")
                        self.start_event()  # Reinicia o timer
            else:  # Se não houver empilhadeira detectada
                if self.relay_status() == 1:  # Se a luz estiver acesa
                    if self.desligar_timer is not None:
                        self.desligar_timer.cancel()  # Cancela o timer anterior se existir
                    self.desligar_timer = threading.Timer(DESLIGAR_DELAY, self.delay_lamp_off)  # Inicia o timer de atraso para desligar a luz
                    self.desligar_timer.start()  # Inicia o timer

    def process_inputs(self, inputs):
        """Processa os frames de entrada, verificando a detecção de empilhadeiras."""
        try:
            for idx, inp in enumerate(inputs):
                for key, value in inp["frame_data"].items():
                    if "component_" in key and value['component_name'] == "roi_tracker":
                        if len(value['outputs']) > 0:  # Se houver saídas
                            self.process_outputs(value['outputs'])  # Processa as saídas

        except Exception as expt:
            log.error(traceback.format_exc())  # Registra o erro no log
        
        return {}

# Código principal, executado quando o script é iniciado diretamente
if __name__ == '__main__':
    parms = {
        "options": {
            "mongodb_url": "mongodb+srv://app_conferencia:CIc24O4pMhBDCq2w@eyeflow-dev.9bm6s.mongodb.net/copa_conferencia?retryWrites=true&w=majority",
            "consolidate_events": True,
            "consolidate_time": 1.0,
            "save_event_image": True
        }
    }

    # Cria o componente usando os parâmetros fornecidos
    comp = Component(parms)