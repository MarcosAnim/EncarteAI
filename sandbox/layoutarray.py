import sys, json
from pathlib import Path
from encarteai.product_processor import XlsxLayoutProcessor
from xlsx_reader import XLSXToJSONReader as converter

BASE_PATH = Path(__file__).resolve().parent
XLSXDIR = BASE_PATH.parent / "temp_xlsx"
DESTINATION_BASE = BASE_PATH.parent / "output"

client = "dellys"
preset_name = "Aniversario"

# Inicando FTP connection
processor = XlsxLayoutProcessor(preset_name=preset_name, FTP_HOST="177.154.191.246", 
                                FTP_USER="dellysns@rgconsultorias.com.br", FTP_PASS="&FlgBe59XHqw", debug_level=3)

for file in XLSXDIR.iterdir():
    print(f" - Processando arquivo: {file.name}")

    if file.suffix == ".xlsx" and not file.name.startswith("~$"):
        with converter(str(file)) as reader:
            data = reader.read_xlsx()
            json_files = reader.convert_to_json_files()
            
            if json_files:
                first_sheet = list(json_files.keys())[0]
                sheet_count = len(json_files)
                json_data = reader.read_json_file(first_sheet)
                print(f" - {sheet_count} planilhas convertidas. Lendo a primeira: '{first_sheet}'")

                destination = DESTINATION_BASE / file.name.replace(".xlsx","")
                
                if sheet_count > 1:
                    destination = DESTINATION_BASE / file.name.replace(".xlsx","") / first_sheet

                destination.mkdir(parents=True, exist_ok=True)
                print(f" - Salvando em: {destination}")

                if isinstance(json_data, list) and len(json_data) > 0:
                    products = json.dumps(json_data, indent=2, ensure_ascii=False)
                    # Agora preciso fazer uma classe/função para corrigir os cabeçálhos json (chaves)
                    
                    for product in json_data:
                        # Valores obrigatórios
                        cod = product.get("COD")
                        descricao = product.get("DESC")
                        preco = product.get("TAG")

                        # Valores secundários
                        medida = product.get("MED")
                        selo = product.get("SELO")

                        layout1_path = processor.process_product(
                            prod_code = cod,
                            preco = "R$102,99",
                            descricao = descricao,
                            client = client,
                            tipo = medida,
                            selo = selo, # Selo ST
                            is_destaque = False,
                            force_recreate = True, # Força a recriação mesmo se o arquivo já existir
                            output_dir = destination
                        )

                        if layout1_path:
                            print(f"-> Layout gerado com sucesso: {Path(layout1_path).name}")
                        else:
                            print(f"-> Falha ao gerar layout: {Path(layout1_path).name}.")

                        
                        

        #processor = XlsxLayoutProcessor(preset_name=preset_name, FTP_HOST="177.154.191.246", FTP_USER="dellysns@rgconsultorias.com.br", FTP_PASS="&FlgBe59XHqw", debug_level=3)
        #layout_array = processor.process_layouts()
        #print(f" - Layout Array: {layout_array}")
        


