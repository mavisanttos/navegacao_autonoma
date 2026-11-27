"""Gera as imagens do README a partir dos arquivos da pasta resultados/.

Não usa ROS nem o jogo: só lê os mapas/rotas que as Partes 1 e 2 salvaram
e desenha com as MESMAS CORES do jogo (src/cg/cg/Maze.py).

Como rodar (da raiz do repositório, depois de rodar as Partes 1 e 2):
    python3 docs/gerar_imagens.py
As imagens são salvas em docs/img/.
"""
import json
import os
import sys
from collections import deque

from PIL import Image, ImageDraw, ImageFont

# Reaproveita as funções do nosso pacote (sem precisar do ROS)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'cg_solver'))
from cg_solver.bfs import vizinhos  # noqa: E402
from cg_solver.labirinto import encontrar  # noqa: E402
from cg_solver.arquivos import carregar_mapa_csv, carregar_rota  # noqa: E402

PASTA_SAIDA = os.path.join('docs', 'img')

# ---- Cores (as do jogo + algumas extras para explicar) ----
LIVRE = (220, 224, 232)        # OFFWHITE do jogo
PAREDE = (35, 38, 52)          # GREY do jogo
ROBO = (114, 135, 253)         # BLUE do jogo
ALVO = (230, 69, 83)           # RED do jogo
GRADE = (0, 0, 0)              # linhas pretas do jogo
DESCONHECIDO = (120, 126, 140)  # casa que o robô ainda não viu
ROTA = (247, 185, 40)          # rota ótima (BFS)
VISITADA = (178, 222, 180)     # casa onde o robô já passou (Parte 2)
PILHA = (250, 140, 60)         # "fio de lã" do DFS (pilha atual)
FUNDO = (255, 255, 255)
TEXTO = (30, 30, 30)


def fonte(tamanho, negrito=False):
    nome = 'DejaVuSans-Bold.ttf' if negrito else 'DejaVuSans.ttf'
    try:
        return ImageFont.truetype(os.path.join('/usr/share/fonts/truetype/dejavu', nome), tamanho)
    except OSError:
        return ImageFont.load_default()


def desenhar_grade(mapa, tam, cor_da_celula):
    """Desenha a grade: `cor_da_celula(linha, coluna)` decide a cor de cada casa."""
    linhas, colunas = len(mapa), len(mapa[0])
    img = Image.new('RGB', (colunas * tam + 1, linhas * tam + 1), GRADE)
    d = ImageDraw.Draw(img)
    for i in range(linhas):
        for j in range(colunas):
            x, y = j * tam, i * tam
            d.rectangle([x + 1, y + 1, x + tam - 1, y + tam - 1], fill=cor_da_celula(i, j))
    return img


def cor_padrao(mapa):
    """Cores iguais às do jogo."""
    tabela = {'b': PAREDE, 'f': LIVRE, 'r': ROBO, 't': ALVO, '?': DESCONHECIDO}
    return lambda i, j: tabela.get(mapa[i][j], LIVRE)


def com_titulo(img, titulo, subtitulo=None):
    """Coloca um título em cima da imagem."""
    altura = 34 if subtitulo is None else 54
    nova = Image.new('RGB', (img.width, img.height + altura), FUNDO)
    nova.paste(img, (0, altura))
    d = ImageDraw.Draw(nova)
    d.text((img.width // 2, 6), titulo, fill=TEXTO, font=fonte(17, True), anchor='mt')
    if subtitulo:
        d.text((img.width // 2, 30), subtitulo, fill=(90, 90, 90), font=fonte(13), anchor='mt')
    return nova


def lado_a_lado(imagens, espaco=24):
    largura = sum(i.width for i in imagens) + espaco * (len(imagens) - 1)
    altura = max(i.height for i in imagens)
    nova = Image.new('RGB', (largura, altura), FUNDO)
    x = 0
    for i in imagens:
        nova.paste(i, (x, 0))
        x += i.width + espaco
    return nova


def legenda(itens, largura):
    """Faixa de legenda: lista de (cor, texto)."""
    f = fonte(13)
    nova = Image.new('RGB', (largura, 30), FUNDO)
    d = ImageDraw.Draw(nova)
    x = 10
    for cor, texto in itens:
        d.rectangle([x, 8, x + 14, 22], fill=cor, outline=GRADE)
        d.text((x + 20, 15), texto, fill=TEXTO, font=f, anchor='lm')
        x += 20 + int(d.textlength(texto, font=f)) + 22
    return nova


def empilhar(*imagens):
    largura = max(i.width for i in imagens)
    nova = Image.new('RGB', (largura, sum(i.height for i in imagens)), FUNDO)
    y = 0
    for i in imagens:
        nova.paste(i, ((largura - i.width) // 2, y))
        y += i.height
    return nova


def salvar(img, nome):
    caminho = os.path.join(PASTA_SAIDA, nome)
    img.save(caminho, optimize=True)
    print('salvo', caminho)


# ---------------------------------------------------------------------------
# Parte 1
# ---------------------------------------------------------------------------
def distancias_bfs(mapa, inicio):
    """Distância (em passos) de `inicio` até cada casa: as "ondas" do BFS."""
    dist = {inicio: 0}
    fila = deque([inicio])
    while fila:
        atual = fila.popleft()
        for v in vizinhos(mapa, atual):
            if v not in dist:
                dist[v] = dist[atual] + 1
                fila.append(v)
    return dist


def imagem_ondas_bfs(mapa, caminho, tam=22):
    inicio, alvo = caminho[0], caminho[-1]
    dist = distancias_bfs(mapa, inicio)
    maior = max(dist.values())
    na_rota = set(caminho)

    def cor(i, j):
        if mapa[i][j] == 'b':
            return PAREDE
        if (i, j) == inicio:
            return ROBO
        if (i, j) == alvo:
            return ALVO
        # degradê: perto do robô = azul claro, longe = roxo
        t = dist.get((i, j), maior) / maior
        return (int(200 - 120 * t), int(230 - 190 * t), int(255 - 60 * t))

    img = desenhar_grade(mapa, tam, cor)
    d = ImageDraw.Draw(img)
    f = fonte(9)
    for (i, j), k in dist.items():
        if (i, j) in (inicio, alvo):
            continue
        branco = k / maior > 0.45
        d.text((j * tam + tam // 2, i * tam + tam // 2), str(k), font=f, anchor='mm',
               fill=(255, 255, 255) if branco else TEXTO)
    # contorno da rota ótima
    for (i, j) in na_rota:
        d.rectangle([j * tam + 1, i * tam + 1, j * tam + tam - 1, i * tam + tam - 1],
                    outline=ROTA, width=2)
    img = com_titulo(img, 'As "ondas" do BFS',
                     f'número = passos desde o robô · alvo alcançado na onda {dist[alvo]}')
    return empilhar(img, legenda([(ROBO, 'robô'), (ALVO, 'alvo'),
                                  ((200, 230, 255), 'perto'), ((80, 40, 195), 'longe'),
                                  (ROTA, 'contorno = rota ótima')], img.width))


def imagem_rota(mapa, caminho, titulo, subtitulo, tam=20):
    na_rota = set(caminho[1:-1])
    base = cor_padrao(mapa)

    def cor(i, j):
        return ROTA if (i, j) in na_rota else base(i, j)

    return com_titulo(desenhar_grade(mapa, tam, cor), titulo, subtitulo)


# ---------------------------------------------------------------------------
# Parte 2
# ---------------------------------------------------------------------------
def estado_exploracao(mapa_final, trajetoria, passo):
    """O que o robô sabia no `passo` k da exploração.

    Conhecidas = as 8 vizinhas (e a própria casa) de todas as casas por onde
    ele passou até ali. A pilha do DFS é reconstruída pelo trajeto: se ele
    voltou para a casa anterior da pilha, foi backtracking (desempilha);
    senão, avançou para uma casa nova (empilha).
    """
    conhecidas, visitadas, pilha = set(), set(), []
    for k, pos in enumerate(trajetoria[:passo + 1]):
        pos = tuple(pos)
        if len(pilha) >= 2 and pilha[-2] == pos:
            pilha.pop()            # backtracking
        elif k == 0 or pos != pilha[-1]:
            pilha.append(pos)      # avançou
        visitadas.add(pos)
        for dl in (-1, 0, 1):
            for dc in (-1, 0, 1):
                conhecidas.add((pos[0] + dl, pos[1] + dc))
    return conhecidas, visitadas, pilha


def quadro_exploracao(mapa_final, trajetoria, passo, alvo, tam):
    conhecidas, visitadas, pilha = estado_exploracao(mapa_final, trajetoria, passo)
    robo = tuple(trajetoria[passo])
    na_pilha = set(pilha)

    def cor(i, j):
        if (i, j) == robo:
            return ROBO
        if (i, j) not in conhecidas:
            return DESCONHECIDO
        c = mapa_final[i][j]
        if c == 'b':
            return PAREDE
        if (i, j) == alvo:
            return ALVO
        if (i, j) in na_pilha:
            return PILHA
        if (i, j) in visitadas:
            return VISITADA
        return LIVRE

    return desenhar_grade(mapa_final, tam, cor), len(visitadas)


def imagens_parte2(mapa_construido, exploracao):
    trajetoria = exploracao['trajetoria']
    alvo = tuple(exploracao['alvo'])
    total = len(trajetoria) - 1
    itens_legenda = [(ROBO, 'robô'), (PILHA, 'pilha do DFS ("fio")'),
                     (VISITADA, 'já visitada'), (LIVRE, 'vista, não visitada'),
                     (DESCONHECIDO, 'desconhecida'), (ALVO, 'alvo (visto)')]

    # --- 4 momentos lado a lado ---
    paineis = []
    for frac in (0.08, 0.30, 0.65, 1.0):
        passo = round(frac * total)
        img, n_vis = quadro_exploracao(mapa_construido, trajetoria, passo, alvo, tam=11)
        paineis.append(com_titulo(img, f'movimento {passo}/{total}', f'{n_vis} casas visitadas'))
    tira = lado_a_lado(paineis, espaco=14)
    salvar(empilhar(tira, legenda(itens_legenda, tira.width)), 'parte2_progresso.png')

    # --- GIF animado ---
    quadros = []
    for passo in list(range(0, total + 1, 6)) + [total] * 25:   # pausa no final
        img, n_vis = quadro_exploracao(mapa_construido, trajetoria, passo, alvo, tam=12)
        img = com_titulo(img, 'Parte 2: exploração com DFS',
                         f'movimento {passo}/{total} · {n_vis} casas visitadas')
        quadros.append(img.convert('P', palette=Image.ADAPTIVE, colors=32))
    caminho = os.path.join(PASTA_SAIDA, 'parte2_exploracao.gif')
    quadros[0].save(caminho, save_all=True, append_images=quadros[1:],
                    duration=55, loop=0, optimize=True)
    print('salvo', caminho)


# ---------------------------------------------------------------------------
# Sensores (diagrama 3x3)
# ---------------------------------------------------------------------------
def imagem_sensores(tam=96):
    nomes = [['up_left', 'up', 'up_right'],
             ['left', 'ROBÔ', 'right'],
             ['down_left', 'down', 'down_right']]
    exemplo = [['b', 'f', 'b'], ['f', 'r', 'b'], ['b', 'f', 'b']]
    cores = {'b': PAREDE, 'f': LIVRE, 'r': ROBO}
    img = Image.new('RGB', (3 * tam + 1, 3 * tam + 1), GRADE)
    d = ImageDraw.Draw(img)
    for i in range(3):
        for j in range(3):
            c = cores[exemplo[i][j]]
            d.rectangle([j * tam + 1, i * tam + 1, j * tam + tam - 1, i * tam + tam - 1], fill=c)
            claro = c != LIVRE
            d.text((j * tam + tam // 2, i * tam + tam // 2 - 9), nomes[i][j], anchor='mm',
                   font=fonte(13, True), fill=(255, 255, 255) if claro else TEXTO)
            if exemplo[i][j] != 'r':
                d.text((j * tam + tam // 2, i * tam + tam // 2 + 12), f"'{exemplo[i][j]}'",
                       anchor='mm', font=fonte(13), fill=(255, 255, 255) if claro else TEXTO)
    return com_titulo(img, 'O que o sensor informa', 'as 8 casas em volta do robô')


def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    mapa_real = carregar_mapa_csv('parte1_mapa.csv')
    mapa_construido = carregar_mapa_csv('parte2_mapa_construido.csv')
    rota1 = carregar_rota('parte1_rota.json')
    rota2 = carregar_rota('parte2_rota.json')
    with open(os.path.join('resultados', 'parte2_exploracao.json')) as f:
        exploracao = json.load(f)

    caminho1 = [tuple(p) for p in rota1['caminho']]
    caminho2 = [tuple(p) for p in rota2['caminho']]
    assert encontrar(mapa_real, 'r') == caminho1[0]

    # Parte 1
    salvar(imagem_rota(mapa_real, caminho1, 'Parte 1: rota ótima (BFS)',
                       f'{rota1["movimentos"]} movimentos'), 'parte1_rota.png')
    salvar(imagem_ondas_bfs(mapa_real, caminho1), 'bfs_ondas.png')

    # Parte 2
    salvar(imagem_sensores(), 'sensores.png')
    imagens_parte2(mapa_construido, exploracao)

    # Comparação final
    a = imagem_rota(mapa_real, caminho1, 'Mapa real (/get_map)',
                    f'Parte 1 · rota de {rota1["movimentos"]} movimentos', tam=14)
    b = imagem_rota(mapa_construido, caminho2, 'Mapa construído pelo robô',
                    f'Parte 2 · rota de {rota2["movimentos"]} movimentos', tam=14)
    lado = lado_a_lado([a, b], espaco=30)
    diferentes = sum(1 for i in range(len(mapa_real)) for j in range(len(mapa_real[0]))
                     if mapa_real[i][j] != mapa_construido[i][j])
    rodape = Image.new('RGB', (lado.width, 34), FUNDO)
    ImageDraw.Draw(rodape).text(
        (lado.width // 2, 17),
        f'{diferentes} casas diferentes · mesma rota: '
        f'{"SIM" if rota1["direcoes"] == rota2["direcoes"] else "NÃO"}',
        anchor='mm', font=fonte(15, True), fill=(20, 120, 40) if diferentes == 0 else ALVO)
    salvar(empilhar(lado, rodape), 'comparacao.png')


if __name__ == '__main__':
    main()
