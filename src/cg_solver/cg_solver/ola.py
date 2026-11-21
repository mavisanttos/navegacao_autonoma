"""Nó mínimo de teste: só mostra que o pacote cg_solver está funcionando.

Ele serve como "esqueleto" de qualquer nó ROS 2 em Python. Os nós das
partes 1 e 2 seguirão exatamente esta mesma estrutura.
"""
import rclpy
from rclpy.node import Node


class Ola(Node):
    def __init__(self):
        # Registra este programa na rede ROS 2 com o nome 'ola'
        super().__init__('ola')
        # get_logger().info(...) é o "print" do ROS: mostra hora e nome do nó
        self.get_logger().info('Olá! O pacote cg_solver está funcionando.')


def main(args=None):
    rclpy.init(args=args)   # 1. liga a comunicação do ROS 2
    no = Ola()              # 2. cria o nó
    no.destroy_node()       # 3. desliga o nó (este não tem mais nada a fazer)
    rclpy.shutdown()        # 4. encerra a comunicação do ROS 2


if __name__ == '__main__':
    main()
