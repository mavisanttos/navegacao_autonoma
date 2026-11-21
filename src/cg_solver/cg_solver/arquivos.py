"""Salvar e carregar resultados (mapas e rotas) na pasta resultados/.

Servem para a COMPROVAÇÃO da Parte 2: a Parte 1 salva o mapa real e a rota
ótima; a Parte 2 salva o mapa que construiu e a rota que calculou nele, e
depois compara as duas. Os arquivos ficam na pasta onde o comando foi
rodado (rode sempre da raiz do repositório).
"""
import csv
import json
import os

PASTA = 'resultados'


def caminho_arquivo(nome):
    os.makedirs(PASTA, exist_ok=True)
    return os.path.join(PASTA, nome)


def salvar_mapa_csv(nome, matriz):
    """Salva a matriz no mesmo formato dos mapas do jogo (CSV com vírgulas)."""
    arquivo = caminho_arquivo(nome)
    with open(arquivo, 'w', newline='') as f:
        csv.writer(f).writerows(matriz)
    return arquivo


def carregar_mapa_csv(nome):
    """Lê um mapa salvo. Devolve None se o arquivo não existir."""
    arquivo = os.path.join(PASTA, nome)
    if not os.path.exists(arquivo):
        return None
    with open(arquivo) as f:
        return [linha for linha in csv.reader(f)]


def salvar_rota(nome, inicio, alvo, caminho, direcoes):
    """Salva a rota em JSON (texto legível, fácil de comparar)."""
    dados = {
        'inicio': list(inicio),
        'alvo': list(alvo),
        'movimentos': len(direcoes),
        'direcoes': direcoes,
        'caminho': [list(p) for p in caminho],
    }
    arquivo = caminho_arquivo(nome)
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=1)
    return arquivo


def carregar_rota(nome):
    """Lê uma rota salva. Devolve None se o arquivo não existir."""
    arquivo = os.path.join(PASTA, nome)
    if not os.path.exists(arquivo):
        return None
    with open(arquivo) as f:
        return json.load(f)
