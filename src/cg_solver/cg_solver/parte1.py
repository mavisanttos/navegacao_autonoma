"""PARTE 1: navegação COM mapa.

Etapas:
    1a. Pedir o mapa ao jogo pelo serviço /get_map e remontar a matriz.
    1b. Achar a rota mais curta com BFS.
    1c. Transformar a rota em direções e mandar o robô andar, um passo por
        vez, chamando o serviço /move_command.

Ao final, salva em resultados/ o mapa real (parte1_mapa.csv) e a rota
ótima (parte1_rota.json), que a Parte 2 usa para a comprovação.

Como rodar (da RAIZ do repositório, com o jogo aberto em outro terminal):
    ros2 run cg_solver parte1
"""
import time

import rclpy
from rclpy.node import Node

# Os "formulários" dos serviços, definidos no pacote do jogo
from cg_interfaces.srv import GetMap, MoveCmd, Reset

from cg_solver.labirinto import remontar_matriz, encontrar, desenhar
from cg_solver.bfs import bfs, marcar_caminho, caminho_para_direcoes
from cg_solver.arquivos import salvar_mapa_csv, salvar_rota

# Pausa entre um passo e outro, só para dar tempo de ver o robô andando
# na janela do jogo. Com 0 ele anda o mais rápido possível.
PAUSA_ENTRE_PASSOS = 0.05  # segundos


class Parte1(Node):
    def __init__(self):
        super().__init__('parte1')

        # Um CLIENTE para cada serviço do jogo (cada um é um "telefone")
        self.cliente_mapa = self.create_client(GetMap, '/get_map')
        self.cliente_mover = self.create_client(MoveCmd, '/move_command')
        self.cliente_reset = self.create_client(Reset, '/reset')

        # Espera o jogo (o SERVIDOR) estar no ar antes de ligar
        for cliente in (self.cliente_mapa, self.cliente_mover, self.cliente_reset):
            while not cliente.wait_for_service(timeout_sec=1.0):
                self.get_logger().info(
                    f'Esperando o serviço {cliente.srv_name}... o jogo está aberto?')

    def chamar(self, cliente, pedido):
        """Faz uma chamada de serviço e espera a resposta.

        call_async devolve um `future` (a "senha da padaria"); o
        spin_until_future_complete processa a comunicação até a resposta chegar.
        """
        future = cliente.call_async(pedido)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def obter_mapa(self):
        """Chama /get_map e devolve o mapa como matriz (lista de listas)."""
        resposta = self.chamar(self.cliente_mapa, GetMap.Request())
        lista = list(resposta.occupancy_grid_flattened)
        formato = tuple(resposta.occupancy_grid_shape)
        return remontar_matriz(lista, formato)

    def reiniciar(self):
        """Chama /reset para recomeçar o MESMO mapa e devolve o mapa novo.

        Atenção: o jogo só AGENDA o reset. Ele responde "ok" na hora, mas só
        recarrega o labirinto na próxima volta do seu laço de desenho. Por
        isso pedimos o mapa várias vezes até o alvo 't' aparecer de novo.
        """
        pedido = Reset.Request()
        pedido.is_random = False
        resposta = self.chamar(self.cliente_reset, pedido)
        self.get_logger().info(f'Reset pedido (mapa {resposta.loaded_map_name})')

        for _ in range(50):              # tenta por até ~5 segundos
            mapa = self.obter_mapa()
            if encontrar(mapa, 't') is not None:
                return mapa
            time.sleep(0.1)
        raise RuntimeError('O jogo não reiniciou a tempo')

    def mover(self, direcao):
        """Chama /move_command com uma direção. Devolve a resposta do jogo."""
        pedido = MoveCmd.Request()
        pedido.direction = direcao
        return self.chamar(self.cliente_mover, pedido)

    def executar_rota(self, caminho):
        """Faz o robô percorrer `caminho`, conferindo cada passo.

        Devolve True se chegou ao fim do caminho sem problemas.
        """
        direcoes = caminho_para_direcoes(caminho)
        for i, direcao in enumerate(direcoes):
            resposta = self.mover(direcao)

            # O jogo devolve onde o robô está de verdade. Conferimos se é
            # exatamente a próxima célula da rota planejada.
            posicao_real = (int(resposta.robot_pos[0]), int(resposta.robot_pos[1]))
            posicao_esperada = caminho[i + 1]
            if not resposta.success or posicao_real != posicao_esperada:
                self.get_logger().error(
                    f'Passo {i + 1} ({direcao}) falhou: robô em {posicao_real}, '
                    f'esperado {posicao_esperada}')
                return False

            time.sleep(PAUSA_ENTRE_PASSOS)
        return True


def main(args=None):
    rclpy.init(args=args)
    no = Parte1()

    # ---- 1a. Obter o mapa ----
    mapa = no.obter_mapa()

    # Se o robô já pisou no alvo antes, o 't' some do mapa e o jogo passa a
    # recusar movimentos. Nesse caso, reiniciamos e pedimos o mapa de novo.
    if encontrar(mapa, 't') is None:
        no.get_logger().warn('Alvo não está no mapa (jogo já vencido?). Reiniciando...')
        mapa = no.reiniciar()

    inicio = encontrar(mapa, 'r')
    alvo = encontrar(mapa, 't')
    no.get_logger().info(f'Mapa recebido: {len(mapa)} linhas x {len(mapa[0])} colunas')
    no.get_logger().info(f'Robô em {inicio} | Alvo em {alvo}  (linha, coluna)')

    # ---- 1b. Rota mais curta com BFS ----
    caminho = bfs(mapa, inicio, alvo)
    if caminho is None:
        no.get_logger().error('Não existe caminho até o alvo!')
    else:
        # O caminho inclui o início, então nº de movimentos = nº de células - 1
        no.get_logger().info(f'Rota ótima encontrada: {len(caminho) - 1} movimentos')
        print(desenhar(marcar_caminho(mapa, caminho)))
        direcoes = caminho_para_direcoes(caminho)
        print('Direções:', ' '.join(direcoes))

        # Salva o mapa real e a rota, para a Parte 2 comparar depois
        arq_mapa = salvar_mapa_csv('parte1_mapa.csv', mapa)
        arq_rota = salvar_rota('parte1_rota.json', inicio, alvo, caminho, direcoes)
        no.get_logger().info(f'Resultados salvos em {arq_mapa} e {arq_rota}')

        # ---- 1c. Executar a rota no robô ----
        no.get_logger().info('Executando a rota...')
        inicio_tempo = time.time()
        if no.executar_rota(caminho):
            no.get_logger().info(
                f'ALVO ALCANÇADO em {len(caminho) - 1} movimentos '
                f'({time.time() - inicio_tempo:.1f} s)')

    no.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
