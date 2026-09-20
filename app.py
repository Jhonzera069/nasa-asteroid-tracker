import datetime
from flask import Flask, render_template
import pymysql

app = Flask(__name__)

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "nasa_db"
DB_PORT = 3306


def buscar_dados():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM asteroides ORDER BY data_aproximacao ASC, diametro_max_km DESC;"
    )
    dados = cursor.fetchall()
    conn.close()
    return dados


@app.route("/")
def index():
    asteroides = buscar_dados()

    total_ast = len(asteroides)
    total_perigosos = sum(1 for a in asteroides if a.get("perigoso") == 1)

    diametros = [
        a["diametro_max_km"]
        for a in asteroides
        if a.get("diametro_max_km") is not None
    ]
    maior_diametro = max(diametros) if diametros else 0

    velocidades = [
        a["velocidade_km_h"]
        for a in asteroides
        if a.get("velocidade_km_h") is not None
    ]
    media_vel = sum(velocidades) / len(velocidades) if velocidades else 0

    ultima_atualizacao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "index.html",
        asteroides=asteroides,
        total_ast=total_ast,
        total_perigosos=total_perigosos,
        maior_diametro=round(maior_diametro, 2),
        media_vel=round(media_vel, 0),
        ultima_atualizacao=ultima_atualizacao,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
