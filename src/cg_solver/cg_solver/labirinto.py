"""Funções utilitárias sobre o mapa (grid) do labirinto.

Este arquivo NÃO usa ROS: são só funções Python que recebem e devolvem
listas. Assim podemos reaproveitá-las tanto na Parte 1 quanto na Parte 2.

Legenda das células:
    'b' = parede (block)      'f' = livre (free)
    'r' = robô                't' = alvo (target)
    '?' = desconhecida (usada só na Parte 2, no mapa que o robô constrói)
"""


def remontar_matriz(lista_achatada, formato):
    """Transforma a lista "achatada" que vem do /get_map de volta em matriz.

    O jogo manda o mapa como uma lista única, linha após linha:
        [l0c0, l0c1, ..., l0c28, l1c0, l1c1, ...]
    e o formato (linhas, colunas). Basta "fatiar" a lista a cada
    `colunas` elementos. Exemplo com formato (2, 3):
        ['b','f','b', 'f','f','t']  ->  [['b','f','b'],
                                         ['f','f','t']]
    """
    linhas, colunas = formato
    if len(lista_achatada) != linhas * colunas:
        raise ValueError(
            f'Tamanho inconsistente: {len(lista_achatada)} células, '
            f'mas o formato diz {linhas}x{colunas}')

    matriz = []
    for i in range(linhas):
        inicio = i * colunas          # onde a linha i começa na lista
        fim = inicio + colunas        # onde ela termina
        matriz.append(list(lista_achatada[inicio:fim]))
    return matriz


def encontrar(matriz, simbolo):
    """Devolve a posição (linha, coluna) da primeira célula com `simbolo`.

    Usamos para achar o robô ('r') e o alvo ('t'). Devolve None se não achar.
    """
    for linha, conteudo_da_linha in enumerate(matriz):
        for coluna, celula in enumerate(conteudo_da_linha):
            if celula == simbolo:
                return (linha, coluna)
    return None


def dicionario_para_matriz(mapa_dict):
    """Converte o mapa da Parte 2 (dicionário) em matriz.

    Na Parte 2 o robô NÃO sabe o tamanho do labirinto, então vai anotando
    o que descobre num dicionário {(linha, coluna): conteúdo}, que cresce
    à vontade. No final, criamos uma matriz do tamanho necessário e
    preenchemos com '?' tudo o que o robô nunca viu.
    """
    num_linhas = max(linha for linha, _ in mapa_dict) + 1
    num_colunas = max(coluna for _, coluna in mapa_dict) + 1
    matriz = [['?'] * num_colunas for _ in range(num_linhas)]
    for (linha, coluna), conteudo in mapa_dict.items():
        matriz[linha][coluna] = conteudo
    return matriz


# Como cada célula aparece ao imprimir o mapa no terminal
DESENHO = {
    'b': '█',   # parede
    'f': ' ',   # livre
    'r': 'R',   # robô
    't': 'T',   # alvo
    '?': '·',   # desconhecida (Parte 2)
    '*': '•',   # caminho encontrado (usaremos no passo 5)
}


def desenhar(matriz):
    """Devolve um texto com o mapa desenhado, para imprimir no terminal.

    Cada célula vira 2 caracteres para o desenho não ficar "achatado".
    """
    linhas_texto = []
    for linha in matriz:
        linhas_texto.append(''.join(DESENHO.get(c, c) * 2 for c in linha))
    return '\n'.join(linhas_texto)
