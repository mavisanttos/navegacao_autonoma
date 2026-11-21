from setuptools import find_packages, setup

package_name = 'cg_solver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Maria Santos',
    maintainer_email='maria.santos@sou.inteli.edu.br',
    description='Solucao do desafio de navegacao autonoma: rota otima com BFS (parte 1) e mapeamento com DFS (parte 2)',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # nome_do_comando = pacote.arquivo:funcao
            # -> permite rodar: ros2 run cg_solver ola
            'ola = cg_solver.ola:main',
            'parte1 = cg_solver.parte1:main',
            'parte2 = cg_solver.parte2:main',
        ],
    },
)
