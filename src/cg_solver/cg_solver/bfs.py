"""BFS (Busca em Largura) para achar o caminho MAIS CURTO no labirinto.

O labirinto visto como GRAFO:
    - VÉRTICE (nó do grafo) = cada célula em que o robô pode ficar
      (tudo que não é parede 'b' nem desconhecido '?').
    - ARESTA = ligação entre duas células vizinhas em 4 direções
      (cima, baixo, esquerda, direita). Não há movimento na diagonal.
    - Todas as arestas têm o MESMO custo (1 passo).

Por que o BFS acha o caminho mais curto?
    Ele explora em "ondas": primeiro todas as células a 1 passo do início,
    depois todas a 2 passos, depois a 3... (como uma pedra jogada num lago).
    A fila (FIFO) garante essa ordem. Então, a PRIMEIRA vez que a onda
    alcança o alvo, foi pelo menor número de passos possível.
    Isso vale porque todo passo custa igual (se os custos fossem diferentes,
    precisaríamos de Dijkstra).

Este arquivo não usa ROS: é usado igualzinho na Parte 1 e na Parte 2.
"""
from collections import deque

# As 4 direções de movimento: nome -> (variação na linha, variação na coluna)
# 'up' diminui a linha, 'down' aumenta, 'left' diminui a coluna, 'right' aumenta
DIRECOES = {
    'up': (-1, 0),
    'down': (1, 0),
    'left': (0, -1),
    'right': (0, 1),
}

# Células em que o robô NÃO pode entrar.
# '?' (desconhecido) é tratado como parede: na Parte 2, só usamos o que
# o robô realmente viu.
BLOQUEADAS = {'b', '?'}


def pode_andar(mapa, linha, coluna):
    """True se (linha, coluna) está dentro do mapa e não é parede/desconhecido."""
    dentro = 0 <= linha < len(mapa) and 0 <= coluna < len(mapa[0])
    return dentro and mapa[linha][coluna] not in BLOQUEADAS


def vizinhos(mapa, posicao):
    """Devolve as células vizinhas (arestas do grafo) em que dá para andar."""
    linha, coluna = posicao
    resultado = []
    for dl, dc in DIRECOES.values():
        nl, nc = linha + dl, coluna + dc
        if pode_andar(mapa, nl, nc):
            resultado.append((nl, nc))
    return resultado


def bfs(mapa, inicio, alvo):
    """Acha o caminho mais curto de `inicio` até `alvo`.

    Devolve a lista de posições [inicio, ..., alvo],
    ou None se não existir caminho.
    """
    # Fila de células "descobertas mas ainda não exploradas".
    # FIFO: a primeira que entra é a primeira que sai (fila de banco).
    fila = deque([inicio])

    # veio_de[celula] = de qual célula chegamos nela.
    # Serve para duas coisas:
    #   1) marcar quem já foi visitado (não visitar duas vezes);
    #   2) no final, reconstruir o caminho de trás para frente.
    veio_de = {inicio: None}

    while fila:
        atual = fila.popleft()          # tira o PRIMEIRO da fila

        if atual == alvo:               # chegou! monta o caminho e devolve
            return reconstruir_caminho(veio_de, alvo)

        for vizinho in vizinhos(mapa, atual):
            if vizinho not in veio_de:  # ainda não visitado
                veio_de[vizinho] = atual
                fila.append(vizinho)    # entra no FIM da fila

    return None  # a fila esvaziou sem achar o alvo: não há caminho


def reconstruir_caminho(veio_de, alvo):
    """Volta do alvo até o início seguindo as "setas" de veio_de.

    Como uma trilha de migalhas: do alvo, pergunto "vim de onde?",
    e repito até chegar no início (que veio de None). Depois inverto.
    """
    caminho = []
    atual = alvo
    while atual is not None:
        caminho.append(atual)
        atual = veio_de[atual]
    caminho.reverse()
    return caminho


def caminho_para_direcoes(caminho):
    """Converte a lista de posições em lista de comandos ('up', 'down'...).

    Para cada par de células seguidas, olha a diferença entre elas:
        (5, 3) -> (6, 3): linha +1, coluna 0  -> 'down'
        (6, 3) -> (6, 4): linha 0,  coluna +1 -> 'right'
    """
    # "Dicionário ao contrário": (variação) -> nome da direção
    nome_da_variacao = {variacao: nome for nome, variacao in DIRECOES.items()}

    direcoes = []
    for (l1, c1), (l2, c2) in zip(caminho, caminho[1:]):
        direcoes.append(nome_da_variacao[(l2 - l1, c2 - c1)])
    return direcoes


def marcar_caminho(mapa, caminho):
    """Devolve uma CÓPIA do mapa com o caminho marcado com '*' (para desenhar).

    O início ('r') e o alvo ('t') continuam aparecendo com sua letra.
    """
    copia = [list(linha) for linha in mapa]
    for linha, coluna in caminho[1:-1]:
        copia[linha][coluna] = '*'
    return copia
