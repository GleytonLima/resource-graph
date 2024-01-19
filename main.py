import json

import networkx as nx
import pandas as pd
from bs4 import BeautifulSoup
from pyvis.network import Network


def adicionar_titulo_html(file_path, title, h1_text):
    with open(file_path, 'r+') as f:
        soup = BeautifulSoup(f, 'html.parser')

        # Adiciona a meta tag para o conjunto de caracteres UTF-8
        meta_tag = soup.new_tag("meta", charset="UTF-8")
        soup.head.insert(0, meta_tag)

        # Adiciona uma tag de estilo para definir a margem do corpo
        style_tag = soup.new_tag("style")
        style_tag.string = "body { margin: 50px; }"
        soup.head.append(style_tag)

        # Verifica se a tag <title> existe
        if soup.title:
            # Modifica o título existente
            soup.title.string = title
        else:
            # Cria uma nova tag <title> e adiciona ao objeto soup
            title_tag = soup.new_tag("title")
            title_tag.string = title
            soup.head.append(title_tag)

        # Cria uma nova tag <h1> e adiciona ao corpo da página
        h1_tag = soup.new_tag("h2")
        h1_tag.string = h1_text
        soup.body.insert(0, h1_tag)

        # Sobrescreve o arquivo HTML com o novo título e o novo elemento h1
        f.seek(0)
        f.write(str(soup))
        f.truncate()


def criar_grafo(file_path):
    # Leitura do arquivo CSV
    df = pd.read_csv(file_path)

    # Criação do grafo direcionado
    G = nx.MultiDiGraph()  # Alterado para MultiDiGraph

    # Adiciona arestas ao grafo
    for index, row in df.iterrows():
        G.add_edge(row['resource_id_from'], row['resource_id_to'], integration_type=row['integration_type'],
                   metadata=row['metadata'])
        # Adiciona metadata como um atributo do nó
        G.nodes[row['resource_id_from']]['metadata'] = row['metadata']
        G.nodes[row['resource_id_to']]['metadata'] = row['metadata']

    return G


def visualizar_grafo(G, name="grafo.html", impacted_nodes=set(), impacted_color="red", altered_resource=None,
                     altered_color="green", enable_custom_icons=True):
    # Criação da rede Pyvis a partir do grafo NetworkX
    net = Network(notebook=False, directed=True, filter_menu=True, select_menu=True, neighborhood_highlight=True)

    # Dicionário de ícones
    icon_dict = {
        "ecs": "icons/ecs.png",
        "lambda": "icons/lambda.png",
        "dynamodb": "icons/dynamodb.png",
        "s3": "icons/s3.png",
        "sns": "icons/sns.png",
        "sqs": "icons/sqs.png",
        "api-gateway": "icons/api-gateway.png",
        "kafka": "icons/kafka.png",
        "secrets-manager": "icons/secrets-manager.png",
        "step-functions": "icons/step-functions.png",
        "mainframe": "icons/mainframe.png",
        "default": "icons/default.png",
    }

    # Adiciona nós ao grafo Pyvis
    for node in G.nodes():
        if node == altered_resource:
            color = altered_color
        elif node in impacted_nodes:
            color = impacted_color
        else:
            color = "#7678e8"

        if enable_custom_icons:
            # Verifica se o nome do nó contém uma das chaves do dicionário de ícones
            icon_url = icon_dict["default"]
            for key in icon_dict:
                if key in node:
                    icon_url = icon_dict[key]
                    break
            net.add_node(node, color=color, shape='image', image=icon_url)
        else:
            # Adiciona o nó ao grafo
            net.add_node(node, color=color)

    # Adiciona arestas ao grafo Pyvis com metadados como título
    for edge in G.edges(keys=True):
        net.add_edge(edge[0], edge[1], title=G.edges[edge]['metadata'], label=G.edges[edge]['integration_type'])

    # Configurações de física
    options = {
        'physics': {
            'barnesHut': {
                'centralGravity': 0.1,  # Reduzir para espaçar os nós
                'springLength': 300,  # Aumentar para espaçar os nós
            },
            'minVelocity': 0.75,
            'solver': 'barnesHut'
        }
    }
    net.set_options(json.dumps(options))

    # Visualização do grafo
    net.show(name, notebook=False)

    # Adiciona o código CSS, HTML e JavaScript ao arquivo HTML gerado
    with open('custom-content.html', 'r') as script_file:
        script_content = script_file.read()

    with open(name, 'a') as f:
        f.write(script_content)

def encontrar_recursos_impactados_primeiro_nivel(G, recurso_alterado):
    recursos_impactados = {recurso_alterado}
    if G.has_node(recurso_alterado):
        for predecessor in G.predecessors(recurso_alterado):
            recursos_impactados.add(predecessor)
        for successor in G.successors(recurso_alterado):
            recursos_impactados.add(successor)
    return recursos_impactados


def encontrar_recursos_impactados(G, recurso_alterado):
    recursos_impactados = set()

    # Verifica se o recurso alterado existe no grafo
    if G.has_node(recurso_alterado):
        # Adiciona os predecessores imediatos do recurso alterado
        for predecessor in G.predecessors(recurso_alterado):
            recursos_impactados.add(predecessor)

        # Realiza uma busca em profundidade a partir do recurso alterado para obter todos os sucessores
        for recurso in nx.dfs_preorder_nodes(G, source=recurso_alterado):
            recursos_impactados.add(recurso)

    return recursos_impactados


def run():
    file_path = 'recursos.csv'

    # Criar o grafo a partir do arquivo CSV
    G = criar_grafo(file_path)

    # Visualizar o grafo
    visualizar_grafo(G, name="grafo.html")
    adicionar_titulo_html("grafo.html", "grafo recursos", "Grafo Recursos")

    # Exemplo de uso: Encontrar recursos impactados pela alteração em um recurso específico
    recurso_alterado = 'book-ecs-fargate'
    recursos_impactados = encontrar_recursos_impactados(G, recurso_alterado)

    print(f"Recursos impactados no primeiro nível pela alteração em {recurso_alterado}: {recursos_impactados}")

    # Criar e visualizar subgrafo dos recursos impactados
    G_sub = G.subgraph(recursos_impactados)
    visualizar_grafo(G_sub, name="subgrafo.html", impacted_nodes=recursos_impactados, impacted_color="lightcoral",
                     altered_resource=recurso_alterado, altered_color="gray")

    adicionar_titulo_html("subgrafo.html", "grafo recursos impactados",
                          f'Recursos Impactados por alteracao em {recurso_alterado}')


if __name__ == "__main__":
    run()
