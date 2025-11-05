# app.py
from flask import Flask, request, jsonify, send_file
from product_processor import XlsxLayoutProcessor
import traceback
import io

app = Flask(__name__)

@app.route("/gerar-layout", methods=["POST"])

def gerar_layout():
    processor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "erro", "mensagem": "Corpo da requisição deve ser um JSON válido."}), 400

        # --- Extração de dados com valores padrão ---
        prod_code = data.get("prod_code")
        preco = data.get("preco")
        descricao = data.get("descricao")
        preset = data.get("preset") # Tornando o preset dinâmico

        # Validar dados obrigatórios
        if not all([prod_code, preco, descricao, preset]):
            return jsonify({"status": "erro", "mensagem": "Os campos 'prod_code', 'preco', 'descricao' e 'preset' são obrigatórios."}), 400

        # --- Instanciação do Processador ---
        processor = XlsxLayoutProcessor(
            preset_name=preset,
            FTP_HOST="177.154.191.246",
            FTP_USER="dellysns@rgconsultorias.com.br",
            FTP_PASS="&FlgBe59XHqw",
            debug_level=1  # Reduzido para não poluir os logs da API
        )

        # --- Chamada ao novo método que retorna bytes ---
        image_bytes = processor.process_product_to_memory(
            prod_code=prod_code,
            preco=preco,
            descricao=descricao,
            client=data.get("client", "dellys"),
            tipo=data.get("tipo"),
            selo=data.get("selo"),
            is_destaque=data.get("destaque", False)
        )

        if image_bytes:
            # Pega o código do produto que foi usado para gerar a imagem
            prod_code = data.get("prod_code")
            
            # Cria o nome do arquivo que será sugerido ao cliente
            nome_sugerido = f"{prod_code}.png"

            return send_file(
                io.BytesIO(image_bytes),
                mimetype='image/png',
                as_attachment=True,  # Mude para 'True' para sugerir o download
                download_name=nome_sugerido # <<< A MÁGICA ACONTECE AQUI
            )
        else:
            # --- Falha na geração ---
            # Pode ser que a imagem do produto não foi encontrada ou outro erro interno.
            return jsonify({"status": "falha", "mensagem": f"Não foi possível gerar o layout para o produto {prod_code}"}), 404

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        # --- Limpeza Final ---
        if processor:
            processor.close_ftp_connection()
            processor.cleanup_temp_dir()

if __name__ == "__main__":
    # Use 'debug=True' apenas para desenvolvimento local
    app.run(host="0.0.0.0", port=5000, debug=False)