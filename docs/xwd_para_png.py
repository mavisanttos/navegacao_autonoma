"""Converte uma captura de janela feita com o `xwd` em PNG.

Usado para tirar os prints da janela do jogo que aparecem no README:
    xwd -name "Culling Games" -silent > captura.xwd
    python3 docs/xwd_para_png.py captura.xwd docs/img/jogo_inicio.png

Detalhe: dependendo da captura, cada pixel vem com 3 bytes (BGR) ou 4
bytes (BGRX). O script testa os dois e fica com o que tem MENOS cores
distintas (o jogo usa poucas cores; a leitura errada vira "ruído").
"""
import struct, sys
from PIL import Image
d = open(sys.argv[1], 'rb').read()
h = struct.unpack('>25I', d[:100])
larg, alt, bpl = h[4], h[5], h[12]
ini = h[0] + h[19] * 12
melhor = None
for modo in ('BGR', 'BGRX'):
    try:
        img = Image.frombuffer('RGB', (larg, alt), d[ini:], 'raw', modo, bpl, 1)
    except ValueError:
        continue
    n = len(img.crop((20, 60, larg - 20, alt - 20)).getcolors(1 << 22))
    if melhor is None or n < melhor[0]:
        melhor = (n, modo, img)
melhor[2].save(sys.argv[2]); print(sys.argv[2].split('/')[-1], melhor[1], 'cores:', melhor[0])
