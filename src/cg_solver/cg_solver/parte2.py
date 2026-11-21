"""PARTE 2: mapeamento SEM usar o mapa pronto (/get_map é proibido aqui).

Etapas:
    2a. Ouvir os sensores do robô pelo tópico /culling_games/robot_sensors.
    2b. Explorar o labirinto com DFS + backtracking, montando o mapa.
    2c. Rodar o MESMO BFS da Parte 1 no mapa construído ('?' = parede),
        salvar o mapa e a rota em resultados/, comparar com a Parte 1 e
        executar a rota no robô até o alvo.

O que o robô PODE usar aqui:
    - os sensores (o que há nas 8 células em volta dele);
    - o /move_command, e a posição dele (robot_pos) que vem na resposta.
O que NÃO usa: /get_map (seria "colar") e target_pos (o alvo é
descoberto pelos sensores).

Como rodar (da RAIZ do repositório, com o jogo recém-aberto em outro terminal):
    ros2 run cg_solver parte2
"""
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from cg_interfaces.msg import RobotSensors
from cg_interfaces.srv import MoveCmd

from cg_solver.labirinto import desenhar, dicionario_para_matriz
from cg_solver.bfs import DIRECOES, bfs, marcar_caminho, caminho_para_direcoes
from cg_solver.arquivos import (salvar_mapa_csv, carregar_mapa_csv,
                                salvar_rota, carregar_rota)

# Cada campo da mensagem do sensor e a posição RELATIVA da célula que ele
# descreve: (variação na linha, variação na coluna) em relação ao robô.
SENSORES = {
    'up_left': (-1, -1), 'up': (-1, 0), 'up_right': (-1, 1),
    'left': (0, -1),                     'right': (0, 1),
    'down_left': (1, -1), 'down': (1, 0), 'down_right': (1, 1),
}

# Direção contrária (usada para conferir leituras e para voltar)
OPOSTA = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}

# Ordem em que o DFS tenta as direções (qualquer ordem funciona)
ORDEM_DIRECOES = ['up', 'right', 'down', 'left']


def leitura_para_dict(msg):
    """Transforma a mensagem do sensor num dicionário {campo: conteúdo}."""
    return {campo: getattr(msg, campo) for campo in SENSORES}


def somar(posicao, variacao):
    """(linha, coluna) + (dl, dc)."""
    return (posicao[0] + variacao[0], posicao[1] + variacao[1])


class Parte2(Node):
    def __init__(self):
        super().__init__('parte2')

        # ---- Sensores (tópico) ----
        self.leitura = None      # última leitura recebida
        self.num_leituras = 0    # quantas leituras já chegaram (contador)
        self.create_subscription(
            RobotSensors,
            '/culling_games/robot_sensors',
            self.ao_receber_sensores,
            qos_profile_sensor_data,   # MESMA QoS do publicador (BEST_EFFORT)
        )

        # ---- Movimento (serviço) ----
        self.cliente_mover = self.create_client(MoveCmd, '/move_command')
        while not self.cliente_mover.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Esperando o serviço /move_command... o jogo está aberto?')

        # ---- O mapa que o robô vai construindo ----
        # Dicionário {(linha, coluna): 'b' | 'f' | 't'}. Começa vazio:
        # o robô não sabe nem o tamanho do labirinto.
        self.mapa = {}
        self.alvo = None         # posição do alvo, quando os sensores o virem
        self.num_movimentos = 0  # estatística: quantos passos a exploração deu

    # ------------------------------------------------------------------
    # Sensores
    # ------------------------------------------------------------------
    def ao_receber_sensores(self, msg):
        """CALLBACK: chamado pelo ROS a cada mensagem nova (durante o spin)."""
        self.leitura = leitura_para_dict(msg)
        self.num_leituras += 1

    def esperar_leitura_nova(self, quantidade=2, tempo_max=10.0):
        """Espera chegarem `quantidade` leituras NOVAS e devolve a última.

        Por que isso importa: a mensagem do sensor não diz onde o robô está.
        Se usássemos a leitura guardada logo depois de um movimento, ela
        poderia ser de ANTES do movimento, e anotaríamos as paredes no lugar
        errado. Esperar 2 leituras novas (≈ 20 ms a 100 Hz) garante que
        a leitura já é da posição atual.
        """
        meta = self.num_leituras + quantidade
        inicio = time.time()
        while self.num_leituras < meta:
            rclpy.spin_once(self, timeout_sec=0.05)   # deixa o callback rodar
            if time.time() - inicio > tempo_max:
                raise RuntimeError('Os sensores pararam de chegar. O jogo está aberto?')
        return self.leitura

    def anotar(self, posicao, leitura):
        """Registra no mapa o que os sensores viram em volta de `posicao`."""
        self.mapa[posicao] = 'f'   # onde o robô está é, claro, livre
        for campo, variacao in SENSORES.items():
            celula = somar(posicao, variacao)
            conteudo = leitura[campo]
            if conteudo == 'r':        # (não deve acontecer; por segurança)
                conteudo = 'f'
            anterior = self.mapa.get(celula)
            if anterior is not None and anterior != conteudo:
                self.get_logger().warn(
                    f'Leitura inconsistente em {celula}: antes {anterior}, agora {conteudo}')
            self.mapa[celula] = conteudo
            if conteudo == 't' and self.alvo is None:
                self.alvo = celula
                self.get_logger().info(f'ALVO avistado pelos sensores em {celula}!')

    # ------------------------------------------------------------------
    # Movimento
    # ------------------------------------------------------------------
    def chamar_mover(self, direcao):
        """Chama /move_command e devolve (success, posicao_do_robo)."""
        pedido = MoveCmd.Request()
        pedido.direction = direcao
        future = self.cliente_mover.call_async(pedido)
        rclpy.spin_until_future_complete(self, future)
        resposta = future.result()
        posicao = (int(resposta.robot_pos[0]), int(resposta.robot_pos[1]))
        return resposta.success, posicao

    def andar(self, direcao, destino_esperado):
        """Move o robô 1 passo, confere a posição e devolve a leitura NOVA."""
        sucesso, posicao = self.chamar_mover(direcao)
        if not sucesso or posicao != destino_esperado:
            raise RuntimeError(
                f'Movimento {direcao} falhou (robô em {posicao}, esperado '
                f'{destino_esperado}). O jogo já foi vencido? Reinicie com a '
                f'tecla r no teleop ou: ros2 service call /reset '
                f'cg_interfaces/srv/Reset "{{is_random: false}}"')
        self.num_movimentos += 1

        # Leitura nova + conferência: se acabei de andar para 'down', a
        # célula de onde vim ('up') tem que estar livre, não pode ser parede.
        for _ in range(5):
            leitura = self.esperar_leitura_nova()
            if leitura[OPOSTA[direcao]] != 'b':
                return leitura
        raise RuntimeError('Leitura dos sensores não bate com o movimento feito')

    def descobrir_posicao_inicial(self, leitura):
        """Descobre a posição do robô sem /get_map.

        Truque: mandar o robô andar contra uma PAREDE que o sensor já viu.
        O jogo recusa o movimento (o robô não sai do lugar), mas a resposta
        traz robot_pos, a posição atual. Assim, nenhum passo é gasto.
        """
        for direcao in ORDEM_DIRECOES:
            if leitura[direcao] == 'b':
                _, posicao = self.chamar_mover(direcao)
                return posicao
        # Sem parede em volta (raro): anda para uma célula livre e volta.
        for direcao in ORDEM_DIRECOES:
            if leitura[direcao] == 'f':
                self.chamar_mover(direcao)
                _, posicao = self.chamar_mover(OPOSTA[direcao])
                return posicao
        raise RuntimeError('Não consegui descobrir a posição inicial')

    # ------------------------------------------------------------------
    # DFS + backtracking
    # ------------------------------------------------------------------
    def explorar(self):
        """Explora o labirinto inteiro com DFS (busca em profundidade).

        Ideia (como explorar uma caverna com um novelo de lã):
          - Estou numa célula. Existe vizinha LIVRE que eu ainda não visitei?
              SIM -> ando até ela, olho os sensores, anoto, e repito de lá.
              NÃO -> beco sem saída (ou tudo em volta já visto): VOLTO um
                     passo pelo mesmo caminho por onde vim (BACKTRACKING).
          - Quando eu voltar até o início e não houver mais nada novo,
            o labirinto inteiro foi explorado.

        A PILHA guarda o caminho do início até onde estou agora (o "fio de
        lã"). Avançar = empilhar; voltar = desempilhar.
        O robô NUNCA entra no alvo 't' (o jogo encerraria a partida).
        """
        leitura = self.esperar_leitura_nova()
        inicio = self.descobrir_posicao_inicial(leitura)
        self.get_logger().info(f'Posição inicial do robô: {inicio}')
        self.anotar(inicio, leitura)

        visitados = {inicio}
        pilha = [inicio]

        while pilha:
            atual = pilha[-1]   # topo da pilha = onde o robô está

            # Procura uma vizinha livre ('f') ainda não visitada
            proxima = None
            for direcao in ORDEM_DIRECOES:
                vizinha = somar(atual, DIRECOES[direcao])
                if self.mapa.get(vizinha) == 'f' and vizinha not in visitados:
                    proxima = (direcao, vizinha)
                    break

            if proxima is not None:
                # AVANÇA: entra na célula nova
                direcao, vizinha = proxima
                leitura = self.andar(direcao, vizinha)
                visitados.add(vizinha)
                self.anotar(vizinha, leitura)
                pilha.append(vizinha)
            else:
                # BACKTRACKING: nada novo aqui, volta 1 passo pelo fio
                pilha.pop()
                if pilha:
                    anterior = pilha[-1]
                    direcao = self.direcao_entre(atual, anterior)
                    self.andar(direcao, anterior)

            if self.num_movimentos and self.num_movimentos % 100 == 0:
                self.get_logger().info(
                    f'{self.num_movimentos} movimentos | {len(visitados)} células visitadas')

        return inicio, visitados

    def executar_rota(self, caminho):
        """Percorre `caminho` com o robô, conferindo a posição a cada passo."""
        for i, direcao in enumerate(caminho_para_direcoes(caminho)):
            sucesso, posicao = self.chamar_mover(direcao)
            if not sucesso or posicao != caminho[i + 1]:
                self.get_logger().error(
                    f'Passo {i + 1} ({direcao}) falhou: robô em {posicao}, '
                    f'esperado {caminho[i + 1]}')
                return False
            time.sleep(0.05)   # só para dar tempo de ver o robô andando
        return True

    @staticmethod
    def direcao_entre(origem, destino):
        """Qual direção leva de `origem` a `destino` (células vizinhas)."""
        variacao = (destino[0] - origem[0], destino[1] - origem[1])
        for nome, v in DIRECOES.items():
            if v == variacao:
                return nome
        raise ValueError(f'{origem} e {destino} não são vizinhas')


def comparar_com_parte1(no, mapa, caminho, direcoes):
    """Compara o mapa e a rota da Parte 2 com os salvos pela Parte 1.

    A Parte 1 só é lida AQUI, depois do mapeamento terminado, para provar o
    resultado. Ela não é usada em nenhum momento para guiar o robô.
    """
    log = no.get_logger()
    rota1 = carregar_rota('parte1_rota.json')
    mapa1 = carregar_mapa_csv('parte1_mapa.csv')
    if rota1 is None or mapa1 is None:
        log.warn('Não achei resultados/parte1_*. Rode a Parte 1 no mesmo mapa '
                 'para a comparação automática.')
        return

    print('=========== COMPROVAÇÃO: Parte 1 x Parte 2 ===========')
    if tuple(rota1['inicio']) != caminho[0] or tuple(rota1['alvo']) != caminho[-1]:
        log.warn('Início/alvo diferentes dos da Parte 1: os resultados salvos '
                 'parecem ser de OUTRO mapa. Rode a Parte 1 no mesmo mapa.')

    # 1) O mapa construído é igual ao mapa real?
    if len(mapa1) == len(mapa) and len(mapa1[0]) == len(mapa[0]):
        diferentes = sum(1 for i in range(len(mapa)) for j in range(len(mapa[0]))
                         if mapa[i][j] != mapa1[i][j])
        print(f'Mapa: {diferentes} células diferentes do mapa real '
              f'({len(mapa)}x{len(mapa[0])} = {len(mapa) * len(mapa[0])} células)')
    else:
        print(f'Mapa: tamanhos diferentes ({len(mapa)}x{len(mapa[0])} x '
              f'{len(mapa1)}x{len(mapa1[0])})')

    # 2) A rota tem o mesmo tamanho? (é isso que o enunciado pede)
    print(f'Rota Parte 1 (mapa real):       {rota1["movimentos"]} movimentos')
    print(f'Rota Parte 2 (mapa construído): {len(direcoes)} movimentos')
    if rota1['movimentos'] == len(direcoes):
        print('MESMO TAMANHO: o mapa construído é suficiente para reproduzir '
              'a rota ótima da Parte 1. ✅')
    else:
        print('TAMANHOS DIFERENTES ❌')
    if rota1['direcoes'] == direcoes:
        print('(E a sequência de direções é idêntica.)')
    print('=======================================================')


def main(args=None):
    rclpy.init(args=args)
    no = Parte2()

    try:
        # ---- 2b. Explorar e mapear ----
        no.get_logger().info('Iniciando exploração (DFS + backtracking)...')
        tempo_inicial = time.time()
        inicio, visitados = no.explorar()
        duracao = time.time() - tempo_inicial

        mapa = dicionario_para_matriz(no.mapa)
        mapa[inicio[0]][inicio[1]] = 'r'   # marca o ponto de partida no desenho
        desconhecidas = sum(linha.count('?') for linha in mapa)

        no.get_logger().info(
            f'Exploração concluída em {duracao:.1f} s: {no.num_movimentos} movimentos, '
            f'{len(visitados)} células visitadas, mapa {len(mapa)}x{len(mapa[0])}, '
            f'{desconhecidas} células desconhecidas')
        no.get_logger().info(f'Alvo encontrado em {no.alvo} (sem pisar nele)')
        print('Mapa construído pelo robô (R = partida, T = alvo, · = desconhecido):')
        print(desenhar(mapa))
        arq_mapa = salvar_mapa_csv('parte2_mapa_construido.csv', mapa)
        no.get_logger().info(f'Mapa construído salvo em {arq_mapa}')

        if no.alvo is None:
            raise RuntimeError('Os sensores nunca viram o alvo')

        # ---- 2c. BFS no mapa CONSTRUÍDO (o mesmo bfs() da Parte 1) ----
        # Células '?' (nunca vistas) contam como parede: só confiamos no que
        # o robô realmente viu.
        caminho = bfs(mapa, inicio, no.alvo)
        if caminho is None:
            raise RuntimeError('Não há caminho até o alvo no mapa construído')
        direcoes = caminho_para_direcoes(caminho)
        no.get_logger().info(f'Rota ótima no mapa construído: {len(direcoes)} movimentos')
        print(desenhar(marcar_caminho(mapa, caminho)))
        salvar_rota('parte2_rota.json', inicio, no.alvo, caminho, direcoes)

        # ---- Comprovação: comparar com o que a Parte 1 salvou ----
        comparar_com_parte1(no, mapa, caminho, direcoes)

        # ---- Executar a rota no robô ----
        # Ao fim do DFS o robô voltou ao ponto de partida (a pilha esvaziou
        # voltando pelo caminho) e o jogo não foi vencido. Então não precisa
        # de /reset: basta seguir a rota a partir de onde ele já está.
        no.get_logger().info('Executando a rota calculada no mapa construído...')
        if no.executar_rota(caminho):
            no.get_logger().info(f'ALVO ALCANÇADO em {len(direcoes)} movimentos '
                                 'usando só o mapa construído pelo robô!')
    except (RuntimeError, KeyboardInterrupt) as erro:
        no.get_logger().error(f'Exploração interrompida: {erro}')

    no.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
