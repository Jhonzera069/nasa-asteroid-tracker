import datetime
import re
import pymysql
import requests

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "nasa_db"
DB_PORT = 3306

# Substitua pela sua chave obtida em https://api.nasa.gov/
API_KEY = "gnza5M8lMrLfxbr49OfiUWc54HYEJr4kyBYcGWDq"

hoje = datetime.date.today().strftime("%Y-%m-%d")


def tratar_com_regex(nome_raw):
    match_ano = re.search(r"\b(19|20)\d{2}\b", nome_raw)
    ano_descoberta = int(match_ano.group(0)) if match_ano else None
    nome_limpo = re.sub(r"[()]", "", nome_raw).strip()
    return nome_limpo, ano_descoberta


def sincronizar_nasa():
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={hoje}&end_date={hoje}&api_key={API_KEY}"
    print(f"🔄 Consultando API da NASA ({hoje})...")

    res = requests.get(url)

    if res.status_code != 200:
        print(f"❌ Erro ao acessar a API da NASA (Código {res.status_code})")
        print(f"Resposta da NASA: {res.text}")
        return

    dados = res.json()
    near_earth_objects = dados.get("near_earth_objects", {})

    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        autocommit=True,
    )
    cursor = conn.cursor()

    # 1. Garante que a tabela existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asteroides (
            id VARCHAR(50) PRIMARY KEY,
            nome VARCHAR(100),
            ano_descoberta INT,
            data_aproximacao DATE,
            diametro_max_km FLOAT,
            velocidade_km_h FLOAT,
            distancia_lunar FLOAT,
            perigoso TINYINT(1),
            data_coleta DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
    """)

    # 2. Garante a inclusão da coluna data_coleta caso a tabela seja de uma versão anterior
    try:
        cursor.execute("""
            ALTER TABLE asteroides 
            ADD COLUMN data_coleta DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
        """)
    except pymysql.err.OperationalError:
        pass  # A coluna já existe na tabela, ignora o erro

    query = """
        INSERT INTO asteroides (id, nome, ano_descoberta, data_aproximacao, diametro_max_km, velocidade_km_h, distancia_lunar, perigoso, data_coleta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            nome=VALUES(nome),
            ano_descoberta=VALUES(ano_descoberta),
            data_aproximacao=VALUES(data_aproximacao),
            diametro_max_km=VALUES(diametro_max_km),
            velocidade_km_h=VALUES(velocidade_km_h),
            distancia_lunar=VALUES(distancia_lunar),
            perigoso=VALUES(perigoso),
            data_coleta=NOW();
    """

    total_salvos = 0
    for dia, asteroides in near_earth_objects.items():
        for ast in asteroides:
            ast_id = ast["id"]
            nome_raw = ast["name"]
            nome_limpo, ano_descoberta = tratar_com_regex(nome_raw)
            diametro = float(ast["estimated_diameter"]["kilometers"]["estimated_diameter_max"])
            perigoso = int(ast["is_potentially_hazardous_asteroid"])

            aprox = ast["close_approach_data"][0]
            data_aprox = aprox["close_approach_date"]
            velocidade = float(aprox["relative_velocity"]["kilometers_per_hour"])
            distancia_ld = float(aprox["miss_distance"]["lunar"])

            cursor.execute(
                query,
                (
                    ast_id,
                    nome_limpo,
                    ano_descoberta,
                    data_aprox,
                    diametro,
                    velocidade,
                    distancia_ld,
                    perigoso,
                ),
            )
            total_salvos += 1

    conn.close()
    print(f"✅ Sucesso: {total_salvos} asteroides do dia ({hoje}) processados e salvos!")


if __name__ == "__main__":
    sincronizar_nasa()
