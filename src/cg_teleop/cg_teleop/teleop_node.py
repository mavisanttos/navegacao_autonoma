import rclpy
from rclpy.node import Node
from cg_interfaces.srv import MoveCmd, Reset

import sys
import termios
import tty

msg = """
Lendo o teclado e chamando o servico /move_command!
---------------------------
Mover o robo:
        w / seta cima
   a / seta esq.   d / seta dir.
        s / seta baixo

r : reinicia o mapa atual
n : carrega um novo mapa aleatorio

CTRL-C para sair
"""

class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')
        self.move_cli = self.create_client(MoveCmd, '/move_command')
        self.reset_cli = self.create_client(Reset, '/reset')
        
        while not self.move_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Move service not available, waiting again...')
        while not self.reset_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Reset service not available, waiting again...')
            
        self.move_req = MoveCmd.Request()

    def send_move_request(self, direction):
        self.move_req.direction = direction
        self.future = self.move_cli.call_async(self.move_req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def send_reset_request(self, is_random=False):
        reset_req = Reset.Request()
        reset_req.is_random = is_random
        self.future = self.reset_cli.call_async(reset_req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    # As setas nao mandam 1 caractere, mandam 3: ESC + '[' + letra
    # (ex.: seta para cima = '\x1b[A'). Se o primeiro for ESC,
    # lemos os outros 2 para montar a sequencia completa.
    if key == '\x1b':
        key += sys.stdin.read(2)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def main(args=None):
    rclpy.init(args=args)
    teleop_node = TeleopKeyboard()
    settings = termios.tcgetattr(sys.stdin)

    print(msg)
    while rclpy.ok():
        key = get_key(settings)
        direction = None
        if key in ['w', 'W', '\x1b[A']:  # w ou seta para cima
            direction = 'up'
        elif key in ['s', 'S', '\x1b[B']:  # s ou seta para baixo
            direction = 'down'
        elif key in ['a', 'A', '\x1b[D']:  # a ou seta para esquerda
            direction = 'left'
        elif key in ['d', 'D', '\x1b[C']:  # d ou seta para direita
            direction = 'right'
        elif key == 'r':
            response = teleop_node.send_reset_request(is_random=False)
            if response.success:
                teleop_node.get_logger().info(f'Successfully reset board to map: {response.loaded_map_name}')
            else:
                teleop_node.get_logger().info('Failed to reset the board')
        elif key == 'n':
            response = teleop_node.send_reset_request(is_random=True)
            if response.success:
                teleop_node.get_logger().info(f'Successfully loaded new random map: {response.loaded_map_name}')
            else:
                teleop_node.get_logger().info('Failed to load new random map')
        elif key == '\x03':  # ctrl-c
            break
        
        if direction:
            response = teleop_node.send_move_request(direction)
            if response.success:
                teleop_node.get_logger().info(f'Successfully moved {direction}')
            else:
                teleop_node.get_logger().info(f'Failed to move {direction}')

    teleop_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
