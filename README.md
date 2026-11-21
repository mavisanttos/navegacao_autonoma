# Navegação Autônoma em Labirinto (ROS 2)

Solução do **Desafio de Navegação Autônoma**: um robô dentro de um labirinto precisa chegar até um alvo usando algoritmos de grafos, no simulador **Culling Games** ([rmnicola/culling_games](https://github.com/rmnicola/culling_games)).

O desafio tem duas partes:

| | Parte 1: navegação **com** mapa | Parte 2: mapeamento **sem** mapa |
|---|---|---|
| O que o robô sabe | O mapa completo do labirinto | Nada. Só o que os sensores mostram ao redor dele |
| O que ele faz | Calcula a rota mais curta e vai até o alvo | Explora o labirinto inteiro, desenha o próprio mapa e depois calcula a rota |
| Algoritmo | **BFS** (busca em largura) | **DFS** (busca em profundidade) para explorar + **BFS** para a rota |

---

## Resultados (mapa `1.csv`)

| | Parte 1 | Parte 2 |
|---|---|---|
| Rota mais curta até o alvo | **102 movimentos** | **102 movimentos** ✅ |
| Movimentos gastos explorando | — | 780 |
| Células do mapa construído diferentes do mapa real | — | **0 de 841** |
| Pisou no alvo durante a exploração? | — | Não |

O mapa que o robô construiu sozinho na Parte 2 é **idêntico** ao mapa real. A rota calculada nele tem **o mesmo tamanho e as mesmas direções** da rota da Parte 1. Os arquivos que comprovam isso estão na pasta [`resultados/`](resultados/).

A rota mais curta nos outros mapas (Parte 1): `2.csv` = 102 · `3.csv` = 192 · `4.csv` = 114 · `5.csv` = 204 · `6.csv` = 110 · `7.csv` = 96 · `8.csv` = 164 · `9.csv` = 190 · `10.csv` = 48.

---

## Como o repositório está organizado

```
navegacao_autonoma/
├── src/
│   ├── cg/              ← o jogo (simulador), do professor
│   ├── cg_interfaces/   ← os "formulários" de comunicação com o jogo, do professor
│   ├── cg_teleop/       ← controle pelo teclado, do professor (com um ajuste, ver abaixo)
│   └── cg_solver/       ← ★ A NOSSA SOLUÇÃO
│       └── cg_solver/
│           ├── parte1.py     → programa da Parte 1
│           ├── parte2.py     → programa da Parte 2
│           ├── bfs.py        → algoritmo BFS (usado pelas duas partes)
│           ├── labirinto.py  → funções para montar e desenhar o mapa
│           ├── arquivos.py   → salva e lê mapas e rotas na pasta resultados/
│           └── ola.py        → programa de teste ("olá mundo")
├── resultados/          ← mapas e rotas salvos (a comprovação da Parte 2)
├── lobotomy_kaisen/     ← imagens usadas pelo jogo, do professor
└── README.md
```

---

## Como rodar

### 1. O que precisa estar instalado

- Ubuntu 24.04 com **ROS 2 Jazzy**
- `colcon` (ferramenta que monta os pacotes)
- `pygame` (biblioteca gráfica que o jogo usa):
  ```bash
  sudo apt install python3-pygame
  ```

### 2. Baixar e montar (compilar) o projeto

```bash
git clone https://github.com/mavisanttos/navegacao_autonoma.git
cd navegacao_autonoma
colcon build
source install/setup.bash
```

> **Importante:** todo terminal novo precisa do `source install/setup.bash`, que é o que "apresenta" os nossos pacotes ao terminal. Rode os comandos sempre **da pasta raiz do repositório**, porque é nela que a pasta `resultados/` é criada.

### 3. Abrir o jogo (Terminal 1)

```bash
source install/setup.bash
ros2 run cg maze -- --map 1.csv
```

Troque `1.csv` por outro mapa (de `1.csv` a `10.csv`) ou use `-- --generate` para gerar um labirinto aleatório.

### 4. Parte 1 (Terminal 2)

```bash
source install/setup.bash
ros2 run cg_solver parte1
```

O programa mostra a rota no terminal (marcada com `••`), salva o mapa e a rota em `resultados/` e leva o robô até o alvo.

### 5. Parte 2 (Terminal 2)

Para começar do zero, reinicie o jogo antes. Depois de uma vitória, o jogo recusa novos movimentos.

```bash
ros2 service call /reset cg_interfaces/srv/Reset "{is_random: false}"
ros2 run cg_solver parte2
```

O robô explora o labirinto todo, desenha o mapa que construiu, calcula a rota, **compara com a Parte 1** e vai até o alvo. Ao final aparece:

```
=========== COMPROVAÇÃO: Parte 1 x Parte 2 ===========
Mapa: 0 células diferentes do mapa real (29x29 = 841 células)
Rota Parte 1 (mapa real):       102 movimentos
Rota Parte 2 (mapa construído): 102 movimentos
MESMO TAMANHO: o mapa construído é suficiente para reproduzir a rota ótima da Parte 1. ✅
```

> Para a comparação automática funcionar, rode a Parte 1 e a Parte 2 **no mesmo mapa**.

### (Opcional) Controlar o robô pelo teclado

```bash
ros2 run cg_teleop teleop_keyboard
```
Use **W A S D** ou as **setas**. A tecla `r` reinicia o mapa e `n` carrega um mapa aleatório.

---

## Como funciona

### Como o programa conversa com o jogo

O jogo e a nossa solução são programas separados (no ROS, cada um é um **nó**) que trocam mensagens. Existem dois jeitos de conversar:

- **Serviço:** funciona como fazer um pedido no balcão. Você pede, o jogo responde, uma vez.
- **Tópico:** funciona como ouvir uma rádio. O jogo transmite o tempo todo e quem quiser escuta.

| Nome | Tipo | Para que usamos | Parte |
|---|---|---|---|
| `/get_map` | serviço | Pedir o mapa completo | Só na 1 |
| `/move_command` | serviço | Mover o robô 1 casa. A resposta diz se deu certo e onde o robô está | 1 e 2 |
| `/reset` | serviço | Reiniciar o mapa | 1 |
| `/culling_games/robot_sensors` | tópico | Ver o que há nas 8 casas em volta do robô (100 vezes por segundo) | Só na 2 |

### O labirinto como um grafo

O mapa é uma grade de casas: `b` = parede, `f` = livre, `r` = robô, `t` = alvo. Para os algoritmos, ele vira um **grafo**: cada casa livre é um **ponto** (vértice), e duas casas vizinhas (em cima, embaixo, à esquerda ou à direita) são ligadas por uma **linha** (aresta). Todo passo custa o mesmo: 1 movimento.

### Parte 1: BFS, a rota mais curta

1. Pede o mapa ao jogo (`/get_map`). Ele chega "achatado", como uma lista única com todas as casas, e é remontado em linhas e colunas.
2. Roda o **BFS (busca em largura)**. Ele explora o labirinto **em ondas**, como uma pedra jogada num lago: primeiro todas as casas a 1 passo do robô, depois todas a 2 passos, depois a 3, e assim por diante. A primeira vez que a onda encosta no alvo é, garantidamente, pelo **menor caminho possível**.
3. Transforma o caminho em comandos (`up`, `down`, `left`, `right`) e manda o robô andar, um passo por vez. A cada passo, confere se o robô está mesmo onde deveria.

### Parte 2: DFS, explorar e mapear

Aqui o robô **não pode** pedir o mapa. Ele só tem os sensores e a própria posição, que vem na resposta de cada movimento.

1. **Onde estou?** O robô "esbarra" numa parede que o sensor já mostrou. O jogo recusa o movimento, mas a resposta traz a posição atual. Assim ele descobre onde está sem gastar nenhum passo.
2. **Explorar com DFS (busca em profundidade):** funciona como explorar uma caverna com um novelo de lã. O robô segue por um corredor enquanto houver casa nova para visitar. Quando chega num beco sem saída, **volta pelo mesmo caminho** (*backtracking*) até o último ponto com passagem nova. Em cada casa, anota no seu mapa o que os sensores mostram.
3. **Cuidados:**
   - o robô **nunca pisa no alvo**, só o anota quando o sensor o vê (pisar nele encerraria o jogo);
   - depois de cada passo, espera uma **leitura nova** do sensor antes de anotar, para não usar a "foto" de antes do movimento.
4. Quando o robô volta ao início sem nada novo para ver, o labirinto inteiro foi mapeado. Em seguida ele roda **o mesmo BFS da Parte 1** no mapa que construiu (casas nunca vistas contam como parede), compara com o resultado da Parte 1 e vai até o alvo.

### Por que DFS para explorar e BFS para a rota?

- **DFS** é ótimo para um robô de verdade explorar: o próximo lugar a visitar está sempre **ao lado** de onde ele está, seja indo em frente ou voltando. Mas ele **não garante** o caminho mais curto.
- **BFS** garante o caminho mais curto, mas visita as casas "em ondas", espalhadas pelo labirinto. Um robô físico teria que atravessar o mapa inteiro a cada casa nova.
- Por isso: **DFS para mapear, BFS para planejar a rota.**

---

## O que veio pronto e o que foi feito

- **Do professor (sem alterações):** os pacotes `cg` (jogo), `cg_interfaces` (comunicação) e a pasta `lobotomy_kaisen` (imagens), copiados de [rmnicola/culling_games](https://github.com/rmnicola/culling_games).
- **Do professor, com um ajuste:** `cg_teleop`. As **setas do teclado não funcionavam** (o programa lia só 1 dos 3 caracteres que cada seta envia) e o menu mostrava teclas que não eram as usadas. As setas foram consertadas, o controle ficou com W A S D e o menu foi traduzido. Esse pacote é só um controle de teste e não faz parte da solução.
- **Feito neste trabalho:** todo o pacote `cg_solver` e a pasta `resultados/`.

## Créditos e licença

Simulador Culling Games © 2024 Rodrigo Nicola, licença MIT (ver [`LICENSE-culling_games`](LICENSE-culling_games)). O pacote `cg_solver` também usa a licença MIT.
