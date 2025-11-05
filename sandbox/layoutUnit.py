import sys
from pathlib import Path
from productGen.product_processor import XlsxLayoutProcessor

#Watchdog para testes rápidos
# python E:\Files\Trabalho\Fastlay\live_viewer.py E:\Files\Trabalho\Fastlay\CodeXlsxGen\xlsx_code\output\113395.png

sys.path.append(str(Path(__file__).resolve().parent))

def run_layout_examples():

    # --- Configurações Iniciais ---
    preset_name = "Aniversario"
    processor = None 

    try:
        # --- 1. Inicializa o Processador ---
        # debug_level=3 para ver todas as mensagens de debug
        processor = XlsxLayoutProcessor(preset_name=preset_name, FTP_HOST="177.154.191.246", FTP_USER="dellysns@rgconsultorias.com.br", FTP_PASS="&FlgBe59XHqw", debug_level=3)
        print(f"\n--- XlsxLayoutProcessor inicializado com preset: '{preset_name}' ---")

        print(f"\n--- Processando Exemplo 1: Produto Padrão (Dellys) ---")
        layout1_path = processor.process_product(
            prod_code=113395,
            preco="R$102,99",
            descricao="BATATA PRÉ FRITA CORTE FINO CONGELADO MCCAIN 2,5KG",
            client="dellys",
            tipo="KG",
            selo="ST", # Selo ST
            is_destaque=False,
            force_recreate=True, # Força a recriação mesmo se o arquivo já existir
            output_dir=Path("C:/Users/Marcos/Desktop/Carapaça")
        )
        
        if layout1_path:
            print(f"-> Layout 1 gerado com sucesso: {Path(layout1_path).name}")
        else:
            print(f"-> Falha ao gerar layout 1.")

    except FileNotFoundError as fnfe:
        print(f"\nERRO CRÍTICO: Um arquivo ou diretório essencial não foi encontrado: {fnfe}", file=sys.stderr)
        print(f"Verifique se o preset '{preset_name}' e a pasta 'fonts' existem e contêm os arquivos necessários.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERRO INESPERADO durante o processamento: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        # Garante que a conexão FTP seja fechada e o diretório temporário seja limpo
        if processor:
            processor.close_ftp_connection()
            processor.cleanup_temp_dir()
        print("\n--- Todos os exemplos de layout concluídos ---")

if __name__ == "__main__":
    import time
    while True:
        run_layout_examples()
        break